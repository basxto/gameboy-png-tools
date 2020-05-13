#!/bin/env python3
# Compress binary data with RLE-like format
import argparse
import os
import sys

def array2data(arr):
    formatted_output = ""
    counter = 0
    for a in arr:
        if counter == 0:
            formatted_output += "\n\t"
        formatted_output += "{0}, ".format(a)
        counter = (counter + 1) % 16
    return formatted_output[1:] + "\n"

# print as hex
def hx(num):
    return "0x{0:02X}".format(num)

# for commands bytes
def hxc(num):
    return "(0x{0:02X})".format(num)

def enc_poppable(encoding_pair, amount=0):
    cmd = encoding_pair[0]
    value = 0
    if cmd == ENC_EOD:
        sys.exit("{0}: error: 0xFF command in data stream".format(args.image[0]))
    if (cmd & 0xF0) == ENC_INC:
        value = cmd & 0xF
        return value != 0
    elif (cmd & 0x80) == 0:
        return True
    elif (cmd & 0xE0) == ENC_ROW:
        value = cmd & 0x7
    else:
        value = cmd & 0x1F
    return value-amount > 0

# function for popping last character from encoding
def enc_pop(encoding_pair):
    cmd = encoding_pair[0]
    if (cmd & 0xF0) == ENC_INC:
        value = cmd & 0xF
        if value == 0:
            # had two elements, reduce to verbatim
            return [encoding_pair[1][0]+value+1], [ENC_LIT, encoding_pair[1]]
        else:
            return [encoding_pair[1][0]+value+1], [cmd-1, encoding_pair[1]]
    if (cmd & 0x80) == 0:#verbatim
        if cmd == 0:
            return [encoding_pair[1][0]], []
        else:
            return [encoding_pair[1][-1]], [cmd-1, encoding_pair[1][:-1]]
    if (cmd & 0xE0) == ENC_ROW:
        value = cmd & 0xE
        byte1 = "0xFF"
        byte2 = "0xFF"
        if (cmd & 0x10) == 0:
            byte1 = "0x00"
        if (cmd & 0x8) == 0:
            byte2 = "0x00"
        if value == 0:
            return [byte1, byte2], []
        else:
            return [byte1, byte2], [cmd-1]
    value = cmd & 0x1F
    if (cmd & 0xE0) == ENC_RUN or (cmd & 0xE0) == ENC_ALT:
        if value == 0:
            return encoding_pair[1], [ENC_LIT, encoding_pair[1]]
        else:
            return encoding_pair[1], [cmd-1, encoding_pair[1]]
    if (cmd & 0xE0) == ENC_INV:
        if value == 0:
            return [encoding_pair[1][0], encoding_pair[1][0]^0xFF], [ENC_LIT, [encoding_pair[1][0], encoding_pair[1][0]^0xFF]]
        else:
            return [encoding_pair[1][0], encoding_pair[1][0]^0xFF], [cmd-1, encoding_pair[1]]
    return [], encoding_pair

# we don't have to look at the end of verbatim,
# that's the only thing that got already done
# verbatim blocks are still what we want to improve

# works with those, having onesteps (80, 70, C0) followed by verbatim:
#####

