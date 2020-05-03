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

# totally new compression idea:
# 0000000 end of data
# 0000000 could also have special meaning like two row mode
# -> next byte is a mask where 1 is the first common double byte and 0 is the second
# XXXXXXX mask that indicates where the most common double byte (row) occurs
# this is followed by the most common double byte
# when mask bit is 1, write the common double byte, if it is 0 read another doube byte
# it should be possible to quickly skip through this encoding tile-wise

# new idea:
# 2 bytes don’t have to be repeated more than 16 times (2 tiles)
# one byte doesn’t have to run more than 32 times (2 tiles)
# 00 0XXXXXXX - write through the next X bytes (127+1)
# 80 100XXXXX - run next byte X times (31+2) - highest and lowest color only
# A0 101XXXXX - run next byte X times alternating normal and inverted  (31+2) - middle colors only
# C0 110HLXXX - High Low colored line X times (7+1)
# E0 111XXXXX - run next 2 bytes X times alternating (30+2)
# FF 11111111 - end of data

# 1101 1111 represents 8 times 0xFF 0xFF, which are 16 bytes

# current:
# 0XXXXXXX - write through the next X bytes (127+1)
# 100XXXXX - run next byte X times (63+2) - highest and lowest color only
# 111XXXXX - run next 2 bytes X times alternating (63+2) - duplicate row
# 11111111 - end of data

def compress_rle(data):
    global datasize
    # we calculate new compressed datasize
    datasize = 0
    # clean up
    data = data.replace("\n","").replace("\t","")[:-2]
    # convert to array
    data = data.split(", ")
    output = []
    verbatim = [data[0]]
    # 0 is one byte and 1 is 2 bytes
    mode = 0 
    # first character has run of 1
    counter = 1
    # first character is already in verbatim buffer
    # we basically handle byte from last round
    i = 1
    while i < len(data):
        if mode == 0 and data[i-1] == data[i]:
            # run
            counter += 1
            # delete data[i-1] from array since it's in our run
            if len(verbatim) > 0:
                del verbatim[-1:]
            # flush verbatim buffer
            if len(verbatim) > 0:
                output.append("( 0x{0:02X} )".format(len(verbatim)-1))
                output += verbatim
                datasize += 1+len(verbatim)
                del verbatim[:]
            # maximum counter reached
            if counter == (0x1F + 3) or i == (len(data) - 1):
                append = False
                if counter > (0x1F + 2):
                    # only put current byte into run if it's last run
                    # and there is still place
                    counter -= 1
                    append = True
                if(counter > 1):
                    output.append("( 0x{0:02X} )".format(0x80 | (counter-2)))
                    output.append(data[i])
                    datasize += 2
                if append:
                    verbatim.append(data[i])
                counter = 1
        elif mode == 1 and (i+1) < len(data) and data[i-2] == data[i] and data[i-1] == data[i+1]:
            # run of alternating two bytes
            counter += 1
            # maximum counter reached
            if counter == (0x1E + 3) or i == (len(data) - 2):
                append = False
                if counter > (0x1E + 2):
                    # only put current bytes into run if it's last run
                    # and there is still place
                    counter -= 1
                    append = True
                if(counter > 1):
                    if counter <= 8 and (data[i-2] == '0xFF' or data[i-2] == '0x00') and (data[i-1] == '0xFF' or data[i-1] == '0x00'):
                        h = 0x0
                        l = 0x0
                        if data[i-2] == '0xFF':
                            h = 0x10
                        if data[i-1] == '0xFF':
                            l = 0x08
                        output.append("(0x{0:02X})".format(0xC0 | h | l | (int(counter)-1)))
                        datasize += 1
                    # only invert on a byte scale
                    elif int(data[i-2],16) == (int(data[i-1],16)^0xFF):
                        output.append("((0x{0:02X}))".format(0xA0 | (counter-2)))
                        output.append(data[i-2])
                        datasize += 2
                    else:
                        output.append("((0x{0:02X}))".format(0xE0 | (counter-2)))
                        output.append(data[i-2])
                        output.append(data[i-1])
                        datasize += 3
                if append:
                    verbatim.append(data[i])
                    verbatim.append(data[i+1])
                counter = 1
                mode = 0
            # since we handled two bytes
            i+=1
        elif counter > 1:
            # run just ended
            if mode == 0:
                if(counter <= 8*2 and counter%2 == 0 and (data[i-1] == '0xFF' or data[i-1] == '0x00')):
                    hl = 0x0
                    if data[i-1] == '0xFF':
                        hl = 0x18
                    output.append("(0x{0:02X})".format(0xC0 | hl | (int(counter/2)-1)))
                    datasize += 1
                else:
                    output.append("(0x{0:02X})".format(0x80 | (counter-2)))
                    output.append(data[i-1])
                    datasize += 2
            else:
                if counter <= 8 and (data[i-2] == '0xFF' or data[i-2] == '0x00') and (data[i-1] == '0xFF' or data[i-1] == '0x00'):
                    #print("We could optimize this")
                    h = 0x0
                    l = 0x0
                    if data[i-2] == '0xFF':
                        h = 0x10
                    if data[i-1] == '0xFF':
                        l = 0x08
                    output.append("(0x{0:02X})".format(0xC0 | h | l | (int(counter)-1)))
                    datasize += 1
                elif int(data[i-2],16) == (int(data[i-1],16)^0xFF):
                    output.append("(0x{0:02X})".format(0xA0 | (counter-2)))
                    output.append(data[i-2])
                    datasize += 2
                else:
                    output.append("(0x{0:02X})".format(0xE0 | (counter-2)))
                    output.append(data[i-2])
                    output.append(data[i-1])
                    datasize += 3
            verbatim.append(data[i])
            counter = 1
            mode = 0
        elif len(verbatim) == (0x7F + 1) or (len(verbatim) > 0 and i == (len(data) - 1)):
            # flush full verbatim buffer
            append = True
            if i == (len(data) - 1) and len(verbatim) < (0x7F + 1):
                # only do this if it still fits
                verbatim.append(data[i])
                append = False
            output.append("(0x{0:02X} )".format(len(verbatim)-1))
            output += verbatim
            datasize += 1+len(verbatim)
            del verbatim[:]
            if append:
                verbatim.append(data[i])
            counter = 1
        elif len(verbatim) >= 3 and mode == 0 and data[i-3] == data[i-1] and data[i-2] == data[i]:
            del verbatim[-3:]
            if len(verbatim) > 0:
                output.append("( 0x{0:02X})".format(len(verbatim)-1))
                output += verbatim
                datasize += 1+len(verbatim)
                del verbatim[:]
            counter = 2
            mode = 1
        else:
            verbatim.append(data[i])
            counter = 1
        i+=1
    # last byte
    if len(verbatim) > 0:
        output.append("(  0x{0:02X}  )".format(len(verbatim)-1))
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
    if args.compress_rle != "no" or args.size != "no":
        print("Before compression: 0x{0:02X} bytes".format(datasize))
    if args.compress_rle != "no":
        data = compress_rle(data)
    if args.compress_rle != "no" or args.size != "no":
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
    parser.add_argument("--size", "-s", default="no", help="Always print size for non compressed images")
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