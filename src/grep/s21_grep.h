#ifndef S21_GREP_H_
#define S21_GREP_H_

#include <regex.h>
#include <stdio.h>

#define GREP_USAGE "[-ivclnhso] [-e pattern] [-f file] [pattern] file ..."

// Growing list of pattern strings collected from -e, -f or argv.
typedef struct {
  char **items;
  int count;
  int capacity;
} PatternList;

// Which features were requested on the command line.
typedef struct {
  int ignore_case;    // -i
  int invert;         // -v
  int count_only;     // -c
  int files_only;     // -l
  int line_numbers;   // -n
  int no_filenames;   // -h
  int silent;         // -s
  int only_matching;  // -o
  int pattern_given;  // at least one -e or -f was used
  PatternList patterns;
} GrepOptions;

// Everything a file handler needs while searching.
typedef struct {
  const GrepOptions *options;
  regex_t *regexes;
  int regex_count;
  int show_filename;  // prefix output lines with "file:"
  int any_selected;   // at least one line was selected in some file
} GrepContext;

// Reads flags and patterns. Returns 0 on success, 2 on error.
int ParseGrepOptions(int argc, char *argv[], GrepOptions *options);

// Searches one opened file; `data` points to a GrepContext.
void GrepFile(FILE *file, const char *path, void *data);

#endif  // S21_GREP_H_
