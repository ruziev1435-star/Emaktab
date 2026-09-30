#ifndef S21_CAT_H_
#define S21_CAT_H_

#include <stdio.h>

#define CAT_USAGE                               \
  "[-benstvET] [--number] [--number-nonblank] " \
  "[--squeeze-blank] file ..."

// Which features were requested on the command line.
typedef struct {
  int number_nonblank;   // -b, --number-nonblank
  int number_all;        // -n, --number
  int squeeze_blank;     // -s, --squeeze-blank
  int show_ends;         // -E (and -e)
  int show_tabs;         // -T (and -t)
  int show_nonprinting;  // -v (and -e, -t)
} CatOptions;

// State that has to survive between characters and between files.
typedef struct {
  const CatOptions *options;
  int line_number;      // last number that was printed
  int at_line_start;    // the next character begins a new line
  int prev_line_empty;  // the previous line was empty (for -s)
  int pending_cr;       // a '\r' is waiting to be printed (for -E)
} CatState;

// Reads the flags into `options`. Returns 0 on success, 1 on a bad flag.
int ParseCatOptions(int argc, char *argv[], CatOptions *options);

// Prints one opened file; `data` points to a CatState.
void CatFile(FILE *file, const char *path, void *data);

#endif  // S21_CAT_H_
