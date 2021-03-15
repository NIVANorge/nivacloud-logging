# -*- coding: utf-8 -*-

from setuptools import setup

# These are optional dependencies needed for tracing...
OPTIONAL_REQUIREMENTS = {
    'requests': ["requests>=2.22.0"],
    'flask': ["Flask>=1.1.0"],
    'aiohttp': ["aiohttp>=3.0.0"],
    'starlette': ["starlette>=0.7.2"],
    'gunicorn': ["gunicorn>=19.0.0"],
}

# ...but we always need them for testing:
TEST_REQUIREMENTS = [
    req for reqs in OPTIONAL_REQUIREMENTS.values() for req in reqs
]

setup(
    name='nivacloud-logging',

    # Versions should comply with PEP440.  For a discussion on single-sourcing
    # the version across setup.py and the project code, see
    # https://packaging.python.org/en/latest/single_source_version.html
    version="0.8.15",

    description="Utils for setting up logging used in nivacloud applications",
    long_description_content_type='text/markdown',

    # The project's main homepage.
    url='https://github.com/NIVANorge/nivacloud-logging',

    author='Norwegian Institute for Water Research',
    author_email="cloud@niva.no",

    license='MIT',

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 4 - Beta',

        # Indicate who your project is intended for
        'Intended Audience :: Developers',
        'Topic :: System :: Logging  ',

        # Pick your license as you wish (should match "license" above)
        'License :: OSI Approved :: MIT License',

        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
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
        *TEST_REQUIREMENTS,
    ],
    extras_require=OPTIONAL_REQUIREMENTS,
    packages=["nivacloud_logging"]
)
