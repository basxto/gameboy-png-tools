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

def data2array(data):
    # clean up
    data = data.replace("\n","").replace("\t","")[:-2]
    # convert to array
    arr = data.split(", ")
    return arr

def array2data(arr):
    formatted_output = ""
    counter = 0
    for a in arr:
        if counter == 0:
            formatted_output += "\n\t"
        formatted_output += "{0}, ".format(a)
        counter = (counter + 1) % 16
    return formatted_output[1:] + "\n"

# function for popping last character from encoding
def enc_pop(encoding_pair):
    element = 0
    return element, encoding_pair

# we don't have to look at the end of verbatim,
# that's the only thing that got already done
# verbatim blocks are still what we want to improve

# works with those, having onesteps (80, 70, C0) followed by verbatim:
#####

# 10 could be followed by two increments of it, same goes for C0
# -> saves nothing, slows down skipping
# -> unless that’s all the verbatim contains = 1 byte saved

# 07 could be followed by repetitions of the last number
# -> could become C0 or 80

# 10 and 07 could be followed by alternations
# -> could become C0 or A0 or E0

# works with those who could be transformed to a shorter notation with one or two additional numbers
#####

# 3 byte notations to 1 or 2 byte notations
# 2 byte notations to 1 byte notation

# verbatim that can change encoding with one or two additional numbers:
#####

# this is basically a special case of the first section
# can this even save space?

def improve_compression(output):
    return output

# helper function for compress_rle
def flush_verbatim(verbatim, output, datasize):
    if(args.color_line_compression == "yes" and len(verbatim) == 2 and (verbatim[0] == '0xFF' or verbatim[0] == '0x00') and (verbatim[1] == '0xFF' or verbatim[1] == '0x00')):
        # 1 byte instead of 3
        h = 0x0
        l = 0x0
        if verbatim[0] == '0xFF':
            h = 0x10
        if verbatim[1] == '0xFF':
            l = 0x08
        output.append(["(0x{0:02X})".format(ENC_LIN | h | l | 0),[]])
        datasize += 1
    else:
        output.append(["(0x{0:02X})".format(ENC_LIT | len(verbatim)-1), verbatim.copy()])
        datasize += 1+len(verbatim)
    return datasize, output

ENC_LIT = 0x00
ENC_INC = 0x70
ENC_RUN = 0x80
ENC_INV = 0xA0
ENC_LIN = 0xC0
ENC_ALT = 0xE0

# current:
# 2 bytes don’t have to be repeated more than 16 times (2 tiles)
# one byte doesn’t have to run more than 32 times (2 tiles)
# 00 0XXXXXXX - write through the next X bytes (127+1-15) [1 + n bytes]
# 70 0111XXXX - run next byte X times incrementing it each time (15+2) - map compression [2 bytes]
# 80 100XXXXX - run next byte X times (31+2) - highest and lowest color only [2 bytes]
# A0 101XXXXX - run next byte X*2 times alternating normal and inverted  (31+2) - middle colors only [2 bytes]
# C0 110HLXXX - High Low colored line X times (7+1) [1 byte]
# E0 111XXXXX - run next 2 bytes X times alternating (30+2) [3 bytes]
# FF 11111111 - end of data [1 byte]

# 1101 1111 represents 8 times 0xFF 0xFF, which are 16 bytes / one tile

# 70 and C0 can be unused, which shrinks down the decompressor

