#ifndef S21_COMMON_H_
#define S21_COMMON_H_

#include <getopt.h>
#include <stdio.h>

// Function that processes one opened file. `path` is the name given on the
// command line, `context` is utility-specific data (options and state).
typedef void (*FileHandler)(FILE *file, const char *path, void *context);

// Function that applies one command line flag to utility-specific options.
// Returns 0 on success, or the exit status to finish with.
typedef int (*FlagHandler)(int flag, void *options);

// Reads all flags with getopt_long and passes each one to `handler`.
// Flags may also follow file names ("file -n"), as in BusyBox on Alpine.
// Stops at the first error and returns its status (0 if all flags are fine).
int ParseFlags(int argc, char *argv[], const char *short_options,
               const struct option *long_options, FlagHandler handler,
               void *options);

// Prints "program: path: reason" to stderr using the current errno.
void PrintFileError(const char *program, const char *path);

// Prints a short usage hint to stderr.
void PrintUsage(const char *program, const char *usage);

// Opens every file from `paths` in order and passes it to `handler`.
// Files that cannot be opened are reported (unless `silent` is non-zero)
// and skipped. Returns 0 if every file was opened, 1 otherwise.
int ForEachFile(char *const paths[], int count, const char *program, int silent,
                FileHandler handler, void *context);

#endif  // S21_COMMON_H_
