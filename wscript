#!/usr/bin/env python3
# encoding: utf-8
#
#   wscript - part of TRE
#   Top level waf build script by Tom Rushworth <tbr@acm.org>.
#
#   This software is released under a BSD-style license.
#   See the file LICENSE for details and copyright.
#
#
import os,sys,platform,sysconfig,subprocess,collections
# enum needs >= 3.4
from enum import Enum
# make sure the unit tests can handle UTF-8 output.
# import codecs
# # Python3.1+:
# sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
 
from waflib import Logs
from waflib import Options
from waflib import Utils

debug_final_config_envs = 0
debug_build_config_envs = 0
debug_build_defaults = False
debug_specific_config_env = None # "nls/ap/wc/mb/ti" # e.g. "nls/ap/wc/sb"

top = "."
# Set up platform dependent build directory so the project can live on a shared file system
platsys = platform.system().lower()
Logs.pprint("NORMAL","Platform is {0:s}".format(platsys))
# Known platforms: "darwin", "netbsd", "linux", "windows", "freebsd"
out = "build/"+platsys

package_name = "tre"
package_version_major = 0
package_version_minor = 8
package_version_miniscule = 1
package_version = "{:d}.{:d}.{:d}".format(package_version_major,package_version_minor,package_version_miniscule)

# To check on where imports are coming from, look at the system module import path:
# for mispe in sys.path:
#    print('module import search path element [{0:s}]'.format(mispe))
# Add the project tool directory to the system import paths so we can get at things like build variants.
sys.path = sys.path[0:1] + [os.path.normpath(os.getcwd()+'/'+top+'/Tools/waf')] + sys.path[1:None]

#=============================================================================================================
# Build variants are different configurations of the targets, such as with or without native language support.
# We want to be able to build and test all the viable combinations while developing, although end users will
# probably only want one of them.
# 
# Variants for TRE:
#   nls/sls      (native/single) language support (i.e. gettext() and .po/.mo files)
#      used for lib, agrep, and retests
lang_variants = ["nls","sls"]
#   ap/ex        (approximate/exact) matching
match_variants = ["ap","ex"]
#   wc/nc        (wide/narrow) char
width_variants = ["wc","nc"]
#      build the wchar_t variants (wide) or not
#   mb/sb        (multi/single) byte (multi-byte is encodings like UTF-8)
encoding_variants = ["mb","sb"]
#      conform to the system regex ABI or not
#   ti/ri        Tre Interface or system Regex Interface
rxabi_variants = ["ti","ri"]
#
# Strings names for the variants need to be unique with respect to all the other variant names because
# they get used as part of variable names (e.g. cfg.env.variant_nls or cfg.env.variant_mb).
#
variant_group_list = [lang_variants,match_variants,width_variants,encoding_variants,rxabi_variants]
# Note that the python extension requires wide char, and is cannot be built for the narrow char variants.

# Import the build variant machinery and start creating the data structures for the variants we want.
# The final part of the variant setup is done in the configure step.
import build_variants
variant_name_path_list = build_variants.construct_variants(platsys,variant_group_list)

def options(opt):
   # Add option for logging calls to wscript build() functions (helps with debugging wscripts)
   opt.parser.set_defaults(log_wscripts=False)
   opt.add_option("--lws", action="store_true", dest="log_wscripts", help="Display wscripts entered")
   opt.add_option("--nolws", action="store_false", dest="log_wscripts", help="Skip displaying wscripts entered")
   #
   # The waf build system has slightly different semantics for configuration options from the GNU autotools,
   # because the option flags are available at configuration (like autotools), but also at build time (i.e.
   # like the "make" step in "./configure; make; make install"), and they don't have to have the same values.
   # This is handled here by recording the option values at the config step, and using them as defaults in the
   # build step.  The convention used for the recorded value is:
   #       -1 for option disabled,
   #        0 for option not specified (i.e. choose a default),
   #       +1 for option enabled.
   #
   # Build all variants
   #
   opt.parser.set_defaults(build_all_variants=1)
   opt.add_option("--all", action="store_const", const=1, dest="build_all_variants", help="build all viable variants")
   opt.add_option("--noall", action="store_const", const=-1, dest="build_all_variants", help="build only requested (or default) variants")
   opt.add_option("--notall", action="store_const", const=-1, dest="build_all_variants", help="build only requested (or default) variants")
   #
   # Since multiple variants are possible, the exclusive pairs for a single variant have more possibilities.
   # For examle, when building only one variant there are two (exclusive) possibilities for National Language Support,
   # the built target must have NLS enabled or disabled.  However when building multipble variants there are three
   # possibilities, (1) build only variants with NLS enabled, or (2) build only variants with NSL disabled, or (3) build
   # both kinds of variants.  It doesn't make too much sense for the fourth combination (no enabled OR disabled NLS variants)
   # because then there are no variants at all being built.
   #
   # Rather than trying to come up with wording for the option names that makes the 3 possibilities clear, I've kept the
   # enable/disable terminology and added a negation style name with its own enable/disable options.  To continue the NLS
   # example from above, I've kept --enable-nls and --disable-nls, but added SLS (Single Language Support) with the options
   # --enable-sls and --disable--sls.
   #
   # NLS/SLS
   #
   # Add option for building the native language support variant
   opt.parser.set_defaults(enable_nls=(-1 if "windows"==platsys else 0))
   opt.add_option("--enable-nls", action="store_const", const=1, dest="enable_nls",
                  help="build native language support variant, i.e. gettext (default)")
   opt.add_option("--disable-nls", action="store_const", const=-1, dest="enable_nls",
                  help="skip native language support variant")
   # Add option for building the single language support variant
   opt.parser.set_defaults(enable_sls=0)
   opt.add_option("--enable-sls", action="store_const", const=1, dest="enable_sls",
                  help="build single language support variant")
   opt.add_option("--disable-sls", action="store_const", const=-1, dest="enable_sls",
                  help="skip single language support variant (default)")
   #
   # ap/ex
   #
   # Add option for building the approximate matching variant
   opt.parser.set_defaults(enable_ap=0)
   opt.add_option("--enable-approx", action="store_const", const=1, dest="enable_ap",
                  help="build approximate matching variant (default)")
   opt.add_option("--disable-approx", action="store_const", const=-1, dest="enable_ap",
                  help="skip approximate matching variant")
   # Add option for building the exact matching variant
   opt.parser.set_defaults(enable_ex=0)
   opt.add_option("--enable-exact", action="store_const", const=1, dest="enable_ex",
                  help="build exact matching variant")
   opt.add_option("--disable-exact", action="store_const", const=-1, dest="enable_ex",
                  help="skip exact matching variant (default)")
   #
   # wc/nc
   #
   # Add option for building the wide character (wchar_t) variant
   opt.parser.set_defaults(enable_wc=0)
   opt.add_option("--enable-wchar", action="store_const", const=1, dest="enable_wc",
                  help="build wide character (wchar_t) variant (default)")
   opt.add_option("--disable-wchar", action="store_const", const=-1, dest="enable_wc",
                  help="skip wide character (wchar_t) variant (eliminates multibyte)")
   # Add option for building the narrow character (char) variant
   opt.parser.set_defaults(enable_nc=0)
   opt.add_option("--enable-nchar", action="store_const", const=1, dest="enable_nc",
                  help="build narrow character (char) variant (eliminates multibyte)")
   opt.add_option("--disable-nchar", action="store_const", const=-1, dest="enable_nc",
                  help="skip narrow character (char) variant (default)")
   #
   opt.parser.set_defaults(use_libutf8=0)
   opt.add_option("--with-libutf8", action="store_const", const=1, dest="use_libutf8",
                  help="use <libutf8.h> instead of <wchar.h> and <wctype.h>")
   opt.add_option("--without-libutf8", action="store_const", const=-1, dest="use_libutf8",
                  help="do not use <libutf8.h> instead of <wchar.h> and <wctype.h>")
   #
   # mb/sb
   #
   # Add option for building the multibyte variant
   opt.parser.set_defaults(enable_mb=0)
   opt.add_option("--enable-multibyte", action="store_const", const=1, dest="enable_mb",
                  help="build multibyte (e.g. UTF-8) variant (default, requires wchar)")
   opt.add_option("--disable-multibyte", action="store_const", const=-1, dest="enable_mb",
                  help="skip multibyte variant")
   # Add option for building the single byte variant
   opt.parser.set_defaults(enable_sb=0)
   opt.add_option("--enable-singlebyte", action="store_const", const=1, dest="enable_sb",
                  help="build single byte (char) variant")
   opt.add_option("--disable-singlebyte", action="store_const", const=-1, dest="enable_sb",
                  help="skip single byte (char) variant (default)")
   #
   # ti/ri
   #
   # Add option for building the TRE interface (ABI) variant
   opt.parser.set_defaults(enable_ti=0)
   opt.add_option("--enable-tre-abi", action="store_const", const=1, dest="enable_ti",
                  help="build TRE ABI variant (default)")
   opt.add_option("--disable-tre-abi", action="store_const", const=-1, dest="enable_ti",
                  help="skip TRE ABI variant")
   # Add option for building the system regex interface (ABI) variant
   opt.parser.set_defaults(enable_ri=0)
   opt.add_option("--enable-system-abi", action="store_const", const=1, dest="enable_ri",
                  help="build system regex ABI variant")
   opt.add_option("--disable-system-abi", action="store_const", const=-1, dest="enable_ri",
                  help="skip system regex ABI variant (default)")
   #
   # ###################
   # Add option for building agrep (only makes sense for the approximate matching variant)
   opt.parser.set_defaults(enable_agrep=1)
   opt.add_option("--enable-agrep", action="store_const", const=1, dest="enable_agrep", help="enable building agrep (default)")
   opt.add_option("--disable-agrep", action="store_const", const=-1, dest="enable_agrep", help="skip building agrep")
   # Add option for building python extension
   if "windows" == platsys:
      # ... but not on windows for now
      opt.parser.set_defaults(enable_python_extension=False)
   else:
      opt.parser.set_defaults(enable_python_extension=True)
      opt.add_option("--enable-pyext", action="store_true", dest="enable_python_extension", help="enable building python extension (default)")
      opt.add_option("--disable-pyext", action="store_false", dest="enable_python_extension", help="disable building python extension")
   # Add option for building and running library tests.
   opt.parser.set_defaults(enable_tests=1)
   opt.add_option("--enable-tests", action="store_const", const=1, dest="enable_tests",
                  help="enable building and running library tests (default)")
   opt.add_option("--disable-tests", action="store_const", const=-1, dest="enable_tests", help="disable building and running library tests")
   opt.add_option("--test", action="store_const", const=1, dest="enable_tests", help="enable building and running library tests (default)")
   opt.add_option("--notest", action="store_const", const=-1, dest="enable_tests", help="disable building and running library tests")
   # Add option for using alloca if the header is present.
   opt.parser.set_defaults(with_alloca=True)
   opt.add_option("--with-alloca", action="store_true", dest="with_alloca", help="use alloca() if available (default)")
   opt.add_option("--without-alloca", action="store_false", dest="with_alloca", help="do not use alloca()")
   # Add option for using libutf8.
   opt.parser.set_defaults(with_libutf8=False)
   opt.add_option("--with-libutf8", action="store_true", dest="with_libutf8", help="use libutf8.h if available")
   opt.add_option("--without-libutf8", action="store_false", dest="with_libutf8", help="do not use libutf8.h (default)")
   # FIXME - lots more to do in configure before actually completing this.
   # opt.add_option("--enable-system-abi", action="store_true", dest="enable_sys_regex", help="try to make TRE compatible with the system regex ABI")
   # opt.add_option("--disable-system-abi", action="store_false", dest="enable_sys_regex", help="ignore the system regex ABI (default)")
   # # Add option for profiling with gprof
   # opt.parser.set_defaults(enable_profile=False)
   # opt.add_option("--enable-profile", action="store_true", dest="enable_profile", help="enable profiling with gprof")
   # opt.add_option("--disable-profile", action="store_false", dest="enable_profile", help="disable profiling with gprof (default)")
   # # No direct option for debug build, now treated as a target variation (rel/dbg)
   # opt.parser.set_defaults(release_bciuls=False)
   # opt.add_option("--rel", action="store_true", dest="release_bciuls", help="Build/clean/install/uninstall release versions")
   # opt.add_option("--norel", action="store_false", dest="release_bciuls", help="Skip build/clean/install/uninstall release versions")
   # opt.parser.set_defaults(debug_bciuls=True)
   # opt.add_option("--dbg", action="store_true", dest="debug_bciuls", help="Build/clean/install/uninstall debug versions")
   # opt.add_option("--nodbg", action="store_false", dest="debug_bciuls", help="Skip build/clean/install/uninstall debug versions")
   # When clang is one of multiple compilers available, try it first.
   # Standard alternative:
   # waf configure --check-c-compiler=gcc
   # waf configure --check-c-compiler=clang
   opt.check_c_compiler = ["clang","gcc"]
   opt.load("compiler_c")
   # And finally pick up options for things we might build (options have not actually
   # been SET at this point, only initialized, so we don't know what will actually be built).
   opt.recurse("lib")    # tre library
   opt.recurse("src")    # agrep
   opt.recurse("python") # python extension
   # opt.recurse("po")     # NLS
   opt.recurse("tests")  # what it says
   # Logs.pprint("NORMAL","finished options")

