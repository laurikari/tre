/*
  tre-python.c - TRE Python language bindings

  This software is released under a BSD-style license.
  See the file LICENSE for details and copyright.

  The original version of this code was contributed by
  Nikolai Saoukh <nms+python@otdel1.org>.

  It was introduced to the TRE repository by PR#49,
  written by Hannu Väisänen <Hannu.Vaisanen@uef.fi>.
  The code was present in the main repository but the
  PR was not marked as merged.

  The timeline is a bit tangled, but PR#19 Brian A. Jones
  (github bjones1) introduced releasing the GIL during a
  compile or match as well as fixes to setup.py and updated
  documentation.

  Further updates for python versions 3.9+ and more
  error checking in 20023/03 by Tom Rushworth <tbr@acm.org>

*/


#include "Python.h"
#include "structmember.h"

#ifdef USE_LOCAL_TRE_H
/* Make certain to use the header(s) from the TRE package that this
   file is part of by giving the full path to the header from this directory. */
#include "../local_includes/tre.h"
#else
/* Use the header(s) from an installed version of the TRE package
   (so that this extension matches the installed libtre),
   not the one(s) in the local_includes directory. */
#include <tre/tre.h>
#endif

/* Define this if you want to release the GIL during compilation or searching.
   This builds and runs, but has not been tested with a multi-threaded test case.
   However, both compiling and searching make a private copy of the string they
   are operating on, so only the match results can possibly have problems if the
   search string gets modified by another thread. */
/* #define FUTURE_RELEASE_GIL 1 */

#define	TRE_MODULE	"tre"

typedef struct {
  PyObject_HEAD
  regex_t rgx;
  int flags;
} TrePatternObject;

typedef struct {
  PyObject_HEAD
  regaparams_t ap;
} TreFuzzynessObject;

typedef struct {
  PyObject_HEAD
  regamatch_t am;
  PyObject *targ;	  /* string we matched against */
  TreFuzzynessObject *fz; /* fuzzyness used during match */
} TreMatchObject;


static PyObject *ErrorObject;

static void
_set_tre_err(int rc, regex_t *rgx)
{
  PyObject *errval;
  char emsg[256];
  size_t elen;

  elen = tre_regerror(rc, rgx, emsg, sizeof(emsg));
  if (emsg[elen] == '\0')
    elen--;
  errval = Py_BuildValue("s#", emsg, elen);
  PyErr_SetObject(ErrorObject, errval);
  Py_XDECREF(errval);
}

static PyObject *
TreFuzzyness_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
  static char *kwlist[] = {
    "delcost", "inscost", "maxcost", "subcost",
    "maxdel", "maxerr", "maxins", "maxsub",
    NULL
  };

  TreFuzzynessObject *self;

  self = (TreFuzzynessObject*)type->tp_alloc(type, 0);
  if (self == NULL)
    return NULL;
  tre_regaparams_default(&self->ap);
  if (!PyArg_ParseTupleAndKeywords(args, kwds, "|iiiiiiii", kwlist,
				   &self->ap.cost_del, &self->ap.cost_ins,
				   &self->ap.max_cost, &self->ap.cost_subst,
				   &self->ap.max_del, &self->ap.max_err,
				   &self->ap.max_ins, &self->ap.max_subst))
    {
      Py_DECREF(self);
      return NULL;
    }
  return (PyObject*)self;
}

static PyObject *
TreFuzzyness_repr(PyObject *obj)
{
  TreFuzzynessObject *self = (TreFuzzynessObject*)obj;
  PyObject *o;

  o = PyUnicode_FromFormat("%s(delcost=%d,inscost=%d,maxcost=%d,subcost=%d,"
			  "maxdel=%d,maxerr=%d,maxins=%d,maxsub=%d)",
			  Py_TYPE(self)->tp_name, self->ap.cost_del,
			  self->ap.cost_ins, self->ap.max_cost,
			  self->ap.cost_subst, self->ap.max_del,
			  self->ap.max_err, self->ap.max_ins,
			  self->ap.max_subst);
  return o;
}

