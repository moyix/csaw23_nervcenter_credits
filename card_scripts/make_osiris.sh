#!/bin/bash

convert \
    -size 100x75 xc:none \
    \( "$1" -resize 70x70 -modulate 120 -geometry +0-7 \) \
    -gravity center -composite \
    -font Helvetica-Neue-Bold -pointsize 12 \
    -gravity south \
    -fill white -stroke black -strokewidth 2 -annotate +0+2 'OSIRIS Lab' \
                -stroke none                 -annotate +0+2 'OSIRIS Lab' \
    "$2"

