#! /bin/sh
#

set -e

pkg=`ls dist/tre-*.tar.gz`
pkg=`basename $pkg`
dir=`basename $pkg .tar.gz`

scp dist/$pkg hemuli:build-tmp
ssh hemuli "cd build-tmp; rm -rf $dir; tar xzf $pkg; cd $dir; ./utils/build-rpm.sh"
scp hemuli:build-tmp/$dir/\*.rpm dist