static PyMemberDef TreFuzzyness_members[] = {
  { "delcost", T_INT, offsetof(TreFuzzynessObject, ap.cost_del), 0,
    "The cost of a deleted character" },
  { "inscost", T_INT, offsetof(TreFuzzynessObject, ap.cost_ins), 0,
    "The cost of an inserted character" },
  { "maxcost", T_INT, offsetof(TreFuzzynessObject, ap.max_cost), 0,
    "The maximum allowed cost of a match. If this is set to zero, an exact "
    "match is searched for" },
  { "subcost", T_INT, offsetof(TreFuzzynessObject, ap.cost_subst), 0,
    "The cost of a substituted character" },
  { "maxdel", T_INT, offsetof(TreFuzzynessObject, ap.max_del), 0,
    "Maximum allowed number of deleted characters" },
  { "maxerr", T_INT, offsetof(TreFuzzynessObject, ap.max_err), 0,
    "Maximum allowed number of errors (inserts + deletes + substitutes)" },
  { "maxins", T_INT, offsetof(TreFuzzynessObject, ap.max_ins), 0,
    "Maximum allowed number of inserted characters" },
  { "maxsub", T_INT, offsetof(TreFuzzynessObject, ap.max_subst), 0,
    "Maximum allowed number of substituted characters" },
  { NULL }
};

static PyTypeObject TreFuzzynessType = {
  PyVarObject_HEAD_INIT(NULL,0)
  TRE_MODULE ".Fuzzyness",	/* tp_name */
  sizeof(TreFuzzynessObject),	/* tp_basicsize */
  0,			        /* tp_itemsize */
  /* methods */
  0,				/* tp_dealloc */
  0,				/* tp_print */
  0,				/* tp_getattr */
  0,				/* tp_setattr */
  0,				/* tp_compare */
  TreFuzzyness_repr,		/* tp_repr */
  0,				/* tp_as_number */
  0,				/* tp_as_sequence */
  0,				/* tp_as_mapping */
  0,				/* tp_hash */
  0,				/* tp_call */
  0,				/* tp_str */
  0,				/* tp_getattro */
  0,				/* tp_setattro */
  0,				/* tp_as_buffer */
  Py_TPFLAGS_DEFAULT,		/* tp_flags */
  /* tp_doc */
  TRE_MODULE ".fuzzyness object holds approximation parameters for match",
  0,				/* tp_traverse */
  0,				/* tp_clear */
  0,				/* tp_richcompare */
  0,				/* tp_weaklistoffset */
  0,				/* tp_iter */
  0,				/* tp_iternext */
  0,				/* tp_methods */
  TreFuzzyness_members,		/* tp_members */
  0,				/* tp_getset */
  0,				/* tp_base */
  0,				/* tp_dict */
  0,				/* tp_descr_get */
  0,				/* tp_descr_set */
  0,				/* tp_dictoffset */
  0,				/* tp_init */
  0,				/* tp_alloc */
  TreFuzzyness_new		/* tp_new */
};

static PyObject *
PyTreMatch_groups(TreMatchObject *self, PyObject *dummy)
{
  PyObject *result;
  size_t i;

  if (self->am.nmatch < 1)
    {
      Py_INCREF(Py_None);
      return Py_None;
    }
  result = PyTuple_New(self->am.nmatch);
  for (i = 0; i < self->am.nmatch; i++)
    {
      PyObject *range;
      regmatch_t *rm = &self->am.pmatch[i];

      if (rm->rm_so == (-1) && rm->rm_eo == (-1))
	{
	  Py_INCREF(Py_None);
	  range = Py_None;
	}
      else
	{
	  range = Py_BuildValue("(ii)", rm->rm_so, rm->rm_eo);
	}
      PyTuple_SetItem(result, i, range);
    }
  return (PyObject*)result;
}

