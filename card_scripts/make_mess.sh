#!/bin/bash

convert \
    -size 100x75 xc:none \
    -font Helvetica-Neue-Bold -pointsize 12 \
    -gravity north \
    -fill white -stroke black -strokewidth 2 -annotate +0+2 'Presented By' \
                -stroke none                 -annotate +0+2 'Presented By' \
    -gravity south \
    -fill white -stroke black -strokewidth 2 -annotate +0+3 'MESS LAB' \
                -stroke none                 -annotate +0+3 'MESS LAB' \
    \( "$1" -resize 35x35 \) \
    -gravity center -composite \
    "$2"