def de_dup_os_search_path(os_search_path):
   old_path_lst = os_search_path.split(os.pathsep)
   new_path_lst = []
   for p in old_path_lst:
      if p not in new_path_lst:
         new_path_lst.append(p)
   return(os.pathsep.join(new_path_lst))

# Useful bit to get a look at the compiler defines (gcc or clang):
# clang -dM -E -

def normalize_option(enable_value,default_value):
   # There are 3 possiblities for enable and disable, giving 9 cases to check.
   # Return:
   #    -1 for setting_name disabled
   #    +1 for setting_name enabled
   #    default_value for setting_name not set
   if enable_value < 0:
      return(-1)
   if enable_value > 0:
      return(1)
   return(default_value)

def normalize_option_all(enable_value,default_value):
   if Options.options.build_all_variants > 0:
      # Build all implies the other options are +1.
      return(1)
   return normalize_option(enable_value,default_value)

# Data structure for describing what needs to be done for the C #define lines
# in headers depending on whether a variant is True (yes) or not.
CDef_Action = Enum("CDef_Action",["CPY_FRM_PLTFM","UNDEF","DEFINE"])
CDef_Val_Type = Enum("CDef_Val_Type",["INT","STR","VAR"])
CDef_Info = collections.namedtuple("CDef_Info",["name","comment",
                                                "yes_action","yes_data",
                                                "no_action","no_data"])

cdefs_for_all_variants = [
   CDef_Info("HAVE_DLFCN_H","Define to 1 if you have the <dlfcn.h> header file.",
             CDef_Action.CPY_FRM_PLTFM,None, CDef_Action.UNDEF,None),
   CDef_Info("HAVE_GETOPT_H","Define to 1 if you have the <getopt.h> header file.",
             CDef_Action.CPY_FRM_PLTFM,None, CDef_Action.UNDEF,None),
   CDef_Info("HAVE_GETOPT_LONG","Define to 1 if you have the 'getopt_long' function.",
             CDef_Action.CPY_FRM_PLTFM,None, CDef_Action.UNDEF,None),
   CDef_Info("HAVE_INTTYPES_H","Define to 1 if you have the <inttypes.h> header file.",
             CDef_Action.CPY_FRM_PLTFM,None, CDef_Action.UNDEF,None),
   CDef_Info("HAVE_ISASCII","Define to 1 if you have the 'isascii' function.",
             CDef_Action.CPY_FRM_PLTFM,None, CDef_Action.UNDEF,None),
   CDef_Info("HAVE_ISBLANK","Define to 1 if you have the 'isblank' function.",
             CDef_Action.CPY_FRM_PLTFM,None, CDef_Action.UNDEF,None),
   CDef_Info("HAVE_LIBUTF8_H","Define to 1 if you have the <libutf8.h> header file.",
             CDef_Action.CPY_FRM_PLTFM,None, CDef_Action.UNDEF,None),
   CDef_Info("HAVE_STDINT_H","Define to 1 if you have the <stdint.h> header file.",
             CDef_Action.CPY_FRM_PLTFM,None, CDef_Action.UNDEF,None),
   CDef_Info("HAVE_STDIO_H","Define to 1 if you have the <stdio.h> header file.",
             CDef_Action.CPY_FRM_PLTFM,None, CDef_Action.UNDEF,None),
   CDef_Info("HAVE_STDLIB_H","Define to 1 if you have the <stdlib.h> header file.",
             CDef_Action.CPY_FRM_PLTFM,None, CDef_Action.UNDEF,None),
   CDef_Info("HAVE_STRINGS_H","Define to 1 if you have the <strings.h> header file.",
             CDef_Action.CPY_FRM_PLTFM,None, CDef_Action.UNDEF,None),
   CDef_Info("HAVE_STRING_H","Define to 1 if you have the <string.h> header file.",
             CDef_Action.CPY_FRM_PLTFM,None, CDef_Action.UNDEF,None),
   CDef_Info("HAVE_SYS_STAT_H","Define to 1 if you have the <sys/stat.h> header file.",
             CDef_Action.CPY_FRM_PLTFM,None, CDef_Action.UNDEF,None),
   CDef_Info("HAVE_SYS_TYPES_H","Define to 1 if you have the <sys/types.h> header file.",
             CDef_Action.CPY_FRM_PLTFM,None, CDef_Action.UNDEF,None),
   CDef_Info("_GNU_SOURCE","Define to enable GNU extensions in glibc.",
             CDef_Action.CPY_FRM_PLTFM,None, CDef_Action.UNDEF,None),
   # ("HAVE_ICONV",True,"Define if you have the iconv() (codeset conversion) function and it works."),
   # ("STDC_HEADERS",True,"Define to 1 if all of the C90 standard headers exist (not just the ones
   #    required in a freestanding environment). This macro is provided for
   #    backward compatibility; new code need not use it."),
]

cdefs_for_debug = [
   CDef_Info("TRE_DEBUG","Define if you want TRE to print debug messages to stdout.",
             CDef_Action.DEFINE,(CDef_Val_Type.INT,1),CDef_Action.UNDEF,None),
   CDef_Info("NDEBUG","____.",
             CDef_Action.DEFINE,(CDef_Val_Type.INT,1),CDef_Action.UNDEF,None),
]

