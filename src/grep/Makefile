CC = gcc
CFLAGS = -Wall -Wextra -Werror -std=c11 -D_POSIX_C_SOURCE=200809L

COMMON_DIR = ../common
SOURCES = s21_grep.c $(COMMON_DIR)/s21_common.c
HEADERS = s21_grep.h $(COMMON_DIR)/s21_common.h

all: s21_grep

s21_grep: $(SOURCES) $(HEADERS)
	$(CC) $(CFLAGS) $(SOURCES) -o $@

test: s21_grep
	bash tests/test_grep.sh

clean:
	rm -f s21_grep
	rm -rf tests/out

rebuild: clean all

.PHONY: all test clean rebuild
