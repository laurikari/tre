#! /bin/sh
#
# Assembles the documentation website published via GitHub Pages.
# Requires pandoc, which is used to convert README.md to HTML.
#
# Usage: doc/build-website.sh [output-directory]
#

set -e

srcdir=`dirname "$0"`
outdir=${1:-_site}

if ! command -v pandoc > /dev/null 2>&1; then
  echo "error: pandoc is required to build the website" >&2
  exit 1
fi

mkdir -p "$outdir"
cp "$srcdir/default.css" "$outdir"

# The HTML files in doc/ are body fragments with no <html> or <head>;
# they were originally embedded in a site template.  This wraps a
# fragment (read from stdin) into a complete page.
emit_page() {
  title=$1
  out=$2

  {
    cat << EOF
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>$title</title>
<link rel="stylesheet" href="default.css">
<style>
body {
  max-width: 50em;
  margin: 0 auto;
  padding: 0 1em 2em 1em;
  font-family: sans-serif;
  line-height: 1.5;
}
nav.site {
  border-bottom: 1px solid #cbc5b8;
  padding: 0.5em 0;
  margin-bottom: 1.5em;
}
nav.site a {
  margin-right: 1em;
}
</style>
</head>
<body>
<nav class="site">
<a href="index.html">TRE</a>
<a href="tre-api.html">API reference</a>
<a href="tre-syntax.html">Regexp syntax</a>
<a href="https://github.com/laurikari/tre">GitHub</a>
</nav>
EOF
    cat
    cat << EOF
</body>
</html>
EOF
  } > "$out"
}

pandoc --from gfm --to html "$srcdir/../README.md" \
  | emit_page "TRE" "$outdir/index.html"

emit_page "TRE API reference manual" "$outdir/tre-api.html" \
  < "$srcdir/tre-api.html"

emit_page "TRE Regexp Syntax" "$outdir/tre-syntax.html" \
  < "$srcdir/tre-syntax.html"
