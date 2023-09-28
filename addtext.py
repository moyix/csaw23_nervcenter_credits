#!/usr/bin/env python3

import argparse
from subtitle_render import add_subtitle

def main():
    parser = argparse.ArgumentParser("Add text to an image")
    parser.add_argument('input', help='image to add text to')
    parser.add_argument('output', help='output image')
    parser.add_argument('text', help='text to add')
    parser.add_argument('-f', '--font', default='Helvetica-Neue-Bold', help='font to use')
    parser.add_argument('-z', '--size', type=int, default=12, help='font size')
    parser.add_argument('-g', '--gravity', default='south', help='gravity')
    parser.add_argument('-o', '--offset', default='+0+2', help='offset')
    parser.add_argument('-c', '--color', default='white', help='color')
    args = parser.parse_args()
    add_subtitle(
        args.input, args.output, subtitle=args.text,
        font=args.font, size=args.size,
        gravity=args.gravity, offset=args.offset, color=args.color)

if __name__ == '__main__':
    main()
