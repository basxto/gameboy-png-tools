// complementary decompressor for png2gb.py
#include <gb/gb.h>
// for debug output
#include "../../../hud.h"

unsigned char decompress_tile_buffer[16];

#define set_bkg_data_rle set_win_data_rle

// broken
void set_bkg_data_rle(UINT8 first_tile, UINT8 nb_tiles, unsigned char *data) NONBANKED{
    UINT16 counter = 0;
    UINT8 index = 0;
    UINT8 position = 0;
    while(1){
        UINT8 cmd = data[counter];
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
            for(UINT8 i = 0; i < cmd; ++i){
                decompress_tile_buffer[index++] = data[counter++];
                if(index == 16){
                    set_bkg_data(first_tile + position, 1, decompress_tile_buffer);
                    ++position;
                    index = 0;
                    if(position >= nb_tiles)
                        return;
                }
            }
        }else if((cmd & 0xC0) == 0xC0){
            //run alternating
            cmd = (cmd & 0x3F) + 2;// 0 is twice
            for(UINT8 i = 0; i < cmd; ++i){
                decompress_tile_buffer[index++] = data[counter];
                if(index == 16){
                    set_bkg_data(first_tile + position, 1, decompress_tile_buffer);
                    ++position;
                    index = 0;
                    if(position >= nb_tiles)
                        return;
                }
                decompress_tile_buffer[index++] = data[counter+1];
                if(index == 16){
                    set_bkg_data(first_tile + position, 1, decompress_tile_buffer);
                    ++position;
                    index = 0;
                    if(position >= nb_tiles)
                        return;
                }
            }
            counter+=2;
        }else{
            // run
            cmd = (cmd & 0x3F) + 2;// 0 is twice
            for(UINT8 i = 0; i < cmd; ++i){
                decompress_tile_buffer[index++] = data[counter];
                if(index == 16){
                    set_bkg_data(first_tile + position, 1, decompress_tile_buffer);
                    ++position;
                    index = 0;
                    if(position >= nb_tiles)
                        return;
                }
            }
            ++counter;
        }
    }
}