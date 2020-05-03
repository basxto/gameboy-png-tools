## RLE

One byte 32 times repeated makes two tiles.

Two bytes 16 times repeated makes two tiles. (24 for 3)

We won't need more than that, since we eliminate duplicate tiles. Even though 3 tiles minus 2 rows could occur.

0 reduces the overhead for data, which can't be compressed. (max 64 rows/8 tiles)

110 allows to describe a tile filled with one color in just one byte instead of 16 (2 bytes per row).

100, 101 and 111 don't need to run once, since 0 can handle that.

Jumps to 111 when 100 hits it's limit. This could save a byte on an even run.

```
0XXX XXXX - write through the next X bytes (1-128)
100X XXXX - repeat next byte X times (2-33) - highest and lowest color
101X XXXX - repeated next byte X*2 times alternating normal and inverted (2-33) - middle colors
110H LXXX - [H]igh [L]ow colored line X times (1-8)
111X XXXX - repeat next 2 bytes X times alternating (2-32)
1111 1111 - end of data
```
