#!/bin/bash

convert \
    -size 100x75 xc:none \
    '(' \
        -size 100x75 xc:none -font Helvetica-Neue-Bold -pointsize 12 -gravity north \
        -fill gold -stroke black -strokewidth 2 -annotate +0+0 'Dedicated To' \
        -stroke none -annotate +0+0 'Dedicated To' -evaluate multiply 1.0 \
    ')' \
    -composite \
        '(' gideoncard_crop.png -gravity south ')' \
    -composite gideoncard2.png