cdefs_for_nls = [
   CDef_Info("ENABLE_NLS","Define to 1 if translation of program messages to the user+s native language is requested.",
             # NLS - enable NLS
             CDef_Action.DEFINE,(CDef_Val_Type.INT,1),
             # SLS - disable NLS
             CDef_Action.UNDEF,None),
   CDef_Info("HAVE_DCGETTEXT","Define if the GNU dcgettext() function is already present or preinstalled.",
             CDef_Action.CPY_FRM_PLTFM,None, CDef_Action.UNDEF,None),
   CDef_Info("HAVE_GETTEXT","Define if the GNU gettext() function is already present or preinstalled.",
             CDef_Action.CPY_FRM_PLTFM,None, CDef_Action.UNDEF,None),
   # These functions do not appear anywhere in the source code (as of 2023/05/25, so it is pointless to look for them.
   # ("HAVE_CFLOCALECOPYCURRENT",Define to 1 if you have the MacOS X function CFLocaleCopyCurrent in the CoreFoundation framework."),
   # ("HAVE_CFPREFERENCESCOPYAPPVALUE",Define to 1 if you have the MacOS X function CFPreferencesCopyAppValue in the CoreFoundation framework."),
]

cdefs_for_ap = [
   CDef_Info("TRE_APPROX","Define if you want to enable approximate matching functionality.",
             # AP - enable approximate matching
             CDef_Action.DEFINE,(CDef_Val_Type.INT,1),
             # EX - disable approximate matching
             CDef_Action.UNDEF,None),
]

cdefs_for_wide_characters = [
   CDef_Info("TRE_WCHAR","Define if you want to enable wide character functionality.",
             # WC - enable wide character
             CDef_Action.DEFINE,(CDef_Val_Type.INT,1),
             # NC - disable wide character
             CDef_Action.UNDEF,None),
   CDef_Info("TRE_WTYPE","Define if you want to enable wide character functionality.",
             # WC - enable wide character
             CDef_Action.DEFINE,(CDef_Val_Type.INT,1),
             # NC - disable wide character
             CDef_Action.UNDEF,None),
   CDef_Info("HAVE_MBSTATE_T","Define to 1 if the system has the type 'mbstate_t'.",
             CDef_Action.CPY_FRM_PLTFM,None, CDef_Action.UNDEF,None),
   CDef_Info("HAVE_WCSRTOMBS","Define to 1 if you have the 'wcsrtombs' function or macro.",
             CDef_Action.CPY_FRM_PLTFM,None, CDef_Action.UNDEF,None),
   CDef_Info("HAVE_ISWASCII","Define to 1 if you have the 'iswascii' function or macro.",
             CDef_Action.CPY_FRM_PLTFM,None, CDef_Action.UNDEF,None),
   CDef_Info("HAVE_ISWBLANK","Define to 1 if you have the 'iswblank' function or macro.",
             CDef_Action.CPY_FRM_PLTFM,None, CDef_Action.UNDEF,None),
   CDef_Info("HAVE_ISWCTYPE","Define to 1 if you have the 'iswctype' function or macro.",
             CDef_Action.CPY_FRM_PLTFM,None, CDef_Action.UNDEF,None),
   CDef_Info("HAVE_ISWLOWER","Define to 1 if you have the 'iswlower' function or macro.",
             CDef_Action.CPY_FRM_PLTFM,None, CDef_Action.UNDEF,None),
   CDef_Info("HAVE_ISWUPPER","Define to 1 if you have the 'iswupper' function or macro.",
             CDef_Action.CPY_FRM_PLTFM,None, CDef_Action.UNDEF,None),
   CDef_Info("HAVE_TOWLOWER","Define to 1 if you have the 'towlower' function or macro.",
             CDef_Action.CPY_FRM_PLTFM,None, CDef_Action.UNDEF,None),
   CDef_Info("HAVE_TOWUPPER","Define to 1 if you have the 'towupper' function or macro.",
             CDef_Action.CPY_FRM_PLTFM,None, CDef_Action.UNDEF,None),
   CDef_Info("HAVE_WCHAR_H","Define to 1 if you have the <wchar.h> header file.",
             CDef_Action.CPY_FRM_PLTFM,None, CDef_Action.UNDEF,None),
   CDef_Info("HAVE_WCHAR_T","Define to 1 if the system has the type 'wchar_t'.",
             CDef_Action.CPY_FRM_PLTFM,None, CDef_Action.UNDEF,None),
   CDef_Info("HAVE_WCSCHR","Define to 1 if you have the 'wcschr' function or macro.",
             CDef_Action.CPY_FRM_PLTFM,None, CDef_Action.UNDEF,None),
   CDef_Info("HAVE_WCSCPY","Define to 1 if you have the 'wcscpy' function or macro.",
             CDef_Action.CPY_FRM_PLTFM,None, CDef_Action.UNDEF,None),
   CDef_Info("HAVE_WCSLEN","Define to 1 if you have the 'wcslen' function or macro.",
             CDef_Action.CPY_FRM_PLTFM,None, CDef_Action.UNDEF,None),
   CDef_Info("HAVE_WCSNCPY","Define to 1 if you have the 'wcsncpy' function or macro.",
             CDef_Action.CPY_FRM_PLTFM,None, CDef_Action.UNDEF,None),
   CDef_Info("HAVE_WCTYPE","Define to 1 if you have the 'wctype' function or macro.",
             CDef_Action.CPY_FRM_PLTFM,None, CDef_Action.UNDEF,None),
   CDef_Info("HAVE_WCTYPE_H","Define to 1 if you have the <wctype.h> header file.",
             CDef_Action.CPY_FRM_PLTFM,None, CDef_Action.UNDEF,None),
   CDef_Info("HAVE_WINT_T","Define to 1 if the system has the type 'wint_t'.",
             CDef_Action.CPY_FRM_PLTFM,None, CDef_Action.UNDEF,None),
]

cdefs_for_multibyte = [
   CDef_Info("TRE_MULTIBYTE","Define to enable multibyte character set support.",
             # MB - enable multibyte
             CDef_Action.DEFINE,(CDef_Val_Type.INT,1),
             # SB - disable multibyte
             CDef_Action.UNDEF,None),
   CDef_Info("HAVE_MBRTOWC","Define to 1 if you have the 'mbrtowc' function or macro.",
             CDef_Action.CPY_FRM_PLTFM,None, CDef_Action.UNDEF,None),
   CDef_Info("HAVE_MBTOWC","Define to 1 if you have the 'mbtowc' function or macro.",
             CDef_Action.CPY_FRM_PLTFM,None, CDef_Action.UNDEF,None),
   CDef_Info("HAVE_WCSTOMBS","Define to 1 if you have the 'wcstombs' function or macro.",
             CDef_Action.CPY_FRM_PLTFM,None, CDef_Action.UNDEF,None),
]

# The regex defines may seem backwards because the "yes" action is to NOT use the system regex ABI.
cdefs_for_regex = [
   CDef_Info("TRE_USE_SYSTEM_REGEX_H","Define to include the system regex.h from TRE regex.h",
             # TI - use TRE native ABI
             CDef_Action.UNDEF,None,
             # RI - use system ABI from <regex.h>
             CDef_Action.DEFINE,(CDef_Val_Type.INT,1)),
   CDef_Info("HAVE_REGEX_H","Define to 1 if you have the <regex.h> header file.",
             # TI - use TRE native ABI
             CDef_Action.UNDEF,None,
             # RI - use system ABI from <regex.h>
             CDef_Action.CPY_FRM_PLTFM,None),
   CDef_Info("TRE_SYSTEM_REGEX_H_PATH","Define to the absolute path to the system regex.h",
             # TI - use TRE native ABI
             CDef_Action.UNDEF,None,
             # RI - use system ABI from <regex.h>
             CDef_Action.CPY_FRM_PLTFM,None),
   CDef_Info("HAVE_REG_ERRCODE_T","Define to 1 if the system has the type 'reg_errcode_t'.",
             # TI - use TRE native ABI
             CDef_Action.UNDEF,None,
             # RI - use system ABI from <regex.h>
             CDef_Action.CPY_FRM_PLTFM,None),
   CDef_Info("TRE_REGEX_T_FIELD",
             "Define to a field in the regex_t struct where TRE should store a pointer to the internal tre_tnfa_t structure",
             # TI - use TRE native ABI
             CDef_Action.DEFINE,(CDef_Val_Type.VAR,"value"),
             # CDef_Action.CPY_FRM_PLTFM,None,
             # RI - use system ABI from <regex.h>
             CDef_Action.CPY_FRM_PLTFM,None),
   CDef_Info("_REGCOMP_INTERNAL", "Define on IRIX",
             # TI - use TRE native ABI
             CDef_Action.UNDEF,None,
             # RI - use system ABI from <regex.h>
             CDef_Action.DEFINE,(CDef_Val_Type.INT,1)),
]