static PyObject *
PyTreMatch_groupi(PyObject *obj, Py_ssize_t gn)
{
  TreMatchObject *self = (TreMatchObject*)obj;
  PyObject *result;
  regmatch_t *rm;

  if (gn < 0 || (size_t)gn > self->am.nmatch - 1)
    {
      PyErr_SetString(PyExc_ValueError, "out of bounds");
      return NULL;
    }
  rm = &self->am.pmatch[gn];
  if (rm->rm_so == (-1) && rm->rm_eo == (-1))
    {
      Py_INCREF(Py_None);
      return Py_None;
    }
  result = PySequence_GetSlice(self->targ, rm->rm_so, rm->rm_eo);
  return result;
}

static PyObject *
PyTreMatch_group(TreMatchObject *self, PyObject *grpno)
{
  PyObject *result;
  long gn;

  gn = PyLong_AsLong(grpno);

  if (PyErr_Occurred())
    return NULL;

  result = PyTreMatch_groupi((PyObject*)self, gn);
  return result;
}

static PyMethodDef TreMatch_methods[] = {
  {"group", (PyCFunction)PyTreMatch_group, METH_O,
   "return submatched string or None if a parenthesized subexpression did "
   "not participate in a match"},
  {"groups", (PyCFunction)PyTreMatch_groups, METH_NOARGS,
   "return the tuple of slice tuples for all parenthesized subexpressions "
   "(None for not participated)"},
  {NULL, NULL}
};

static PyMemberDef TreMatch_members[] = {
  { "cost", T_INT, offsetof(TreMatchObject, am.cost), READONLY,
    "Cost of the match" },
  { "numdel", T_INT, offsetof(TreMatchObject, am.num_del), READONLY,
    "Number of deletes in the match" },
  { "numins", T_INT, offsetof(TreMatchObject, am.num_ins), READONLY,
    "Number of inserts in the match" },
  { "numsub", T_INT, offsetof(TreMatchObject, am.num_subst), READONLY,
    "Number of substitutes in the match" },
  { "fuzzyness", T_OBJECT, offsetof(TreMatchObject, fz), READONLY,
    "Fuzzyness used during match" },
  { NULL }
};

static void
PyTreMatch_dealloc(TreMatchObject *self)
{
  Py_XDECREF(self->targ);
  Py_XDECREF(self->fz);
  if (self->am.pmatch != NULL)
    PyMem_Del(self->am.pmatch);
  PyObject_Del(self);
}

static PySequenceMethods TreMatch_as_sequence_methods = {
  0, /* sq_length */
  0, /* sq_concat */
  0, /* sq_repeat */
  PyTreMatch_groupi, /* sq_item */
  0, /* sq_slice */
  0, /* sq_ass_item */
  0, /* sq_ass_slice */
  0, /* sq_contains */
  0, /* sq_inplace_concat */
  0 /* sq_inplace_repeat */
};

static PyTypeObject TreMatchType = {
  PyVarObject_HEAD_INIT(NULL,0)
  TRE_MODULE ".Match",		/* tp_name */
  sizeof(TreMatchObject),	/* tp_basicsize */
  0,			        /* tp_itemsize */
  /* methods */
  (destructor)PyTreMatch_dealloc, /* tp_dealloc */
  0,			        /* tp_print */
  0,				/* tp_getattr */
  0,				/* tp_setattr */
  0,				/* tp_compare */
  0,				/* tp_repr */
  0,				/* tp_as_number */
  &TreMatch_as_sequence_methods,	/* tp_as_sequence */
  0,				/* tp_as_mapping */
  0,				/* tp_hash */
  0,				/* tp_call */
  0,				/* tp_str */
  0,				/* tp_getattro */
  0,				/* tp_setattro */
  0,				/* tp_as_buffer */
  Py_TPFLAGS_DEFAULT,		/* tp_flags */
  TRE_MODULE ".match object holds result of successful match",	/* tp_doc */
  0,				/* tp_traverse */
  0,				/* tp_clear */
  0,				/* tp_richcompare */
  0,				/* tp_weaklistoffset */
  0,				/* tp_iter */
  0,				/* tp_iternext */
  TreMatch_methods,		/* tp_methods */
  TreMatch_members		/* tp_members */
};

