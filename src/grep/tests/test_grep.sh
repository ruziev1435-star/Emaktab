#!/bin/bash
# Integration tests for s21_grep: runs the real grep and s21_grep with the
# same arguments and compares the results (see ../../common/test_lib.sh).

cd "$(dirname "$0")" || exit 1
# shellcheck source-path=SCRIPTDIR
source ../../common/test_lib.sh

S21_GREP=../s21_grep
mkdir -p "$OUT_DIR"

find_reference grep
REF_GREP=("${REFERENCE[@]}")

# BusyBox has a bug with -v and -o together (it prints bare "file:" / "N:"
# prefixes or even crashes), so GNU grep is the reference for that pair:
# lines selected by -v contain no match, so nothing is printed.
GNU_GREP=()
if grep --version 2>/dev/null | grep -q GNU; then
  GNU_GREP=(grep)
elif command -v ggrep >/dev/null 2>&1; then
  GNU_GREP=(ggrep)
fi

check_grep() {
  run_case "grep $*" "${REF_GREP[@]}" "$@" -- "$S21_GREP" "$@"
}

check_grep_gnu() {
  if [ ${#GNU_GREP[@]} -eq 0 ]; then
    skip_case "grep $*"
  else
    run_case "grep $* (GNU)" "${GNU_GREP[@]}" "$@" -- "$S21_GREP" "$@"
  fi
}

# 1. No flags, every single flag and every pair of flags (e.g. -iv, -in),
#    with each way of giving patterns and with one, two or a missing file.
FLAGS=(i v c l n h s o)
FLAG_SETS=("")
for ((a = 0; a < ${#FLAGS[@]}; a++)); do
  FLAG_SETS+=("-${FLAGS[a]}")
  for ((b = a + 1; b < ${#FLAGS[@]}; b++)); do
    FLAG_SETS+=("-${FLAGS[a]}${FLAGS[b]}")
  done
done

FILE_SETS=("data/fruits.txt"
  "data/fruits.txt data/mixed.txt"
  "data/fruits.txt missing.txt data/mixed.txt")

for flags in "${FLAG_SETS[@]}"; do
  check=check_grep
  [ "$flags" = "-vo" ] && check=check_grep_gnu
  for files in "${FILE_SETS[@]}"; do
    # shellcheck disable=SC2086
    {
      $check $flags apple $files
      $check $flags -e apple -e ch $files
      $check $flags -e 'pie$' -e '^a' $files
      $check $flags -f data/patterns.txt $files
      $check $flags -e APPLE -f data/patterns_regex.txt $files
    }
  done
done

# 2. Flags written separately and some triple combinations.
check_grep -i -n apple data/fruits.txt data/mixed.txt
check_grep -v -c -i apple data/fruits.txt
check_grep -inc apple data/fruits.txt data/mixed.txt
check_grep -ivn apple data/fruits.txt
check_grep -hno apple data/fruits.txt data/mixed.txt
check_grep -lvi apple data/fruits.txt data/mixed.txt data/empty.txt
check_grep -ohi -e apple -e pie data/fruits.txt data/mixed.txt
check_grep -e apple -f data/patterns.txt -e grape data/fruits.txt
# Flags may also come after the pattern and the file names.
check_grep apple data/fruits.txt -n
check_grep apple data/fruits.txt data/mixed.txt -c -i
check_grep -e apple data/fruits.txt -o -e pie

# 3. Regular expressions (basic syntax, like grep without -E).
for pattern in 'a.b' '\[x\]' '^caret' 'end$' '\^caret\$' '[0-9]\{3\}' \
  'p*' '.*' '' '^$' 'ap\+' '[[:upper:]]' 'x*y*'; do
  check_grep "$pattern" data/fruits.txt data/mixed.txt
  check_grep -o "$pattern" data/fruits.txt data/mixed.txt
  check_grep -c "$pattern" data/fruits.txt data/mixed.txt
done

# 4. Pattern files: empty lines match everything, an empty file matches
#    nothing (and so -v selects every line).
for pattern_file in data/patterns_empty_line.txt data/patterns_none.txt \
  data/patterns_regex.txt; do
  check_grep -f "$pattern_file" data/fruits.txt data/mixed.txt
  check_grep -v -f "$pattern_file" data/fruits.txt
  check_grep -c -f "$pattern_file" data/fruits.txt
  check_grep -o -f "$pattern_file" data/mixed.txt
done

# 5. -o with several patterns that overlap.
check_grep -o -e apple -e 'apple pie' data/fruits.txt
check_grep -o -e p -e pp data/fruits.txt
check_grep -on -e a -e ap -e app data/fruits.txt data/mixed.txt

# 6. Empty files and errors.
check_grep apple data/empty.txt
check_grep -c apple data/empty.txt data/fruits.txt
check_grep -v apple data/empty.txt
check_grep apple missing.txt
check_grep -s apple missing.txt
check_grep -sc apple missing.txt data/fruits.txt
check_grep -f missing.txt data/fruits.txt
check_grep -s -f missing.txt data/fruits.txt
check_grep apple data
check_grep -s apple data data/fruits.txt
check_grep -Q apple data/fruits.txt
check_grep 'a\{1' data/fruits.txt

print_summary
