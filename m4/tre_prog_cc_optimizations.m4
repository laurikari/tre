dnl @synopsis TRE_PROG_CC_OPTIMIZATIONS
dnl
dnl Sets C compiler optimizations which have been found to give
dnl best results for TRE with this compiler and architecture.
dnl
dnl @version 1.3
dnl @author Ville Laurikari <vl@iki.fi>
dnl
AC_DEFUN([TRE_PROG_CC_OPTIMIZATIONS], [
  # Don't override if CFLAGS was already set.
  if test -z "$ac_env_CFLAGS_set"; then
    AC_MSG_CHECKING([for the best optimization flags])
    tre_cflags=""
    if test "$GCC" = "yes"; then
      # The default CFLAGS is `-g -O2' (`-O2' on systems where gcc does
      # not accept `-g').
      case "$target" in
        i686-*-*-* )
          tre_cflags="-O1 -fomit-frame-pointer"
          ;;
      esac
    fi
    if test -n "$tre_cflags"; then
      AC_MSG_RESULT([$tre_cflags])
      CFLAGS="$tre_cflags"
    else
      AC_MSG_RESULT(unknown)
    fi
  fi
])dnl
