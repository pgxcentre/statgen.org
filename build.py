#!/usr/bin/env python3
"""Tool to build the HTML source for the statgen.org website.

The following dependencies are required:

    * yaml (to parse the website configuration page)
    * bibtexparser (to parse the BibTeX files for Dubé's publications)
    * markdown (to convert Markdown files to the HTML format)
    * jinja2 (to help with the HTML templating)

To execute the script, perform the following command (where `site.yaml` is the
website's YAML configuration file):

    python3 build.py site.yaml

Note
----
    This script only works on Python version 3.3 and higher.

"""


import os
import re
import sys
import shutil
import argparse
from glob import glob

import yaml
import bibtexparser
from markdown import Markdown
from jinja2 import Environment, FileSystemLoader


class Site(object):
    LANGUAGES = ("en", "fr")

    def __init__(self, site_root="/", static_dir="static", source_dir="source",
                 build_dir="build", template_dir="templates", bibtex_dir=None):
        """Initiate a new website.

        Args:
            site_root (str): the website root
            static_dir (str): the directory that will contain the static files.
            source_dir (str): the name of the directory containing the source.
            build_dir (str): the name of the build directory.
            template_dir (str): the name of the templates directory.
            bibtex_dir (str): the name of the BibTeX directory.

        """
        # The directories
        self.site_root = site_root.rstrip("/")
        self.static_dir = static_dir
        self.source_dir = source_dir
        self.build_dir = build_dir
        self.template_dir = template_dir
        self.bibtex_dir = bibtex_dir

        # Overwrite the build directory.
        if os.path.isdir(self.build_dir):
            r = input("Delete entire directory '{}'? ".format(self.build_dir))
            if r.upper() not in {"Y", "YES"}:
                print("Stopped")
                sys.exit(0)
            shutil.rmtree(self.build_dir)
        os.mkdir(self.build_dir)

        # Creating the language subdirectories
        for language in self.LANGUAGES:
            os.mkdir(os.path.join(self.build_dir, language))

        # Copying the directory inside the template directory
        for path in os.listdir(self.template_dir):
            full_path = os.path.join(self.template_dir, path)
            if os.path.isdir(full_path):
                shutil.copytree(
                    full_path,
                    os.path.join(self.build_dir, self.static_dir, path),
                )

        # Prepare the jinja2 environment for the templates
        self.template_env = Environment(
            loader=FileSystemLoader(self.template_dir)
        )

        # Prepare the jinja2 environment for the Markdown source files
        self.markdown_env = Environment(
            loader=FileSystemLoader(self.source_dir),
        )

        # The pages
        self.pages = []
        self.navigation = []

    def add_page(self, title, file_prefix, **kwargs):
        """Add a page to the website.

        Args:
            title (dict): the title of the page.
            file_prefix (str): the prefix of the markdown file.

        Note
        ----
            Site should be bilingual, hence the file_prefix is only the prefix,
            and both `_en.mkd` and `_fr.mkd` will be appended to it to get the
            input markdown file. The generated file will be put in both `en`
            and `fr` directory of the build directory, respectively.

        """
        # The page information
        page_info = dict(
            title=title,
            curr_url=file_prefix + ".html",
            filename=os.path.join(self.build_dir, "{language}",
                                  file_prefix + ".html"),
            template=self.template_env.get_template(
                kwargs.get("template", "default.html"),
            ),
        )

        # Reading the page content (both languages)
        for language in self.LANGUAGES:
            # Getting the markdown template
            content = self.markdown_env.get_template(
                file_prefix + "_{}.mkd".format(language),
            )

            # Rendering the markdown template
            content = content.render(
                static_url=self.site_root + "/" + self.static_dir,
                lang_root=self.site_root + "/" + language,
            )

            # Converting to HTML
            page_info["content_" + language] = Markdown().convert(content)

        # If publications, we need something fancy
        if kwargs.get("bibtex", False) and self.bibtex_dir:
            page_info["bibtex"] = self.parse_bibtex()

        # Adding to the web site
        self.pages.append(page_info)

        # Adding the navigation if required
        is_nav = kwargs.get("navigation", False)
        if is_nav:
            self.navigation.append(dict(
                title=title,
                url=file_prefix + ".html",
            ))

    def discover(self, directory, title, **kwargs):
        """Automatically discover Markdown files and add them.

        Args:
            directory (str): the name of the directory to find Markdown files.
            title (dict): the title of the pages to add.

        """
        # Finding the files
        filenames = os.path.join(self.source_dir, directory, "*_en.mkd")
        for filename in glob(filenames):
            # Creating the page information
            file_prefix = directory + "/" + os.path.basename(filename).replace(
                "_en.mkd",
                "",
            )
            page_info = dict(
                title=title,
                curr_url=file_prefix + ".html",
                filename=os.path.join(self.build_dir, "{language}",
                                      file_prefix + ".html"),
                template=self.template_env.get_template(
                    kwargs.get("template", "default.html"),
                ),
            )

            for language in self.LANGUAGES:
                # Getting the Markdown template
                content = self.markdown_env.get_template(
                    file_prefix + "_{}.mkd".format(language),
                )

                # Rendering the markdown template
                content = content.render(
                    static_url=self.site_root + "/" + self.static_dir,
                    lang_root=self.site_root + "/" + language,
                )

                # Converting to HTML
                page_info["content_" + language] = Markdown().convert(content)

            # Adding the page
            self.pages.append(page_info)

    def generate(self):
        """Generates the website."""
        for page in self.pages:
            template = page["template"]
            for language in self.LANGUAGES:
                content = template.render(
                    language=language,
                    title=page["title"][language],
                    content=page["content_" + language],
                    static_url=self.site_root + "/" + self.static_dir,
                    site_root=self.site_root,
                    lang_root=self.site_root + "/" + language,
                    navigation=self.navigation,
                    bibtex=page.get("bibtex", None),
                    curr_url=page["curr_url"],
                )

                # Saving the content
                fn = page["filename"].format(language=language)
                if not os.path.isdir(os.path.dirname(fn)):
                    os.makedirs(os.path.dirname(fn))
                with open(fn, "w") as o_file:
                    o_file.write(content)

    def parse_bibtex(self):
        """Parses all *.bib files inside a directory.

        Returns:
            dict: a dictionary containing years as keys, and
                bibtexparser.bibdatabase.BibDatabase as values.

        Warning
        -------
            The names of the file should always be `YEAR.bib`.

        """
        bib = []

        # The regular expression for the "and" between the authors
        and_re = re.compile(r"\s+and\s+")
        dash_re = re.compile(r"-+")

        # Getting the BibTeX files
        for fn in glob(os.path.join(self.bibtex_dir, "*.bib")):
            year = int(os.path.basename(fn).split(".")[0])
            pubs = []
            with open(fn, "r") as i_file:
                pubs = [
                    entries for entries in bibtexparser.load(i_file).entries
                ]

            # Some formatting
            for i in range(len(pubs)):
                # Adding a dot to the title, if required
                if not pubs[i]["title"].endswith("."):
                    pubs[i]["title"] += "."

                # Adding a dot to the authors, if required
                if not pubs[i]["author"].endswith("."):
                    pubs[i]["author"] += "."

                # Replacing the in between author "and"
                authors = and_re.split(pubs[i]["author"])
                authors = ", ".join(authors[:-1]) + " and " + authors[-1]
                pubs[i]["author"] = authors

                # Replacing '--' with '-'
                pubs[i]["pages"] = dash_re.sub("-", pubs[i].get("pages", ""))

                # Adding the pubmed identification number
                pubs[i]["pmid"] = int(pubs[i]["ID"].replace("pmid", ""))

            # Saving
            bib.append((year, pubs))

        # Sorting
        bib.sort(reverse=True, key=lambda pub: pub[0])

        return bib


def main():
    """The main."""
    # Parsing the arguments and YAML configuration file
    args = parse_args()
    conf = parse_yaml(args.yaml_conf)

    # Creating the new site
    website = Site(**conf["configuration"])

    # Adding the pages
    for page in conf["pages"]:
        website.add_page(**page)

    # Discovering the pages
    for discover in conf["autodiscover"]:
        website.discover(**discover)

    # Generating the website
    website.generate()


def parse_yaml(fn):
    """Parses YAML configuration from file.

    Args:
        fn (str): the name of the YAML configuration file.

    Returns:
        dict: the dictionary containing the configuration (returned by YAML).

    """
    conf = None
    with open(fn, "r") as i_file:
        conf = yaml.load(i_file)
    return conf


def parse_args():
    parser = argparse.ArgumentParser(
        description="Parses the configuration file and generates the website",
    )
    parser.add_argument(
        "yaml_conf",
        metavar="YAML",
        help="YAML configuration file.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    main()
