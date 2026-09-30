#!/bin/bash
# Integration tests for s21_cat: runs the real cat and s21_cat with the same
# flags and files and compares the results (see ../../common/test_lib.sh).

cd "$(dirname "$0")" || exit 1
# shellcheck source-path=SCRIPTDIR
source ../../common/test_lib.sh

S21_CAT=../s21_cat
mkdir -p "$OUT_DIR"

find_reference cat
REF_CAT=("${REFERENCE[@]}")

# GNU-only flags (-s, -E, -T) do not exist in BusyBox, so GNU cat is used as
# their reference when it is available (on Alpine: apk add coreutils).
GNU_CAT=()
if cat --version 2>/dev/null | grep -q GNU; then
  GNU_CAT=(cat)
elif command -v gcat >/dev/null 2>&1; then
  GNU_CAT=(gcat)
fi
echo "GNU reference: ${GNU_CAT[*]:-not found (GNU-only flags are skipped)}"

check_cat() {
  run_case "cat $*" "${REF_CAT[@]}" "$@" -- "$S21_CAT" "$@"
}

check_gnu() {
  if [ ${#GNU_CAT[@]} -eq 0 ]; then
    skip_case "cat $*"
  else
    run_case "cat $* (GNU)" "${GNU_CAT[@]}" "$@" -- "$S21_CAT" "$@"
  fi
}

# check_gnu_numbered <gnu flags> <numbering flags> <file>
# Reference: GNU cat applies the GNU-only flags, then the real cat numbers.
check_gnu_numbered() {
  if [ ${#GNU_CAT[@]} -eq 0 ]; then
    skip_case "cat -$1$2 $3"
  else
    run_case "cat -$1$2 $3 (GNU + reference)" \
      sh -c "${GNU_CAT[*]} -$1 '$3' | ${REF_CAT[*]} -$2" -- \
      "$S21_CAT" "-$1$2" "$3"
  fi
}

FILES=(data/text.txt data/blank_edges.txt data/windows.txt
  data/no_newline.txt data/empty.txt data/bytes.bin)
FILE_SETS=("${FILES[@]}"
  "data/text.txt data/no_newline.txt data/windows.txt"
  "data/no_newline.txt data/no_newline.txt data/blank_edges.txt")

# 1. Flags supported by BusyBox: every combination of b, e, n, t, v.
BUSYBOX_FLAGS=(b e n t v)
for mask in $(seq 0 31); do
  flags=""
  for i in 0 1 2 3 4; do
    if [ $(((mask >> i) & 1)) -eq 1 ]; then flags+=${BUSYBOX_FLAGS[i]}; fi
  done
  [ -n "$flags" ] && flags="-$flags"
  for files in "${FILE_SETS[@]}"; do
    # shellcheck disable=SC2086
    check_cat $flags $files
  done
done

# Flags written separately must behave the same as combined ones.
check_cat -b -n data/text.txt
check_cat -n -e -t data/bytes.bin
check_cat -v -b data/windows.txt
# Flags may also come after the file names.
check_cat data/text.txt -n
check_cat data/windows.txt data/text.txt -b -e

# 2. GNU long options are the same as the short BusyBox flags.
for file in "${FILES[@]}"; do
  run_case "cat --number $file" "${REF_CAT[@]}" -n "$file" -- \
    "$S21_CAT" --number "$file"
  run_case "cat --number-nonblank $file" "${REF_CAT[@]}" -b "$file" -- \
    "$S21_CAT" --number-nonblank "$file"
  run_case "cat --number -e $file" "${REF_CAT[@]}" -n -e "$file" -- \
    "$S21_CAT" --number -e "$file"
done

# 3. GNU-only flags -s, -E, -T (alone, together and with -v/-e/-t).
for flags in -s -E -T -sE -sT -ET -sET -sv -se -st -Ev -Tv --squeeze-blank; do
  for files in "${FILE_SETS[@]}"; do
    # shellcheck disable=SC2086
    check_gnu $flags $files
  done
done

# 4. GNU-only flags together with numbering. The binary file is left out:
#    there the two-step reference would treat '\0' differently than a
#    single cat call does.
for file in "${FILES[@]}"; do
  [ "$file" = data/bytes.bin ] && continue
  for gnu_flags in s E T sE sT sET; do
    check_gnu_numbered "$gnu_flags" n "$file"
  done
  for gnu_flags in s T sT; do
    check_gnu_numbered "$gnu_flags" b "$file"
  done
  for numbering in nv ne nt bv be bt; do
    check_gnu_numbered s "$numbering" "$file"
  done
done

# 5. Errors: missing files, directories and unknown flags.
check_cat data/text.txt missing.txt data/windows.txt
check_cat -n missing.txt data/text.txt
check_cat missing.txt
check_cat data
check_cat -z data/text.txt

print_summary
