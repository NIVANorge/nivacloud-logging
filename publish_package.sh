#!/usr/bin/env bash

set -eu

VERSION=$(python setup.py --version)
python setup.py sdist

curl -i -L --fail -F package="@dist/nivacloud-logging-${VERSION}.tar.gz" "https://${FURY_TOKEN}@push.fury.io/niva/"