static TreMatchObject *
newTreMatchObject(void)
{
  TreMatchObject *self;

  self = PyObject_New(TreMatchObject, &TreMatchType);
  if (self == NULL)
    return NULL;
  memset(&self->am, '\0', sizeof(self->am));
  self->targ = NULL;
  self->fz = NULL;
  return self;
}

static PyObject *
PyTrePattern_search(TrePatternObject *self, PyObject *args)
{
  PyObject *pstring;
  Py_ssize_t num_codepoints = 0;
  int codepoint_kind = PyUnicode_1BYTE_KIND;
  void const *src = NULL;
#ifdef TRE_WCHAR
  Py_UCS4 *ucs_mstring = NULL;
#else
  Py_UCS1 *ucs_mstring = NULL;
#endif
  int eflags = 0;
  TreMatchObject *mo;
  TreFuzzynessObject *fz;
  size_t nsub;
  int rc;
  regmatch_t *pm;

  if (PyTuple_Size(args) > 0 && PyUnicode_Check(PyTuple_GetItem(args, 0)))
    {
      /* First object in tuple is a Unicode object or an instance of a
         Unicode subtype (i.e. a Python str). */
      if (!PyArg_ParseTuple(args, "UO!|i:search", &pstring, &TreFuzzynessType,
			&fz, &eflags))
        return NULL;
      /* Since the user may pass in any string value, the object may have 1-byte, 2-byte, or 4-byte codepoints.
         The simplest way to deal with this is to convert to a buffer of 4-byte codepoints.
         Having a separate buffer also allows us to release the GIL without worrying about the input argument
         being modified by another thread while we are using it, so it is worth doing even if the
         input arg already has 4-byte codepoints. */
      /* For python versions <= 3.9 we may need PyUnicode_READY(pstring), but the fn is deprecated in 3.10. */
      num_codepoints = PyUnicode_GET_LENGTH(pstring); // number of codepoints
      codepoint_kind = PyUnicode_KIND(pstring);
#ifndef TRE_WCHAR
      if (PyUnicode_1BYTE_KIND != codepoint_kind)
        {
          /* Without wchar_t we cannot handle any of the larger codepoint sizes. */
          PyErr_SetString(PyExc_ValueError, "In search(), this build of TRE does not support characters with codepoints that cannot fit in a byte.");
          return NULL;
        }
#endif
      /* Since the Unicode objects have an internal codepoint buffer, we can copy from it directly. */
      src = PyUnicode_DATA(pstring);
    }
  else if (PyTuple_Size(args) > 0 && PyBytes_Check(PyTuple_GetItem(args, 0)))
    {
      /* First object in tuple is bytes type object. */
      if (!PyArg_ParseTuple(args, "SO!|i:search", &pstring, &TreFuzzynessType,
			&fz, &eflags))
        return NULL;
      num_codepoints = PyBytes_GET_SIZE(pstring);
      codepoint_kind = PyUnicode_1BYTE_KIND;
      src = PyBytes_AS_STRING(pstring); // We are certain of pstring's type, so we don't need error checking
    }
  else
    {
      PyErr_SetString(PyExc_ValueError, "In search(), argument is not str or bytes");
      return(NULL);
    }

  mo = newTreMatchObject();
  if (mo == NULL)
    return NULL;

  nsub = self->rgx.re_nsub + 1;
  pm = PyMem_New(regmatch_t, nsub);
  if (!pm)
    {
      Py_DECREF(mo);
      return PyErr_NoMemory();
    }

  mo->am.nmatch = nsub;
  mo->am.pmatch = pm; /* Let mo hold onto pm. */

#ifdef TRE_WCHAR
  /* Just to complicate life, wchar_t is usually 2 bytes on Windows systems, and 4 bytes on POSIX sytems.
     This whole scheme is going to fail for a 2-byte wchar_t TRE library, so generate a compile error
     instead of building successfully but failing later.  This generates no code if it compiles. */
  ((void)sizeof(char[1 - 2*!!(4!=sizeof(wchar_t))]));  // This bit of hocus-pocus is from the Linux BUILD_BUG_ON() macro
#endif

  /* Allocate then copy the src codepoints into ucs_mstring. */
#ifdef TRE_WCHAR
  ucs_mstring = (Py_UCS4 *) calloc(sizeof(Py_UCS4), num_codepoints+1);
#else
  ucs_mstring = (Py_UCS1 *) calloc(sizeof(Py_UCS1), num_codepoints+1);
#endif
  if (NULL == ucs_mstring)
    {
      Py_DECREF(mo);
      return PyErr_NoMemory();
    }
  switch (codepoint_kind)
    {
#ifdef TRE_WCHAR
#if PY_MAJOR_VERSION >= 3 && (PY_MINOR_VERSION >= 3 && PY_MINOR_VERSION < 10)
      case PyUnicode_WCHAR_KIND: // CAUTION: WCHAR_KIND, deprecated in 3.10, removed in 3.12
        for (int cpx = 0; cpx < num_codepoints; cpx++)
          {
            ucs_mstring[cpx] = ((wchar_t *) src)[cpx];
          }
        break;
#endif
#endif
      case PyUnicode_1BYTE_KIND:
#ifdef TRE_WCHAR
        for (int cpx = 0; cpx < num_codepoints; cpx++)
          {
            ucs_mstring[cpx] = ((Py_UCS1 *) src)[cpx];
          }
#else /* !TRE_WCHAR */
        memcpy(ucs_mstring,src,num_codepoints*sizeof(Py_UCS1));
#endif
        break;
#ifdef TRE_WCHAR
      case PyUnicode_2BYTE_KIND:
        for (int cpx = 0; cpx < num_codepoints; cpx++)
          {
            ucs_mstring[cpx] = ((Py_UCS2 *) src)[cpx];
          }
        break;
      case PyUnicode_4BYTE_KIND:
        memcpy(ucs_mstring,src,num_codepoints*sizeof(Py_UCS4));
        break;
#endif
      default:
        PyErr_Format(PyExc_ValueError, "In search(), argument is unrecognized codepoint kind (%d)",codepoint_kind);
        Py_DECREF(mo);
        free(ucs_mstring);
        return(NULL);
    }
  /* Terminate ucs_mstring for paranoia's sake (len _should_ take care of it, but this is cheap, so...). */
  ucs_mstring[num_codepoints] = 0; 
  // Introduced by PR#19.
  // The matching process can be slow. So, let other Python threads
  // run in parallel by releasing the GIL. See
  // https://docs.python.org/2/c-api/init.html#releasing-the-gil-from-extension-code.
#ifdef FUTURE_RELEASE_GIL
  Py_BEGIN_ALLOW_THREADS
#endif
#ifdef TRE_WCHAR
  rc = tre_regawnexec(&self->rgx, (wchar_t const *) ucs_mstring, num_codepoints, &mo->am, fz->ap, eflags);
#else
  rc = tre_reganexec(&self->rgx, (char const *) ucs_mstring, num_codepoints, &mo->am, fz->ap, eflags);
#endif
#ifdef FUTURE_RELEASE_GIL
  Py_END_ALLOW_THREADS
#endif
  free(ucs_mstring);

  if (PyErr_Occurred())
    {
      Py_DECREF(mo);
      return NULL;
    }

  if (rc == REG_OK)
    {
      Py_INCREF(pstring);
      /* The match object does not access the original string directly,
         it only provides index values for the user to use, so there is
         no need to worry about the size of the codepoints in that string. */
      mo->targ = pstring;
      Py_INCREF(fz);
      mo->fz = fz;
      return (PyObject*)mo;
    }

  if (rc == REG_NOMATCH)
    {
      Py_DECREF(mo);
      Py_INCREF(Py_None);
      return Py_None;
    }
  _set_tre_err(rc, &self->rgx);
  Py_DECREF(mo);
  return NULL;
}

