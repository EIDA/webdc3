#!/bin/bash
#
# Some very simple checks on the source code
# and documentation.
#
# PLE July 2013
#
# ----------------------------------------------------------------------
set -u

base='..'

# Some basic documentation checks
function check_doc_links () {
  # No missing anchors?
   echo "Used: ($( sort $base/index.html | grep -c "div id=\"wi-"))"
   sort $base/index.html | grep --color "div id=\"wi-"   # What's used on the site
   echo "Defined in help page ($(grep -c "dt id=" $base/help.html)):"
   sort $base/help.html | grep --color "dt id="          # What's defined
   echo "Referred to in help page ($(grep -c 'ref=\"\#' $base/help.html)):"
   sort $base/help.html | grep --color 'ref=\"\#'        # What's cited
   echo "Done check_doc"
}

function check_doc_words () {
  rstfiles="$base/doc/source/*.rst $base/doc/base/*.rst $base/doc/source/specs/*"

  grep --color "timewindow" $rstfiles         # Should be two words (getrennt)
  grep --color "webservice" $rstfiles         # Should be two words (getrennt)
  grep --color "dropdown" $rstfiles           # Should be two words (getrennt)
  grep --color "datacent" $rstfiles           # Should be 'data cent(re,er)'
  #grep --color "[^/]webinterface" $rstfiles   # Should be two words (getrennt)

  grep --color "JS[^SO][^N]" $rstfiles   # Should be JavaScript
  grep --color "Javascript" $rstfiles   # Should be JavaScript
  grep --color "Java " $rstfiles  
  #grep --color "top"  $rstfiles # no 'top layer' - use 'presentation'
  grep --color "backend" $rstfiles   # 'back end'
  grep --color AJAX $rstfiles        # Should be 'Ajax'
  grep --color ArcLink $rstfiles     # Should be 'Arclink' ???
  #grep --color " python" $rstfiles   # Should be 'Python'

  # Long lines where a new sentence starts (break at '.'):
  #grep --color '[^0-9]\.\ [A-Z]' $rstfiles
}

# No stray 'print' statements
function check_prints () {
  filelist=`find $base/wsgi -name "*.py" -print | sort`

  # No print statements to stdout:
  for f in ${filelist} ; do
        grep "print" $f | grep -v "print >>"
  done

  echo "Done check_prints"
}

# References from the index.html page to the help.html page:
function check_help_links () {
  echo "" > 1
  grep "dt id=" help.html | cut -f2 -d\" | sort >> 1
  grep help.html index.html | sed 's/^\W*</</' | sort > 2
  diff -y  1 2
  rm 1 2
}

# JavaScript:
function check_js () {
  # All <script> must have a type="text/javascript attribute":
  grep "<script" *.html | grep -v type
}

#-------------------------------------------------------------- 

#check_doc_links
check_doc_words
#check_prints

pushd ..
check_help_links
popd
