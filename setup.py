from setuptools import setup, find_packages
import sys, os

version = '0.1'

setup(
    name='ckanext-privatedatasets',
    version=version,
    description="This extensions allows users to create private datasets only visible to certain users. The extension provides also an API to specify programatically which users can access private datasets",
    long_description='''
    ''',
    classifiers=[], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
    keywords='',
    author='Aitor Magan',
    author_email='amagan@conwet.com',
    url='',
    license='',
    packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
    namespace_packages=['ckanext', 'ckanext.privatedatasets'],
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        # -*- Extra requirements: -*-
    ],
    entry_points='''
        [ckan.plugins]
        # Add plugins here, e.g.
        privatedatasets=ckanext.privatedatasets.plugin:PrivateDatasets
    ''',
)
