#!/usr/bin/env python3


import os
import argparse
from glob import glob

import yaml
import bibtexparser
from jinja2 import Environment, FileSystemLoader


def main():
    """The main."""
    # Parsing the arguments and YAML configuration file
    args = parse_args()
    conf = parse_yaml(args.yaml_conf)

    # Reading the publications
    publications = parse_bibtex(conf["configuration"]["bibtex_dir"])


def parse_bibtex(dn):
    """Parses all *.bib files inside a directory.

    Args:
        dn (str): the directory name containing all the BIB file (*.bib).

    Returns:
        dict: a dictionary containing years as keys, and
              bibtexparser.bibdatabase.BibDatabase as values.

    Warning
    -------
        The names of the file should always be `YEAR.bib`.

    """
    # Getting the BibTeX files
    bib = {}
    bibfiles = glob(os.path.join(dn, "*.bib"))
    for fn in bibfiles:
        year = int(os.path.basename(fn).split(".")[0])
        with open(fn, "r") as i_file:
            bib[year] = bibtexparser.load(i_file)

    return bib


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
