How to build a distribution package
==================================

Prerequisites
=============

* Ubuntu Linux - 14.04 is known to work
* Run the following command to get necessary software: 
    $ sudo apt-get install vim build-essential gettext autopoint autoconf libtool zip

Making the package
==================

1. Check out the repository.
2. cd to the reposotory root
3. Run this command:
    $ ./utils/build-package.sh
4. The package (in tar.gz, tar.bz2, and zip formats)
   will appear in the dist/ subdirectory

Compiling
=========

The package can now be compiled on Linux or Mac via:

    $ ./configure --disable-debug --disable-dependency-tracking
    $ make && make install

If you are using homebrew on Mac, you can do (replacing 0.8.0 with the current version number):

    $ ./configure --disable-debug --disable-dependency-tracking --prefix=/usr/local/Cellar/tre/0.8.0
    $ make && make install
    $ brew unlink tre && brew link tre


