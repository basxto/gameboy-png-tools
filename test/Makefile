pngconvert?=../png2gb.py -ci
compress?=../compress2bpp.py -ci $(PFLAGS)
rgbgfx?=rgbgfx
convert?=convert

.PHONY: build
build: ./test

.PHONY: run
run: ./test
	./test

TESTS=test1 test2 test3 test4_mon
TESTDATA=$(foreach test, $(TESTS), $(test)_data.c $(test)_uncompressed_data.c)

test: test.c ../csrc/decompress.c ../csrc/decompress.h  $(TESTDATA)
	$(CC) $(CFLAGS) $< -o $@

%_uncompressed_data.c %_mon_uncompressed_data.c:: %.png FORCE
	$(pngconvert) -u yes $< -o $@

%_mon_data.c: %.1bpp FORCE
	$(compress) -mon $< -o$@

%_data.c: %.png FORCE
	$(pngconvert) -u yes $< -o $@ -bin | $(compress) - -o$@

%.1bpp: %_mono.png
	$(rgbgfx) -d1 $^ -o$@

%_mono.png: %.png
	$(convert) $^ -monochrome $@

clean:
	rm -f ./test
	find . -maxdepth 1 -type f -regex '.*_\(map\|data\|pal\)\.c' -delete
	find . -maxdepth 1 -type f -regex '.*\.\(tilemap\|pal\|2bpp\|1bpp\)' -delete
	find . -maxdepth 1 -type f -regex '.*_mon\.c' -delete

FORCE: