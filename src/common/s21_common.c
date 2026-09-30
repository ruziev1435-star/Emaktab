#include "s21_common.h"

#include <errno.h>
#include <string.h>

int ParseFlags(int argc, char *argv[], const char *short_options,
               const struct option *long_options, FlagHandler handler,
               void *options) {
  int status = 0;
  int flag = 0;
  while (status == 0 && flag != -1) {
    flag = getopt_long(argc, argv, short_options, long_options, NULL);
    if (flag != -1) status = handler(flag, options);
  }
  return status;
}

void PrintFileError(const char *program, const char *path) {
  fprintf(stderr, "%s: %s: %s\n", program, path, strerror(errno));
}

void PrintUsage(const char *program, const char *usage) {
  fprintf(stderr, "usage: %s %s\n", program, usage);
}

int ForEachFile(char *const paths[], int count, const char *program, int silent,
                FileHandler handler, void *context) {
  int status = 0;
  for (int i = 0; i < count; i++) {
    FILE *file = fopen(paths[i], "r");
    if (file == NULL) {
      if (!silent) PrintFileError(program, paths[i]);
      status = 1;
    } else {
      handler(file, paths[i], context);
      // Reading can still fail, for example when the path is a directory.
      if (ferror(file)) {
        if (!silent) PrintFileError(program, paths[i]);
        status = 1;
      }
      fclose(file);
    }
  }
  return status;
}
