## Process this file with automake to produce Makefile.in

lib_LTLIBRARIES = libtre.la
libtre_la_LDFLAGS = -version-info 6:2:2 $(LDFLAGS)
libtre_la_LIBADD = $(LTLIBINTL)

noinst_HEADERS =		\
	tre-ast.h		\
	tre-compile.h		\
	tre-filter.h		\
	tre-internal.h		\
	tre-match-utils.h	\
	tre-mem.h		\
	tre-parse.h		\
	tre-stack.h		\
	xmalloc.h		\
	gettext.h

libtre_la_SOURCES =		\
	tre-ast.c		\
	tre-compile.c		\
	tre-filter.c		\
	tre-match-backtrack.c	\
	tre-match-parallel.c	\
	tre-mem.c		\
	tre-parse.c		\
	tre-stack.c		\
	regcomp.c		\
	regexec.c		\
	regerror.c

if TRE_APPROX
libtre_la_SOURCES += tre-match-approx.c
endif TRE_APPROX

dist_pkginclude_HEADERS = regex.h
nodist_pkginclude_HEADERS = tre-config.h
