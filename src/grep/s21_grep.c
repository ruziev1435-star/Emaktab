#include "s21_grep.h"

#include <stdlib.h>
#include <string.h>

#include "../common/s21_common.h"

#define GREP_PROGRAM "s21_grep"
#define GREP_FLAGS "e:f:ivclnhso"

// ---------------------------------------------------------------------------
// Patterns
// ---------------------------------------------------------------------------

static void StripNewline(char *line, ssize_t length) {
  if (length > 0 && line[length - 1] == '\n') line[length - 1] = '\0';
}

static int AddPattern(PatternList *list, const char *pattern) {
  int status = 0;
  if (list->count == list->capacity) {
    int capacity = list->capacity == 0 ? 8 : list->capacity * 2;
    char **items = realloc(list->items, capacity * sizeof(char *));
    if (items == NULL) {
      status = 2;
    } else {
      list->items = items;
      list->capacity = capacity;
    }
  }
  if (status == 0) {
    list->items[list->count] = strdup(pattern);
    if (list->items[list->count] == NULL) status = 2;
    if (status == 0) list->count++;
  }
  if (status != 0) fprintf(stderr, "%s: out of memory\n", GREP_PROGRAM);
  return status;
}

static void FreePatterns(PatternList *list) {
  for (int i = 0; i < list->count; i++) free(list->items[i]);
  free(list->items);
  list->items = NULL;
  list->count = 0;
  list->capacity = 0;
}

// Adds every line of the file as a separate pattern (-f).
static int ReadPatternFile(const char *path, PatternList *list) {
  int status = 0;
  FILE *file = fopen(path, "r");
  if (file == NULL) {
    PrintFileError(GREP_PROGRAM, path);
    status = 2;
  } else {
    char *line = NULL;
    size_t capacity = 0;
    ssize_t length = getline(&line, &capacity, file);
    while (status == 0 && length != -1) {
      StripNewline(line, length);
      status = AddPattern(list, line);
      length = getline(&line, &capacity, file);
    }
    free(line);
    fclose(file);
  }
  return status;
}

// ---------------------------------------------------------------------------
// Command line
// ---------------------------------------------------------------------------

static int ApplyFlag(int flag, void *data) {
  GrepOptions *options = data;
  int status = 0;
  switch (flag) {
    case 'e':
      options->pattern_given = 1;
      status = AddPattern(&options->patterns, optarg);
      break;
    case 'f':
      options->pattern_given = 1;
      status = ReadPatternFile(optarg, &options->patterns);
      break;
    case 'i':
      options->ignore_case = 1;
      break;
    case 'v':
      options->invert = 1;
      break;
    case 'c':
      options->count_only = 1;
      break;
    case 'l':
      options->files_only = 1;
      break;
    case 'n':
      options->line_numbers = 1;
      break;
    case 'h':
      options->no_filenames = 1;
      break;
    case 's':
      options->silent = 1;
      break;
    case 'o':
      options->only_matching = 1;
      break;
    default:
      PrintUsage(GREP_PROGRAM, GREP_USAGE);
      status = 2;
      break;
  }
  return status;
}

int ParseGrepOptions(int argc, char *argv[], GrepOptions *options) {
  const struct option no_long_options[] = {{NULL, 0, NULL, 0}};
  int status =
      ParseFlags(argc, argv, GREP_FLAGS, no_long_options, ApplyFlag, options);
  // Without -e / -f the first free argument is the pattern.
  if (status == 0 && !options->pattern_given && optind < argc) {
    status = AddPattern(&options->patterns, argv[optind]);
    optind++;
  }
  // Reading from stdin is not required, so at least one file is needed.
  int no_pattern = !options->pattern_given && options->patterns.count == 0;
  if (status == 0 && (no_pattern || optind >= argc)) {
    PrintUsage(GREP_PROGRAM, GREP_USAGE);
    status = 2;
  }
  return status;
}

// ---------------------------------------------------------------------------
// Regular expressions
// ---------------------------------------------------------------------------

static int CompilePatterns(GrepContext *context) {
  const PatternList *patterns = &context->options->patterns;
  int flags = context->options->ignore_case ? REG_ICASE : 0;
  int status = 0;
  context->regexes = calloc(patterns->count + 1, sizeof(regex_t));
  if (context->regexes == NULL) {
    fprintf(stderr, "%s: out of memory\n", GREP_PROGRAM);
    status = 2;
  }
  for (int i = 0; status == 0 && i < patterns->count; i++) {
    regex_t *regex = &context->regexes[i];
    int error = regcomp(regex, patterns->items[i], flags);
    if (error != 0) {
      char message[256];
      regerror(error, regex, message, sizeof(message));
      fprintf(stderr, "%s: %s: %s\n", GREP_PROGRAM, patterns->items[i],
              message);
      status = 2;
    } else {
      context->regex_count++;
    }
  }
  return status;
}

