// dummy main
#include <gb/gb.h>

#include "csrc/decompress.h"

void main() {
    HIDE_BKG;
    HIDE_WIN;
    DISPLAY_OFF;
    cgb_compatibility();

    BGP_REG = 0xE1;
    OBP0_REG = 0xE1;
    SHOW_BKG;
    SHOW_WIN;
    DISPLAY_ON;
    while(1){
        waitpad(J_A);
        BGP_REG = 0x1E;
        delay(100);
        waitpad(J_A);
        BGP_REG = 0xE1;
        delay(100);
    };
}