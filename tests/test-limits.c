#ifdef HAVE_CONFIG_H
#include <config.h>
#endif /* HAVE_CONFIG_H */

#include <limits.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifdef USE_SYSTEM_REGEX
# include <regex.h>
# ifndef REG_BASIC
#  define REG_BASIC 0
# endif
# ifndef REG_OK
#  define REG_OK 0
# endif
#else
# include "tre-internal.h"
# define regcomp tre_regcomp
# define regexec tre_regexec
# define regfree tre_regfree
#endif

#define MIN_SHIFT 2
#define MAX_SHIFT 32

static int ntests, nok;

static void ok(void) { fputc('+', stderr); ntests++; nok++; }
static void notok(void) { fputc('-', stderr); ntests++; }
static void done(void) { fputc('\n', stderr); exit(nok == ntests ? 0 : 1); }
#define check(expr) do { ((expr) ? ok() : notok()); } while (0)

int
main(void)
{
  regmatch_t pm[9];
  regex_t preg;
  size_t npm = sizeof(pm) / sizeof(pm[0]);
  size_t size;
  char *buf;
  int error, expect, shift;

  if ((size = 1ULL << MAX_SHIFT) == 0 || (buf = malloc(size + 1)) == NULL) {
    notok();
  } else {
    memset(buf, 'a', size);
    buf[size] = '\0';
    for (shift = MIN_SHIFT; shift <= MAX_SHIFT; shift++) {
      fprintf(stderr, "%d", shift);
      if ((size = 1ULL << shift) == 0) {
	notok();
	continue;
      }
      buf[0] = buf[size - 1] = 'x';
      buf[size] = '\0';

#ifdef USE_SYSTEM_REGEX
      expect = REG_OK;
#else
      /* expected outcome of regcomp() for a regex this size */
      expect = size <= TRE_MAX_RE ? REG_OK : REG_ESPACE;
#endif

      /* compile a BRE size characters long */
      error = regcomp(&preg, buf, REG_BASIC);
      if (error != expect) {
	notok();
      } else if (error == REG_OK) {
	ok();
	regfree(&preg);
      } else {
	ok();
      }

      /* compile an ERE size characters long */
      error = regcomp(&preg, buf, REG_EXTENDED);
      if (error != expect) {
	notok();
      } else if (error == REG_OK) {
	ok();
	regfree(&preg);
      } else {
	ok();
      }

#ifdef USE_SYSTEM_REGEX
      expect = REG_OK;
#else
      /* expected outcome of regexec() for a string this size */
      expect = size <= TRE_MAX_STRING ? REG_OK : REG_NOMATCH;
#endif

      /* match a BRE with a string size characters long */
      error = regcomp(&preg, "x\\(aa*\\)x", REG_BASIC);
      if (error == REG_OK) {
	ok();
	error = regexec(&preg, buf, npm, pm, 0);
	if (error != expect) {
	  notok();
	} else if (error == REG_OK) {
	  ok();
	  check(pm[0].rm_so == 0 && (size_t)pm[0].rm_eo == size);
	  check(pm[1].rm_so == 1 && (size_t)pm[1].rm_eo == size - 1);
	} else {
	  ok();
	}
	regfree(&preg);
      } else {
	notok();
      }

      /* match an ERE with a string size characters long */
      error = regcomp(&preg, "x(a+)x", REG_EXTENDED);
      if (error == REG_OK) {
	ok();
	error = regexec(&preg, buf, npm, pm, 0);
	if (error != expect) {
	  notok();
	} else if (error == REG_OK) {
	  ok();
	  check(pm[0].rm_so == 0 && (size_t)pm[0].rm_eo == size);
	  check(pm[1].rm_so == 1 && (size_t)pm[1].rm_eo == size - 1);
	} else {
	  ok();
	}
	regfree(&preg);
      } else {
	notok();
      }

      /* undo our changes to the buffer */
      buf[0] = buf[size - 1] = buf[size] = 'a';
      fflush(stderr);
    }
    free(buf);
  }
  done();
}
