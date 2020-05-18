// complementary decompressor for png2gb.py
#include "decompress.h"
#include "utils.h"

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

#define ENC_INC $(0x00)
#define ENC_INC_MIN $(1)
#define ENC_INC_MAX $(ENC_INC_MIN+15)
#define ENC_LIT $(0x00)
#define ENC_LIT_MIN (1-0x10)
#define ENC_LIT_MAX $(ENC_LIT_MIN+127-(ENC_INC_MAX-ENC_INC_MIN))
#define ENC_RUN $(0x80)
#define ENC_RUN_MIN $(1)
#define ENC_RUN_MAX $(ENC_RUN_MIN+31)
#define ENC_INV $(0xC0)
#define ENC_INV_MIN $(2)
#define ENC_INV_MAX $(ENC_INV_MIN+31)
#define ENC_ROW $(0xA0)
#define ENC_ROW_MIN $(1)
#define ENC_ROW_MAX $(ENC_ROW_MIN+7)
#define ENC_ALT $(0xE0)
#define ENC_ALT_MIN $(2)
#define ENC_ALT_MAX $(ENC_ALT_MIN+30)
#define ENC_EOD $(0x00)

// 2 bytes don’t have to be repeated more than 16 times (2 tiles)
// one byte doesn’t have to run more than 32 times (2 tiles)

// 0x 0b       NAME SIZE  OUT VALUES
//###################################
// 00 00000000 EOD [ 1B ] 0B  1
// 00 0000XXXX INC [ 2B ] 1B  2-(17-1)
// 00 0XXXXXXX LIT [1B+n] 1B  1-(128-15)
// 80 10000000 MON [ 1B ] 0B  1
// 80 100XXXXX RUN [ 2B ] 1B  2-(33-1)
// A0 101HXXXL ROW [ 1B ] 2B  1-8
// C0 11XXXXX0 INV [ 2B ] 2B  2-33
// E0 11XXXXX1 ALT [ 3B ] 2B  2-33

// this can't load into sprite VRAM < index 128
unsigned char* set_bkg_data_rle(UINT8 first_tile, UINT8 nb_tiles, const unsigned char *data, UINT8 skip_tiles) NONBANKED{
    // max 0x0FF0
    UINT16 skip_bytes = skip_tiles*$(16);
    unsigned char* dectbuf = decompress_tile_buffer;
    UINT8 cmd, value, byte1, byte2;
    _Bool monochrome = 0;
    // allows faster *(++data) in loop
    --data;
    while(1){
        value = *(++data);
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
        }
#endif
        cmd = value;
        if((cmd & $(0x80)) == 0){
            cmd = 0;
#ifndef NOINCREMENTER
            if((value & $(0xF0)) == ENC_INC){
                // incremental sequence
                ++value;
                ++cmd;
                byte1 = *(++data);
            }else
#endif
                //verbatim
                value= $(value + ENC_LIT_MIN);
        }else{
            value &= 0x7F;// remove leading 1
            if(value == 0){//switch monochrome mode
                monochrome=!monochrome;
                skip_bytes = (monochrome? skip_bytes>>1 : skip_bytes<<1);
                continue;
            }
            if((cmd&0x40) == 0){
                if((cmd&$(0x20))==0){//RUN
                    byte1 = *(++data);
                    byte2 = byte1;
                    ++value;
#ifndef NOCOLORLINE
                }else{//ROW
                    // 0x00-1=0xFF 0x01-1=0x00
                    byte1 = ((value>>4)&0x1)-$(1);
                    byte2 = (value&0x1)-$(1);
                    value = (value&$(0xE)) + (ENC_ROW_MIN*$(2));
#endif
                }
            }else{
                value = (value&$(0xBE))+$(4);
                byte1 = *(++data);
                byte2 = ~byte1;//INV
                if((cmd&$(0x1))!=0){//ALT
                    byte2 = *(++data);
                }
            }
            cmd = 4;
        }
        if(skip_bytes != 0){
            // if skip_bytes is smaller than value, it fits into a UINT8
            UINT8 tmp = MIN(value, skip_bytes);
            // only verbatim needs this
            if(cmd == 0)
                data += tmp;
            value -= tmp;
            skip_bytes -= tmp;
        }
        for(; value != 0; --value){
            UINT8 tmp = byte1;
            if(cmd == 0)
                tmp = *(++data); // LIT
#ifndef NOINCREMENTER
            else if(cmd%2 != 0)
                ++byte1; // INV
#endif
            else if(value%2 != 0)
                tmp = byte2;

            *(dectbuf++) = tmp;
            if(monochrome)// should be set from beginning of tile on
                *(dectbuf++) = tmp;

            if (dectbuf == decompress_tile_buffer+16) {
                dectbuf = decompress_tile_buffer;
                if(nb_tiles == 0)
                    goto ret;
                set_bkg_data(first_tile++, 1, decompress_tile_buffer);
                if($(--nb_tiles) == 0)
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
    UINT8 sizecounter = 0;
    for(UINT8 i = 0; i <= max; ++i){
        pointer = set_bkg_data_rle(0, 0, data, i);
        memcpy(decompress_map_buffer+(sizecounter), pointer, tile_size);
        sizecounter += tile_size;
    }
    return decompress_map_buffer;
}
#endif