# png2gb
Convert indexed 8bit png to image in gameboy format.

Supports two forms of compression:
* mapping for saving VRAM space
* [RLE](compression.md) for saving ROM space

Allows to define meta sprites:
* top to bottom, left to right (for 8x16 mode)
* tiles get placed sequentially in memory

Multiple images can be concatenated, which improves mapping performance.

Mapping can be disabled for tile animation, but RLE assumes that duplicate tiles got eliminated.

Palette indexes must be a multiple of 4 and subpalettes for GBC get exported to a `_pal.c` file. Index 0 is the darkest color on the screen and 3 the lightest.

A tile limit for sprites can be defined, so you get warned when it would take up more VRAM space after mapping than you planned.

ROM addresses for data, mapping and palette can be defined if you don't want the compiler to handle that.

The [decompressor](csrc/decompress.c) currently allocates **708-1016 bytes**, depending on the used features. [See the measure script](measure_size.sh).

Mappings can also be compressed with RLE. The decompressor for those can be disabled with `-DNOMAPRLE`.

You can see all accepted parameters with: (flag parameters need a `"yes"`)
```
./png2gb.py -h
```

----

## Compression modes

### No one colored lines compression

This reduces a row to one byte, including command byte, and repeats it up to 8 times. Works only if the row has a constant color.

png2gb: `--color-line-compression=no`

CFLAG: `-DNOCOLORLINE`

### No incremental sequence compression

Compresses sequences, which increment with each further byte. This is especially handy for mappings.

png2gb: `--increment-compression=no`

CFLAG: `-DNOINCREMENTER`