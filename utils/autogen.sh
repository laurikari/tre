#! /bin/sh

set -e

# Replace variables here and there to get a consistent tree.
./utils/replace-vars.sh

# Set up libtool stuff for use with Automake.
libtoolize --automake

# Update aclocal.m4, using the macros from the m4 directory.
aclocal -I m4

# Run autoheader to generate config.h.in.
autoheader

# Create Makefile.in's.
automake --add-missing

# Create the configure script.
autoconf
