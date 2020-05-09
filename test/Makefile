pngconvert?=../png2gb.py -ci
compress?=../compress2bpp.py -ci $(PFLAGS)

.PHONY: build
build: ./test

.PHONY: run
run: ./test
	./test

TESTS=test1 test2 test3
TESTDATA=$(foreach test, $(TESTS), $(test)_data.c $(test)_uncompressed_data.c)

test: test.c ../csrc/decompress.c ../csrc/decompress.h  $(TESTDATA)
	$(CC) $(CFLAGS) $< -o $@

%_uncompressed_data.c: %.png FORCE
	$(pngconvert) -u yes $< -o $@

%_data.c: %.png FORCE
	$(pngconvert) -u yes $< -o $@ -bin | $(compress) - -o$@

clean:
	rm -f ./test
	find . -maxdepth 1 -type f -regex '.*_\(map\|data\|pal\)\.c' -delete

FORCE: