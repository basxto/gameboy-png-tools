#!/bin/sh
cd $(dirname "$0")
STATUS=0
PFLAGS="" CFLAGS="" make -B run
STATUS=$((STATUS | $?))
PFLAGS="--increment-compression=no" CFLAGS="-DNOINCREMENTER" make -B run
STATUS=$((STATUS | $?))
PFLAGS="--color-line-compression=no" CFLAGS="-DNOCOLORLINE" make -B run
STATUS=$((STATUS | $?))
PFLAGS="--increment-compression=no --color-line-compression=no" CFLAGS="-DNOINCREMENTER -DNOCOLORLINE" make -B run
STATUS=$((STATUS | $?))
make clean

exit $STATUS
