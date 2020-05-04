// complementary decompressor for png2gb.py
#include "decompress.h"

unsigned char decompress_tile_buffer[16];

#ifndef NOMAPRLE
// stuff needed for map decompression
#include <string.h>
unsigned char decompress_map_buffer[0xFF];
#endif

// 2 bytes don’t have to be repeated more than 16 times (2 tiles)
// one byte doesn’t have to run more than 32 times (2 tiles)
// 00 0XXXXXXX - write through the next X bytes (127+1)
// 80 100XXXXX - run next byte X*2 times (31+2) - highest and lowest color only
// A0 101XXXXX - run next byte X times alternating normal and inverted  (31+2) - middle colors only
// C0 110HLXXX - High Low colored line X times (7+1)
// E0 111XXXXX - run next 2 bytes X times alternating (30+2)
// FF 11111111 - end of data

// this can't load into sprite VRAM < index 128
unsigned char* set_bkg_data_rle(UINT8 first_tile, UINT8 nb_tiles, unsigned char *data, UINT8 skip_tiles) NONBANKED{
    // max 0x0FF0
    UINT16 skip_bytes = skip_tiles*16;
    unsigned char* dectbuf = decompress_tile_buffer;
    UINT8 cmd;
    UINT8 value;
    UINT8 byte1;
    UINT8 byte2;
    while(1){
        value = *(data++);
        // command part
        cmd = value & 0xE0;
        if(value == 0xFF){
            // end of data, especially needed for non-image data
#ifdef DEADMARKER
            // generate a 0xDEAD marker
            *(dectbuf++) = 0xDE;
            if(dectbuf != decompress_tile_buffer)
                *(dectbuf) = 0xAD;
#endif
            // this returns a partially filled tile
            goto ret;
        }else if((cmd & 0x80) == 0){
            //verbatim
            // value is amount; 0 is once
            ++value;
            if(skip_bytes != 0){
                cmd = (value > skip_bytes ? skip_bytes : value);
                value -= cmd;
                data += cmd;
                skip_bytes -= cmd;
            }
            for(; value != 0; --value){
                *(dectbuf) = *(data++);
                if (++dectbuf == decompress_tile_buffer+16) {
                    dectbuf = decompress_tile_buffer;
                    if(nb_tiles == 0)
                        goto ret;
                    set_bkg_data(first_tile++, 1, decompress_tile_buffer);
                    if(--nb_tiles == 0)
                        goto ret;
                }
            }
        }else{
            // value part
            value &= 0x1F;
            if(cmd == 0xC0){
                // one color line run
                byte1 = (value & 0x10 ? 0xFF : 0x00);
                byte2 = (value & 0x8 ? 0xFF : 0x00);
                // remove H and L bit
                // 0 counts as once
                // amount was for 2 bytes
                value = ((value&0x7) + 1)*2;
            }else{
                byte1 = *(data++);
                if(cmd == 0x80){
                    // run
                    byte2 = byte1;
                    // 0 counts as twice
                    value += 2;
                }else{
                    // matches 0x80 and 0xA0
                    if((cmd & 0x40) == 0){// 0xA0
                        // alternating inverted run
                        byte2 = ~byte1;
                    }else{
                        // double byte run
                        byte2 = *(data++);
                    }
                    // 0 counts as twice
                    // amount was for 2 bytes
                    value = (value+2)*2;
                }
            }
            if(skip_bytes != 0){
                cmd = (value > skip_bytes ? skip_bytes : value);
                value -= cmd;
                skip_bytes -= cmd;
            }
            for(; value != 0; --value){
                *(dectbuf) = (value%2 == 0 ? byte1 : byte2);
                if (++dectbuf == decompress_tile_buffer+16) {
                    dectbuf = decompress_tile_buffer;
                    if(nb_tiles == 0)
                        goto ret;
                    set_bkg_data(first_tile++, 1, decompress_tile_buffer);
                    if(--nb_tiles == 0)
                        goto ret;
                }
            }
        }
    }
    ret: return decompress_tile_buffer;
}

// this can be excluded if not needed, because it's quite huge
#ifndef NOMAPRLE
// 8 row and 2 bytes per row
#define tile_size (8*2)
// always returns a 256 byte big array
// but only nb_bytes have meaningful content
unsigned char* get_map_rle(UINT8 nb_bytes, unsigned char *data) NONBANKED{
    unsigned char* pointer;
    // won't be more than 16
    UINT8 max = (nb_bytes/tile_size);
    // ceil
    if(nb_bytes%tile_size != 0)
        ++max;
    for(UINT8 i = 0; i <= max; ++i){
        pointer = set_bkg_data_rle(0, 0, data, i);
        memcpy(decompress_map_buffer+(tile_size*i), pointer, tile_size);
    }
    return decompress_map_buffer;
}
#endif