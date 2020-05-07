// stubs for testing
#include <string.h>
#include <stdio.h>

typedef unsigned char UINT8;
typedef unsigned int UINT16;

#define RAMSIZE (256)
// background and window
UINT8 VRAMBG[RAMSIZE];
// sprites
UINT8 VRAMFG[RAMSIZE];


#define set_win_data(first_tile, nb_tiles, data) set_bkg_data(first_tile, nb_tiles, data)
void set_bkg_data(UINT8 first_tile, UINT8 nb_tiles, const unsigned char *data){
    memcpy(VRAMBG + first_tile*16, data, nb_tiles*16);
    // second half overlaps
    if(first_tile + nb_tiles > RAMSIZE/2)
        memcpy(VRAMFG + first_tile*16 + RAMSIZE/2, data, nb_tiles*16 - RAMSIZE/2);
}

void set_sprite_data(UINT8 first_tile, UINT8 nb_tiles, const unsigned char *data){
    memcpy(VRAMFG + first_tile*16, data, nb_tiles*16);
    if(first_tile + nb_tiles > RAMSIZE/2)
        memcpy(VRAMBG + first_tile*16 + RAMSIZE/2, data, nb_tiles*16 - RAMSIZE/2);
}

void rst_bkg_data(){
    memset(VRAMBG, 0xFF, RAMSIZE);
}

void rst_sprite_data(){
    memset(VRAMFG, 0xFF, RAMSIZE);
}

// 0 is equal
int cmp_bkg_data(UINT8 first_tile, UINT8 nb_tiles, const unsigned char *data){
    return memcmp(VRAMBG + first_tile*16, data, nb_tiles*16);
}

int cmp_sprite_data(UINT8 first_tile, UINT8 nb_tiles, const unsigned char *data){
    return memcmp(VRAMFG + first_tile*16, data, nb_tiles*16);
}

#include "../csrc/decompress.c"
#include "test1_data.c"
#include "test1_uncompressed_data.c"
#include "test2_data.c"
#include "test2_uncompressed_data.c"
#include "test3_data.c"
#include "test3_uncompressed_data.c"

int status = 0;

void starttest(int number){
    rst_bkg_data();
    rst_sprite_data();
    printf("Test %d...", number);
    fflush(stdout);
}

int endtest(int result){
    if(result == 0){
        printf(" succeeded.\n");
    }else{
        printf(" failed!\n");
        status = 1;
    }
}

int main() {
    UINT8 first = 0;
    UINT8 nb = test1_uncompressed_data_length;
    starttest(1);
    set_win_data_rle(first, nb, test1_data, 0);
    endtest(cmp_bkg_data(first, nb, test1_uncompressed_data));

    nb = 2;
    starttest(2);
    set_win_data_rle(first, nb, test1_data, 1);
    endtest(cmp_bkg_data(first, nb, test1_uncompressed_data+16));

    nb = 0;
    nb = test2_uncompressed_data_length;
    starttest(3);
    set_win_data_rle(first, nb, test2_data, 0);
    endtest(cmp_bkg_data(first, nb, test2_uncompressed_data));

    nb = 1;
    starttest(4);
    set_win_data_rle(first, nb, test2_data, 3);
    endtest(cmp_bkg_data(first, nb, test2_uncompressed_data+(16*3)));

    nb = 0;
    nb = test3_uncompressed_data_length;
    starttest(5);
    set_win_data_rle(first, nb, test3_data, 0);
    endtest(cmp_bkg_data(first, nb, test3_uncompressed_data));

    nb = 1;
    starttest(6);
    set_win_data_rle(first, nb, test3_data, 1);
    endtest(cmp_bkg_data(first, nb, test3_uncompressed_data+16));

    return status;
}