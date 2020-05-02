// complementary decompressor for png2gb.py
#include "decompress.h"
// for debug output
#include "../../../hud.h"

unsigned char decompress_tile_buffer[16];

// 2 bytes don’t have to be repeated more than 16 times (2 tiles)
// one byte doesn’t have to run more than 32 times (2 tiles)
// 00 0XXXXXXX - write through the next X bytes (127+1)
// 80 100XXXXX - run next byte X times (31+2) - highest and lowest color only
// A0 101XXXXX - run next byte X times alternating normal and inverted  (31+2) - middle colors only
// C0 110HLXXX - High Low colored line X times (7+1)
// E0 111XXXXX - run next 2 bytes X times alternating (30+2)
// FF 11111111 - end of data

// TODO: allow to skip bytes
void set_bkg_data_rle(UINT8 first_tile, UINT8 nb_tiles, unsigned char *data) NONBANKED{
    UINT16 counter = 0;
    UINT8 index = 0;
    UINT8 position = 0;
    UINT8 cmd;
    UINT8 value;
    UINT8 byte1;
    UINT8 byte2;
    UINT8 i;
    while(1){
        cmd = data[counter];
        ++counter;
        // end of compression
        if(cmd == 0xFF){
            //continue;
            write_hex(12, 0, 2, position);
            write_hex(12, 1, 2, counter>>8);
            write_hex(14, 1, 2, counter&0xFF);
            return;
        }else if((cmd & 0x80) == 0){
            //verbatim
            ++cmd;// 0 is once
            for(i = 0; i < cmd; ++i){
                decompress_tile_buffer[index++] = data[counter++];
                if(index == 16){
                    set_bkg_data(first_tile + position, 1, decompress_tile_buffer);
                    ++position;
                    index = 0;
                    if(position >= nb_tiles)
                        return;
                }
            }
        }else{
            // value part
            value = cmd & 0x1F;
            // command part
            cmd = cmd & 0xE0;
            switch(cmd){
                case 0xE0:
                    // double run
                    byte1 = data[counter++];
                    byte2 = data[counter++];
                    // 0 counts as twice
                    value += 2;
                    // amount for was for 2 bytes
                    value *= 2;
                    break;
                case 0x80:
                    // run
                    byte1 = byte2 = data[counter++];
                    value += 2;
                    break;
            }
            for(i = 0; i < value; ++i){
                if(i%2 == 0)
                    decompress_tile_buffer[index++] = byte1;
                else
                    decompress_tile_buffer[index++] = byte2;
                if(index == 16){
                    set_bkg_data(first_tile + position, 1, decompress_tile_buffer);
                    ++position;
                    index = 0;
                    if(position >= nb_tiles)
                        return;
                }
            }
        }
    }
}