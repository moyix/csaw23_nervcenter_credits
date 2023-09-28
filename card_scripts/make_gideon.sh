#!/bin/bash

convert \
   -size 100x75 xc:none \
    '(' \
        -size 100x75 xc:none -font Helvetica-Neue-Bold -pointsize 12 -gravity north \
        -fill gold -stroke black -strokewidth 2 -annotate +0+0 'Dedicated To' \
        -stroke none -annotate +0+0 'Dedicated To' -evaluate multiply 1.0 \
    ')' \
    -composite \
    '(' \
        -size 100x60 xc:none \
        '(' "$1" -resize x60 ')' \
        -gravity west -composite \
        '(' \
        -font Helvetica-Neue-Bold -pointsize 12 \
        -gravity center \
        -fill white -stroke black -strokewidth 2 -annotate +25+0 $'Gideon\nApril\n2023' \
                    -stroke none                 -annotate +25+0 $'Gideon\nApril\n2023' \
        ')' \
    ')' \
    -gravity south \
    -composite "$2"
