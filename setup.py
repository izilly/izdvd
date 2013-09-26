#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  Copyright (c) 2013 William Adams
#  Distributed under the terms of the Modified BSD License.
#  The full license is in the file LICENSE, distributed with this software.

from distutils.core import setup

with open('README.rst') as f:
    long_description = f.read()

setup(
    name='izdvd',
    version='0.1.2',
    packages=['izdvd'],
    scripts=['bin/izdvd', 'bin/izdvdmenu', 'bin/izdvdbg'],
    author='William Adams',
    author_email='willadams+dev@gmail.com',
    url='https://github.com/izzilly/izdvd',
    license='BSD License',
    description=('A set of python scripts for authoring DVDs '
                 'and/or DVD menus with little or no user interaction.'),
    long_description=long_description,
    classifiers=['Development Status :: 4 - Beta',
                 'Environment :: Console',
                 'Intended Audience :: End Users/Desktop',
                 'License :: OSI Approved :: BSD License',
                 'Natural Language :: English',
                 'Operating System :: POSIX :: Linux',
                 'Programming Language :: Python',
                 'Programming Language :: Python :: 3',
                 'Topic :: Multimedia :: Video',
                 'Topic :: Multimedia :: Video :: Conversion'],
    platforms=['linux']
    )
