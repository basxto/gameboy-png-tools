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
    tile=[]
    for suby in range(0, 8):
        for subx in range(0, 8):
            pxl = ~(pixel[y*8+suby][x*8+subx] % 4)
            lobyte |= ((pxl & 0x2)>>1) << (7-subx)
            hibyte |= (pxl & 0x1) << (7-subx)
            if subx == 7:
                #tile += '0x{0:02X}, 0x{1:02X}, '.format(hibyte, lobyte)
                tile += [hibyte, lobyte]
                hibyte=0
                lobyte=0
    return tile

def convert_image(width, height, filebase, pixel, d, m):
    global args
    global mapper
    global mapcounter
    global mapsize
    global maprealsize
    global datasize
    datasize = 0
    maprealsize = 0

    data = []
    dmap = []
    for y in range(0, (int)(height/(8*args.height))):
        for x in range(0, (int)(width/(8*args.width))):
            for subx in range(0, args.width):
                for suby in range(0, args.height):
                    # subx and suby go top to bottom and then left to right
                    tile = convert_tile(x*args.width+subx, y*args.height+suby, pixel)
                    tilestr = ",".join(map(str,tile))
                    # mirror tile horizontally (bitwise)
                    mh_tilestr = ",".join(map(lambda x: str(int('{:08b}'.format(x)[::-1], 2)),tile))
                    if compress and (tilestr in mapper):
                        # use existing tile
                        if(mapcounter < args.limit):
                            #dmap += "0x{0:02X}, ".format(mapper[tile][0])
                            dmap.append(mapper[tilestr][0])
                            mapper[tilestr][1] += 1 # count occurences
                    elif compress and mirror and (mh_tilestr in mapper):
                        # use existing tile
                        if(mapcounter < args.limit):
                            dmap.append(0x80 | mapper[mh_tilestr][0])
                            mapper[mh_tilestr][1] += 1
                    else:
                        # add new tile
                        if(mapcounter < args.limit):
                            data += tile
                            datasize += 16
                        mapper[tilestr] = [mapcounter, 1]
                        if(mapcounter < args.limit):
                            #dmap += "0x{0:02X}, ".format(mapcounter)
                            dmap.append(mapcounter)
                        mapcounter += 1
                    mapsize += 1
                    maprealsize += 1
    return data, dmap

# print as hex
def hx(num):
    return "0x{0:02X}".format(num)

# We aim for ENC_ROW optimization foremost
# 2 byte encoding after that
def mapping_optimizer(data, dmap):
    sortedkeys = list({k: v for k, v in sorted(mapper.items(), key=lambda item: item[1][1], reverse=True)})
    #print("Most used mapping is 0x{0:02X} ({1} times)".format(mapper[sortedkeys[0]][0], mapper[sortedkeys[0]][1]))
    #print("Second most used mapping is 0x{0:02X} ({1} times)".format(mapper[sortedkeys[1]][0], mapper[sortedkeys[1]][1]))
    #print("Last index is 0x{0:02X}".format(len(mapper)-1))

def convert_palette(palette, filebase, p):
    counter = 0
    pal = []
    subpal = []
    for color in palette:
        if args.c_include != "no":
            subpal = ["RGB({0}, {1}, {2})".format((int)(color[0]/8), (int)(color[1]/8), (int)(color[2]/8))] + subpal
        else:
            r = int(color[0]/8)
            g = int(color[1]/8)
            b = int(color[2]/8)
            rgb555 = r<<10 | g<<5 | b
            subpal = [rgb555>>8, rgb555&0xFF] + subpal
        counter += 1
        if counter == 4:
            counter = 0
            #pal += subpal[:-2] + "\n},{\n\t"
            pal.append(subpal)
            subpal = []
            #print(pal)
    return pal
    #p.write("\n},{\n\t".join(map(",".join,pal)))

