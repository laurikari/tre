/*
  tre-stack.h: Stack definitions

  Copyright (C) 2001-2004 Ville Laurikari <vl@iki.fi>

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


#ifndef TRE_STACK_H
#define TRE_STACK_H 1

#include "regex.h"

typedef struct tre_stack_rec tre_stack_t;

/* Creates a new stack object.	`size' is initial size in bytes, `max_size'
   is maximum size, and `increment' specifies how much more space will be
   allocated with realloc() if all space gets used up.	Returns the stack
   object or NULL if out of memory. */
tre_stack_t *
tre_stack_new(int size, int max_size, int increment);

/* Frees the stack object. */
void
tre_stack_destroy(tre_stack_t *s);

/* Returns the current number of objects in the stack. */
int
tre_stack_num_objects(tre_stack_t *s);

/* Pushes `value' on top of stack `s'.	Returns REG_ESPACE if out of memory
   (tries to realloc() more space before failing if maximum size not yet
   reached).  Returns REG_OK if successful. */
reg_errcode_t
tre_stack_push(tre_stack_t *s, void *value);

/* Pops the topmost element off of stack `s' and returns it.  The stack must
   not be empty. */
void *
tre_stack_pop(tre_stack_t *s);


/* Just to save some typing. */
#define STACK_PUSH(s, value)						      \
  do									      \
    {									      \
      status = tre_stack_push(s, (void *)(value));			      \
    }									      \
  while (0)

#define STACK_PUSHX(s, value)						      \
  {									      \
    status = tre_stack_push(s, (void *)(value));			      \
    if (status != REG_OK)						      \
      break;								      \
  }

#define STACK_PUSHR(s, value)						      \
  {									      \
    reg_errcode_t status;						      \
    status = tre_stack_push(s, (void *)(value));			      \
    if (status != REG_OK)						      \
      return status;							      \
  }

#endif /* TRE_STACK_H */

/* EOF */