# FUTURE: make this a variation, only valid if "HAVE_ALLOCA" is in the platform env (header may be separate, or part of standard C library)
cdefs_for_alloca = [
   CDef_Info("TRE_USE_ALLOCA","Define if you want TRE to use alloca() instead of malloc() when allocating memory needed for regexec operations.",
             CDef_Action.DEFINE,(CDef_Val_Type.INT,1),
             CDef_Action.UNDEF,None),
   CDef_Info("HAVE_ALLOCA","Define to 1 if you have 'alloca', as a function or macro.",
             CDef_Action.CPY_FRM_PLTFM,None, CDef_Action.UNDEF,None),
   CDef_Info("HAVE_ALLOCA_H","Define to 1 if <alloca.h> works.",
             CDef_Action.CPY_FRM_PLTFM,None, CDef_Action.UNDEF,None),
   CDef_Info("C_ALLOCA","Define to 1 if using 'alloca.c'.",
             CDef_Action.CPY_FRM_PLTFM,None, CDef_Action.UNDEF,None), # FIXME this should be yet another variant..
]

cdefs_for_alloca = [
   CDef_Info("WCHAR_MAX","Define to the maximum value of wchar_t if not already defined elsewhere.",
             CDef_Action.CPY_FRM_PLTFM,None, CDef_Action.UNDEF,None),
   CDef_Info("WCHAR_T_SIGNED","Define if wchar_t is signed.",
             CDef_Action.CPY_FRM_PLTFM,None, CDef_Action.UNDEF,None),
   CDef_Info("WCHAR_T_UNSIGNED","Define if wchar_t is unsigned",
             CDef_Action.CPY_FRM_PLTFM,None, CDef_Action.UNDEF,None),
   CDef_Info("_FILE_OFFSET_BITS","Number of bits in a file offset, on hosts where this is settable.",
             CDef_Action.CPY_FRM_PLTFM,None, CDef_Action.UNDEF,None),
   CDef_Info("_LARGE_FILES","Define for large files, on AIX-style hosts.",
             CDef_Action.CPY_FRM_PLTFM,None, CDef_Action.UNDEF,None),
   # See tail end of autoconf generated config.h for const, inline, and size_t workarounds.
]

def cdef_is_in_env(key,env):
   # Check to see if key is a cdef in the given env.
   ban = key + '='
   for x in env.DEFINES:
      if x.startswith(ban):
         return True
   return False

def copy_define(key,comment,dst_env,src_env):
   # Define (or undefine) key in dst_env to match key in src_env if it is in the src_env.
   # This does not modify the src_env in any way.
   # FIXME - try to convert to using dst_cfg and the methods in ConfigContext instead of operating directly.
   DEFKEYS="define_key" 
   dst_DEFINES = dst_env.DEFINES # S.B. a list of "key=val" strings
   dst_DEFKEYS = dst_env[DEFKEYS] # S.B. a list of "key" strings
   src_DEFINES = src_env.DEFINES # S.B. a list of "key=val" strings
   src_DEFKEYS = src_env[DEFKEYS] # S.B. a list of "key" strings
   dbg_this_cfg = (debug_build_config_envs > 0) or (dst_env.VARIANT == debug_specific_config_env)
   if dbg_this_cfg:
      Logs.pprint("CYAN","-------------------")
      Logs.pprint("CYAN","considering key {{{:s}}} for cfg {{{:s}}} from {{{:s}}}".format(key,dst_env.VARIANT,src_env.VARIANT))
   if key in src_DEFKEYS:
      if dbg_this_cfg:
         Logs.pprint("CYAN","key {{{:s}}} present in cfg {{{:s}}} DEFKEYS".format(key,src_env.VARIANT))
      def_start = key + "="
      # Look for the defn in the src.
      defn = None
      for possible_defn in src_DEFINES:
         if possible_defn.startswith(def_start):
            defn = possible_defn
            break
      # If there is a defn in the src copy it to the dst.
      replaced_first = -1
      if None != defn:
         if dbg_this_cfg :
            Logs.pprint("YELLOW","found key {{{:s}}} in src {{{:s}}}".format(key,defn))
         # Replace the first defn in dst_env, or just append the defn if there is no existing one in dst.
         for x in range(len(dst_DEFINES)):
            if dst_DEFINES[x].startswith(def_start):
               replaced_first = x
               dst_DEFINES[x] = defn
               break
         if replaced_first < 0:
            # No existing defn.
            replaced_first = len(dst_DEFINES)
            dst_DEFINES.append(defn)
         if dbg_this_cfg:
            Logs.pprint("GREEN","replaced key {{{:s}}} : {{{:s}}} at dst[{:d}]".format(key,defn,replaced_first))
      # Remove any unwanted defns (after replaced_first, or all if no defn in src) from dst_env.
      start = replaced_first + 1
      removed_one = True
      while removed_one and start < len(dst_DEFINES):
         removed_one = False
         for x in range(start,len(dst_DEFINES)):
            if dst_DEFINES[x].startswith(def_start):
               del dst_DEFINES[x:x+1]
               if dbg_this_cfg:
                  Logs.pprint("PINK","removed key {{{:s}}} : {{{:s}}} from dst[{:d}]".format(key,defn,x))
               # The del may have messed up the iteration, get out of the for loop,
               # but repeat the while in the unlikely case of more than 1 define.
               start = x
               removed_one = True
               break
      # Add the key in either a define or undefine case.
      if key not in dst_DEFKEYS:
         dst_DEFKEYS.append(key)
      # Add the comment in either a define or undefine case.
      if "DEFINE_COMMENTS" in dst_env:
         dst_env.DEFINE_COMMENTS[key] = comment or ""
      else:
         dst_env.DEFINE_COMMENTS = {key:(comment or "")}
      # Make sure the dst_env is updated, just in case any of the ops above copied the data instead of modifying it.
      dst_env.DEFINES = dst_DEFINES
      dst_env[DEFKEYS] = dst_DEFKEYS

def find_sys_regex_path(cfg_ctx):
   # Find the path to the system <regex.h> file or "_" if not available.
   # Use the C preprocessor to do the search, and look for lines like:
   #  {# 1 "/usr/include/regex.h" 1 3 4}
   # in its output.
   # The autotool configure uses:
   # echo '#include <regex.h>' | $CC -E | grep '^#[a-z]* [0-9]* "\(.*regex.h\)"' | head -1 | sed 's/^#[a-z]* [0-9]* \"\(.*\)\".*/\1/'
   no_path = "_"
   rc = -1
   stdout_data = None
   stderr_data = None
   if cfg_ctx.is_defined("HAVE_REGEX_H"):
      cc_path = cfg_ctx.env.CC
      # Logs.pprint("RED","cc_path {{{!s}}}".format(cc_path))
      args = [cc_path[0], "-E", "-"] # Both clang and gcc need a "-" argument to say to read from stdin.
      # if "clang" in cc_path[0]:
      #    # clang needs a "-" argument to tell it to read from stdin.
      #    args += "-"
      # GAH!  The type of input and output of the Popen depens on how streams have been opened, and I don't want to figure that out...
      try:
         proc = Utils.subprocess.Popen(args,stdin=Utils.subprocess.PIPE,stderr=Utils.subprocess.PIPE,stdout=Utils.subprocess.PIPE)
         (stdout_data,stderr_data) = proc.communicate(input="#include <regex.h>\n")
         rc = proc.returncode
      except:
         proc = Utils.subprocess.Popen(args,stdin=Utils.subprocess.PIPE,stderr=Utils.subprocess.PIPE,stdout=Utils.subprocess.PIPE)
         (stdout_data,stderr_data) = proc.communicate(input=b"#include <regex.h>\n")
         stdout_data = stdout_data.decode("UTF-8")
         stderr_data = stderr_data.decode("UTF-8")
         rc = proc.returncode
      # Logs.pprint("PINK","type(stdout_data) = {{{!s}}}".format(type(stdout_data)))
      if 0 == rc:
         # Logs.pprint("PINK","rc==0")
         for line in stdout_data.splitlines():
            # Logs.pprint("PINK","|{!s}".format(line))
            if line.startswith('#'):
               rx = line.find('regex.h"')
               if -1 != rx:
                  rx += 7 # postion of trailing '"'
                  qx = line.find('"') # look for leading '"'
                  if -1 != qx and qx+1 < rx:
                     cfg_ctx.define("TRE_SYSTEM_REGEX_H_PATH",line[qx+1:rx],comment="Define to the absolute path of the system regex.h")
                     return
      else:
         Logs.pprint("PINK","rc=={:d}".format(rc))
         Logs.pprint("PINK","{!s}".format(stderr_data))
   # Not found.
   cfg_ctx.define("TRE_SYSTEM_REGEX_H_PATH","_",comment="Define to the absolute path of the system regex.h (no <regex.h> found)")

def find_sys_regex_field(cfg_ctx):
   for candidate in ["buffer","re_comp","__re_comp","__reg_expression","re_g","re_pad[0]"]:
      pgm = '''
#include <sys/types.h>
#include <regex.h>
int zot()
  {regex_t foo;
   void *bar = foo.''' + candidate + ''';
   foo.''' + candidate + ''' = bar;}
'''
      # If pgm compiles OK, candidate is good.
      msg = "Checking for usable regex_t field {:s}".format(candidate)
      ok = cfg_ctx.check(features="c",mandatory=False,fragment=pgm,msg=msg)
      if ok:
         cfg_ctx.define("TRE_REGEX_T_FIELD",candidate,quote=False)
         return
   cfg_ctx.define("TRE_REGEX_T_FIELD","failed_usable_regex_t_field_name_search",quote=False)

