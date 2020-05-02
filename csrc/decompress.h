#ifndef decompress_h
#define decompress_h

#include <gb/gb.h>
#define set_bkg_data_rle set_win_data_rle
void set_bkg_data_rle(UINT8 first_tile, UINT8 nb_tiles, unsigned char *data) NONBANKED;
#endif
