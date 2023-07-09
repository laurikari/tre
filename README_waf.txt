Introduction
============

This file documents the work in progress as of 2023/07/08 for adding
"waf" (an alternate build system, see https://waf.io) to the TRE
project.

Why add yet another build tool?  Well, I wasn't really planning to when
I started, but as I did testing I found myself doing a lot of repetitive
actions to get clean build and test environments.  Since I had good
results using "waf" for testing builds in my own projects, I thought I'd
try using it in a "testing only" way for TRE, and then I got kinda
carried away :).  However, the GNU autotools remain the recommended way
to build and install TRE if you are not doing TRE development. 

The waf build system is based on Python, and if waf was the only way to
build it, it would add a dependency on Python to this project.  However,
waf can use any version of Python later than 3.5, and since one of the
features of this project is a Python extension, the dependency does not
seem too onerous.

Advantages
==========

What the waf build system does do for TRE developement is:

   + It builds and tests most reasonable configurations on a given
     platform with two commands (i.e. it builds and tests multiple
     configurations, such as with and without multibyte support).

   + It puts all build products and test results in a separate
     directory, which makes sorting out modified files for version
     control much less confusing.

   + It works on multiple platforms without further depenencies.
     As of 2023/07/08, it builds and tests successfully on Linux,
     FreeBSD, and MacOS.  (MacOS does need the Xcode command line tools,
     but does not need an xcode project file.)

   + It builds and tests the python extension in virtual python
     environments for each viable configuration.

   + It runs the various test programs without needing an intermediate
     shell, and so dodges the issue of escaping shell characters in
     regular expressions in order to test them.

Building
========

The steps needed to build and test with waf are:

   1) clone the git repository or download a tarball and unpack it
      (presumably you have already done this, or you wouldn't be reading
      this file).

   2) In the cloned or unpacked directory do:
         ./waf configure

   3) then to build and test do:
         ./waf
      or
         ./waf build

This builds and tests *multiple* configurations rather than just one
like the GNU autotools do with "./configure;make".  This is very
different from the usual project build process, and is even different
from the usual use of the waf build system.

There are many command line options, use:

   ./waf -h

to see them.  There are quite a few that might seem to duplicate
functionality, but because the options can apply to both the configure
step and the build+test step (with multiple configurations possible
in both) the apparent duplicate functionality makes fine tuning
during development possible.

The waf output is coloured if you are using a colour terminal for your
command shell.

Selectable Features
===================

The current scripts attempt to build 12 different configurations on
Linux and FreeBSD, and 6 on MacOS.  The various configurations are built
in different directories depending on the platform and available
features.  The features that are (currently) selectable are:

   - nls (or sls) -- National Language Support (or Single)
   - ap (or ex)   -- APproximate matching (or EXact)
   - wc (or nc)   -- Wide Character support (32-bit) (or Narrow (8-bit))
   - mb (or sb)   -- MultiByte characters (or SingleByte)
   - ti (or ri)   -- TRE Interface or system Regex.h Interface

MultiByte requires Wide Character, so there are 24 viable combinations
of selected features.

National Language Support on MacOS currently depends on Objective-C
or Swift macros and functions, so the MacOS build disables nls.
(Also, there is a bug in the MacOS linker that breaks the Python
extension for clang versions 14.0 to 14.2, but is has been fixed in
14.3.)

As an example of where the build results end up, for FreeBSD with
nls, ap, wc, mb, and ti features selected, the build results are in:

   build/freebsd/nls/ap/wc/mb/ti

or for MacOS with sls, ap, wc, mb, and ti they are in:

   build/darwin/sls/ap/wc/mb/ti

Installing
==========

This would normally be a simple command:

   ./waf install

but at this time (2023/07/08) it is still not recommended.  It will
currently attempt to installl exactly one of the viable variations
but it chooses a "default" configuration of the selectable features
and that may not be the configuration you want.

Cleaning
========

The simple command:

   ./waf clean

will remove a large portion of the build products, but it will not
remove the configuration information, and it has not been tested to
see if it removes everything it should remove and leaves everything
it should leave.

If you want to completely clean up after experimenting with waf, just
remove the entire build tree.  The build tree includes the configuration
information, so if you remove the entire tree you will have to configure
waf again before further building.

Roadmap
=======

I am actively working on the waf build system, and I will work on a
more functional "install" once I have sorted out the outstanding PRs.

I'm not a big user of Windows, but waf does work on that platform
(again, needing only python and compiler tools, no IDE).  However, the
windows build of TRE using waf has not been tried at all, even to see if
it configures and builds successfully.  I will look at the build and
test situation on Windows after the "install" on other platforms, but
will probably leave installation on Windows to someone else.

Tom Rushworth <tbr@acm.org>
