#! /bin/sh
#

set -e

rm -rf dist
./utils/autogen.sh
./utils/build-sources.sh