def compress_rle(data):
    # we calculate new compressed datasize
    datasize = 0
    data = data2array(data)
    output = []
    verbatim = [data[0]]
    # 0 is one byte, 1 is 2 bytes and 2 is incremental
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
                datasize, output = flush_verbatim(verbatim, output, datasize)
                del verbatim[:]
            if i == (len(data) - 1):
                # handle last iteration
                append = False
                if counter > (0x1F + 2):
                    # only put current byte into run if it's last run
                    # and there is still place
                    counter -= 1
                    append = True
                if(counter > 1):
                    output.append(["( 0x{0:02X} )".format(ENC_RUN | (counter-2)),[data[i]]])
                    datasize += 2
                if append:
                    verbatim.append(data[i])
            elif counter == (0x1F + 3):
                # maximum counter reached
                # switch to double mode
                # double mode is 1 byte shorter
                # if even amount of bytes is ahead
                counter = int(counter/2)
                mode = 1
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
                    if args.color_line_compression == "yes" and  counter <= 8 and (data[i-2] == '0xFF' or data[i-2] == '0x00') and (data[i-1] == '0xFF' or data[i-1] == '0x00'):
                        h = 0x0
                        l = 0x0
                        if data[i-2] == '0xFF':
                            h = 0x10
                        if data[i-1] == '0xFF':
                            l = 0x08
                        output.append(["(0x{0:02X})".format(ENC_LIN | h | l | (int(counter)-1)),[]])
                        datasize += 1
                    # only invert on a byte scale
                    elif int(data[i-2],16) == (int(data[i-1],16)^0xFF):
                        output.append(["((0x{0:02X}))".format(ENC_INV | (counter-2)),[data[i-2]]])
                        datasize += 2
                    else:
                        output.append(["((0x{0:02X}))".format(ENC_ALT | (counter-2)), [data[i-2], data[i-1]]])
                        datasize += 3
                if append:
                    verbatim.append(data[i])
                    # jump back by one, we don't wanna put two here
                    i-=1
                counter = 1
                mode = 0
            # since we handled two bytes
            i+=1
        elif mode == 2 and (int(data[i-2], 16) + 1 == int(data[i-1], 16)) and (int(data[i-1], 16) + 1 == int(data[i], 16)):
            counter += 1
            if counter == (0xF + 3) or i == (len(data) - 1):
                # maximum counter or end reached
                append = False
                # we have to calculate this once 0x01 would have 0x01 as data
                inc = int(data[i], 16) - counter + 1
                if counter > (0xF + 2):
                    counter -= 1
                    inc += 1
                    append = True
                output.append(["(( 0x{0:02X}))".format(0x70 |  (counter-2)), [inc]])
                datasize += 2
                if append:
                    verbatim.append(data[i])
                counter = 1
                mode = 0
        elif counter > 1:
            # run just ended
            if mode == 0:
                if args.color_line_compression == "yes" and (counter <= 8*2 and counter%2 == 0 and (data[i-1] == '0xFF' or data[i-1] == '0x00')):
                    hl = 0x0
                    if data[i-1] == '0xFF':
                        hl = 0x18
                    output.append(["(0x{0:02X})".format(ENC_LIN | hl | (int(counter/2)-1)), []])
                    datasize += 1
                else:
                    output.append(["(0x{0:02X})".format(ENC_RUN | (counter-2)),[data[i-1]]])
                    datasize += 2
            elif mode == 1:
                if args.color_line_compression == "yes" and  counter <= 8 and (data[i-2] == '0xFF' or data[i-2] == '0x00') and (data[i-1] == '0xFF' or data[i-1] == '0x00'):
                    h = 0x0
                    l = 0x0
                    if data[i-2] == '0xFF':
                        h = 0x10
                    if data[i-1] == '0xFF':
                        l = 0x08
                    output.append(["(0x{0:02X})".format(ENC_LIN | h | l | (int(counter)-1)),[]])
                    datasize += 1
                elif int(data[i-2],16) == (int(data[i-1],16)^0xFF):
                    output.append(["(0x{0:02X})".format(ENC_INV | (counter-2)),[data[i-2]]])
                    datasize += 2
                else:
                    output.append(["(0x{0:02X})".format(ENC_ALT | (counter-2)),[data[i-2], data[i-1]]])
                    datasize += 3
            else: # mode 2
                # we have to calculate this once 0x01 would have 0x01 as data
                output.append(["(0x{0:02X})".format(0x70 |  (counter-2)), ["0x{0:02X}".format(int(data[i-1], 16) - counter + 1)]])
                datasize += 2
            verbatim.append(data[i])
            counter = 1
            mode = 0
        elif len(verbatim) == (0x7F + 1 - 0xF) or (len(verbatim) > 0 and i == (len(data) - 1)):
            # flush full verbatim buffer
            append = True
            if i == (len(data) - 1) and len(verbatim) < (0x7F + 1):
                # only do this if it still fits
                verbatim.append(data[i])
                append = False
            datasize, output = flush_verbatim(verbatim, output, datasize)
            del verbatim[:]
            if append:
                verbatim.append(data[i])
            counter = 1
        elif args.increment_compression == "yes" and len(verbatim) >= 2 and mode == 0 and (int(data[i-3], 16) + 1 == int(data[i-2], 16)) and (int(data[i-2], 16) + 1 == int(data[i-1], 16)) and (int(data[i-1], 16) + 1 == int(data[i], 16)):
            # start incremental mode
            del verbatim[-2:]
            if len(verbatim) > 0:
                datasize, output = flush_verbatim(verbatim, output, datasize)
                del verbatim[:]
            counter = 3
            mode = 2
        elif len(verbatim) >= 3 and mode == 0 and data[i-3] == data[i-1] and data[i-2] == data[i]:
            # start double byte mode
            del verbatim[-3:]
            if len(verbatim) > 0:
                datasize, output = flush_verbatim(verbatim, output, datasize)
                del verbatim[:]
            counter = 2
            mode = 1
        else:
            verbatim.append(data[i])
            counter = 1
        i+=1
    # save even more bytes
    # from decompnessor view it’s free
    output = improve_compression(output)
    # flatten output
    #print(output)
    flatoutput = []
    for o in output:
        flatoutput.append(o[0])
        flatoutput+=o[1]
    #print(flatoutput)
    if datasize != len(flatoutput):
        print("Warning: counting is wrong {} vs {}".format(datasize, len(flatoutput)))
    # last byte
    if len(verbatim) > 0:
        datasize, output = flush_verbatim(verbatim, output, datasize)
    return datasize, array2data(flatoutput)

