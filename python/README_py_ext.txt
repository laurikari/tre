Status of the Python extension for TRE as of 2023/05/10.

This version of the C code for the python extension includes
changes suggested by Brian A. Jones in PR 19, and also includes
changes by Tom Rushworth for the new Python3 Unicode strings
(i.e. strings composed of codepoints rather than characters).

It also includes #ifdef'd out code to release the GIL around
comple and search functions as suggested by Brian A. Jones.
This code builds correctly and passes single threaded tests
but has not yet been tested with multi-threaded python, so
the default build leaves it out.

There are some suggestions for changes to setup.py that involve
include and library directories that have not been tested, 
because the testing that has been done is done through a process
that involves virtual python environments using venv and an
alternate build setup (i.e. not setup.py).  The alternate build
setup is only for development at this point although it is
likely to be added to the public repository once it matures.

The tiny test in example.py has been extended to include a
small bit of testing for the codepoint size checking code.
If built WITHOUT wide character support the extension can
not handle codepoint sizes larger than 1 byte, so the extension
will now produce a ValueError exception if a non-wide-character
build is passed a python string that contains codepoints
that do not fit in 1 byte.


Testing to date has been done on 64-bit systems as follows:

   python 3.6.1, clang 802.0.42 (Apple LLVM 8.1.0) on MacOS 10.12.6 (Sierra)
   python 3.9.16, clang 13.0.0 on FreeBSD 13.1
   python 3.10.6, gcc 11.3.0 on Linux Mint 

The extension builds on an M2 Apple:

   python 3.9.6, clang 14.0.0 (Apple clang-14.0.29.202) MacOS 13.3.1 (Ventura)

but as of 2023/05/10 there is a bug in the compiler or linker that breaks
python extensions, so the python extension does not work.  (The TRE library
itself does build and pass tests.)  Apple is actively working on the bug.


No attempt has yet been made to test 32-bit systems.  (I (Tom Rushworth)
plan to deal with the remaining PR's before looking at 32-bit systems,
although I see no obvious reason that TRE or the extension would stop
working with these changes.

Tom Rushworth
   email_addr = "tbratacmdotorg".replace("at",'@').replace("dot",'.')