# 10 could be followed by two increments of it, same goes for C0
# -> saves nothing, slows down skipping
# -> unless that’s all the verbatim contains = 1 byte saved
# -> or we need at least 3 -> we'd already found that
# X

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
    output = output.copy()
    i = 1
    while i < len(output):
        cmd = output[i][0]
        lcmd = output[i-1][0]
        if (cmd & 0x80) == 0 and (cmd & ENC_INC) != ENC_INC:
            value = cmd+ENC_LIT_MIN
            # verbatim
            if enc_poppable(output[i-1]) and value >= 2:
                # they are all 1B
                if (lcmd & 0xE0) == ENC_RUN or (lcmd & 0xF0) == ENC_INC or (lcmd & 0x80) == ENC_LIT:
                    el, encoding_pair = enc_pop(output[i-1])
                    el = el[0]
                    byte1 = output[i][1][0]
                    byte2 = output[i][1][1]
                    if args.increment_compression == "yes" and  (lcmd & 0xE) == ENC_RUN and value == 2:
                        if el + 1 == byte1 and byte1+1 == byte2:
                            # ENC_INC
                            if args.output != "-":
                                print("- I found something improvable!")
                    elif (lcmd & 0xE) == ENC_RUN and value == 3:
                        byte3 = output[i][1][2]
                        if el == byte2 and byte1 == byte3:
                            # ENC_ALT || ENC_INV or even ENC_RUN || ENC_ROW
                            if args.output != "-":
                                print("- I found something improvable!!")
            elif args.increment_compression == "yes" and value == 1 and lcmd == ENC_ALT:# short for min amount ALT
                # ALT A B LIT C -> INC A INC A
                a = output[i-1][1][0]
                b = output[i-1][1][1]
                c = output[i][1][0]
                if a+1 == b and b+1 == c:
                    output[i-1][0] = ENC_INC
                    del output[i-1][1][1]
                    output[i][0] = ENC_INC + 1
                    output[i][1][0] = output[i-1][1][0]
            # those are usually not found because this length could interrupt LITs
            # we lack knowledge during parsing
            elif args.increment_compression == "yes" and value == 2 and output[i][1][0]+1 == output[i][1][1]:
                # LIT A B -> INC A
                output[i][0] = ENC_INC
                del output[i][1][1]
        i += 1
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
            l = 0x01
        output.append([ENC_ROW | h | l | 0,[]])
        datasize += 1
    else:
        output.append([ENC_LIT | len(verbatim)-ENC_LIT_MIN, verbatim.copy()])
        datasize += 1+len(verbatim)
    return datasize, output

ENC_INC = 0x00 # 2+
ENC_INC_MIN = 1
ENC_INC_MAX = ENC_INC_MIN+15-1 #exclude MON
ENC_LIT = 0x00 # 1+
ENC_LIT_MIN = (1-0x10)
ENC_LIT_MAX = ENC_LIT_MIN+127-(ENC_INC_MAX-ENC_INC_MIN)
ENC_RUN = 0x80 # 2+
ENC_RUN_MIN = 1
ENC_RUN_MAX = ENC_RUN_MIN+31-1
ENC_INV = 0xC0 # 4+
ENC_INV_MIN = 2
ENC_INV_MAX = ENC_INV_MIN+31
ENC_ROW = 0xA0 # 2+
ENC_ROW_MIN = 1
ENC_ROW_MAX = ENC_ROW_MIN+7
ENC_ALT = 0xC1 # 4+
ENC_ALT_MIN = 2
ENC_ALT_MAX = ENC_ALT_MIN+30
ENC_EOD = 0x00 # 0
ENC_MON = 0x80 # 0