def convert_image(width, height, filebase, pixel, d, m):
    global mapper
    global mapcounter
    global mapsize
    global maprealsize
    global datasize
    datasize = 0
    maprealsize = 0

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
                            dmap += "0x{0:02X}, ".format(mapper[tile][0])
                            mapper[tile][1] += 1 # count occurences
                    else:
                        # add new tile
                        if(mapcounter < args.limit):
                            data += "\t" + tile + "\n"
                            datasize += 16
                        mapper[tile] = [mapcounter, 1]
                        if(mapcounter < args.limit):
                            dmap += "0x{0:02X}, ".format(mapcounter)
                        mapcounter += 1
                    mapsize += 1
                    maprealsize += 1
    return data, dmap

# We aim for ENC_LIN optimization foremost
# 2 byte encoding after that
def mapping_optimizer(data, dmap):
    sortedkeys = list({k: v for k, v in sorted(mapper.items(), key=lambda item: item[1][1], reverse=True)})
    #print("Most used mapping is 0x{0:02X} ({1} times)".format(mapper[sortedkeys[0]][0], mapper[sortedkeys[0]][1]))
    #print("Second most used mapping is 0x{0:02X} ({1} times)".format(mapper[sortedkeys[1]][0], mapper[sortedkeys[1]][1]))
    #print("Last index is 0x{0:02X}".format(len(mapper)-1))

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
    global maprealsize
    mapsize = 0
    maprealsize = 0
    global mapcounter
    mapcounter = 0
    global datasize
    databuffer = ""
    mapbuffer = ""
    datasize = 0
    dataaccu = 0
    mapaccu = 0
    # dimension of meta tiles

    parser = argparse.ArgumentParser()
    parser.add_argument('image', metavar='image.png', nargs='+',help='8bit PNG image')
    parser.add_argument("--uncompressed", "-u", default="no", help="Allow duplicate tiles (default: no)")
    parser.add_argument("--width", type=int, default=1, help="Meta tile width (default: 1)")
    parser.add_argument("--height", type=int, default=1, help="Meta tile height (default: 1)")
    parser.add_argument("--output", "-o", default="", help="Base name for output files (default: derived from image name)")
    parser.add_argument("--datarom", "-d", default="", help="Address within the ROM, data should be placed at")
    parser.add_argument("--maprom", "-m", default="", help="Address within the ROM, map should be placed at")
    parser.add_argument("--palrom", "-p", default="", help="Address within the ROM, palette should be placed at")
    parser.add_argument("--limit", type=int, default=255, help="Maximum of tiles to put into data (default: 255)")
    parser.add_argument("--compress-rle", "-c", default="no", help="Additionally compress data with improved RLE algorithm (default: no)")
    parser.add_argument("--compress-map-rle", "-r", default="no", help="Additionally compress map with improved RLE algorithm (default: no)")
    parser.add_argument("--color-line-compression", "-l", default="yes", help="Encode rows with just one color in one byte (default: yes)")
    parser.add_argument("--increment-compression", "-i", default="yes", help="Encode incrementing byte sequence (default: yes)")
    parser.add_argument("--size", "-s", default="no", help="Always print size for non compressed images (default: no)")
    #parser.add_argument("--extreme-compression", "-x", default="no", help="Try all permutations of the image (default: no)")
    #parser.add_argument("--permutation-seed", default="0", help="Specify permutation of the image (Find a good one with -x)")
    #parser.add_argument("--palmap", default="no", help="Concatenate the palette to the mapping array (helpful for RLE de/compression)")
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
    if args.compress_map_rle != "no":
        m.write("// Compressed with RLE\n")
    if args.maprom != "":
        m.write("__at ({0}) ".format(args.maprom))
    m.write("const unsigned char {0}_map[] = ".format(os.path.basename(outbase))+"{\n\t")
    p = open(outbase + '_pal.c', 'w')
    p.write("// Generated by png2gb.py\n")
    if args.palrom != "":
        p.write("__at ({0}) ".format(args.palrom))
    p.write("const unsigned int {0}_pal[][4] = ".format(os.path.basename(outbase)) + "{{\n\t")

    for filename in args.image:
        # read original image
        r=png.Reader(filename=filename)
        original = r.read()

        if original[0]%(8*args.height) != 0 or original[1]%(8*args.width) != 0:
            print("Image height must be a multiple of {0}".format(8*args.height), file=sys.stderr)
            print("Image width must be a multiple of {0}".format(8*args.width), file=sys.stderr)
            exit(2)

        data, dmap = convert_image(original[0], original[1], outbase, list(original[2]), d, m)
        databuffer += data
        mapbuffer += dmap
        dataaccu += datasize
        mapaccu += maprealsize
        convert_palette(original[3]['palette'], outbase, p)
    # maybe only do this with --compress-map-rle enabled
    # but data compression could still improve
    # only do this when mapping compression is active, so not for --uncompressed
    # compress both versions and take the smaller one
    mapping_optimizer(databuffer, mapbuffer)
    # compress everything as a whole
    if args.compress_rle != "no" or args.size != "no":
        print("Before compression: 0x{0:02X} bytes".format(dataaccu))
    if args.compress_rle != "no":
        dataaccu, databuffer = compress_rle(databuffer)
    if args.compress_rle != "no" or args.size != "no":
        print("After compression: 0x{0:02X} bytes".format(dataaccu))
    if args.compress_map_rle != "no" or args.size != "no":
        print("Map before compression: 0x{0:02X} bytes".format(mapaccu))
    if args.compress_map_rle != "no":
        mapaccu, mapbuffer = compress_rle(mapbuffer)
    if args.compress_map_rle != "no" or args.size != "no":
        print("Map after compression: 0x{0:02X} bytes".format(mapaccu))
    d.write(databuffer)
    m.write(mapbuffer)
    # we go by the length
    #if args.compress_rle != "no":
    #    # end of compression
    #    d.write("\t(0xFF),\n\t")
    #    dataaccu+=1;
    d.seek(d.tell() - 3, 0)
    d.write("\n};")
    d.write("\n// {0} tiles".format(mapcounter))
    d.write("\n// 0x{0:02X} bytes".format(dataaccu))
    d.write("\nconst unsigned char {0}_data_length = {1};".format(os.path.basename(outbase), (mapcounter if mapcounter < args.limit else args.limit)))
    d.close()
    m.seek(m.tell() - 2, 0)
    if args.compress_map_rle != "no":
        #end of compression
        m.write("\n(0xFF)};")
        mapaccu+=1
    else:
        m.write("\n};")
    m.write("\n// {0} tiles".format(mapsize))
    m.write("\n// 0x{0:02X} bytes".format(mapsize))
    if args.compress_map_rle != "no":
        m.write("\n// 0x{0:02X} real bytes".format(mapaccu))
    m.close()
    p.seek(p.tell() - 4, 0)
    p.write("};")
    p.close()

    if(mapsize > 256):
        print("{1}: warning: Too many mapped tiles in tileset: {0} (UINT8/unsigned char maximum is 255)".format(mapsize, args.image[0]))

    if(mapcounter >= args.limit):
        print("{1}: warning: Too many unique tiles in tileset: {0}".format(mapcounter+1, args.image[0]))


main()