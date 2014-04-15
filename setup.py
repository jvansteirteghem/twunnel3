#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

if sys.argv[-1] == 'publish':
    os.system('python setup.py sdist upload')
    sys.exit()


with open(os.path.join(os.path.dirname(__file__), 'README.rst')) as f:
    readme = f.read()

packages = [
    'twunnel3',
]

package_data = {
}

requires = [
    'asyncio'
]

classifiers=[
    'Programming Language :: Python',
    'Programming Language :: Python :: 3',
    'Programming Language :: Python :: 3.3',
]

setup(
    name='twunnel3',
    version='0.1.0',
    description='A HTTPS/SOCKS4/SOCKS5 tunnel for AsyncIO.',
    long_description=readme,
    packages=packages,
    package_data=package_data,
    install_requires=requires,
    author='Jeroen Van Steirteghem',
    author_email='jeroen.vansteirteghem@gmail.com',
    url='https://github.com/jvansteirteghem/twunnel3',
    license='MIT',
    classifiers=classifiers,
)
