Introduction
============

This document describes how to build TRE from git repository
sources.  Typical users should use the source code release packages,
available from the `TRE website <http://laurikari.net/tre/>`_.

Building from git is necessary for example if you want to test some
of the latest changes before they are offically released.

Unix
====

Prerequisites
-------------
You will need the following tools installed on your system:

  - darcs (if you're reading this, you should already have it)
  - autoconf 2.59 or newer
  - automake 1.9.x (newer is usually better)
  - gettext 0.17 or newer
  - libtool 1.5.22 or newer
  - zip (Info-Zip 2.3), optional

Using Ubuntu, the necessary command is::

  sudo apt-get install build-essential autotools-dev automake gettext libtool autopoint zip python-dev python-setuptools

Preparing the tree
------------------
Change to the root of the source directory and run::

  ./utils/autogen.sh

This will regenerate various things using the prerequisite tools so
that you end up with a buildable tree.

Build
-----
After this, you can run the configure script and build TRE as usual::

  make
  sudo make install

Next, to build the Python extension::

  cd python
  python setup.py build_ext
  sudo python setup.py install
  # Note: the line below should be added to your .bashrc, so the Python
  # extension can find the tre library.
  export LD_LIBRARY_PATH=/usr/local/lib:$LD_LIBRARY_PATH

Building a source code package
------------------------------
In a prepared tree, this command creates a source code tarball::

  ./configure && make dist

Alternatively, you can run::

  ./utils/build-sources.sh

which builds the source code packages and puts them in the ``dist``
subdirectory.  This script needs a working ``zip`` command.

Windows
=======
- Build a Release version of the TRE library using Visual Studio 2008 express
  (or the full version) based on the solution file ``tre/win32/tre.sln``.
- From a command line in ``tre/python``, run
  ``python setup.py build_ext -I../include install``.
