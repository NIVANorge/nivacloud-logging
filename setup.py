# -*- coding: utf-8 -*-
from setuptools import setup

setup(
    name='nivacloud-logging',

    # Versions should comply with PEP440.  For a discussion on single-sourcing
    # the version across setup.py and the project code, see
    # https://packaging.python.org/en/latest/single_source_version.html
    version='0.5.1',

    description="Utils for setting up logging used in nivacloud application",
    long_description_content_type='text/markdown',

    # The project's main homepage.
    url='https://github.com/NIVANorge/nivacloud-logging',

    author='Håkon Drolsum Røkenes',
    author_email="drhaakondr@gmail.com",

    license='MIT',

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 3 - Alpha',

        # Indicate who your project is intended for
        'Intended Audience :: Developers',
        'Topic :: System :: Logging  ',

        # Pick your license as you wish (should match "license" above)
        'License :: OSI Approved :: MIT License',

        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
    install_requires=[
        "python-json-logger>=0.1.11,<0.2",
    ],
    setup_requires=[
        "pytest-runner",
    ],
    tests_require=[
        "pytest>=4.4.0",
        "pytest-asyncio>=0.10.0",
    ],
    packages=["nivacloud_logging"]
)
