#!/bin/env python3
# Convert indexed png to image in gameboy format
# This needs https://github.com/drj11/pypng
import png
import argparse
import os
import sys

# https://www.huderlem.com/demos/gameboy2bpp.html
def convert_tile(x, y, pixel):
    hibyte=0
    lobyte=0
    tile=""
    for suby in range(0, 8):
        for subx in range(0, 8):
            pxl = ~(pixel[y*8+suby][x*8+subx] % 4)
            lobyte |= ((pxl & 0x2)>>1) << (7-subx)
            hibyte |= (pxl & 0x1) << (7-subx)
            if subx == 7:
                tile += '0x{0:02X}, 0x{1:02X}, '.format(hibyte, lobyte)
                hibyte=0
                lobyte=0
    return tile

def convert_image(width, height, filename, pixel):
    mapper = dict()
    mapcounter = 0

    data = "const unsigned char {0}_data[] = ".format(os.path.basename(filename)[:-4])+"{\n"
    dmap = "const unsigned char {0}_map[] = ".format(os.path.basename(filename)[:-4])+"{\n\t"
    for y in range(0, (int)(height/(8*args.height))):
        for x in range(0, (int)(width/(8*args.width))):
            for subx in range(1, args.width+1):
                for suby in range(1, args.height+1):
                    # subx and suby go top to bottom and then left to right
                    tile = convert_tile(x*subx, y*suby, pixel)
                    if compress and (tile in mapper):
                        # use existing tile
                        dmap += "0x{0:02X}, ".format(mapper[tile])
                    else:
                        # add new tile
                        data += "\t" + tile + "\n"
                        mapper[tile] = mapcounter
                        dmap += "0x{0:02X}, ".format(mapcounter)
                        mapcounter += 1
    dmap = dmap[:-2] + "\n};"
    data = data[:-3] + "\n};"

    d = open(filename[:-4] + '_data.c', 'w')
    d.write(data)
    d.close()
    m = open(filename[:-4] + '_map.c', 'w')
    m.write(dmap)
    m.close()

def convert_palette(palette, filename):
    counter = 0
    pal = "const UWORD {0}_pal[][] = ".format(os.path.basename(filename)[:-4]) + "{{\n\t"
    subpal = ""
    for color in palette:
        subpal = "RGB({0}, {1}, {2}), ".format((int)(color[0]/8), (int)(color[1]/8), (int)(color[2]/8)) + subpal
        counter += 1
        if counter == 4:
            counter = 0
            pal += subpal[:-2] + "\n},{\n\t"
            subpal = ""
    pal = pal[:-4] + "};"

    p = open(filename[:-4] + '_pal.c', 'w')
    p.write(pal)
    p.close()

def main():
    global compress
    compress = True
    # dimension of meta tiles
    width = 1
    height = 1

    parser = argparse.ArgumentParser()
    parser.add_argument('image', help='8bit PNG image')
    parser.add_argument("--uncompressed", default="no", help="Allow duplicate tiles")
    parser.add_argument("--width", type=int, default=1, help="Meta tile width")
    parser.add_argument("--height", type=int, default=1, help="Meta tile height")
    global args

    args = parser.parse_args()
    if args.uncompressed != "no":
        compress = False
    if args.width:
        width = args.width
        height = args.height

    filename = args.image
    if filename.split('.')[-1] != 'png':
        print("Please give a .png file", file=sys.stderr)
        exit(1)

    # read original image
    r=png.Reader(filename=filename)
    original = r.read()

    if original[0]%(8*height) != 0 or original[1]%(8*width) != 0:
        print("Image height must be a multiple of {0}".format(8*height), file=sys.stderr)
        print("Image width must be a multiple of {0}".format(8*width), file=sys.stderr)
        exit(2)

    convert_image(original[0], original[1], filename, list(original[2]))

    convert_palette(original[3]['palette'], filename)


main()