#ifndef decompress_h
#define decompress_h

#include <gb/gb.h>
#define set_bkg_data_rle set_win_data_rle
// format description in .c comment and ../compression.md
// does not write to first_tile 0xFF, please use 0xFE with two tiles
// returns pointer to the last decompressed tile, which will be overwritten on next call
// returns 0 if it hits end of data
// This is only useful for decompressing a single tile, you want to manipulate
// other than set_bkg_data, this allows to skip tiles, since that can't be done without decompressing the data
unsigned char* set_bkg_data_rle(UINT8 first_tile, UINT8 nb_tiles, unsigned char *data, UINT8 skip_tiles) NONBANKED;
#endif
