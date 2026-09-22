# Task 2 — Three deliberate errors

Compiler: `g++ 13.3.0` (same clang/gcc-family diagnostics VS Code's C/C++ extension shows).
Command used for each: `g++ <file>.cpp -o <out>`

## Error 1 — Missing semicolon (`break1_missing_semicolon.cpp`)

Changed line 4 by deleting the trailing `;` after `std::endl`.

```
break1_missing_semicolon.cpp: In function 'int main()':
break1_missing_semicolon.cpp:4:47: error: expected ';' before 'return'
    4 |     std::cout << "Hello, Ruslan!" << std::endl
      |                                               ^
      |                                               ;
    5 |     return 0;
      |     ~~~~~~
```

**Cause:** every C++ statement must end in `;`. The compiler doesn't know statement 4 is finished, so it keeps reading into line 5 and reports the error at the point it got confused (before `return`) — not on the line that's actually missing the semicolon.

## Error 2 — Undeclared variable (`break2_undeclared_variable.cpp`)

Used a variable `name` that was never declared or initialized.

```
break2_undeclared_variable.cpp: In function 'int main()':
break2_undeclared_variable.cpp:4:31: error: 'name' was not declared in this scope; did you mean 'tzname'?
    4 |     std::cout << "Hello, " << name << "!" << std::endl;
      |                               ^~~~
      |                               tzname
```

**Cause:** every identifier must be declared before use. The compiler even suggests a near-miss (`tzname`, a symbol from a system header) — a reminder that "did you mean" suggestions aren't always what you actually want.

## Error 3 — Mismatched brace (`break3_mismatched_brace.cpp`)

Deleted the closing `}` of `main`.

```
break3_mismatched_brace.cpp: In function 'int main()':
break3_mismatched_brace.cpp:5:14: error: expected '}' at end of input
    5 |     return 0;
      |              ^
break3_mismatched_brace.cpp:3:12: note: to match this '{'
    3 | int main() {
      |            ^
```

**Cause:** every `{` needs a matching `}`. The compiler reaches the end of the file still "inside" `main`, so instead of pointing at one bad line it points back to the unmatched opening brace and asks you to close it.
