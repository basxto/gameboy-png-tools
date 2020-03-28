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

def convert_image(width, height, filebase, pixel, d, m):
    global mapper
    global mapcounter

    data = ""
    dmap = ""
    for y in range(0, (int)(height/(8*args.height))):
        for x in range(0, (int)(width/(8*args.width))):
            for subx in range(0, args.width):
                for suby in range(0, args.height):
                    # subx and suby go top to bottom and then left to right
                    tile = convert_tile(x*args.width+subx, y*args.height+suby, pixel)
                    if compress and (tile in mapper):
                        # use existing tile
                        dmap += "0x{0:02X}, ".format(mapper[tile])
                    else:
                        # add new tile
                        data += "\t" + tile + "\n"
                        mapper[tile] = mapcounter
                        dmap += "0x{0:02X}, ".format(mapcounter)
                        mapcounter += 1
    d.write(data)
    m.write(dmap)

def convert_palette(palette, filebase, p):
    counter = 0
    pal = ""
    subpal = ""
    for color in palette:
        subpal = "RGB({0}, {1}, {2}), ".format((int)(color[0]/8), (int)(color[1]/8), (int)(color[2]/8)) + subpal
        counter += 1
        if counter == 4:
            counter = 0
            pal += subpal[:-2] + "\n},{\n\t"
            subpal = ""
    p.write(pal)

def main():
    global compress
    compress = True
    # for tile  mapping
    global mapper
    mapper = dict()
    global mapcounter
    mapcounter = 0
    # dimension of meta tiles

    parser = argparse.ArgumentParser()
    parser.add_argument('image', metavar='image.png', nargs='+',help='8bit PNG image')
    parser.add_argument("--uncompressed", "-u", default="no", help="Allow duplicate tiles")
    parser.add_argument("--width", type=int, default=1, help="Meta tile width")
    parser.add_argument("--height", type=int, default=1, help="Meta tile height")
    parser.add_argument("--output", "-o", default="", help="Base name for output files (default: derived from image name)")
    global args

    args = parser.parse_args()
    if args.uncompressed != "no":
        compress = False

    for filename in args.image:
        if filename.split('.')[-1] != 'png':
            print("Please give a .png file", file=sys.stderr)
            exit(1)

    # base name for output files
    outbase = args.image[0][:-4]

    if args.output != "":
        outbase = args.output
        if args.output.split('.')[-1] == 'png':
            outbase = args.output[:-4]
        if args.output.split('.')[-1] == 'c':
            outbase = args.output[:-2]
        if args.output[-7:] == '_data.c':
            outbase = args.output[:-7]
        if args.output[-6:] == '_map.c':
            outbase = args.output[:-6]
        if args.output[-6:] == '_pal.c':
            outbase = args.output[:-6]
    
    d = open(outbase + '_data.c', 'w')
    d.write("const unsigned char {0}_data[] = ".format(os.path.basename(outbase))+"{\n")
    m = open(outbase + '_map.c', 'w')
    m.write("const unsigned char {0}_map[] = ".format(os.path.basename(outbase))+"{\n\t")
    p = open(outbase + '_pal.c', 'w')
    p.write("const UWORD {0}_pal[][4] = ".format(os.path.basename(outbase)) + "{{\n\t")

    for filename in args.image:
        # read original image
        r=png.Reader(filename=filename)
        original = r.read()

        if original[0]%(8*args.height) != 0 or original[1]%(8*args.width) != 0:
            print("Image height must be a multiple of {0}".format(8*args.height), file=sys.stderr)
            print("Image width must be a multiple of {0}".format(8*args.width), file=sys.stderr)
            exit(2)

        convert_image(original[0], original[1], outbase, list(original[2]), d, m)

        convert_palette(original[3]['palette'], outbase, p)
    d.seek(d.tell() - 3, 0)
    d.write("\n};")
    d.close()
    m.seek(m.tell() - 2, 0)
    m.write("\n};")
    m.close()
    p.seek(p.tell() - 4, 0)
    p.write("};")
    p.close()


main()