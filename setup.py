#!/usr/bin/env python
# -*- coding: utf-8 -*-

try:
    from setuptools import setup, Extension
except ImportError:
    from distutils.core import setup, Extension


DESCRIPTION = 'Python library for Tecan Cavro OEM syringe pump control'

DISTNAME = 'tecancavro'
LICENSE = 'MIT'
AUTHORS = 'Ben Pruitt'
EMAIL = 'benjamin.pruitt@wyss.harvard.edu'
URL = 'https://github.com/benpruitt/tecancavro'
DOWNLOAD_URL = ''
CLASSIFIERS = [
    'Development Status :: 1 - Beta',
    'Environment :: Console',
    'Intended Audience :: Science/Research',
    'Programming Language :: Python',
    'Programming Language :: Python :: 2',
    'Programming Language :: Python :: 3',
    'Programming Language :: Python :: 2.7',
    'Programming Language :: Python :: 3.3',
    'Programming Language :: Python :: 3.4',
    'Topic :: Scientific/Engineering',
]


setup(
    name=DISTNAME,
    maintainer=AUTHORS,
    packages=['tecancavro'],
    maintainer_email=EMAIL,
    description=DESCRIPTION,
    license=LICENSE,
    url=URL,
    download_url=DOWNLOAD_URL,
    long_description=DESCRIPTION,
    classifiers=CLASSIFIERS
)