static PyMethodDef TrePattern_methods[] = {
  { "search", (PyCFunction)PyTrePattern_search, METH_VARARGS,
    "try to search in the given string, returning " TRE_MODULE ".match object "
    "or None on failure" },
  {NULL, NULL}
};

static PyMemberDef TrePattern_members[] = {
  { "nsub", T_INT, offsetof(TrePatternObject, rgx.re_nsub), READONLY,
    "Number of parenthesized subexpressions in regex" },
  { NULL }
};

static void
PyTrePattern_dealloc(TrePatternObject *self)
{
  tre_regfree(&self->rgx);
  PyObject_Del(self);
}

static PyTypeObject TrePatternType = {
  PyVarObject_HEAD_INIT(NULL,0)
  TRE_MODULE ".Pattern",	/* tp_name */
  sizeof(TrePatternObject),	/* tp_basicsize */
  0,			        /* tp_itemsize */
  /* methods */
  (destructor)PyTrePattern_dealloc, /*tp_dealloc*/
  0,				/* tp_print */
  0,				/* tp_getattr */
  0,				/* tp_setattr */
  0,				/* tp_compare */
  0,				/* tp_repr */
  0,				/* tp_as_number */
  0,				/* tp_as_sequence */
  0,				/* tp_as_mapping */
  0,				/* tp_hash */
  0,				/* tp_call */
  0,				/* tp_str */
  0,				/* tp_getattro */
  0,				/* tp_setattro */
  0,				/* tp_as_buffer */
  Py_TPFLAGS_DEFAULT,		/* tp_flags */
  TRE_MODULE ".pattern object holds compiled tre regex",	/* tp_doc */
  0,				/* tp_traverse */
  0,				/* tp_clear */
  0,				/* tp_richcompare */
  0,				/* tp_weaklistoffset */
  0,				/* tp_iter */
  0,				/* tp_iternext */
  TrePattern_methods,		/* tp_methods */
  TrePattern_members		/* tp_members */
};

