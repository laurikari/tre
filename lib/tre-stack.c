/*
  tre-stack.c - Simple stack implementation

  Copyright (C) 2001-2006 Ville Laurikari <vl@iki.fi>

  This library is free software; you can redistribute it and/or
  modify it under the terms of the GNU Lesser General Public
  License as published by the Free Software Foundation; either
  version 2.1 of the License, or (at your option) any later version.

  This library is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
  Lesser General Public License for more details.

  You should have received a copy of the GNU Lesser General Public
  License along with this library; if not, write to the Free Software
  Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

*/

#ifdef HAVE_CONFIG_H
#include <config.h>
#endif /* HAVE_CONFIG_H */
#include <stdlib.h>
#include <assert.h>

#include "tre-stack.h"
#include "tre-internal.h"
#include "xmalloc.h"

struct tre_stack_rec {
  int size;
  int max_size;
  int increment;
  int ptr;
  void **stack;
};


tre_stack_t *
tre_stack_new(int size, int max_size, int increment)
{
  tre_stack_t *s;

  s = xmalloc(sizeof(*s));
  if (s != NULL)
    {
      s->stack = xmalloc(sizeof(*s->stack) * size);
      if (s->stack == NULL)
	{
	  xfree(s);
	  return NULL;
	}
      s->size = size;
      s->max_size = max_size;
      s->increment = increment;
      s->ptr = 0;
    }
  return s;
}

void
tre_stack_destroy(tre_stack_t *s)
{
  xfree(s->stack);
  xfree(s);
}

int
tre_stack_num_objects(tre_stack_t *s)
{
  return s->ptr;
}

reg_errcode_t
tre_stack_push(tre_stack_t *s, void *value)
{
  if (s->ptr < s->size)
    {
      s->stack[s->ptr] = value;
      s->ptr++;
    }
  else
    {
      if (s->size >= s->max_size)
	{
	  DPRINT(("tre_stack_push: stack full\n"));
	  return REG_ESPACE;
	}
      else
	{
	  void **new_buffer;
	  int new_size;
	  DPRINT(("tre_stack_push: trying to realloc more space\n"));
	  new_size = s->size + s->increment;
	  if (new_size > s->max_size)
	    new_size = s->max_size;
	  new_buffer = xrealloc(s->stack, sizeof(*new_buffer) * new_size);
	  if (new_buffer == NULL)
	    {
	      DPRINT(("tre_stack_push: realloc failed.\n"));
	      return REG_ESPACE;
	    }
	  DPRINT(("tre_stack_push: realloc succeeded.\n"));
	  assert(new_size > s->size);
	  s->size = new_size;
	  s->stack = new_buffer;
	  tre_stack_push(s, value);
	}
    }
  return REG_OK;
}

void *
tre_stack_pop(tre_stack_t *s)
{
  return s->stack[--s->ptr];
}

/* EOF */
