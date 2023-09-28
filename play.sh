#!/bin/bash

trap ctrl_c INT

function ctrl_c() {
    printf '\033c'
}

(printf '\033[H\033[2J\033[3J\e[?25l'; for f in "$1"/*.txt ; do cat "$f" ; sleep .03 ; done ; printf '\e[?25h')
