DEV?=./dev

# globally installed
LCC?=lcc -Wa-l -Wl-m -Wl-j
CC=$(LCC) -c 
MKROM?=$(LCC)
CFLAGS += --peep-file csrc/peep-rules.txt

ROM=png2gb

.PHONY: build
build: $(ROM).gb

.PHONY: test
test:
	./test/test_all.sh

$(ROM).gb: main.rel csrc/decompress.rel
	$(MKROM) -o $@ $^

$(ROM)_noc.gb: main.rel
	$(MKROM) -o $@ $^

%.rel: %.c
	$(CC) $(CFLAGS) -o $@ $^

clean:
	find . -maxdepth 2 -type f -regex '.*.\(gb\|o\|map\|lst\|sym\|rel\|ihx\|lk\|noi\|asm\|adb\|cdb\|bi4\)' -delete
	make -C ./test clean
