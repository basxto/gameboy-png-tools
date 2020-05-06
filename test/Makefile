pngconvert?=../png2gb.py

.PHONY: build
build: ./test

.PHONY: run
run: ./test
	./test

test: test.c ../csrc/decompress.c ../csrc/decompress.h test1_data.c test1_uncompressed_data.c
	$(CC) $< -o $@

%_uncompressed_data.c: %.png FORCE
	$(pngconvert) $< -o $@

%_data.c: %.png FORCE
	$(pngconvert) --compress-rle=1 $< -o $@

clean:
	rm -f ./test
	find . -maxdepth 1 -type f -regex '.*_\(map\|data\|pal\)\.c' -delete

FORCE: