#!/bin/bash

infile=$1
shift
t=$(mktemp)
mv "${t}" "${t}.png"
t=${t}.png
if [ -z "$*" ]; then
    imgargs="-resize 100x>"
else
    imgargs=$@
fi
convert $imgargs "$infile" "$t"
( ~/git/img2xterm/img2xterm "$t" | ghead -n -1 ; echo -en '\033[0m')
rm -f "$t"
