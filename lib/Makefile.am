## Process this file with automake to produce Makefile.in
lib_LTLIBRARIES = libtre.la
libtre_la_LDFLAGS = -no-undefined -version-info 5:0:0 $(LDFLAGS)
libtre_la_LIBADD = $(LTLIBINTL)
AM_CPPFLAGS = -I$(top_srcdir)/include/tre

noinst_HEADERS =		\
	tre-ast.h		\
	tre-compile.h		\
	tre-internal.h		\
	tre-match-utils.h	\
	tre-mem.h		\
	tre-parse.h		\
	tre-stack.h		\
	xmalloc.h

libtre_la_SOURCES =		\
	tre-ast.c		\
	tre-compile.c		\
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