def handle_c_defines(cfg,do_yes_actions,list_of_cdefs,platform_env):
   dbg_this_cfg = (debug_build_config_envs > 0) or (cfg.env.VARIANT == debug_specific_config_env)
   for info in list_of_cdefs:
      cdef_name = info.name
      cdef_comment = info.comment
      if do_yes_actions:
         action = info.yes_action
         data = info.yes_data
      else:
         action = info.no_action
         data = info.no_data
      if CDef_Action.DEFINE == action:
         if None == data:
            # The value isn't important, just define to 1.
            cfg.define(cdef_name,1,comment=cdef_comment)
         else:
            # data is a tuple (CDef_Val_Type,val).
            cdef_type = data[0]
            if CDef_Val_Type.INT == cdef_type:
               cfg.define(cdef_name,data[1],comment=cdef_comment)
            elif CDef_Val_Type.VAR == cdef_type:
               cfg.define(cdef_name,data[1],comment=cdef_comment,quote=False)
            elif CDef_Val_Type.STR == cdef_type:
               cfg.define(cdef_name,data[1],comment=cdef_comment,quote=True)
            else:
               # Unexpected data type for cdef value, whine
               msg = "Unexpected data value type in {:s} action for C #define {:s}"
               Logs.pprint("RED",msg.format("yes" if do_yes_actions else "no",cdef_name))
      elif CDef_Action.UNDEF == action:
         # Remove any definition.
         cfg.undefine(cdef_name,comment=cdef_comment)
      elif CDef_Action.CPY_FRM_PLTFM == action:
         # Copy any definition from the platform_env to the current one.
         copy_define(cdef_name,cdef_comment,cfg.env,platform_env)
      else:
         # Unexpected cdef action, whine
         msg = "Unexpected action type for C #define {:s}"
         Logs.pprint("RED",msg.format(cdef_name))

def gather_env_for_variant(cfg):
   # Figure out the various DEFINES for cfg's current variant given both
   # what the variant requires and what is available from the platform.
   # We need this complicated setup so that for example, we can build
   # a variant without NLS even though the platform has the include files
   # "gettext.h" and "libintl.h" available.
   dbg_this_cfg = (debug_build_config_envs > 0) or (cfg.env.VARIANT == debug_specific_config_env)
   dbg_colour = "BLUE"
   if not cfg.env.viable:
      # This variant has already failed, no point in looking further.
      if dbg_this_cfg:
         Logs.pprint("RED","====== variant {{{:s}}} not viable".format(cfg.env.VARIANT))
      return
   platform_env = cfg.all_envs[cfg.all_envs[""].PLATSYS]
   if dbg_this_cfg:
      Logs.pprint(dbg_colour,"====== Handling defines_for_all_variants variant {{{:s}}}".format(cfg.env.VARIANT))
   handle_c_defines(cfg,True,cdefs_for_all_variants,platform_env)
   #-------------------------------------------------- NLS
   if cfg.env.variant_nls:
      if not cdef_is_in_env("HAVE_LIBINTL_H",platform_env) or "darwin" == platsys:
         # We need gettext and it isn't available.
         if dbg_this_cfg:
            Logs.pprint("RED","====== variant {{{:s}}} not viable (no LIBINTL_H)".format(cfg.env.VARIANT))
         cfg.env.viable = False
         return
   if dbg_this_cfg:
      Logs.pprint(dbg_colour,"====== Handling defines_for_nls variant {{{:s}}}".format(cfg.env.VARIANT))
   handle_c_defines(cfg,cfg.env.variant_nls,cdefs_for_nls,platform_env)
   #-------------------------------------------------- AP
   if dbg_this_cfg:
      Logs.pprint(dbg_colour,"====== Handling defines_for_approximate_matching variant {{{:s}}}".format(cfg.env.VARIANT))
   handle_c_defines(cfg,cfg.env.variant_ap,cdefs_for_ap,platform_env)
   #-------------------------------------------------- WC
   cdfwc = cdefs_for_wide_characters
   if cfg.env.variant_wc:
      # We need wide character support, either <wchar.h> or <libutf8.h>, but not both at the same time.
      if not cdef_is_in_env("HAVE_WCHAR_H",platform_env) or not cdef_is_in_env("HAVE_WCTYPE_H",platform_env):
         if dbg_this_cfg:
            Logs.pprint("RED","====== variant {{{:s}}} not viable (no WCHAR_H or WCTYPE_H)".format(cfg.env.VARIANT))
         cfg.env.viable = False
         return
      if cfg.env.variant_sb:
         # autoconf skips the TRE_WTYPE for the non-multibyte build.
         ndx_to_remove = 1
         # Use cdfwc so we don't end up modifying the original for other variants.
         cdfwc = cdefs_for_wide_characters[0:ndx_to_remove] + cdefs_for_wide_characters[ndx_to_remove+1:]
   if dbg_this_cfg:
      Logs.pprint(dbg_colour,"====== Handling defines_for_wide_characters variant {{{:s}}}".format(cfg.env.VARIANT))
   handle_c_defines(cfg,cfg.env.variant_wc,cdfwc,platform_env)
   #-------------------------------------------------- MB
   # In both Linux and FreeBSD mbstate_t is defined when "#include <wchar.h>" is processed.
   # There are ways to get mbstate_t without wchar.h, but they differ, so for now skip configs with "mb" but not "wc".  
   # Note that autoconf/configure simply rules them out as an error.
   if cfg.env.variant_mb and not cfg.env.variant_wc:
      if dbg_this_cfg:
         Logs.pprint("RED","====== variant {{{:s}}} not viable (no MB without WC)".format(cfg.env.VARIANT))
      cfg.env.viable = False
      return
   if dbg_this_cfg:
      Logs.pprint(dbg_colour,"====== Handling defines_for_multibyte variant {{{:s}}}".format(cfg.env.VARIANT))
   handle_c_defines(cfg,cfg.env.variant_mb,cdefs_for_multibyte,platform_env)
   #-------------------------------------------------- TI/RI system regex compatibility
   if cfg.env.variant_ri and not cdef_is_in_env("HAVE_REGEX_H",platform_env):
      if dbg_this_cfg:
         Logs.pprint("RED","====== variant {{{:s}}} not viable (no <regex.h>)".format(cfg.env.VARIANT))
      cfg.env.viable = False
      return
   if dbg_this_cfg:
      Logs.pprint(dbg_colour,"====== Handling defines_for_regex variant {{{:s}}}".format(cfg.env.VARIANT))
   handle_c_defines(cfg,cfg.env.variant_ti,cdefs_for_regex,platform_env)
   #--------------------------------------------------
   if dbg_this_cfg:
      Logs.pprint(dbg_colour,"====== Handling defines_for_alloca variant {{{:s}}}".format(cfg.env.VARIANT))
   handle_c_defines(cfg,(cfg.env.build_default_with_alloca>0),cdefs_for_alloca,platform_env)
   #--------------------------------------------------
   if dbg_this_cfg:
      Logs.pprint(dbg_colour,"====== Finished defines_* variant {{{:s}}}".format(cfg.env.VARIANT))