static TrePatternObject *
newTrePatternObject(void)
{
  TrePatternObject *self;

  self = PyObject_New(TrePatternObject, &TrePatternType);
  if (self == NULL)
    return NULL;
  self->flags = 0;
  return self;
}

static PyObject *
PyTre_ncompile(PyObject *self, PyObject *args)
{
  TrePatternObject *rv;
  PyObject *pattern = NULL;
  // char *pattern = NULL;
  int codepoint_kind = PyUnicode_1BYTE_KIND;
  Py_ssize_t pat_len = 0;
  int cflags = 0;
  int rc;
  void const *src = NULL;
#ifdef TRE_WCHAR
  Py_UCS4 *ucs_pattern = NULL;
#else
  Py_UCS1 *ucs_pattern = NULL;
#endif

  if (PyTuple_Size(args) > 0 && PyUnicode_Check(PyTuple_GetItem(args, 0)))
    {
      /* First object in tuple is a Unicode object or an instance of a
         Unicode subtype (i.e. a Python str). */
      if (!PyArg_ParseTuple(args, "U|i:search", &pattern, &cflags))
        return NULL;
      /* Since the user may pass in any string value, the object may have 1-byte, 2-byte, or 4-byte codepoints.
         The simplest way to deal with this is to convert to a buffer of 4-byte codepoints.
         Having a separate buffer also allows us to release the GIL without worrying about the input argument
         being modified by another thread while we are using it, so it is worth doing even if the
         input arg already has 4-byte codepoints. */
      /* For python versions <= 3.9 we may need PyUnicode_READY(pattern), but the fn is deprecated in 3.10. */
      codepoint_kind = PyUnicode_KIND(pattern);
      pat_len = PyUnicode_GET_LENGTH(pattern); // number of codepoints
#ifndef TRE_WCHAR
      if (PyUnicode_1BYTE_KIND != codepoint_kind)
        {
          /* Without wchar_t we cannot handle any of the larger codepoint sizes. */
          PyErr_SetString(PyExc_ValueError, "In compile(), this build of TRE does not support characters with codepoints that cannot fit in a byte.");
          return NULL;
        }
#endif
      /* Since the Unicode objects have an internal codepoint buffer, we can copy from it directly. */
      src = PyUnicode_DATA(pattern);
    }
  else if (PyTuple_Size(args) > 0 && PyBytes_Check(PyTuple_GetItem(args, 0)))
    {
      /* First object in tuple is bytes type object. */
      if (!PyArg_ParseTuple(args, "SO!|i:search", &pattern, &cflags))
        return NULL;
      codepoint_kind = PyUnicode_1BYTE_KIND;
      pat_len = PyBytes_GET_SIZE(pattern);
      src = PyBytes_AS_STRING(pattern); // We are certain of patterns's type, so we don't need error checking
    }
  else
    {
      PyErr_SetString(PyExc_ValueError, "In compile(), argument is not str or bytes");
      return(NULL);
    }

  rv = newTrePatternObject();
  if (rv == NULL)
    return NULL;

#ifdef TRE_WCHAR
  /* Just to complicate life, wchar_t is usually 2 bytes on Windows systems, and 4 bytes on POSIX sytems.
     This whole scheme is going to fail for a 2-byte wchar_t TRE library, so generate a compile error
     instead of building successfully but failing later.  This generates no code if it compiles. */
  ((void)sizeof(char[1 - 2*!!(4!=sizeof(wchar_t))]));  // This bit of hocus-pocus is from the Linux BUILD_BUG_ON() macro
#endif

  /* Allocate then copy the src codepoints into ucs_pattern. */
#ifdef TRE_WCHAR
  ucs_pattern = (Py_UCS4 *) calloc(sizeof(Py_UCS4), pat_len+1);
#else
  ucs_pattern = (Py_UCS1 *) calloc(sizeof(Py_UCS1), pat_len+1);
#endif
  switch (codepoint_kind)
    {
#ifdef TRE_WCHAR
#if PY_MAJOR_VERSION >= 3 && (PY_MINOR_VERSION >= 3 && PY_MINOR_VERSION < 10)
      case PyUnicode_WCHAR_KIND: // CAUTION: WCHAR_KIND, deprecated in 3.10, removed in 3.12
        for (int cpx = 0; cpx < pat_len; cpx++)
          {
            ucs_pattern[cpx] = ((wchar_t *) src)[cpx];
          }
        break;
#endif
#endif
      case PyUnicode_1BYTE_KIND:
#ifdef TRE_WCHAR
        for (int cpx = 0; cpx < pat_len; cpx++)
          {
            ucs_pattern[cpx] = ((Py_UCS1 *) src)[cpx];
          }
#else
        memcpy(ucs_pattern,src,pat_len*sizeof(Py_UCS1));
#endif
        break;
#ifdef TRE_WCHAR
      case PyUnicode_2BYTE_KIND:
        for (int cpx = 0; cpx < pat_len; cpx++)
          {
            ucs_pattern[cpx] = ((Py_UCS2 *) src)[cpx];
          }
        break;
      case PyUnicode_4BYTE_KIND:
        memcpy(ucs_pattern,src,pat_len*sizeof(Py_UCS4));
        break;
#endif
      default:
        PyErr_Format(PyExc_ValueError, "In compile(), argument is unrecognized or unsupported codepoint kind (%d)",codepoint_kind);
        Py_DECREF(rv);
        free(ucs_pattern);
        return(NULL);
    }
  /* Terminate ucs_pattern for paranoia's sake (len _should_ take care of it, but this is cheap, so...). */
  ucs_pattern[pat_len] = 0; 
  // Introduced by PR#19.
  // The compile process can be slow. So, let other Python threads
  // run in parallel by releasing the GIL. See
  // https://docs.python.org/2/c-api/init.html#releasing-the-gil-from-extension-code.
#ifdef FUTURE_RELEASE_GIL
  Py_BEGIN_ALLOW_THREADS
#endif
#ifdef TRE_WCHAR
  rc = tre_regwncomp(&rv->rgx, (wchar_t const *) ucs_pattern, pat_len, cflags);
#else
  rc = tre_regncomp(&rv->rgx, (char const *) ucs_pattern, pat_len, cflags);
#endif
#ifdef FUTURE_RELEASE_GIL
  Py_END_ALLOW_THREADS
#endif
  free(ucs_pattern);

  if (rc != REG_OK)
    {
      if (!PyErr_Occurred())
        _set_tre_err(rc, &rv->rgx);
      Py_DECREF(rv);
      return NULL;
    }
  rv->flags = cflags;
  return (PyObject*)rv;
}

