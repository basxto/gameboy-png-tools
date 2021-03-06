#!/bin/env python3
# Convert gameboy images to indexed png
# Used palette is https://lospec.com/palette-list/dirtyboy
# This needs https://github.com/drj61/pypng
import png
import re
import argparse
import os
import sys
import math


# https://www.huderlem.com/demos/gameboy2bpp.html
def convert_tile(data):
    hibyte=0
    lobyte=0
    index=0
    tile=[]
    for suby in range(0, 8):
        tile.append([])
        # invert with ^0xFF for palette compatibility with png2gb
        hibyte=data[index+1] ^ 0xFF
        lobyte=data[index] ^ 0xFF
        for subx in range(0, 8):
            pxl = ((hibyte>>(7-subx))&0x1) << 1
            pxl |= (lobyte>>(7-subx))&0x1
            tile[suby].append(pxl)
        index+=2
    return tile

def convert_image(data):
    mapper = []
    global tilemap
    image = []
    index = 0
    width = args.width
    while len(data) != 0:
        tile = convert_tile(data)
        mapper.append(tile)
        # 16 byte per tile
        data = data[16:]
    # generate white tile
    white=[]
    for suby in range(0, 8):
        white.append([])
        for subx in range(0, 8):
            white[suby].append(3)
    mapper.append(white)
    white = len(mapper)-1

    # generate tilemap if there is none
    if len(tilemap) == 0:
        for i in range(white):
            tilemap.append(i)

    # calculate width
    if args.height != 1:
        width = math.ceil(white/args.height)

    # fill with whiteness
    while len(tilemap)%width != 0:
        tilemap.append(white)

    # switch x and y in tilemap
    if args.height != 1:
        old_tilemap = tilemap
        tilemap = []
        for y in range(args.height):
            for x in range(width):
                tilemap.append(old_tilemap[x*args.height + y])


    for tile_index in tilemap:
        tile = mapper[tile_index]
        if index == 0:
            for y in range(0, 8):
                image.append(tile[y])
        else:
            for y in range(0, 8):
                image[y-8]+=tile[y]
        # <width> tiles per row
        index=(index+1)%width
    return image

def mono2color(data):
    color_data = []
    for dat in data:
        color_data.append(dat)
        color_data.append(dat)
    return color_data


def main():
    global mirror
    global tilemap
    tilemap = []
    mirror = False
    outbase = 'unnamed'

    parser = argparse.ArgumentParser()
    parser.add_argument('image', metavar='image.2bpp', help='2bpp image')
    parser.add_argument("--output", "-o", default="", help="Output image (default: image_gb.png)")
    parser.add_argument("--monochrome", "-m", default="no", help="1bpp mode (default: no)")
    parser.add_argument("--tilemap", "-t", default="", help="Tilemap file, '' gets treated as disabled [unsupported]")
    parser.add_argument("--width", type=int, default=16, help="Row width (default: 16)")
    parser.add_argument("--height", type=int, default=1, help="Meta tile height (default: 1)")
    parser.add_argument("--flip-horizontally", "-f", default="no", help="0x80 marks flipped tiles (default: no) [unsupported]")
    global args

    args = parser.parse_args()
    if args.flip_horizontally != "no":
        mirror = True

    if args.image != "-":
        if args.monochrome != "no":
            if args.image.split('.')[-1] != '1bpp':
                print("Please give a .1bpp file", file=sys.stderr)
                exit(1)
        else:
            if args.image.split('.')[-1] != '2bpp':
                print("Please give a .2bpp file", file=sys.stderr)
                exit(1)
        # base name for output files
        if args.output == "":
            args.output = re.sub("(_gbc)?\.[12]bpp", "_gb.png", args.image)

    # read piped data
    if args.image == "-":
        data = list(sys.stdin.buffer.read())
    else:
        f = open(args.image, "rb")
        data = list(f.read())
        f.close
    if len(data) == 0:
        print("Error: Empty input stream", file=sys.stderr)
        exit(1)

    if args.monochrome != "no":
        data = mono2color(data)

    s = convert_image(data)

    palette = [(0x1f,0x1f,0x1f),(0x4d,0x53,0x3c),(0x8b,0x95,0x6d),(0xc4,0xcf,0xa1)]
    w = png.Writer(len(s[0]), len(s), palette=palette, bitdepth=2)
    f = open(args.output, 'wb')
    w.write(f, s)

main()