#!/bin/bash

convert \
    -size 100x75 xc:none \
    '(' \
        -size 100x75 xc:none -font Helvetica-Neue-Bold -pointsize 12 -gravity center \
        -fill gold -stroke black -strokewidth 2 -annotate +0-20 'Special Thanks' \
        -stroke none -annotate +0-20 'Special Thanks' -evaluate multiply 1.0 \
    ')' \
    -composite \
    '(' -size 100x75 xc:none -font Helvetica-Neue-Bold -pointsize 12 -gravity center \
        -fill SkyBlue -stroke black -strokewidth 2 -annotate +0+4 $'Annuska\nRiedlmayer' \
        -stroke none -annotate +0+4 $'Annuska\nRiedlmayer' -evaluate multiply 1.0 \
    ')' \
    -composite \
    '(' "$1" -resize 20x20 -gravity east -geometry +0+4 ')' \
    -composite \
    '(' "$1" -resize 20x20 -gravity west -geometry +0+4 ')' \
    -composite "$2"
