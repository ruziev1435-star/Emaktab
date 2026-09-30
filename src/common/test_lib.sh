#!/bin/bash
# Shared helpers for the integration tests of s21_cat and s21_grep.
#
# Every test runs the reference utility and our utility with the same
# arguments and compares three things:
#   1. stdout (byte by byte),
#   2. the exit code,
#   3. whether something was written to stderr (the text itself may differ).
#
# Environment variables:
#   BUSYBOX=path   BusyBox binary to use as the reference (default: busybox)
#   VALGRIND=1     run our utility under valgrind and fail on leaks/errors
#   VERBOSE=1      print every passed test, not only the failures

TESTS_PASSED=0
TESTS_FAILED=0
TESTS_SKIPPED=0
OUT_DIR="out"

# Sets REFERENCE to the command that runs the real utility `$1`.
# BusyBox is preferred because the project is graded on Alpine, where
# cat and grep are BusyBox applets.
find_reference() {
  local util=$1
  local busybox=${BUSYBOX:-busybox}
  if command -v "$busybox" >/dev/null 2>&1 &&
    "$busybox" --list 2>/dev/null | grep -qx "$util"; then
    REFERENCE=("$busybox" "$util")
  else
    REFERENCE=("$util")
    echo "WARNING: BusyBox not found, comparing with the system $util."
    echo "         Results can differ from Alpine (see src/README.md)."
  fi
  echo "Reference: ${REFERENCE[*]}"
}

# run_case <label> <reference command...> -- <our command...>
run_case() {
  local label=$1
  shift
  local reference=()
  while [ "$1" != "--" ]; do
    reference+=("$1")
    shift
  done
  shift
  local mine=("$@")
  if [ "${VALGRIND:-0}" = "1" ]; then
    mine=(valgrind --quiet --leak-check=full --errors-for-leak-kinds=all
      --error-exitcode=99 "${mine[@]}")
  fi

  "${reference[@]}" >"$OUT_DIR/ref.out" 2>"$OUT_DIR/ref.err"
  local ref_code=$?
  "${mine[@]}" >"$OUT_DIR/my.out" 2>"$OUT_DIR/my.err"
  local my_code=$?
  local ref_err=0 my_err=0
  [ -s "$OUT_DIR/ref.err" ] && ref_err=1
  [ -s "$OUT_DIR/my.err" ] && my_err=1

  if cmp -s "$OUT_DIR/ref.out" "$OUT_DIR/my.out" &&
    [ "$ref_code" -eq "$my_code" ] && [ "$ref_err" -eq "$my_err" ]; then
    TESTS_PASSED=$((TESTS_PASSED + 1))
    [ "${VERBOSE:-0}" = "1" ] && echo "OK   $label"
  else
    TESTS_FAILED=$((TESTS_FAILED + 1))
    echo "FAIL $label"
    echo "     exit code: reference=$ref_code ours=$my_code;" \
      "stderr used: reference=$ref_err ours=$my_err"
    diff "$OUT_DIR/ref.out" "$OUT_DIR/my.out" | head -n 10
  fi
}

skip_case() {
  TESTS_SKIPPED=$((TESTS_SKIPPED + 1))
  [ "${VERBOSE:-0}" = "1" ] && echo "SKIP $1"
}

# Prints the totals and returns 1 if at least one test failed.
print_summary() {
  echo "-----------------------------------------"
  echo "Passed: $TESTS_PASSED  Failed: $TESTS_FAILED  Skipped: $TESTS_SKIPPED"
  rm -rf "$OUT_DIR"
  [ "$TESTS_FAILED" -eq 0 ]
}