static void FreeRegexes(GrepContext *context) {
  for (int i = 0; i < context->regex_count; i++) {
    regfree(&context->regexes[i]);
  }
  free(context->regexes);
  context->regexes = NULL;
  context->regex_count = 0;
}

// Returns the index of a pattern that matches `line`, or -1 if none does.
// Like BusyBox, patterns are tried from the last one to the first; this
// order decides which pattern -o prints when several patterns match.
static int FindMatchingPattern(const GrepContext *context, const char *line) {
  int index = context->regex_count - 1;
  while (index >= 0 &&
         regexec(&context->regexes[index], line, 0, NULL, 0) != 0) {
    index--;
  }
  return index;
}

// ---------------------------------------------------------------------------
// Output
// ---------------------------------------------------------------------------

static void PrintPrefix(const GrepContext *context, const char *path,
                        int line_number) {
  if (context->show_filename) printf("%s:", path);
  if (context->options->line_numbers) printf("%d:", line_number);
}

// Prints every non-empty match of pattern number `pattern` in `line` (-o).
static void PrintMatches(const GrepContext *context, const char *path,
                         const char *line, int line_number, int pattern) {
  const regex_t *regex = &context->regexes[pattern];
  regmatch_t match;
  size_t offset = 0;
  int found = regexec(regex, line, 1, &match, 0) == 0;
  while (found) {
    size_t start = offset + match.rm_so;
    size_t end = offset + match.rm_eo;
    if (end > start) {
      PrintPrefix(context, path, line_number);
      printf("%.*s\n", (int)(end - start), line + start);
    }
    found = line[end] != '\0';
    if (found) {
      // An empty match must still move forward, otherwise we loop forever.
      offset = end > start ? end : end + 1;
      found = regexec(regex, line + offset, 1, &match, REG_NOTBOL) == 0;
    }
  }
}

static void PrintSelectedLine(const GrepContext *context, const char *path,
                              const char *line, int line_number, int pattern) {
  const GrepOptions *options = context->options;
  if (options->only_matching) {
    // A line selected by -v contains no match, so -o prints nothing.
    if (!options->invert) {
      PrintMatches(context, path, line, line_number, pattern);
    }
  } else {
    PrintPrefix(context, path, line_number);
    printf("%s\n", line);
  }
}

static void PrintFileSummary(const GrepContext *context, const char *path,
                             int selected_count) {
  const GrepOptions *options = context->options;
  if (options->files_only) {
    if (selected_count > 0) printf("%s\n", path);
  } else if (options->count_only) {
    if (context->show_filename) printf("%s:", path);
    printf("%d\n", selected_count);
  }
}

// ---------------------------------------------------------------------------
// Searching
// ---------------------------------------------------------------------------

void GrepFile(FILE *file, const char *path, void *data) {
  GrepContext *context = data;
  const GrepOptions *options = context->options;
  int prints_lines = !options->count_only && !options->files_only;
  int line_number = 0;
  int selected_count = 0;
  int done = 0;
  char *line = NULL;
  size_t capacity = 0;
  ssize_t length = getline(&line, &capacity, file);
  while (!done && length != -1) {
    line_number++;
    StripNewline(line, length);
    int pattern = FindMatchingPattern(context, line);
    if ((pattern >= 0) != options->invert) {
      selected_count++;
      if (prints_lines) {
        PrintSelectedLine(context, path, line, line_number, pattern);
      }
      done = options->files_only;  // -l needs only one selected line
    }
    length = getline(&line, &capacity, file);
  }
  free(line);
  // Like BusyBox, read errors are not reported: a directory is searched as
  // if it were an empty file.
  clearerr(file);
  PrintFileSummary(context, path, selected_count);
  if (selected_count > 0) context->any_selected = 1;
}

int main(int argc, char *argv[]) {
  GrepOptions options = {0};
  GrepContext context = {&options, NULL, 0, 0, 0};
  int status = ParseGrepOptions(argc, argv, &options);
  if (status == 0) status = CompilePatterns(&context);
  if (status == 0) {
    int file_count = argc - optind;
    context.show_filename = file_count > 1 && !options.no_filenames;
    int file_error = ForEachFile(argv + optind, file_count, GREP_PROGRAM,
                                 options.silent, GrepFile, &context);
    if (file_error) {
      status = 2;
    } else {
      status = context.any_selected ? 0 : 1;
    }
  }
  FreeRegexes(&context);
  FreePatterns(&options.patterns);
  return status;
}