static PyMethodDef tre_methods[] = {
  { "compile", PyTre_ncompile, METH_VARARGS,
    "Compile a regular expression pattern, returning a "
    TRE_MODULE ".pattern object" },
  {NULL, NULL, 0, NULL}
};

static struct _tre_flags {
  char *name;
  int val;
} tre_flags[] = {
  { "EXTENDED", REG_EXTENDED },
  { "ICASE", REG_ICASE },
  { "NEWLINE", REG_NEWLINE },
  { "NOSUB", REG_NOSUB },
  { "LITERAL", REG_LITERAL },

  { "NOTBOL", REG_NOTBOL },
  { "NOTEOL", REG_NOTEOL },
  { NULL, 0 }
};

static struct PyModuleDef cModPyTRE =
{
  PyModuleDef_HEAD_INIT,
  "tre",            /* Name of module. */
  "Python module for TRE library\n\nModule exports "
  "the only function: compile", /* Module documentation, may be NULL. */
  -1,               /* Size of per-interpreter state of the module, or -1 if the module keeps state in global vars. */
  tre_methods
};

PyMODINIT_FUNC
PyInit_tre(void)
{
  /* PyMODINIT_FUNC defines a function that returns PyObject* in python 3, but was void in python 2. */
  PyObject *m = NULL;
  struct _tre_flags *fp;

  if (PyType_Ready(&TreFuzzynessType) < 0)
    {
      PyErr_SetString(PyExc_Exception,"TreFuzzynessType not ready");
      return(NULL);
    }
  if (PyType_Ready(&TreMatchType) < 0)
    {
      PyErr_SetString(PyExc_Exception,"TreMatchType not ready");
      return(NULL);
    }
  if (PyType_Ready(&TrePatternType) < 0)
    {
      PyErr_SetString(PyExc_Exception,"TrePatternType not ready");
      return(NULL);
    }

  /* Create the module for Python 3 */
  m = PyModule_Create(&cModPyTRE);
  if (m == NULL)
    {
      PyErr_SetString(PyExc_Exception,"PyModule_Create() failed");
      return(NULL);
    }

  Py_INCREF(&TreFuzzynessType);
  if (PyModule_AddObject(m, "Fuzzyness", (PyObject*)&TreFuzzynessType) < 0)
    {
      PyErr_SetString(PyExc_Exception,"PyModule_AddObject(Fuzzyness) failed");
      return(NULL);
    }
  Py_INCREF(&TreMatchType);
  if (PyModule_AddObject(m, "Match", (PyObject*)&TreMatchType) < 0)
    {
      PyErr_SetString(PyExc_Exception,"PyModule_AddObject(Match) failed");
      return(NULL);
    }
  Py_INCREF(&TrePatternType);
  if (PyModule_AddObject(m, "Pattern", (PyObject*)&TrePatternType) < 0)
    {
      PyErr_SetString(PyExc_Exception,"PyModule_AddObject(Pattern) failed");
      return(NULL);
    }
  ErrorObject = PyErr_NewException(TRE_MODULE ".Error", NULL, NULL);
  Py_INCREF(ErrorObject);
  if (PyModule_AddObject(m, "Error", ErrorObject) < 0)
    {
      PyErr_SetString(PyExc_Exception,"PyModule_AddObject(Error) failed");
      return(NULL);
    }

  /* Insert the flags */
  for (fp = tre_flags; fp->name != NULL; fp++)
    if (PyModule_AddIntConstant(m, fp->name, fp->val) < 0)
      {
        char const *mp1 = "PyModule_AddIntConstant(";
        char const *mp2 = ") failed";
        long len = strlen(mp1) + strlen(mp2) + strlen(fp->name) + 1;
        char *msg = calloc(sizeof(char),len);
        /* No point getting too fancy here.  We could check for calloc() failure, but meh. */
        snprintf(msg,len,"%s%s%s",mp1,fp->name,mp2);
        PyErr_SetString(PyExc_Exception,msg);
        free(msg);
        return(NULL);
      }

  return(m);
}
