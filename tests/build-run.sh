#! /bin/sh
#

set -e

# Try to synchronize the file system in case $scp_host and $host are
# different (NFS complains about stale file handles and whatnot
# without this).
sync
sleep 1
sync

. ./build-params.sh

rm -rf build-tmp-$dir
mkdir build-tmp-$dir
mv $pkg build-tmp-$dir
cd build-tmp-$dir

gunzip -c $pkg | tar xf -
cd $dir

./tests/build-tests.sh
