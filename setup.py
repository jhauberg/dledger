#!/usr/bin/env python3

"""
https://github.com/jhauberg/dividendreport

Copyright 2019 Jacob Hauberg Hansen.
License: MIT (see LICENSE)
"""

import sys
import re

from setuptools import setup, find_packages

from dividendreport import VERSION_PATTERN


def determine_version_or_exit() -> str:
    """ Determine version identifier or exit with non-zero status. """

    with open('dividendreport/__version__.py') as file:
        version_contents = file.read()
        version_match = re.search(VERSION_PATTERN, version_contents, re.M)

        if version_match:
            version = version_match.group(1)

            return version

    sys.exit('Version not found')


if sys.version_info < (3, 7):
    sys.exit('Python 3.7+ required to use dividendreport')

VERSION = determine_version_or_exit()

setup(
    name='dividendreport',
    version=VERSION,
    description='Create dividend income reports',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/jhauberg/dividendreport',
    download_url='https://github.com/jhauberg/dividendreport/archive/master.zip',
    author='Jacob Hauberg Hansen',
    author_email='jacob.hauberg@gmail.com',
    license='MIT',
    packages=find_packages(),
    include_package_data=True,
    platforms='any',
    install_requires=[
        'docopt==0.6.2'
    ],
    entry_points={
        'console_scripts': [
            'dividendreport=dividendreport.__main__:main',
        ],
    }
)
