#! /bin/sh

tbr_logfile=/tmp/tbr_agrep_test
echo '##################################' >> ${tbr_logfile}
set -e

agrep="$top_builddir/src/agrep"

echo "$builddir $top_builddir $srcdir"

num_cases=0
num_expanded=0
num_tests=0
num_fail=0
num_ok=0

SIFS="$IFS"

for args in $srcdir/*.args; do
  dir=`dirname $args`
  base=`basename $args .args`
  orig_input=$dir/$base.input
  input=$base.in
  ok=$dir/$base.ok
  out=$base.out

  rm -f $out
  IFS="
"
  for arg in `cat $args`; do
    IFS="$SIFS"
    case "$arg" in
      \#*) continue;;
    esac

    num_cases=`expr $num_cases + 1`
    cp "$orig_input" $input

    for extra in "" -c -H -l -n -s -M --show-position --color \
                 "-H -n -s --color --show-position"; do
      num_expanded=`expr $num_expanded + 1`
      # Note that `echo' cannot be used since it works differently on
      # different platforms with regards to expanding \n (IRIX expands
      # it, others typically do not).  `cat' doesn't process its output.
      cat >> $out <<EOF
#### TEST: agrep $extra $arg $input
EOF
      cat <<EOF
agrep $extra $arg $input
EOF
      set +e
      # Disable globbing in case there are '*' characters in $arg
      # This bug was discovered and reported in PR#87 by Vogtinator
      # on 2022/10/11.  The fix suggested in the PR was to remove
      # the line in tests/agrep/exitstatus.args that contained the
      # '*' character and modify the exitstatus.OK file to match.
      # As Vogtinator pointed out, avoiding the glob expansion is
      # not easy (there may be multiple shell arguments in a line
      # from any of the .args files so escaping the glob character
      # becomes very difficult and error prone).  However, bash
      # shells from 4.4+ and most Almquist shells (e.g. FreeBSD 'sh',
      # Linux 'ash', Debian 'dash', Busybox 'sh', etc.), have a
      # 'noglob' or 'set -/+f' option for disabling globbing.  If
      # this shell script is failing on the 'set -f' below, remove
      # if and the corresponding 'set +f', then remove the line
      # containing the '.*' from exitstatus.args, and the lines
      # produced by that .args line from existatus.ok.  It doesn't
      # seem worth the effort to check the shell version here, because
      # the Almquist shells don't have an easy way to determine the
      # version of the running instance.
      set -f
      $agrep $extra $arg $input >> $out
      status=$?
      set +f
      set -e
      cat >> $out <<EOF

Exit status $status.
EOF

      num_expanded=`expr $num_expanded + 1`
      cat >> $out <<EOF
#### TEST: agrep $extra $arg < $input
EOF
      cat <<EOF
agrep $extra $arg < $input
EOF
      set +e
      set -f
      $agrep $extra $arg < $input >> $out
      status=$?
      set +f
      set -e
      cat >> $out <<EOF

Exit status $status.
EOF
    done

    rm -f $input
  done
  num_tests=`expr $num_tests + 1`
  case $host_triplet in
    *-mingw*)
      # On MinGW something causes \r\n newlines to be output to $out,
      # and our reference results don't have them.
      tr -d '\015' < $out > $out.tmp
      mv $out.tmp $out
      ;;
  esac
  if diff $ok $out; then
    num_ok=`expr $num_ok + 1`
  else
    echo "FAILED (see above)"
    num_fail=`expr $num_fail + 1`
  fi
done

echo "Ran $num_cases tests ($num_expanded expanded) from $num_tests suites."
echo "$num_ok/$num_tests tests OK"

test $num_fail -eq 0
exit $?