def configure(cfg):
   if Options.options.log_wscripts:
      Logs.pprint('CYAN','Configuring in {:s}'.format(cfg.path.abspath()))
   os.environ["PATH"] = de_dup_os_search_path(os.environ.get("PATH",""))
   cfg.env['PLATSYS'] = platsys
   # Just so we have them if we need them in the subdirectories...
   cfg.variant_group_list = variant_group_list
   cfg.variant_name_path_list = variant_name_path_list
   # ================= Config options to be saved for build
   opts = Options.options
   # We want to save the DEFAULT build options from the config, but not to rule out other options on the build command line.
   cfg.env.build_default_build_all_variants = opts.build_all_variants
   cfg.env.build_default_enable_nls = normalize_option_all(opts.enable_nls,1)
   cfg.env.build_default_enable_sls = normalize_option_all(opts.enable_sls,-1)
   if "darwin" == platsys:
      # National Language Support is a completely different animal on darwin, for now skip it.
      cfg.env.build_default_enable_nls = -1
      cfg.env.build_default_enable_sls = 1
   elif "windows" == platsys:
      # GNU gettext is an extra on windows, for now skip it.
      cfg.env.build_default_enable_nls = -1
      cfg.env.build_default_enable_sls = 1
   if not (cfg.env.build_default_enable_nls >= 0 or cfg.env.build_default_enable_sls >= 0):
      # Rule out the "don't build anything" case by taking the simplest one.
      cfg.env.build_default_enable_sls = 1
   cfg.env.build_default_enable_ap = normalize_option_all(opts.enable_ap,1)
   cfg.env.build_default_enable_ex = normalize_option_all(opts.enable_ex,-1)
   if not (cfg.env.build_default_enable_ap >= 0 or cfg.env.build_default_enable_ex >= 0):
      # Rule out the "don't build anything" case by taking the simplest one.
      cfg.env.build_default_enable_ex = 1
   cfg.env.build_default_enable_wc = normalize_option_all(opts.enable_wc,1)
   cfg.env.build_default_enable_nc = normalize_option_all(opts.enable_nc,-1)
   if not (cfg.env.build_default_enable_wc >= 0 or cfg.env.build_default_enable_nc >= 0):
      # Rule out the "don't build anything" case by taking the simplest one.
      cfg.env.build_default_enable_nc = 1
   cfg.env.build_default_enable_mb = normalize_option_all(opts.enable_mb,1)
   cfg.env.build_default_enable_sb = normalize_option_all(opts.enable_sb,-1)
   if cfg.env.build_default_enable_wc < 0:
      # Multibyte reqires widecharacter
      cfg.env.build_default_enable_mb = -1
   if not (cfg.env.build_default_enable_mb >= 0 or cfg.env.build_default_enable_sb >= 0):
      # Rule out the "don't build anything" case by taking the simplest one.
      cfg.env.build_default_enable_sb = 1
   cfg.env.build_default_enable_ti = normalize_option_all(opts.enable_ti,1)
   cfg.env.build_default_enable_ri = normalize_option_all(opts.enable_ri,-1)
   if not (cfg.env.build_default_enable_ti >= 0 or cfg.env.build_default_enable_ri >= 0):
      # Rule out the "don't build anything" case by taking the simplest one.
      cfg.env.build_default_enable_ti = 1
   cfg.env.build_default_with_alloca = 1 if opts.with_alloca else -1
   if debug_build_defaults:
      msg = "type({:s}) {{{!s}}} val {{{!s}}}"
      Logs.pprint("PINK",msg.format("build_default_enable_nls",type(cfg.env.build_default_enable_nls),cfg.env.build_default_enable_nls))
      Logs.pprint("PINK",msg.format("build_default_enable_sls",type(cfg.env.build_default_enable_sls),cfg.env.build_default_enable_sls))
      Logs.pprint("PINK",msg.format("build_default_enable_ap",type(cfg.env.build_default_enable_ap),cfg.env.build_default_enable_ap))
      Logs.pprint("PINK",msg.format("build_default_enable_ex",type(cfg.env.build_default_enable_ex),cfg.env.build_default_enable_ex))
      Logs.pprint("PINK",msg.format("build_default_enable_wc",type(cfg.env.build_default_enable_wc),cfg.env.build_default_enable_wc))
      Logs.pprint("PINK",msg.format("build_default_enable_nc",type(cfg.env.build_default_enable_nc),cfg.env.build_default_enable_nc))
      Logs.pprint("PINK",msg.format("build_default_enable_mb",type(cfg.env.build_default_enable_mb),cfg.env.build_default_enable_mb))
      Logs.pprint("PINK",msg.format("build_default_enable_sb",type(cfg.env.build_default_enable_sb),cfg.env.build_default_enable_sb))
      Logs.pprint("PINK",msg.format("build_default_enable_ti",type(cfg.env.build_default_enable_ti),cfg.env.build_default_enable_ti))
      Logs.pprint("PINK",msg.format("build_default_enable_ri",type(cfg.env.build_default_enable_ri),cfg.env.build_default_enable_ri))
   #
   cfg.env.build_default_enable_agrep = Options.options.enable_agrep
   cfg.env.build_default_enable_python_extension = Options.options.enable_python_extension
   cfg.env.build_default_enable_tests = Options.options.enable_tests
   cfg.find_program('diff',var='DIFF') # Needed for some of the unit tests
   # ================= Package values
   cfg.define("PLATFORM_"+platsys,1)
   cfg.env["PLATFORM_"+platsys] = 1
   cfg.define("PACKAGE",package_name,"Name of package")
   cfg.define("PACKAGE_BUGREPORT","tre-general@lists.laurikari.net","Define to the address where bug reports for this package should be sent.")
   cfg.define("PACKAGE_NAME",package_name.upper(),"Define to the full name of this package.")
   cfg.define("PACKAGE_STRING",package_name.upper()+"_"+package_version,"Define to the full name and version of this package.")
   cfg.define("PACKAGE_TARNAME",package_name,"Define to the one symbol short name of this package.")
   cfg.define("PACKAGE_URL","","Define to the home page for this package.")
   cfg.define("PACKAGE_VERSION",package_version,"Define to the version of this package.")
   cfg.define("TRE_VERSION",package_version)
   cfg.env["TRE_VERSION"] = package_version
   cfg.define("TRE_VERSION_1",package_version_major)
   cfg.define("TRE_VERSION_2",package_version_minor)
   cfg.define("TRE_VERSION_3",package_version_miniscule)
   cfg.define("VERSION",package_version)
   cfg.define("_GNU_SOURCE",1) # only if gcc?
   # ================= Debug
   # FIXME - make this a rel/dbg variant
   cfg.define("NDEBUG",1,comment="Define if you want to disable debug assertions.")
   # ================= Configuration for C code
   cfg.load("compiler_c")
   if "freebsd" == platsys:
      # FreeBSD puts optional library headers into /usr/local/include,
      # so add that to the list of places to look before we test for headers.
      cfg.env.append_unique("INCLUDES",["/usr/local/include"])
      cfg.env.append_unique("CFLAGS",["-fPIC"])
   elif "linux" == platsys:
      cfg.env.append_unique("CFLAGS",["-fPIC"])
   elif "darwin" == platsys:
      # Only if later than Apple M1...
      # Logs.pprint("RED","CFLAGS {{{!s}}}".format(cfg.env.CFLAGS))
      # cfg.env.append_unique("CFLAGS",["-arch","arm64","-arch","x86_64"]) # fails to add 2nd "-arch" because it isn't unique
      cfg.env.CFLAGS += ["-arch","arm64","-arch","x86_64"]
      # We need the link flags for the dylib but they break the static lib
      cfg.env.LINKFLAGS += ["-arch","arm64","-arch","x86_64"]
   cfg.check(header_name="getopt.h", features="c cprogram", mandatory=False)
   cfg.define("HAVE_GETOPT_LONG",1)
   # Configuration defines for C can be on the compiler command line or in a header file.
   # We're going to put most of them into a header file called "config.h", with one define
   # on the command line ("-DHAVE_CONFIG_H") to indicate the header file should be included.
   # Waf manages the defines using a list (cfg.env.DEFINES) of "name=value" strings together
   # with list of names (in cfg.env["define_key"] by default) that are meant for the config file.
   # Any names not in the name list are meant for the compiler command line.  Writing the config
   # file will remove the named defines from the DEFINES list, leaving only the ones meant
   # for the compiler command line.
   cfg.env.append_unique("DEFINES","HAVE_CONFIG_H=1") # no entry in the list of names, so this ends up on the compiler command line.
   cfg.env.append_unique("DEFINES","USE_LOCAL_TRE_H=1") # no entry in the list of names, so this ends up on the compiler command line.
   # ================= Platform specific feature availability
   # Get a platform specific env for discovering what the platform has available.
   # It is derived from the original, so it has all the values set up above.
   cfg.setenv(platsys,cfg.env)
   platform_env = cfg.all_envs[platsys]
   platform_env.VARIANT = platsys
   platform_env.VARNAME = platsys
   # ----------------- Headers for the actual libraries
   lib_incs = [  # ( <file_name>, <mandatory>, <errmsg if not found> )
      ("stdlib.h",True,None),
      ("ctype.h",True,None),
      ("string.h",True,None),
      ("strings.h",True,None),
      ("limits.h",True,None),
      ("errno.h",True,None),
      ("stdint.h",False,None),
      ("unistd.h",False,None),
      ("iconv.h",False,None),
      ("inttypes.h",False,None),

      ("wctype.h",False,None), # guarded by TRE_WCHAR
      ("wchar.h",False,None),
      ("libutf8.h",False,None),

      ("stdio.h",False,None), # guarded by TRE_DEBUG
      ("libintl.h",False,None), # guarded by HAVE_GETTEXT

      ("dlfcn.h",False,None),

      ("sys/types.h",False,None), 
      ("sys/stat.h",False,None), 
      ("alloca.h",False,None), # the alloca() fn may be in the standard C library instead of its own header
      ("malloc.h",False,None),
      ("memory.h",False,None),
      ("regex.h",False,None),
      ("assert.h",True,None)]
   # Logs.pprint("CYAN","0 env.DEFINES {{{!s}}}".format(cfg.env.DEFINES))
   # Logs.pprint("CYAN","0 env.define_key {{{!s}}}".format(cfg.env.define_key))
   #
   feat = "c"
   for lib in lib_incs:
      # Make a basic check that "#include <inc>" can find the named header file using the C compiler with the header_name= keyword.
      # Add "HAVE_upper(inc)=1" to the cfg.env.DEFINES list if it is found (default action), and add the #include to
      # the included headers of following tests (auto_add_header_name=True).
      # The check() method also adds
      #    cfg.env["HAVE_upper(inc)"] = 1
      # on success.  cfg.env is a ConfigSet, which is similar to a dictionary, but among other differences,
      # it returns [] for keys not present, so testing for success of failure at a later point involves something like:
      #    if "HAVE_upper(inc)" in cfg.env.
      if None == lib[2]:
         cfg.check(features=feat,header_name=lib[0],mandatory=lib[1],auto_add_header_name=True)
      else:
         cfg.check(features=feat,header_name=lib[0],mandatory=lib[1],errmsg=lib[2],auto_add_header_name=True)
   regex_path = find_sys_regex_path(cfg)
   find_sys_regex_field(cfg)
   # Make the options consistent with the headers found.
   # The cfg.define() and cfg.undefine() methods manage both DEFINES and define_key lists,
   # so these will go into config.h (or nowhere) not the compiler command line.
   # Note that for FreeBSD, alloca() is part of the standard C library, it can be used without the header.
   if Options.options.with_alloca and ("freebsd" == platsys or cfg.is_defined("HAVE_ALLOCA_H")):
      if debug_build_config_envs > 0 or (None != debug_specific_config_env):
         Logs.pprint("YELLOW","attempting to set TRE_USE_ALLOCA")
      cfg.define("TRE_USE_ALLOCA",1)
   else:
      # We don't want or can't find alloca.
      if debug_build_config_envs > 0 or (None != debug_specific_config_env):
         Logs.pprint("YELLOW","attempting to unset TRE_USE_ALLOCA")
      cfg.undefine("TRE_USE_ALLOCA")
   # Look for things in the platform, so we know what's available.
   # Some of these get copied into the variation environments as appropriate.
   fn_or_mac_frag="""
      int main(int argc, char **argv)
        {{
         {:s}
         (void) argc; (void) argv;
         return(0);}}
   """
   fn_or_mac_list = [
      # (env_key,   key_in/out, define_name,  mandatory, message,
      #     test_fragment)
      # where:
      #    env_key is
      #       None
      #       str as conditional _______________--
      (None,             True, "HAVE_ALLOCA",    False, "Checking for function alloca()",
         'char *foo; foo = (char *) alloca((size_t)10);'),
      ("HAVE_WCHAR_H",   True, "HAVE_WCHAR_T",   False, "Checking for type wchar_t",
         'wchar_t foo;'),
      ("HAVE_WCHAR_H",   True, "HAVE_MBSTATE_T", False, "Checking for type mbstate_t",
         'mbstate_t foo;'),
      ("HAVE_WCHAR_H",   True, "HAVE_MBRTOWC",   False, "Checking for function mbrtowc()",
         'mbstate_t state; wchar_t out[10]; size_t nb = mbrtowc(out,"xxxx",4,&state);'),
      ("HAVE_WCHAR_H",   False,"HAVE_MBTOWC",    False, "Checking for function mbtowc()",
         'wchar_t out[10]; int nb = mbtowc(out,"xxxx",4);'),
      ("HAVE_WCHAR_H",   False,"HAVE_WCSRTOMBS", False, "Checking for function wcsrtombs()",
         'char dst[10]; wchar_t src[10]; mbstate_t ps; size_t foo = wcsrtombs(out,&src,(size_t)10,&ps);'),
      ("HAVE_CTYPE_H",   True, "HAVE_ISASCII",   False, "Checking for function isascii()",
         'int foo = isascii(32);'),
      ("HAVE_CTYPE_H",   True, "HAVE_ISBLANK",   False, "Checking for function isblank()",
         'int foo = isblank(32);'),
      ("HAVE_CTYPE_H",   True, "HAVE_TOLOWER",   False, "Checking for function tolower()",
         'int foo = isblank(32);'),
      ("HAVE_CTYPE_H",   True, "HAVE_TOUPPER",   False, "Checking for function toupper()",
         'int foo = isblank(32);'),
      ("HAVE_WCTYPE_H",  True, "HAVE_WINT_T",    False, "Checking for type wint_t",
         'wint_t foo;'),
      ("HAVE_WCTYPE_H",  True, "HAVE_WCTYPE",    False, "Checking for type wctype",
         'wctype_t foo;'),
      ("HAVE_WCTYPE_H",  True, "HAVE_ISWCTYPE",  False, "Checking for function iswctype()",
         'int foo = iswctype((wint_t)1,(wctype_t)2);'),
      ("HAVE_WINT_T",    True, "HAVE_ISWASCII",  False, "Checking for function iswascii()",
         'int foo = iswascii((wint_t)32);'),
      ("HAVE_WINT_T",    True, "HAVE_ISWBLANK",  False, "Checking for function iswblank()",
         'int foo = iswblank((wint_t)32);'),
      ("HAVE_WINT_T",    True, "HAVE_ISWLOWER",  False, "Checking for function iswlower()",
         'int foo = iswlower((wint_t)32);'),
      ("HAVE_WINT_T",    True, "HAVE_ISWUPPER",  False, "Checking for function iswupper()",
         'int foo = iswupper((wint_t)32);'),
      ("HAVE_WINT_T",    True, "HAVE_TOWLOWER",  False, "Checking for function towlower()",
         'wint_t foo = towlower((wint_t)32);'),
      ("HAVE_WINT_T",    True, "HAVE_TOWUPPER",  False, "Checking for function towupper()",
         'wint_t foo = towupper((wint_t)32);'),
      ("HAVE_WCHAR_T",   True, "HAVE_WCSCHR",    False, "Checking for function wcschr()",
         'wchar_t *foo = wcschr((wchar_t *)NULL,(wchar_t)32);'),
      ("HAVE_WCHAR_T",   True, "HAVE_WCSCPY",    False, "Checking for function wcscpy()",
         'wchar_t *foo = wcscpy((wchar_t *)NULL,(wchar_t *)NULL);'),
      ("HAVE_WCHAR_T",   True, "HAVE_WCSLEN",    False, "Checking for function wcslen()",
         'size_t foo = wcslen((wchar_t *)NULL);'),
      ("HAVE_WCHAR_T",   True, "HAVE_WCSNCPY",   False, "Checking for function wcsncpy()",
         'wchar_t *foo = wcsncpy((wchar_t *)NULL,(wchar_t *)NULL,(size_t)32);'),
      ("HAVE_WCHAR_T",   True, "HAVE_WCSRTOMBS", False, "Checking for function wcsrtombs()",
         'size_t foo = wcsrtombs((char *)NULL,(wchar_t **)NULL,(size_t)32,(mbstate_t *)NULL);'),
      ("HAVE_ICONV_H",   True, "HAVE_ICONV",     False, "Checking for function iconv()",
         'iconv_t foo; size_t bar = iconv(foo,(char**)NULL,(size_t*)NULL,(char **)NULL,(size_t*)NULL);'),
      ("HAVE_LIBINTL_H", True, "HAVE_GETTEXT",   False, "Checking for function gettext()",
         'char *foo = gettext("msgid");'),
      ("HAVE_LIBINTL_H", True, "HAVE_DCGETTEXT", False, "Checking for function dcgettext()",
         'char *foo = dcgettext("domain","msgid",1);'),
      ("HAVE_REGEX_H",   True, "HAVE_REG_ERRCODE_T", False, "Checking for type reg_errcode_t",
         "reg_errcode_t foo;"),
   ]
   for fntest in fn_or_mac_list:
      if debug_build_config_envs > 0 or (None != debug_specific_config_env):
         Logs.pprint("YELLOW","Considering fn or mac {{{:s}}}".format(fntest[2]))
      if (None == fntest[0] or
          (fntest[1] and cfg.is_defined(fntest[0])) or
          (not fntest[1] and not cfg.is_defined(fntest[0]))):
         if debug_build_config_envs > 0 or (None != debug_specific_config_env):
            Logs.pprint("YELLOW","prereqs OK for fn or mac {{{:s}}}".format(fntest[2]))
         cfg.check(features=feat,define_name=fntest[2],mandatory=fntest[3],msg=fntest[4],fragment=fn_or_mac_frag.format(fntest[5]))
   # Logs.pprint("RED","Finished determining platform feature availability")
   if "freebsd" == platsys or "linux" == platsys:
      # cfg.define("LT_OBJDIR",".libs/") # Libtool stuff???
      cfg.define("STDC_HEADERS",1)
   # Return from the platform availability env to the original one.
   cfg.setenv("")
   #===========================================================================
   # Configure for all combinations of build variants, regardless of any options.
   # This will actually build multiple config environments because conf.setenv("foo",old_env)
   # makes a shallow copy of old_env named foo if one doesn't already exist.
   # Note that the name of the default env is the empty string "".
   build_variants.create_variants(cfg,variant_group_list,variant_name_path_list)
   # Create the defines for the variants considering what is available on this platform.
   for vpair in variant_name_path_list:
      cfg.setenv(vpair[1])
      gather_env_for_variant(cfg)
   # Return to the original env.
   cfg.setenv("")
   if debug_build_config_envs > 0 or None != debug_specific_config_env:
      Logs.pprint("RED","# 0 ################################ configuration environments:")
      if None == debug_specific_config_env:
         for env_key in cfg.all_envs:
            Logs.pprint("GREEN","env({:s}) len(DEFINES)={:d}".format(env_key,len(cfg.all_envs[env_key].DEFINES)))
            Logs.pprint("YELLOW","{!s}".format(cfg.all_envs[env_key]))
      else:
         Logs.pprint("GREEN","env({:s}) len(DEFINES)={:d}".format(debug_specific_config_env,
                                                                  len(cfg.all_envs[debug_specific_config_env].DEFINES)))
         Logs.pprint("YELLOW","{!s}".format(cfg.all_envs[debug_specific_config_env]))
   # --- Now look at any configuration needed in the subdirectories.
   # Logs.pprint('NORMAL','starting configure/recurse(lib)')
   cfg.recurse("lib")
   if debug_build_config_envs > 0 or None != debug_specific_config_env:
      Logs.pprint("RED","# lib ################################## configuration environments:")
      if None == debug_specific_config_env:
         for env_key in cfg.all_envs:
            Logs.pprint("GREEN","env({:s}) len(DEFINES)={:d}".format(env_key,len(cfg.all_envs[env_key].DEFINES)))
      else:
         Logs.pprint("GREEN","env({:s}) len(DEFINES)={:d}".format(debug_specific_config_env,
                                                                  len(cfg.all_envs[debug_specific_config_env].DEFINES)))
   cfg.recurse("src")
   if debug_build_config_envs > 0 or None != debug_specific_config_env:
      Logs.pprint("RED","# src ################################## configuration environments:")
      if None == debug_specific_config_env:
         for env_key in cfg.all_envs:
            Logs.pprint("GREEN","env({:s}) len(DEFINES)={:d}".format(env_key,len(cfg.all_envs[env_key].DEFINES)))
      else:
         Logs.pprint("GREEN","env({:s}) len(DEFINES)={:d}".format(debug_specific_config_env,
                                                                  len(cfg.all_envs[debug_specific_config_env].DEFINES)))
   cfg.recurse("python")
   if debug_build_config_envs > 0 or None != debug_specific_config_env:
      Logs.pprint("RED","# python ################################## configuration environments:")
      if None == debug_specific_config_env:
         for env_key in cfg.all_envs:
            Logs.pprint("GREEN","env({:s}) len(DEFINES)={:d}".format(env_key,len(cfg.all_envs[env_key].DEFINES)))
      else:
         Logs.pprint("GREEN","env({:s}) len(DEFINES)={:d}".format(debug_specific_config_env,
                                                                  len(cfg.all_envs[debug_specific_config_env].DEFINES)))
   # cfg.recurse("po")
   if debug_build_config_envs > 0 or None != debug_specific_config_env:
      Logs.pprint("RED","# po ################################## configuration environments:")
      if None == debug_specific_config_env:
         for env_key in cfg.all_envs:
            Logs.pprint("GREEN","env({:s}) len(DEFINES)={:d}".format(env_key,len(cfg.all_envs[env_key].DEFINES)))
      else:
         Logs.pprint("GREEN","env({:s}) len(DEFINES)={:d}".format(debug_specific_config_env,
                                                                  len(cfg.all_envs[debug_specific_config_env].DEFINES)))
   cfg.recurse("tests")
   if debug_build_config_envs > 0 or None != debug_specific_config_env:
      Logs.pprint("RED","# < write ############################## configuration environments:")
      if None == debug_specific_config_env:
         for env_key in cfg.all_envs:
            Logs.pprint("GREEN","env({:s}) len(DEFINES)={:d}".format(env_key,len(cfg.all_envs[env_key].DEFINES)))
      else:
         Logs.pprint("GREEN","env({:s}) len(DEFINES)={:d}".format(debug_specific_config_env,
                                                                  len(cfg.all_envs[debug_specific_config_env].DEFINES)))
   # Create the variant directory structure, write the headers, and choose a default variant.
   default_variant_name = None
   default_variant_value = -1
   for vpair in cfg.variant_name_path_list:
      env_key = vpair[1]
      venv = cfg.all_envs[env_key]
      cfg.setenv(env_key)
      if not cfg.env.viable:
         continue
      if None == default_variant_name or build_variants.variant_value(cfg.env.VARNAME,variant_group_list) > default_variant_value:
         default_variant_name = cfg.env.VARNAME
         default_variant_value = build_variants.variant_value(default_variant_name,variant_group_list)
      # Note that writing this header removes the written defines from the env.
      Logs.pprint("GREEN","Writing configuration header file {:s}".format(venv.VARIANT+"/config.h"))
      cfg.write_config_header(configfile=venv.VARIANT+"/config.h")
   # Return to the original config after messing with variants.
   cfg.setenv("")
   # Set a default variant for the build.
   Logs.pprint("GREEN","Setting default variant to {:s}".format(default_variant_name))
   cfg.env.default_variant_name = default_variant_name
   if debug_final_config_envs > 0 or None != debug_specific_config_env:
      Logs.pprint("RED","# F ################################ final configuration environments (after header defns removed):")
      if None == debug_specific_config_env:
         for env_key in cfg.all_envs:
            Logs.pprint("GREEN","env({:s}) len(DEFINES)={:d}".format(env_key,len(cfg.all_envs[env_key].DEFINES)))
            Logs.pprint("YELLOW","{!s}".format(cfg.all_envs[env_key]))
      else:
         Logs.pprint("GREEN","env({:s}) len(DEFINES)={:d}".format(debug_specific_config_env,
                                                                  len(cfg.all_envs[debug_specific_config_env].DEFINES)))
         Logs.pprint("YELLOW","{!s}".format(cfg.all_envs[debug_specific_config_env]))

