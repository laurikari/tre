/*
  test-str-source.c - Sample program for using tre_reguexec()
                      It also serves as a sanity check for correct
                      linkage when multiple variants of the TRE library 
                      are present.

  This software is released under a BSD-style license.
  See the file LICENSE for details and copyright.

*/

#ifdef HAVE_CONFIG_H
#include <config.h>
#endif /* HAVE_CONFIG_H */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
/* look for getopt in order to use a -o option for output. */
#include <unistd.h>

#include "tre-internal.h"

static FILE *output_fd = NULL;

/* Context structure for the tre_str_source wrappers.  */
typedef struct {
  /* Our string. */
  const char *str;
  /* Current position in the string. */
  size_t pos;
} str_handler_ctx;

/* The get_next_char() handler.  Sets `c' to the value of the next character,
   and increases `pos_add' by the number of bytes read.  Returns 1 if the
   string has ended, 0 if there are more characters. */
static int
str_handler_get_next(tre_char_t *c, unsigned int *pos_add, void *context)
{
  str_handler_ctx *ctx = context;
  unsigned char ch = ctx->str[ctx->pos];

  fprintf(output_fd,"str[%lu] = %d\n", (unsigned long)ctx->pos, ch);
  *c = ch;
  if (ch)
    ctx->pos++;
  *pos_add = 1;

  return ch == '\0';
}

/* The rewind() handler.  Resets the current position in the input string. */
static void
str_handler_rewind(size_t pos, void *context)
{
  str_handler_ctx *ctx = context;

  fprintf(output_fd,"rewind to %lu\n", (unsigned long)pos);
  ctx->pos = pos;
}

/* The compare() handler.  Compares two substrings in the input and returns
   0 if the substrings are equal, and a nonzero value if not. */
static int
str_handler_compare(size_t pos1, size_t pos2, size_t len, void *context)
{
  str_handler_ctx *ctx = context;
  fprintf(output_fd,"comparing %lu-%lu and %lu-%lu\n",
	 (unsigned long)pos1, (unsigned long)pos1 + len,
	 (unsigned long)pos2, (unsigned long)pos2 + len);
  return strncmp(ctx->str + pos1, ctx->str + pos2, len);
}

/* Creates a tre_str_source wrapper around the string `str'.  Returns the
   tre_str_source object or NULL if out of memory. */
static tre_str_source *
make_str_source(const char *str)
{
  tre_str_source *s;
  str_handler_ctx *ctx;

  s = calloc(1, sizeof(*s));
  if (!s)
    {
      fprintf(stderr,"Could not calloc(1,sizeof(tre_str_source)\n");
      return NULL;
    }

  ctx = malloc(sizeof(str_handler_ctx));
  if (!ctx)
    {
      fprintf(stderr,"Could not malloc(sizeof(str_handler_ctx)\n");
      free(s);
      return NULL;
    }

  ctx->str = str;
  ctx->pos = 0;
  s->context = ctx;
  s->get_next_char = str_handler_get_next;
  s->rewind = str_handler_rewind;
  s->compare = str_handler_compare;

  return s;
}

/* Frees the memory allocated for `s'. */
static void
free_str_source(tre_str_source *s)
{
  free(s->context);
  free(s);
}

/* Run one test with tre_reguexec */
static void
test_reguexec(const char *str, const char *regex)
{
  reg_errcode_t ec;
  regex_t preg;
  tre_str_source *source;
  regmatch_t pmatch[5];

  source = make_str_source(str);
  if (!source)
    return;

  ec = tre_regcomp(&preg, regex, REG_EXTENDED);
  if (ec != REG_OK)
    {
      fprintf(output_fd,"Pattern {%s} failed to compile, err code 0x%08x\n", regex, (unsigned)ec);
    }
  else if ((ec = tre_reguexec(&preg, source, elementsof(pmatch), pmatch, 0)) == 0)
    fprintf(output_fd,"Match: %d - %d\n", (int)pmatch[0].rm_so, (int)pmatch[0].rm_eo);
  else
    {
      fprintf(output_fd,"Match pattern {%s} against string {%s} failed, err code 0x%08x\n", regex, str, (unsigned)ec);
    }

  free_str_source(source);
  tre_regfree(&preg);
}

