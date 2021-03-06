DEV?=./dev
BIN=$(DEV)/gbdk-n/bin

LK?=$(BIN)/gbdk-n-link.sh -Wl-m
CC=$(BIN)/gbdk-n-compile.sh -Wa-l
MKROM?=$(BIN)/gbdk-n-make-rom.sh
CFLAGS += --peep-file $(abspath $(DEV))/gbz80-ph/peep-rules.txt

ROM=png2gb

.PHONY: build
build: $(ROM).gb

.PHONY: test
test:
	./test/test_all.sh

$(ROM).gb: main.ihx
	$(MKROM) $< $@

$(ROM)_noc.gb: main_noc.ihx
	$(MKROM) $< $@

main.ihx: main.rel csrc/decompress.rel
	$(LK) -o $@ $^

main_noc.ihx: main.rel
	$(LK) -o $@ $^

%.rel: %.c
	$(CC) $(CFLAGS) -o $@ $^

gbdk-n:
	$(MAKE) -C $(DEV)/gbdk-n

clean:
	find . -maxdepth 2 -type f -regex '.*.\(gb\|o\|map\|lst\|sym\|rel\|ihx\|lk\|noi\|asm\|adb\|cdb\|bi4\)' -delete
	make -C ./test clean