# # When running the C compiler we want to be able to find the config.h header file
# # that was put into the build directory with cfg.write_config_header() above.  Rather
# # than mess arround with levels of '..' in the lower level wscripts, just add the
# # absolute path once whenever we use the 'c' feature.
# #
# # Reminder: the "@foo[(args)]" notation essentially "wraps" the function following and
# # returns the wrapped function.  In this case, we are wrapping include_tre_config_h()
# # in the "after_method('apply_incpaths')" wrapper, and then wrapping the result even
# # further in the "feature('c')" wrapper, both from TaskGen.  The end result is that the
# # include_tre_config_h() function will be called as part of generating any Task that uses
# # the 'c' feature sometime after the generator has called the 'apply_incpaths' method.
# # Python calls this pattern "decoration", but the GoF book calls it something else.
# 
# from waflib.TaskGen import feature,after_method
# 
# debug_include_tre_config_h = False
# 
# @feature('c')
# @after_method('apply_incpaths')
# def include_tre_config_h(self):
#    if debug_include_tre_config_h or True:
#       Logs.pprint("PINK","running include_tre_config_h() for path {:s}".format(self.bld.bldnode.abspath()))
#       Logs.pprint("YELLOW","  include_tre_config_h() self {!s}".format(type(self)))
#       Logs.pprint("YELLOW","  include_tre_config_h() self.bld {!s}".format(type(self.bld)))
#       Logs.pprint("YELLOW","  include_tre_config_h() self.bld.path {!s}".format(self.bld.path.abspath()))
#    # bld.bldnode is the top level build directory
#    # bld.srcnode is the top level source directory
#    # path.get_bld() is the node in the build directory
#    # path.get_src() is the node in the source directory
#    # self.env.append_unique('INCPATHS',self.bld.bldnode.abspath())
#    self.env.append_unique('INCLUDES',self.bld.bldnode.abspath())
#    self.env.append_unique('INCLUDES',self.bld.path.get_bld().abspath())
#    self.env.append_unique('INCLUDES',self.bld.path.get_src().abspath())