#newest idea:
# command bytes with size, values
# and outputed bytes per value
#
# 0x 0b       NAME SIZE  OUT VALUES
####################################
# 00 00000000 EOD [ 1B ] 0B  1
# 00 0000XXXX INC [ 2B ] 1B  2-(17-1)       // don't forget in decompressor that this lost one
# 00 0XXXXXXX LIT [1B+n] 1B  1-(128-15)
# 80 10000000 MON [ 1B ] 0B  1
# 80 100XXXXX RUN [ 2B ] 1B  2-(33-1)
# A0 101HXXXL ROW [ 1B ] 2B  1-8
# C0 11XXXXX0 INV [ 2B ] 2B  2-33
# E0 11XXXXX1 ALT [ 3B ] 2B  2-33
#
# End Of Data marker
# LITerally writes the following bytes through (worst case reduction)
# INCrements the byte each iteration (mapping compression)
# switch to MONochrome mode aka 1bpp
# RUNs the byte X times (darkest and brightest color)
# writes ROWs of constant color, High and Low are inverted (all four colors)
# alternates between byte and it's INVersion (middle colors)
# ALTernates between the two bytes (all four colors)
#
# Switching to 1bpp mode is only allowed at input byte position %2==0
#
# == 0x0 is cheap
# 0x1-1=0x0 and 0x0-1=0xFF
# nibble swap is cheap
# all who output 2B got their values shifted one to the left (*2)
#
# masks are 0x80 (lit) 0x70(inc) 0xE0 (run, row) 0xC1 (inv, alt)
#
# 70 and A0 could be disabled-> speeds up LIT and RUN
# 00 00000000 EOD
# 00 0XXXXXXX LIT
# 80 10XXXXXX RUN
# C0 11XXXXX0 INV
# E0 11XXXXX1 ALT


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
    output = []
    if args.monochrome != "no":
        output.append([ENC_MON, []])
        datasize += 1
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
                    output.append([ENC_RUN | (counter-ENC_RUN_MIN),[data[i]]])
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
                            l = 0x01
                        output.append([ENC_ROW | h | l | (int(counter)-1)<<1,[]])
                        datasize += 1
                    # only invert on a byte scale
                    elif data[i-2] == (data[i-1]^0xFF):
                        output.append([ENC_INV | ((counter-ENC_INV_MIN)<<1),[data[i-2]]])
                        datasize += 2
                    else:
                        output.append([ENC_ALT | ((counter-ENC_ALT_MIN)<<1), [data[i-2], data[i-1]]])
                        datasize += 3
                if append:
                    verbatim.append(data[i])
                    # jump back by one, we don't wanna put two here
                    i-=1
                counter = 1
                mode = 0
            # since we handled two bytes
            i+=1
        elif mode == 2 and (data[i-2] + 1 == data[i-1]) and (data[i-1] + 1 == data[i]):
            counter += 1
            if counter == (ENC_INC_MAX+1) or i == (len(data) - 1):
                # maximum counter or end reached
                append = False
                # we have to calculate this once 0x01 would have 0x01 as data
                inc = data[i] - counter + 1
                if counter > (ENC_INC_MAX):
                    counter -= 1
                    append = True
                output.append([ENC_INC |  (counter-ENC_INC_MIN), [inc]])
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
                        hl = 0x11
                    output.append([ENC_ROW | hl | (int(counter/2)-1)<<1, []])
                    datasize += 1
                else:
                    output.append([ENC_RUN | (counter-ENC_RUN_MIN),[data[i-1]]])
                    datasize += 2
            elif mode == 1:
                if args.color_line_compression == "yes" and  counter <= 8 and (data[i-2] == '0xFF' or data[i-2] == '0x00') and (data[i-1] == '0xFF' or data[i-1] == '0x00'):
                    h = 0x0
                    l = 0x0
                    if data[i-2] == '0xFF':
                        h = 0x10
                    if data[i-1] == '0xFF':
                        l = 0x01
                    output.append([ENC_ROW | h | l | (int(counter)-1)<<1,[]])
                    datasize += 1
                elif data[i-2] == (data[i-1]^0xFF):
                    output.append([ENC_INV | ((counter-ENC_INV_MIN)<<1),[data[i-2]]])
                    datasize += 2
                else:
                    output.append([ENC_ALT | ((counter-ENC_ALT_MIN)<<1),[data[i-2], data[i-1]]])
                    datasize += 3
            else: # mode 2
                # we have to calculate this once 0x01 would have 0x01 as data
                output.append([ENC_INC |  (counter-ENC_INC_MIN), [data[i-1] - counter + 1]])
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
        elif args.increment_compression == "yes" and len(verbatim) >= 2 and mode == 0 and (data[i-3] + 1 == data[i-2]) and (data[i-2] + 1 == data[i-1]) and (data[i-1] + 1 == data[i]):
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
    # last byte
    if len(verbatim) > 0:
        datasize, output = flush_verbatim(verbatim, output, datasize)
    if args.output != "-":
        print("Unoptimized compression: 0x{0:02X} bytes".format(datasize))
    # save even more bytes
    # from decompnessor view it’s free
    # TODO: enable again
    # TODO: make it undersstand new format
    ##output = improve_compression(output)
    # flatten output
    #print(output)

    if args.end_of_data != "no":
        output.append([ENC_EOD, []])

    flatoutput = []
    if args.c_include == "no":
        for o in output:
            if len(o) > 0:
                flatoutput.append(o[0])
                if len(o[1]) > 0:
                    flatoutput+=o[1]
    else:
        for o in output:
            if len(o) > 0:
                flatoutput.append(hxc(o[0]))
                if len(o[1]) > 0:
                    flatoutput+=map(hx, o[1])

    datasize = len(flatoutput)
    if args.c_include != "no":
        flatoutput = array2data(flatoutput)
    #print(flatoutput)
    #if datasize != len(flatoutput):
    #    print("Warning: counting is wrong {} vs {}".format(datasize, len(flatoutput)))
    return datasize, flatoutput

