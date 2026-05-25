/*
  tre-compile.h: Regex compilation definitions

  This software is released under a BSD-style license.
  See the file LICENSE for details and copyright.

*/

#ifndef TRE_COMPILE_H
#define TRE_COMPILE_H 1

/* Limit distribution to prevent $O(2^N)$ AST explosion DoS */
#define MAX_DISTRIBUTION_DEPTH 10 /* Allows 1024 branches */

typedef struct
{
  int position;
  int code_min;
  int code_max;
  int *tags;
  int assertions;
  tre_ctype_t class;
  tre_ctype_t *neg_classes;
  int backref;
  int *params;
} tre_pos_and_tags_t;

#endif /* TRE_COMPILE_H */

/* EOF */