def build(bld):
   # This function builds the list of targets, not the targets themselves.
   # It is acutally used for clean/install/uninstall as well, since they all
   # use the same list of targets.
   # Once this function completes, waf starts running build/clean/install/uninstall
   # tasks in the various groups to do the actual work.
   if Options.options.log_wscripts:
      Logs.pprint("NORMAL","entering build(), cmd={:s}, variant={:s}.".format(bld.cmd,bld.variant))
      # Logs.pprint("CYAN","CFLAGS={!s}".format(bld.env.CFLAGS))
   # debug_include_tre_config_h = False
   # if debug_include_tre_config_h:
   #    Logs.pprint("GREEN","debug_include_tre_config_h set to True")
   # The options are set each time waf is invoked, so we want a fresh look at the build_tests
   # option when we start to build, rather than one saved from the waf configure.
   # We also don't want to build/run the tests for installs/cleans, so make sure the cmd is build or list.
   setattr(bld,'changeable_task_group',(bld.cmd.startswith('build') or bld.cmd.startswith('list')))
   if bld.changeable_task_group:
      # Build and run the tests if (a) explicitly enabled for this command,
      # or (b) not explicitly disabled for both this command and the eariler configuration.
      bld.env['BUILD_TESTS'] = (Options.options.enable_tests > 0 or
                                (Options.options.enable_tests == 0 and getattr(bld.env,"build_default_enable_tests",0) >= 0))
      # Set up two task groups, one for building and one for testing.
      for task_group_name in 'build_tasks test_tasks'.split():
        if not task_group_name in bld.group_names:
           bld.add_group(task_group_name)
      # Start out in the normal build group.
      bld.set_group('build_tasks')
   else:
      bld.env['BUILD_TESTS'] = False
   # Build the actual library.
   bld.recurse("lib")
   # Set up the info for header installation.
   bld.recurse("local_includes")
   # Build agrep if requested (it won't build unless approximate matching is enabled).
   opt_agrep = normalize_option(Options.options.enable_agrep,0)
   if bld.env.variant_ap and (opt_agrep > 0 or (opt_agrep == 0 and bld.env.build_default_enable_agrep > 0)):
      bld.recurse("src")
   # Build the python extension if requested.
   opt_py = normalize_option(Options.options.enable_python_extension,0)
   if opt_py > 0 or (opt_py == 0 and bld.env.build_default_enable_python_extension > 0):
      bld.recurse("python")
   # Both agrep and the python extension might use the .po files
   # if bld.env.enable_agrep or bld.env.enable_python_extension:
   #    bld.recurse("po")
   # Build and run the tests if requested.
   if bld.env.BUILD_TESTS and bld.changeable_task_group:
      bld.recurse("tests")
