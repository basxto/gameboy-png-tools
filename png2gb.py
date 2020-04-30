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

# broken => does not work with overworld_a and cave
# 0x00-0x7F verbatim
# 0x80-BF run
# 0xC0-FF alternating run
def compress_rle(data):
    global datasize
    #datasize = 0 ???
    # clean up
    data = data.replace("\n","").replace("\t","")[:-2]
    # convert to array
    data = data.split(", ")
    output = []
    verbatim = []
    # first character has run of 1
    counter = 1
    mode = 0

    # we skip first
    for i in range(1,len(data)):
        # same char => it's a run
        if mode == 0 and data[i-1] == data[i]:
            counter += 1
            if len(verbatim) != 0:
                output.append("(0x{0:02X})".format(len(verbatim)-1))
                output += verbatim
                datasize += 1+len(verbatim)
                del verbatim[:]
            #TODO: jump to alternating mode
            # maximum counter reached
            if counter == 127:
                output.append("(0x{0:02X})".format(0x80 | (counter-2)))
                output.append(data[i-1])
                datasize += 2
                counter = 1
        # alternating bytes
        elif mode == 1 and data[i-3] == data[i-1] and data[i-2] == data[i]:
            counter += 1
            i += 1
        # we have a new char => write run
        elif counter > 1:
            if mode == 0:
                output.append("(0x{0:02X})".format(0x80 | (counter-2)))
                output.append(data[i-1])
                datasize += 2
            else:
                output.append("(0x{0:02X})".format(0xC0 | (counter-2)))
                output.append(data[i-2])
                output.append(data[i-1])
                datasize += 3
            mode = 0
            counter = 1
        # verbatim buffer is full
        elif len(verbatim) == 255:
            output.append("(0x{0:02X})".format(len(verbatim)-1))
            output += verbatim
            datasize += 1+len(verbatim)
            del verbatim[:]
        # TODO: enable entry point for alternating run
        # check whether this is alternating
        """ elif len(verbatim) == 3:
            if mode == 0 and data[i-3] == data[i-1] and data[i-2] == data[i]:
                del verbatim[:]
                print("Alternating run")
                counter = 2
                mode = 1
            else:
                verbatim.append(data[i-1])
                counter = 1 """
        elif counter == 1:
            verbatim.append(data[i-1])
            counter = 1
    # handle last element
    if counter > 1:
        if mode == 0:
            output.append("(0x{0:02X})".format(0x80 | (counter-2)))
            output.append(data[len(data)-1])
            datasize += 2
        else:
            output.append("(0x{0:02X})".format(0xC0 | (counter-2)))
            output.append(data[len(data)-2])
            output.append(data[len(data)-1])
            datasize += 3
    else:
        verbatim.append(data[len(data)-1])
    if len(verbatim) > 0:
        output.append("(0x{0:02X})".format(len(verbatim)-1))
        output += verbatim
        datasize += 1+len(verbatim)
    # format output
    formatted_output = ""
    counter = 0
    for o in output:
        if counter == 0:
            formatted_output += "\n\t"
        formatted_output += "{0}, ".format(o)
        counter = (counter + 1) % 16
    return formatted_output[1:] + "\n"

def convert_image(width, height, filebase, pixel, d, m):
    global mapper
    global mapcounter
    global mapsize
    global datasize
    datasize = 0

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
                        if(mapcounter < args.limit):
                            dmap += "0x{0:02X}, ".format(mapper[tile])
                    else:
                        # add new tile
                        if(mapcounter < args.limit):
                            data += "\t" + tile + "\n"
                            datasize += 16
                        mapper[tile] = mapcounter
                        if(mapcounter < args.limit):
                            dmap += "0x{0:02X}, ".format(mapcounter)
                        mapcounter += 1
                    
                    mapsize += 1
    if args.compress_rle != "no":
        print("Before compression: 0x{0:02X} bytes".format(datasize))
        data = compress_rle(data)
        print("After compression: 0x{0:02X} bytes".format(datasize))
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
    global mapsize
    mapsize = 0
    global mapcounter
    mapcounter = 0
    global datasize
    datasize = 0
    dataaccu = 0
    # dimension of meta tiles

    parser = argparse.ArgumentParser()
    parser.add_argument('image', metavar='image.png', nargs='+',help='8bit PNG image')
    parser.add_argument("--uncompressed", "-u", default="no", help="Allow duplicate tiles")
    parser.add_argument("--width", type=int, default=1, help="Meta tile width")
    parser.add_argument("--height", type=int, default=1, help="Meta tile height")
    parser.add_argument("--output", "-o", default="", help="Base name for output files (default: derived from image name)")
    parser.add_argument("--datarom", "-r", default="", help="Address within the ROM, data should be placed at")
    parser.add_argument("--maprom", "-m", default="", help="Address within the ROM, map should be placed at")
    parser.add_argument("--palrom", "-p", default="", help="Address within the ROM, palette should be placed at")
    parser.add_argument("--limit", type=int, default=255, help="Maximum of tiles to put into data")
    parser.add_argument("--compress-rle", "-c", default="no", help="Additionally compress data with a simple RLE algorithm")
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
    d.write("// Generated by png2gb.py\n")
    if args.compress_rle != "no":
        d.write("// Compressed with RLE\n")
    if args.datarom != "":
        d.write("__at ({0}) ".format(args.datarom))
    d.write("const unsigned char {0}_data[] = ".format(os.path.basename(outbase))+"{\n")
    m = open(outbase + '_map.c', 'w')
    m.write("// Generated by png2gb.py\n")
    if args.maprom != "":
        m.write("__at ({0}) ".format(args.maprom))
    m.write("const unsigned char {0}_map[] = ".format(os.path.basename(outbase))+"{\n\t")
    p = open(outbase + '_pal.c', 'w')
    p.write("// Generated by png2gb.py\n")
    if args.palrom != "":
        p.write("__at ({0}) ".format(args.palrom))
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
        dataaccu += datasize

        convert_palette(original[3]['palette'], outbase, p)
    if args.compress_rle != "no":
        # end of compression
        d.write("\t(0xFF),\n\t")
        dataaccu+=1;
    d.seek(d.tell() - 3, 0)
    d.write("\n};")
    d.write("\n// {0} tiles".format(mapcounter))
    d.write("\n// 0x{0:02X} bytes".format(dataaccu))
    d.write("\nconst UINT8 {0}_data_length = {1};".format(os.path.basename(outbase), (mapcounter if mapcounter < args.limit else args.limit)))
    d.close()
    m.seek(m.tell() - 2, 0)
    m.write("\n};")
    m.write("\n// {0} tiles".format(mapsize))
    m.write("\n// 0x{0:02X} bytes".format(mapsize))
    m.close()
    p.seek(p.tell() - 4, 0)
    p.write("};")
    p.close()

    if(mapcounter >= args.limit):
        print("Warning: Too many unique tiles in tileset: {0}".format(mapcounter+1))


main()