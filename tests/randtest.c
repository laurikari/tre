/*
  randtest.c - tests with random regexps

  Copyright (C) 2001, 2002 Ville Laurikari <vl@iki.fi>

  This program is free software; you can redistribute it and/or modify
  it under the terms of the GNU General Public License version 2 (June
  1991) as published by the Free Software Foundation.

  This program is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU General Public License for more details.

  You should have received a copy of the GNU General Public License
  along with this program; if not, write to the Free Software
  Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

*/

#ifdef HAVE_CONFIG_H
#include <config.h>
#endif /* HAVE_CONFIG_H */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <regex.h>
#include <time.h>

#undef MALLOC_DEBUGGING
#ifdef MALLOC_DEBUGGING
#include "xmalloc.h"
#endif /* MALLOC_DEBUGGING */

#define REGEXP_MAX_LEN 16

int
main(int argc, char **argv)
{
  int len, i, flags, n;
  char regex[50];
  char *buf;
  regex_t preg;
  int status, seed;

  seed = time(NULL);
  seed = 1028358583;
  printf("seed = %d\n", seed);
  srand(seed);
  n = 0;

  for (n = 0; n < 0; n++)
    rand();

  while (1)
    {
      printf("*");
      fflush(stdout);

      printf("n = %d\n", n);
      len = 1 + (int)(REGEXP_MAX_LEN * (rand() / (RAND_MAX + 1.0)));
      n++;

      for (i = 0; i < len; i++)
	{
	  regex[i] = 1 + (int)(255 * (rand() / (RAND_MAX + 1.0)));
	  n++;
	}
      regex[i] = L'\0';

      printf("len = %d, regexp = \"%s\"\n", len, regex);

      for (flags = 0;
	   flags < (REG_EXTENDED | REG_ICASE | REG_NEWLINE | REG_NOSUB);
	   flags++)
	{
	  buf = malloc(sizeof(*buf) * len);
	  strncpy(buf, regex, len - 1);
	  status = regncomp(&preg, buf, len, flags);
	  if (status == REG_OK)
	    regfree(&preg);
	}
      printf("\n");
    }

  return 0;
}
