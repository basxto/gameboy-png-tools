pngconvert?=../png2gb.py

.PHONY: build
build: ./test

.PHONY: run
run: ./test
	./test

TESTS=test1 test2
TESTDATA=$(foreach test, $(TESTS), $(test)_data.c $(test)_uncompressed_data.c)

test: test.c ../csrc/decompress.c ../csrc/decompress.h  $(TESTDATA)
	$(CC) $< -o $@

%_uncompressed_data.c: %.png FORCE
	$(pngconvert) $< -o $@

%_data.c: %.png FORCE
	$(pngconvert) --compress-rle=1 $< -o $@

clean:
	rm -f ./test
	find . -maxdepth 1 -type f -regex '.*_\(map\|data\|pal\)\.c' -delete

FORCE: