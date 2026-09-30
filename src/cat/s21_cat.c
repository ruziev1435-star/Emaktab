#include "s21_cat.h"

#include "../common/s21_common.h"

#define CAT_PROGRAM "s21_cat"

static int ApplyFlag(int flag, void *data) {
  CatOptions *options = data;
  int status = 0;
  switch (flag) {
    case 'b':
      options->number_nonblank = 1;
      break;
    case 'e':
      options->show_ends = 1;
      options->show_nonprinting = 1;
      break;
    case 'E':
      options->show_ends = 1;
      break;
    case 'n':
      options->number_all = 1;
      break;
    case 's':
      options->squeeze_blank = 1;
      break;
    case 't':
      options->show_tabs = 1;
      options->show_nonprinting = 1;
      break;
    case 'T':
      options->show_tabs = 1;
      break;
    case 'v':
      options->show_nonprinting = 1;
      break;
    default:
      status = 1;
      break;
  }
  return status;
}

int ParseCatOptions(int argc, char *argv[], CatOptions *options) {
  const struct option long_options[] = {
      {"number-nonblank", no_argument, NULL, 'b'},
      {"number", no_argument, NULL, 'n'},
      {"squeeze-blank", no_argument, NULL, 's'},
      {NULL, 0, NULL, 0}};
  int status =
      ParseFlags(argc, argv, "beEnstTv", long_options, ApplyFlag, options);
  // -b always wins over -n.
  if (options->number_nonblank) options->number_all = 0;
  return status;
}

// Prints a character in the ^X / M-X notation used by -v.
static void PrintNonprinting(int c) {
  if (c >= 128) {
    fputs("M-", stdout);
    c -= 128;
  }
  if (c < 32) {
    printf("^%c", c + 64);
  } else if (c == 127) {
    fputs("^?", stdout);
  } else {
    putchar(c);
  }
}

// Prints a '\r' that was held back by -E: GNU cat shows it as ^M only
// when it ends a line (Windows "\r\n" line endings).
static void FlushCarriageReturn(int next, CatState *state) {
  if (state->pending_cr) {
    fputs(next == '\n' ? "^M" : "\r", stdout);
    state->pending_cr = 0;
  }
}

static void PrintChar(int c, CatState *state) {
  const CatOptions *options = state->options;
  FlushCarriageReturn(c, state);
  if (c == '\r' && options->show_ends && !options->show_nonprinting) {
    state->pending_cr = 1;  // the next character decides how to print it
  } else if (c == '\n') {
    if (options->show_ends) putchar('$');
    putchar('\n');
  } else if (c == '\t') {
    fputs(options->show_tabs ? "^I" : "\t", stdout);
  } else if (options->show_nonprinting) {
    PrintNonprinting(c);
  } else {
    putchar(c);
  }
}

static int NeedsNumber(const CatOptions *options, int empty_line) {
  return options->number_all || (options->number_nonblank && !empty_line);
}

static void PrintLineNumber(CatState *state) {
  // BusyBox separates the number with a tab, but with two spaces when
  // -v (or -e / -t) is active.
  const char *separator = state->options->show_nonprinting ? "  " : "\t";
  state->line_number++;
  printf("%6d%s", state->line_number, separator);
}

static void ProcessChar(int c, CatState *state) {
  const CatOptions *options = state->options;
  int empty_line = state->at_line_start && c == '\n';
  int squeezed = options->squeeze_blank && empty_line && state->prev_line_empty;
  if (!squeezed) {
    if (state->at_line_start && NeedsNumber(options, empty_line)) {
      PrintLineNumber(state);
    }
    PrintChar(c, state);
  }
  if (c == '\n') state->prev_line_empty = empty_line;
  state->at_line_start = (c == '\n');
}

// Without -v BusyBox numbers the file line by line: it treats '\0' as the
// end of a line and always finishes the last line with a newline.
static int IsLineMode(const CatOptions *options) {
  int numbering = options->number_all || options->number_nonblank;
  return numbering && !options->show_nonprinting;
}

static void FinishFile(CatState *state) {
  FlushCarriageReturn(EOF, state);
  if (IsLineMode(state->options) && !state->at_line_start) {
    putchar('\n');
    state->at_line_start = 1;
    state->prev_line_empty = 0;
  }
}

void CatFile(FILE *file, const char *path, void *data) {
  CatState *state = data;
  int line_mode = IsLineMode(state->options);
  (void)path;
  int c = getc(file);
  while (c != EOF) {
    ProcessChar(line_mode && c == '\0' ? '\n' : c, state);
    c = getc(file);
  }
  FinishFile(state);
}

int main(int argc, char *argv[]) {
  CatOptions options = {0};
  int status = ParseCatOptions(argc, argv, &options);
  if (status == 0 && optind >= argc) status = 1;
  if (status != 0) {
    PrintUsage(CAT_PROGRAM, CAT_USAGE);
  } else {
    CatState state = {&options, 0, 1, 0, 0};
    status = ForEachFile(argv + optind, argc - optind, CAT_PROGRAM, 0, CatFile,
                         &state);
  }
  return status;
}
