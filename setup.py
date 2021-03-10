#!/usr/bin/env python3

"""
https://github.com/jhauberg/dledger

Copyright 2019 Jacob Hauberg Hansen.
License: MIT (see LICENSE)
"""

import sys
import re

from setuptools import setup, find_packages

from dledger import VERSION_PATTERN


def determine_version_or_exit() -> str:
    """ Determine version identifier or exit with non-zero status. """

    with open("dledger/__version__.py") as file:
        version_contents = file.read()
        version_match = re.search(VERSION_PATTERN, version_contents, re.M)

        if version_match:
            version = version_match.group(1)

            return version

    sys.exit("Version not found")


if sys.version_info < (3, 8):
    sys.exit("Python 3.8+ required to run dledger")

VERSION = determine_version_or_exit()

setup(
    name="dledger",
    version=VERSION,
    description="Track and forecast dividend income",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/jhauberg/dledger",
    download_url="https://github.com/jhauberg/dledger/archive/master.zip",
    author="Jacob Hauberg Hansen",
    author_email="jacob.hauberg@gmail.com",
    license="MIT",
    packages=find_packages(exclude=["test"]),
    include_package_data=True,
    platforms="any",
    install_requires=["docopt==0.6.2"],
    entry_points={
        "console_scripts": [
            "dledger=dledger.__main__:main",
        ],
    },
)
