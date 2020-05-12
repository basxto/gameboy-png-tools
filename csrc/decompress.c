// complementary decompressor for png2gb.py
#include "decompress.h"

unsigned char decompress_tile_buffer[16];

#ifndef NOMAPRLE
// stuff needed for map decompression
#include <string.h>
unsigned char decompress_map_buffer[0xFF];
#endif

#ifndef __SDCC
#define testprint(f_, ...) printf((f_), __VA_ARGS__)
#else
#define testprint(f_, ...)
#endif

#define ENC_INC (0x00)
#define ENC_INC_MIN (2)
#define ENC_INC_MAX (ENC_INC_MIN+15)
#define ENC_LIT (0x00)
#define ENC_LIT_MIN (1-0x10)
#define ENC_LIT_MAX (ENC_LIT_MIN+127-(ENC_INC_MAX-ENC_INC_MIN))
#define ENC_RUN (0x80)
#define ENC_RUN_MIN (1)
#define ENC_RUN_MAX (ENC_RUN_MIN+31)
#define ENC_INV (0xC0)
#define ENC_INV_MIN (2)
#define ENC_INV_MAX (ENC_INV_MIN+31)
#define ENC_ROW (0xA0)
#define ENC_ROW_MIN (1)
#define ENC_ROW_MAX (ENC_ROW_MIN+7)
#define ENC_ALT (0xE0)
#define ENC_ALT_MIN (2)
#define ENC_ALT_MAX (ENC_ALT_MIN+30)
#define ENC_EOD (0x00)

// 2 bytes don’t have to be repeated more than 16 times (2 tiles)
// one byte doesn’t have to run more than 32 times (2 tiles)
// 00 0XXXXXXX - write through the next X bytes (127+1)
// 70 0111XXXX - run next byte X times incrementing it each time (15+2) - map compression
// 80 100XXXXX - run next byte X*2 times (31+2) - highest and lowest color only
// A0 101XXXXX - run next byte X times alternating normal and inverted  (31+2) - middle colors only
// C0 110HLXXX - High Low colored line X times (7+1)
// E0 111XXXXX - run next 2 bytes X times alternating (30+2)
// FF 11111111 - end of data

// this can't load into sprite VRAM < index 128
unsigned char* set_bkg_data_rle(UINT8 first_tile, UINT8 nb_tiles, const unsigned char *data, UINT8 skip_tiles) NONBANKED{
    // max 0x0FF0
    UINT16 skip_bytes = skip_tiles*16;
    unsigned char* dectbuf = decompress_tile_buffer;
    UINT8 cmd, value, byte1, byte2;
    UINT8 monochrome = 0;
    // allows faster *(++data) in loop
    --data;
    while(1){
        value = *(++data);
        // command part
        cmd = value & 0xE0;
#ifndef NOMAPRLE
        if(value == ENC_EOD){
            // end of data, especially needed for non-image data
#ifdef DEADMARKER
            // generate a 0xDEAD marker
            *(dectbuf++) = 0xDE;
            while(dectbuf != decompress_tile_buffer+16)
                *(dectbuf++) = 0xAD;
#endif
            // this returns a partially filled tile
            goto ret;
        }else
#endif
        if((cmd & 0x80) == 0){
            //verbatim
            cmd = 0;
#ifndef NOINCREMENTER
            if((value & 0xF0) == ENC_INC){
                // incremental sequence
                cmd = 1;
                value = (value & 0xF) + ENC_INC_MIN;
                byte1 = *(++data);
            }else
#endif
                // value is amount; 0 is once
                value= (UINT8)(value + ENC_LIT_MIN);
        }else{
            value &= 0x7F;
            if((cmd&0x40) == 0)
                if((cmd&0x20)==0){//RUN
                    if(value == 0){//moonchrome
                        monochrome=1;
                        continue;
                    }
                    byte2 = byte1 = *(++data);
                    value += ENC_RUN_MIN;
#ifndef NOCOLORLINE
                }else{//ROW
                    byte1 = (value & 0x10 ? 0xFF : 0x00);
                    byte2 = (value & 0x1 ? 0xFF : 0x00);
                    //value = ((value&0x7) + ENC_ROW_MIN)*2;
                    value = (value&0xE) + (ENC_ROW_MIN*2);
#endif
                }
            else{
                byte1 = *(++data);
                value &= 0xBF;
                if((value&0x1)==0){//INV
                    // no mask since it’s already 0
                    byte2 = ~byte1;
                    value += ENC_INV_MIN*2;
                }else{//ALT
                    // no mask since we can use that 1
                    byte2 = *(++data);
                    value += ENC_ALT_MIN*2 - 1;
                }
            }
        }
        if(skip_bytes != 0){
            UINT8 tmp = (value > skip_bytes ? skip_bytes : value);
            value -= tmp;
            // only verbatim needs this
            if(cmd == 0)
                data += tmp;
            skip_bytes -= tmp;
        }
        for(; value != 0; --value){
            UINT8 tmp = byte2;
            if(cmd == 0)
                tmp = *(++data);
#ifndef NOINCREMENTER
            else if(cmd == 1)
                tmp = byte1++;
#endif
            else if(value%2==0)
                tmp = byte1;
            *(dectbuf++) = tmp;
            if((monochrome%2) == 1)// should be set from beginning of tile on
                *(dectbuf++) = tmp;
            if (dectbuf == decompress_tile_buffer+16) {
                dectbuf = decompress_tile_buffer;
                if(nb_tiles == 0)
                    goto ret;
                set_bkg_data(first_tile++, 1, decompress_tile_buffer);
                if(--nb_tiles == 0)
                    goto ret;
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
#ifdef DEADMARKER
    memset(decompress_map_buffer, 0xAD, 0xFF);
#endif
    for(UINT8 i = 0; i <= max; ++i){
        pointer = set_bkg_data_rle(0, 0, data, i);
        memcpy(decompress_map_buffer+(tile_size*i), pointer, tile_size);
    }
    return decompress_map_buffer;
}
#endif