# We aim for ENC_ROW optimization foremost
# 2 byte encoding after that
def mapping_optimizer(data, dmap):
    sortedkeys = list({k: v for k, v in sorted(mapper.items(), key=lambda item: item[1][1], reverse=True)})
    #print("Most used mapping is 0x{0:02X} ({1} times)".format(mapper[sortedkeys[0]][0], mapper[sortedkeys[0]][1]))
    #print("Second most used mapping is 0x{0:02X} ({1} times)".format(mapper[sortedkeys[1]][0], mapper[sortedkeys[1]][1]))
    #print("Last index is 0x{0:02X}".format(len(mapper)-1))


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
    parser.add_argument('image', metavar='image.2bpp', help='2bit or 1bit image or - for reading binary data from stdin')
    parser.add_argument("--output", "-o", default="", help="Base name for output files or - for stdout (default: derived from image name)")
    parser.add_argument("--color-line-compression", "-l", default="yes", help="Encode rows with just one color in one byte (default: yes)")
    parser.add_argument("--increment-compression", "-i", default="yes", help="Encode incrementing byte sequence (default: yes)")
    parser.add_argument("--tile-length", "-t", default="no", help="Export tile length (default: no)")
    # this is mostly for debugging purpose,
    # since you can see what's data and command bytes this way
    parser.add_argument("--c-include", "-c", default="no", help="Output c source instead of binary file (default: no)")
    # if length is not know by decompressor
    parser.add_argument("--monochrome", "-m", default="no", help="Switch between 1bpp and 2bpp mode (default: no)")
    parser.add_argument("--end-of-data", "-e", default="no", help="End with EOD (default: no)")
    global args

    args = parser.parse_args()
    fileextension = args.image.split('.')[-1]
    if fileextension != '2bpp' and fileextension != '1bpp' and args.image != "-":
        if args.monochrome == 'no':
            print("Please give a .2bpp file", file=sys.stderr)
        else:
            print("Please give a .1bpp file", file=sys.stderr)
        exit(1)
    if args.output == "":
        if args.image == "-":
            print("You need to specify an output file if you read from stdin", file=sys.stderr)
            exit(1)
        args.output = '.'.join(args.image.split('.')[:-1]+["rle"]+args.image.split('.')[-1:])
        if args.c_include != "no":
            args.output += ".c"

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
    if args.output != "-":
        print("Before compression: 0x{0:02X} bytes".format(len(data)))
    # count amount of tiles which really end up in vram
    mapcounter = int(len(data)/16)
    size, data = compress_rle(data)
    if args.output != "-":
        print("After compression: 0x{0:02X} bytes".format(size))
    d = open(args.output, 'wb')
    if args.c_include == "no":
        if args.output == "-":
            d = sys.stdout.buffer
        d.write(bytes(data))
    else:
        d.close()
        if args.output != "-":
            d = open(args.output, 'w')
        else:
            d = sys.stdout
        d.write("// Generated with compress2bpp.py (from png2gb)\n")
        d.write("// Compressed with RLE\n")
        d.write("// 0x{0:02X} bytes\n".format(size))
        d.write("const unsigned char {0}[] = ".format(os.path.basename('_'.join(args.output.split('.')[:-1])))+"{\n")
        d.write(data[:-3])
        d.write("\n};\n")
        if args.monochrome != "no":
            mapcounter *= 2
        if args.tile_length:
            d.write("\nconst unsigned char {0}_length = {1};\n".format(os.path.basename('_'.join(args.output.split('.')[:-1])), mapcounter))
    d.close()
    exit(0)

main()