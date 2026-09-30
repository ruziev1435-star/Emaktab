CC = gcc
CFLAGS = -Wall -Wextra -Werror -std=c11 -D_POSIX_C_SOURCE=200809L

COMMON_DIR = ../common
SOURCES = s21_cat.c $(COMMON_DIR)/s21_common.c
HEADERS = s21_cat.h $(COMMON_DIR)/s21_common.h

all: s21_cat

s21_cat: $(SOURCES) $(HEADERS)
	$(CC) $(CFLAGS) $(SOURCES) -o $@

test: s21_cat
	bash tests/test_cat.sh

clean:
	rm -f s21_cat
	rm -rf tests/out

rebuild: clean all

.PHONY: all test clean rebuild