int
main(int argc, char **argv)
{
  int ch;
  int rc;
  int query;
  int int_res;
  int desired_config;
  int config_mismatch = 0;
  char *char_res;
  output_fd = stdout;
  while ((ch = getopt(argc,argv,"o:") != EOF))
    {
      switch (ch)
	{
	  case 'o':
	    if ((output_fd = fopen(optarg,"w")) == NULL)
	      {
		fprintf(stderr,"Could not open {%s} for output, quitting\n", optarg);
		exit(1);
	      }
	    break;
	  default:
	    fprintf(stderr,"Invalid command line option '-%c', quitting\n", ch);
	    if (output_fd != NULL && stdout != output_fd)
	      {
		fclose(output_fd);
		output_fd = NULL;
	      }
	    exit(1);
	}
    }

  /* Display the version and configuation of the TRE library we are using. */
  fprintf(output_fd,"Using TRE library version: %s\n", tre_version());
  fprintf(output_fd,"   test compiled for version: %s\n", TRE_VERSION);

  query = (int) TRE_CONFIG_APPROX;
  int_res = -1;
  rc = tre_config(query,&int_res);
#ifdef TRE_APPROX
  desired_config = 1;
#else
  desired_config = 0;
#endif
  fprintf(output_fd,"  TRE_CONFIG_APPROX: library %d (rc=%d) test compiled for %d\n", int_res, rc, desired_config);
  config_mismatch |= (int_res != desired_config);

  query = (int) TRE_CONFIG_WCHAR;
  int_res = -1;
  rc = tre_config(query,&int_res);
#ifdef TRE_WCHAR
  desired_config = 1;
#else
  desired_config = 0;
#endif
  fprintf(output_fd,"  TRE_CONFIG_WCHAR: library %d (rc=%d) test compiled for %d\n", int_res, rc, desired_config);
  config_mismatch |= (int_res != desired_config);

  query = (int) TRE_CONFIG_MULTIBYTE;
  int_res = -1;
  rc = tre_config(query,&int_res);
#ifdef TRE_MULTIBYTE
  desired_config = 1;
#else
  desired_config = 0;
#endif
  fprintf(output_fd,"  TRE_CONFIG_MULTIBYTE: library %d (rc=%d) test compiled for %d\n", int_res, rc, desired_config);
  config_mismatch |= (int_res != desired_config);

  query = (int) TRE_CONFIG_SYSTEM_ABI;
  int_res = -1;
  rc = tre_config(query,&int_res);
#ifdef TRE_CONFIG_SYSTEM_ABI
  desired_config = 1;
#else
  desired_config = 0;
#endif
  fprintf(output_fd,"  TRE_CONFIG_SYSTEM_ABI: library %d (rc=%d) test compiled for %d\n", int_res, rc, desired_config);
  config_mismatch |= (int_res != desired_config);

  query = (int) TRE_CONFIG_VERSION;
  char_res = "---";
  rc = tre_config(query,&char_res);
  fprintf(output_fd,"  TRE_CONFIG_VERSION: {%s} (rc=%d)\n", char_res, rc);

  if (config_mismatch)
    {
      fprintf(output_fd,"WARNING: The configuration this test program was compiled with is not the same");
      fprintf(output_fd,"as the configuration of the libtre being used, some tests may be incorrect.\n");
    }

  fprintf(output_fd,"------------------ Test 1: should Match: 6 - 12\n");
  test_reguexec("xfoofofoofoo","(foo)\\1");
  fprintf(output_fd,"------------------ Test 2: should Match: 0 - 6\n");
  test_reguexec("catcat","(cat|dog)\\1");
  fprintf(output_fd,"------------------ Test 3: should not match\n");
  test_reguexec("catdog","(cat|dog)\\1");
  fprintf(output_fd,"------------------ Test 4: should Match: 0 - 6\n");
  test_reguexec("dogdog","(cat|dog)\\1");
  fprintf(output_fd,"------------------ Test 5: should not match\n");
  test_reguexec("dogcat","(cat|dog)\\1");

  if (NULL != output_fd && stdout != output_fd)
    {
      fclose(output_fd);
      output_fd = NULL;
    }
  return 0;
}
