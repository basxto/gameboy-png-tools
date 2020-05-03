// complementary decompressor for png2gb.py
#include "decompress.h"

unsigned char decompress_tile_buffer[16];

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
    // data can be nb_tiles max [255] * (tile size [2*8] + verbatim [1])
    // = 0x10EF
    // verbatim can encode 8 full tiles, but we simplify
    UINT16 counter = 0;
    UINT8 index = 0;
    UINT8 position = 0;
    UINT8 cmd;
    UINT8 value;
    UINT8 byte1;
    UINT8 byte2;
    // code below depends on nb_tiles > 0
    if(nb_tiles == 0)
        return 0;
    while(1){
        cmd = data[counter++];
        // we actually don't need this
        // end of compression
        /*if(cmd == 0xFF){
            return 0;
        }else */
        if((cmd & 0x80) == 0){
            //verbatim
            // cmd is amount; 0 is once
            ++cmd;
            if(skip_bytes != 0){
                byte1 = (cmd > skip_bytes ? skip_bytes : cmd);
                cmd -= byte1;
                counter += byte1;
                skip_bytes -= byte1;
            }
            for(; cmd != 0; --cmd){
                decompress_tile_buffer[index++] = data[counter++];
                //if((index %= 16) == 0){
                if((index &= 0xF) == 0){
                    if(first_tile != 0xFF)
                        set_bkg_data(first_tile + (position++), 1, decompress_tile_buffer);
                    if(--nb_tiles == 0)
                        return decompress_tile_buffer;
                }
            }
        }else{
            // value part
            value = cmd & 0x1F;
            // command part
            cmd &= 0xE0;
            switch(cmd){
                case 0x80:
                    // run
                    byte1 = byte2 = data[counter++];
                    // 0 counts as twice
                    value += 2;
                    break;
                case 0xC0:
                    // double inverted run
                    byte1 = (value & 0x10 ? 0xFF : 0x00);
                    byte2 = (value & 0x8 ? 0xFF : 0x00);
                    // remove H and L bit
                    // 0 counts as once
                    // amount for was for 2 bytes
                    value = ((value&0x7) + 1)*2;
                    break;
                default:
                    // inverted and double run
                    byte1 = data[counter++];
                    byte2 = ~byte1;
                    if(cmd == 0xE0){
                        // for double run
                        byte2 = data[counter++];
                    }
                    // 0 counts as twice
                    // amount for was for 2 bytes
                    value = (value + 2)*2;
                    break;
            }
            if(skip_bytes != 0){
                cmd = (value > skip_bytes ? skip_bytes : value);
                value -= cmd;
                skip_bytes -= cmd;
            }
            for(; value != 0; --value){
                decompress_tile_buffer[index++] = (value%2 == 0 ? byte1 : byte2);
                if((index &= 0xF) == 0){
                    if(first_tile != 0xFF)
                        set_bkg_data(first_tile + (position++), 1, decompress_tile_buffer);
                    if(--nb_tiles == 0)
                        return decompress_tile_buffer;
                }
            }
        }
    }
}