def main():
    global compress
    compress = True
    global mirror
    mirror = False
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
    databuffer = []
    mapbuffer = []
    palbuffer = []
    datasize = 0
    dataaccu = 0
    mapaccu = 0
    # dimension of meta tiles

    parser = argparse.ArgumentParser()
    parser.add_argument('image', metavar='image.png', nargs='+',help='8bit PNG image')
    parser.add_argument("--uncompressed", "-u", default="no", help="Allow duplicate tiles (default: no)")
    parser.add_argument("--width", type=int, default=1, help="Meta tile width (default: 1)")
    parser.add_argument("--height", type=int, default=1, help="Meta tile height (default: 1)")
    parser.add_argument("--output", "-o", default="", help="Base name for output files or - for stdout (default: derived from image name)")
    parser.add_argument("--datarom", "-d", default="", help="Address within the ROM, data should be placed at (needs -c)")
    parser.add_argument("--maprom", "-m", default="", help="Address within the ROM, map should be placed at (needs -c)")
    parser.add_argument("--palrom", "-p", default="", help="Address within the ROM, palette should be placed at (needs -c)")
    parser.add_argument("--limit", type=int, default=255, help="Maximum of tiles to put into data (default: 255)")
    parser.add_argument("--size", "-s", default="no", help="Always print size for non compressed images (default: no)")
    parser.add_argument("--c-include", "-c", default="no", help="Output c source instead of binary files (default: no)")
    parser.add_argument("--verbose", "-v", default="no", help="Tell which files got written (default: no)")
    parser.add_argument("--binary", "-b", default="no", help="Pipe output binary (default: no)")
    parser.add_argument("--flip-horizontally", "-f", default="no", help="Mirror tiles horizontally during deduplication; 0x80 marks flipped tiles (default: no)")
    global args

    args = parser.parse_args()
    if args.uncompressed != "no":
        compress = False
    if args.flip_horizontally != "no":
        mirror = True

    if args.image[0] != "-":
        for filename in args.image:
            if filename.split('.')[-1] != 'png':
                print("Please give a .png file", file=sys.stderr)
                exit(1)
        # base name for output files
        outbase = args.image[0][:-4]

    if args.output != "" and args.output != "-":
        outbase = args.output
        if args.output.split('.')[-1] == '1bpp':
            outbase = args.output[:-5]
        if args.output.split('.')[-1] == '2bpp':
            outbase = args.output[:-5]
        if args.output.split('.')[-1] == 'tilemap':
            outbase = args.output[:-8]
        if args.output.split('.')[-1] == 'pal':
            outbase = args.output[:-4]
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

    if args.output == "-" and args.image[0] == "-":
        print("You need to specify an output file if you read from stdin", file=sys.stderr)
        exit(1)

    #d = open(outbase + '_data.c', 'w')
    d = sys.stdout
    m = open(outbase + '_map.c', 'w')
    p = open(outbase + '_pal.c', 'w')
    if args.c_include != "no":
        if args.binary == "no":
            if args.output != "-":
                d = open(outbase + '_data.c', 'w')
                if args.verbose != "no":
                    print("Write to {0}...".format(outbase + '_data.c'), file=sys.stderr)
            else:
                if args.verbose != "no":
                    print("Write to {0}...".format("stdout"), file=sys.stderr)
            d.write("// Generated by png2gb.py\n")
            if args.datarom != "":
                d.write("__at ({0}) ".format(args.datarom))
            d.write("const unsigned char {0}_data[] = ".format(os.path.basename(outbase))+"{\n")
        if not (args.output == "-" and args.image[0] == "-"):
            if args.verbose != "no":
                print("Write to {0}...".format(outbase + '_map.c'), file=sys.stderr)
                print("Write to {0}...".format(outbase + '_pal.c'), file=sys.stderr)
            m.write("// Generated by png2gb.py\n")
            if args.maprom != "":
                m.write("__at ({0}) ".format(args.maprom))
            m.write("const unsigned char {0}_map[] = ".format(os.path.basename(outbase))+"{\n\t")
            p.write("// Generated by png2gb.py\n")
            if args.palrom != "":
                p.write("__at ({0}) ".format(args.palrom))
            p.write("const unsigned int {0}_pal[][4] = ".format(os.path.basename(outbase)) + "{{\n\t")

    for filename in args.image:
        # read original image
        #r=png.Reader(filename=filename)
        r = ""
        if filename != "-":
            r=png.Reader(filename=filename)
            if args.verbose != "no":
                print("Read from {0}...".format(filename), file=sys.stderr)
        else:
            r=png.Reader(file=sys.stdin.buffer)
            if args.verbose != "no":
                print("Read from {0}...".format("stdin"), file=sys.stderr)
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
        palbuffer += convert_palette(original[3]['palette'], outbase, p)
    # maybe only do this with --compress-map-rle enabled
    # but data compression could still improve
    # only do this when mapping compression is active, so not for --uncompressed
    # compress both versions and take the smaller one
    mapping_optimizer(databuffer, mapbuffer)

    if args.c_include != "no":
        mapbuffer = ", ".join(map(hx,mapbuffer))
        m.write(mapbuffer)
        if args.binary == "no":
            databuffer = ", ".join(map(hx,databuffer))
            d.write(databuffer)
            d.write("\n};\n")
            d.write("\n// {0} tiles".format(mapcounter))
            d.write("\n// 0x{0:02X} bytes".format(dataaccu))
            d.write("\nconst unsigned char {0}_data_length = {1};\n".format(os.path.basename(outbase), (mapcounter if mapcounter < args.limit else args.limit)))
        else:
            d = sys.stdout.buffer
            if args.verbose != "no":
                print("Write to {0}...".format("stdout"), file=sys.stderr)
            d.write(bytes(databuffer))
        if not (args.output == "-" and args.image[0] == "-"):
            m.write("\n};\n")
            m.write("\n// {0} tiles".format(mapsize))
            m.write("\n// 0x{0:02X} bytes".format(mapsize))
            p.write("\n},{\n\t".join(map(", ".join,palbuffer)))
            p.write("\n}};\n")
    else:
        m.close()
        p.close()
        if args.output != "-":
            d = open(outbase + '.2bpp', 'wb')
            if args.verbose != "no":
                print("Write to {0}...".format(outbase + '.2bpp'), file=sys.stderr)
        else:
            d = sys.stdout.buffer
            if args.verbose != "no":
                print("Write to {0}...".format("stdout"), file=sys.stderr)
        d.write(bytes(databuffer))
        if args.output != "-" and args.image[0] != "-":
            m = open(outbase + '.tilemap', 'wb')
            if args.verbose != "no":
                print("Write to {0}...".format(outbase + '.tilemap'), file=sys.stderr)
            m.write(bytes(mapbuffer))
            flatpal = []
            for pal in palbuffer:
                flatpal += pal
            p = open(outbase + '.pal', 'wb')
            if args.verbose != "no":
                print("Write to {0}...".format(outbase + '.pal'), file=sys.stderr)
            p.write(bytes(flatpal))
    d.close()
    m.close()
    p.close()


    if(mapsize > 256):
        print("{1}: warning: Too many mapped tiles in tileset: {0} (UINT8/unsigned char maximum is 255)".format(mapsize, args.image[0]), file=sys.stderr)

    if(mapcounter >= args.limit):
        print("{1}: warning: Too many unique tiles in tileset: {0}".format(mapcounter+1, args.image[0]), file=sys.stderr)


main()