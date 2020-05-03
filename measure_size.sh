#!/bin/sh
ROM=png2gb
# with decompressor
make ${ROM}.gb
# no decompressor
make ${ROM}_noc.gb

free_space(){
    hexdump -v -e '/1 "%02X\n"' $1 | \
        awk '/FF/ {n += 1} !/FF/ {n = 0} END {print n}'
}
normal=$(free_space ${ROM}.gb)
noc=$(free_space ${ROM}_noc.gb)

echo $((noc-normal))