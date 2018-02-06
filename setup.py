#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2014 CoNWeT Lab., Universidad Politécnica de Madrid

# This file is part of CKAN Private Dataset Extension.

# CKAN Private Dataset Extension is free software: you can redistribute it and/or
# modify it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# CKAN Private Dataset Extension is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with CKAN Private Dataset Extension.  If not, see <http://www.gnu.org/licenses/>.

from setuptools import setup, find_packages

version = '0.3'

setup(
    name='ckanext-privatedatasets',
    version=version,
    description='CKAN Extension - Private Datasets',
    long_description='''
    This CKAN extension allows a user to create private datasets that only certain users will be able to see. When a dataset is being created, it's possible to specify the list of users that can see this dataset. In addition, the extension provides an HTTP API that allows to add users programatically.
    ''',
    classifiers=[], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
    keywords='ckan, private, datasets',
    author='Aitor Magan',
    author_email='amagan@conwet.com',
    url='https://conwet.fi.upm.es',
    download_url='https://github.com/conwetlab/ckanext-privatedatasets/tarball/v' + version,
    license='',
    packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
    namespace_packages=['ckanext', 'ckanext.privatedatasets'],
    include_package_data=True,
    zip_safe=False,
    setup_requires=[
        'nose>=1.3.0'
    ],
    install_requires=[
        # -*- Extra requirements: -*-
    ],
    tests_require=[
        'nose_parameterized==0.3.3',
        'selenium==2.52.0'
    ],
    test_suite='nosetests',
    entry_points='''
        [ckan.plugins]
        # Add plugins here, e.g.
        privatedatasets=ckanext.privatedatasets.plugin:PrivateDatasets
    ''',
)
