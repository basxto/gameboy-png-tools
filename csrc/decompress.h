#ifndef decompress_h
#define decompress_h

#ifdef __SDCC
// we substitute this when we test
#include <gb/gb.h>
#endif
#if !defined __SDCC || __SDCC_VERSION_MAJOR == 0
// fix testing and IDE code analyzer
#define NONBANKED
#endif


#define set_bkg_data_rle set_win_data_rle
// format description in .c comment and ../compression.md
// returns pointer to the last decompressed tile, which will be overwritten on next call
// This is only useful for decompressing a single tile, you want to manipulate
// other than set_bkg_data, this allows to skip tiles, since that can't be done without decompressing the data
// nb_tiles == 0 writes no tile, but still returns one
unsigned char* set_bkg_data_rle(UINT8 first_tile, UINT8 nb_tiles, const unsigned char *data, UINT8 skip_tiles) NONBANKED;

// get an temporary array that holds decompressed bytes
// next call overwrites the array
// if input data is not a multiple of 16 bytes, it should end with 0xFF
unsigned char* get_map_rle(UINT8 nb_bytes, unsigned char *data) NONBANKED;
#endif
