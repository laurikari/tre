#! /bin/sh
#
# Creates the source code distribution packages.
#

rm -rf tmp-build
mkdir tmp-build
cd tmp-build

../configure
make dist

base=`basename tre-*.tar.gz .tar.gz`
gunzip -c tre-*.tar.gz | bzip2 -9 -c > $base.tar.bz2
bunzip2 -c < $base.tar.bz2 | tar xf -
zip -9 -r $base.zip $base
chmod a+r $base.tar.gz $base.tar.bz2 $base.zip

cd ..
if test ! -d dist; then
  mkdir dist
fi
mv tmp-build/$base.tar.gz tmp-build/$base.tar.bz2 tmp-build/$base.zip dist
ls -l dist
