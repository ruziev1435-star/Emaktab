# s21_cat and s21_grep

My own versions of the `cat` and `grep` utilities, written in C11.
They copy the behaviour of the **BusyBox** versions used on Alpine 3.20,
where the project is graded.

## Folder structure

```
src/
├── .clang-format         style settings (copied from materials/linters)
├── common/               code shared by both utilities
│   ├── s21_common.c/.h   flag parsing loop, opening files, error messages
│   └── test_lib.sh       shared helpers for both test scripts
├── cat/
│   ├── s21_cat.c/.h      the cat utility
│   ├── Makefile
│   └── tests/            test_cat.sh + test files in tests/data
└── grep/
    ├── s21_grep.c/.h     the grep utility
    ├── Makefile
    └── tests/            test_grep.sh + test files in tests/data
```

## Building

```sh
cd src/cat  && make s21_cat     # creates src/cat/s21_cat
cd src/grep && make s21_grep    # creates src/grep/s21_grep
```

Other targets in both Makefiles: `all`, `test`, `clean`, `rebuild`.
The code is compiled with `gcc -Wall -Wextra -Werror -std=c11`.

## Supported flags

| Utility | Flags |
|---------|-------|
| s21_cat | `-b` `-e` `-n` `-s` `-t` `-v`, GNU: `-E` `-T` `--number-nonblank` `--number` `--squeeze-blank` |
| s21_grep | `-e` `-i` `-v` `-c` `-l` `-n` `-h` `-s` `-f` `-o` and any combination of them (e.g. `-iv`, `-in`) |

Flags can be combined (`-ne`), written separately (`-n -e`) and placed after
the file names (`s21_cat file.txt -n`), like on Alpine. Reading from stdin is
not supported (the task does not require it), so at least one file is needed.

## Testing

```sh
cd src/cat  && make test
cd src/grep && make test
```

The test scripts run the **real** utility and **ours** with the same flags
and files, and compare the output, the exit code and whether an error message
was printed. They cover every flag, every combination of cat flags, every pair
of grep flags, several patterns, pattern files, missing files and bad flags.

* The reference is `busybox cat` / `busybox grep` when BusyBox is installed,
  otherwise the system `cat` / `grep` (then some results can differ, see below).
* GNU-only cat flags (`-s`, `-E`, `-T`) do not exist in BusyBox, so they are
  compared with GNU cat when it is installed, otherwise skipped.
* `BUSYBOX=/path/to/busybox make test` uses a specific BusyBox binary.
* `VALGRIND=1 make test` also checks every run for memory leaks.

To test exactly like the grading system (Alpine 3.20), from the repository root:

```sh
docker run --rm -v "$PWD":/project -w /project alpine:3.20 sh -c \
  "apk add build-base bash coreutils grep valgrind &&
   make -C src/cat test && make -C src/grep test"
```

## BusyBox details that are copied on purpose

BusyBox sometimes behaves differently from GNU (Ubuntu) or BSD (macOS).
These differences are intentional:

**cat**
* `-n` / `-b`: the number is printed as `%6d` + TAB, and the last line of each
  file always gets a newline, even if the file does not end with one.
  A `\0` byte is treated as the end of a line in this mode.
* With `-v`, `-e` or `-t`, the number is followed by **two spaces** instead of
  a TAB, and no newline is added at the end of a file.
* `-b` wins over `-n`. Numbering continues across files.
* `-E` (GNU) shows `^M$` at the end of Windows `\r\n` lines, like GNU cat.

**grep**
* Patterns are basic regular expressions (`regex.h`), like grep without `-E`.
* With `-o` and several patterns, BusyBox tries the patterns from the last to
  the first and prints the matches of the first one that matches the line.
* `-v -o` prints nothing (BusyBox has a bug here and may crash; GNU grep also
  prints nothing).
* A directory given as a file is searched like an empty file.
* Exit code: `0` = a line was selected, `1` = nothing selected, `2` = error
  (for example a missing file, even with `-s`).

## Structured programming rules followed

* No `goto`, no global variables (options and state are passed in structs).
* Every function has one exit (`return` at the end) and is shorter than
  about 40 lines; blocks are nested at most 4 levels deep.
* No `break` in loops (only inside `switch`).
* Shared code lives in `src/common` and is used by both utilities.
* Everything that is opened or allocated is closed / freed
  (`fclose`, `free`, `regfree`); checked with valgrind.
