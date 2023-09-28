convert \
    -size 100x60 xc:none \
    \( gideon_head.png -resize x60 \) \
    -gravity west -composite \
    \( \
    -font Helvetica-Neue-Bold -pointsize 12 \
    -gravity center \
    -fill white -stroke black -strokewidth 2 -annotate +25+0 $'Gideon\nApril\n2023' \
                -stroke none                 -annotate +25+0 $'Gideon\nApril\n2023' \
    \) \
    "$1"
