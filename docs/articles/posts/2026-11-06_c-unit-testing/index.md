---
date: 2026-11-06T12:00:00
authors:
  - richard
description: Unit testing in C without a framework. Plain C files, assert, a Makefile target and a 20-line bash script.
slug: c-unit-testing-without-a-framework
categories:
  - Tutorials
tags:
  - C
  - From scratch
links:
  - mat.c on GitHub: https://github.com/vanderoost/mat.c
  - articles/posts/2026-10-30_c-matrix-library/index.md
  - articles/posts/2026-08-05_7-levels-effective-makefile-automation/index.md
---

# Writing C unit tests without a framework

![Writing C unit tests without a framework](youtube:YzV1Y1AhFY8)

Real C programmers write everything from scratch, reinvent wheels. I'm somewhat of a C
programmer myself :)

So when I felt the need to add unit tests to my C matrix library, I didn't want to
immediately reach for the nearest C unit testing framework. I wanted to see what it
takes to build my own.

<!-- more -->

C already gives us everything we need for basic unit testing:

*   **Functions** to wrap every single test in
*   **`assert()`** to make the program crash when a test fails

That's it. The rest is adding a nice interface to kick off all the tests. The Makefile
can take care of most of it, and I'll add a little bit of bash for some nice formatting
and coloring.

By the end of this article we'll be able to run `make test` and get this:

```console
$ make test
test_mat_fun         {grn}-> PASS{res}
test_mat_mul         {grn}-> PASS{res}

{grn}ALL GOOD{res}
```

## The starting point

Last week we wrote a [matrix library](../2026-10-30_c-matrix-library/index.md) from
scratch. That's the code base I want to add tests to.

This is what the project looks like:

```text
├── Makefile
└── src
    ├── main.c
    ├── mat
    │   ├── mat.c
    │   └── mat.h
    └── rng
        ├── rng.c
        ├── rng.h
        └── rng_zig_layers.c
```

And this is the interface of the matrix library:

```c
typedef struct {
  uint32_t rows, cols;
  float *data;
} Mat;

void mat_fun(Mat m, float f(void));
void mat_mul(Mat c, Mat a, Mat b);

void mat_print(Mat m);
```

Matrix multiplication is a perfect candidate for unit testing. It's easy to mess up an
index somewhere, and the result still _looks_ like a normal matrix with the right
dimensions. We even swapped the loop order around last time for performance. That's
exactly the kind of refactoring where I want to have the confidence that the math is
still mathing.

Right now the only "test" we have is `main.c`, which runs a benchmark and prints the
time. It doesn't tell us anything about whether the results are correct.

## Folder structure

The first question: where do we put the tests?

I don't want to mix test code into my source files. I have worked on projects where
testing was added "for the sake of testing" and the source code started to bend itself
around the fact that it's being tested.

I don't like that.

I want the test code to be completely separate. A test can reach into the source code,
but the source code doesn't need to know it's being tested.

So all tests go into a `test` directory in the root of the project:

```text hl_lines="4-5"
├── Makefile
├── src
│   └── ...
└── test
    └── test_mat_mul.c
```

Each test file is a plain C file with its own `main()`, so it compiles into its own
little executable. And inside each file, every unit test is just a function.

## Hello, test!

Let's start with our first test as simple as possible. One test file, one test function:

```c title="test/test_mat_mul.c"
#include <assert.h>

void test_mat_mul_square(void) {
  assert(1);
}

int main(void) {
  test_mat_mul_square();

  return 0;
}
```

A test function takes nothing and returns nothing. Inside it, I follow a simple pattern:

1.  Set up the data (create some matrices)
2.  Run the thing we're testing
3.  Assert that the result is what we expect

For now we just `assert(1)`, which passes.

`assert()` comes from `assert.h`. Officially it's a macro, not a function. If the
condition is false, it prints an error message to stderr and aborts the program. That's
exactly the behaviour we want from a failing test.

Let's compile and run it manually:

```console
$ cc test/test_mat_mul.c
$ ./a.out
$ echo $?
0
```

No output, exit code 0. The test passed.

If we change it to `assert(0)`:

```console
$ cc test/test_mat_mul.c
$ ./a.out
Assertion failed: (0), function test_mat_mul_square, file test_mat_mul.c, line 4.
zsh: abort      ./a.out
```

We get the function name, the file and the line number for free. That's honestly most of
what a testing framework would give us.

This is the whole foundation. Everything that follows is just automating this: compile
every test file, run every binary, and report which ones passed.

## A `make test` target

Calling `cc` and `./a.out` by hand is not how I want to run my tests. I want to type:

```console
$ make test
```

If you try that now, something funny happens:

```console
$ make test
make: `test' is up to date.
```

Make sees the `test` directory, thinks that's the target we want, and concludes it
already exists. Nothing to do. That's why `test` needs to go into `.PHONY`. It's not a
file we want to create, it's a command we want to run:

```makefile
.PHONY: all run test clean
```

Now we get the error we expect:

```console
$ make test
make: *** No rule to make target `test'.  Stop.
```

So what should the `test` target depend on? On the test binaries. Before we can run the
tests, they have to be compiled. But we don't have a list of test binaries yet. We do
have a list of test C files though, and we can derive one from the other.

!!! note

    If the Makefile syntax below looks like some form of Elvish, I wrote an
    [entire article](../2026-08-05_7-levels-effective-makefile-automation/index.md)
    that builds this Makefile up line by line.

### Finding all test files

I don't want to manually list every test file. Make should find them for me based on a
pattern, the same way it already finds all the source files:

```makefile
TEST = test

TEST_SRCS = $(wildcard $(TEST)/*.c)
```

Every `.c` file in the `test` directory is a test source. To make this a bit more
interesting, let's add a second test file `test/test_dummy.c` with just an empty
`main()` that returns 0.

A trick I like for checking variables is a temporary `debug` target:

```makefile
debug:
	@echo $(TEST_SRCS)
```

```console
$ make debug
test/test_dummy.c test/test_mat_mul.c
```

And that prints out both test `.c` files. So far so good.

### From test sources to test binaries

Next, every test source becomes a test binary:

```makefile
TEST_BINS = $(patsubst $(TEST)/%.c,$(BIN)/$(TEST)/%,$(TEST_SRCS))
```

`test/test_mat_mul.c` becomes `bin/test/test_mat_mul`.

I put them in a `bin/test` subdirectory on purpose. The `bin` directory already holds
our real executable `main`, and I don't want the test binaries mixed in with it.

```console
$ make debug
bin/test/test_dummy bin/test/test_mat_mul
```

### Compiling the tests

Now we can hook up the `test` target:

```makefile
test: $(TEST_BINS)
	@echo $^
```

`$^` is a special variable that expands to all the prerequisites, so we don't have to
repeat `$(TEST_BINS)`.

```console
$ make test
make: *** No rule to make target `bin/test/test_dummy', needed by `test'.  Stop.
```

Fair enough. We never told make how to build a test binary.

Our regular binaries are built in two steps: every `.c` becomes a `.o`, and then the
objects get linked together. For the tests I don't need that. I want to go from `.c` to
binary in one go, and link in the library objects, because those are what we're testing:

```makefile
$(BIN)/$(TEST)/%: $(TEST)/%.c $(LIB_OBJS)
	@mkdir -p $(@D)
	$(CC) $(CFLAGS) $(LDFLAGS) $< $(LIB_OBJS) -MMD -o $@
```

A couple of details here:

*   `mkdir -p $(@D)` creates `bin/test` if it doesn't exist yet.
*   There's no `-c` flag, because we want a binary, not an object file.
*   `$<` is only the _first_ prerequisite, the test's `.c` file. So we have to add
    `$(LIB_OBJS)` to the compile command explicitly. (I forgot this in the screencast
    and got a whole battery of linker errors once the test actually called `mat_mul()`.)
*   `-MMD` writes a `.d` dependency file next to the binary. If we include those, make
    knows to recompile a test when a header it includes changes.

Including the dependency files looks like this:

```makefile
TEST_DEPS = $(patsubst $(TEST)/%.c,$(BIN)/$(TEST)/%.d,$(TEST_SRCS))

-include $(DEPS) $(TEST_DEPS)
```

And now:

```console
$ make test
cc -Wall -Wextra -O3 test/test_dummy.c obj/mat/mat.o ... -MMD -o bin/test/test_dummy
cc -Wall -Wextra -O3 test/test_mat_mul.c obj/mat/mat.o ... -MMD -o bin/test/test_mat_mul
bin/test/test_dummy bin/test/test_mat_mul
```

The tests compile, and we print their names.

A nice side effect: a plain `make` only builds the `all` target, which doesn't depend on
the tests. The test code only gets compiled when we ask for it with `make test`.

## Gluing it together with bash

Instead of printing the binaries, we should run them. And for each one, check whether
it passed, and print it in green or red.

You could probably code all of that up in the Makefile. But it would turn into a
monstrosity, and the Makefile is already big enough. Bash isn't my favourite place to
be, but it's a good tool for this job: a little glue between the Makefile and the test
binaries.

So the `test` target passes all the test binaries to a script:

```makefile
test: $(TEST_BINS)
	@$(TEST)/run_tests.sh $^
```

Let's create `test/run_tests.sh`:

```bash title="test/run_tests.sh"
#!/usr/bin/env bash

echo "Running the tests"
```

And make it executable if you haven't already: `chmod +x test/run_tests.sh`

Now the bash script is called on `make test`:

```console
$ make test
Running the tests
```

### Looping over the arguments

The script receives the test binaries as arguments. In bash, `$1` is the first argument,
`$2` the second, and so on (`$0` is the name of the script itself). But the magic `$@`
variable gives us all of them at once.

So we can loop over every test binary like this:

```bash
for test in $@
do
  echo "Testing $test"
done
```

```console
$ make test
Testing bin/test/test_dummy
Testing bin/test/test_mat_mul
```

This is only printing the file names of the test binaries, not running them yet. To run
a test, we simply use the variable as a command: `$test`. And to know if it passed, we
put it in an `if`. Bash considers an exit code of 0 as true, and anything else as false:

```bash
for test in $@
do
  printf "$test "

  if $test
  then
    echo "-> PASS"
  else
    echo "-> FAIL"
  fi
done
```

`fi` is bash's way of closing an `if`. I'm using `printf` instead of `echo` for the
test name, because `echo` always adds a newline and I want the name and the result on
the same line. `printf` works just like it does in C.

```console
$ make test
bin/test/test_dummy -> PASS
bin/test/test_mat_mul -> PASS
```

The tests are passing!

## Red (gold) and green

Adding colour is very easy in a bash script, and it improves the dev experience a lot.
Green for pass, red for fail. For that we'll use ANSI escape codes. Here's the cheat
sheet:

| Code       | Effect |
| ---------- | ------ |
| `\033[31m` | Red    |
| `\033[32m` | Green  |
| `\033[0m`  | Reset  |

`\033` is the escape character. You start a colour with one of these codes, print your
text, and reset it afterwards.

We can wrap this in two small functions:

```bash
print_red() { printf "\033[31m$1\033[0m"; }
print_grn() { printf "\033[32m$1\033[0m"; }
```

Bash functions look a lot like C functions, except you don't declare any parameters.
Whatever you pass in is available as `$1`, `$2`, etc. inside the function.

While we're at it, let's clean up the test names. I don't care about the `bin/test/`
prefix, just the name of the test. `basename` takes care of that. And since we're using
`printf` anyway, we print the name with a fixed width, so all the results line up:

```bash
for test in $@
do
  printf "%-20s " $(basename "$test")

  if $test
  then
    print_grn "-> PASS\n"
  else
    print_red "-> FAIL\n"
  fi
done
```

`%20s` pads the name to 20 characters, aligned to the right. The `-` in `%-20s` aligns it
to the left.

```console
$ make test
test_dummy           {grn}-> PASS{res}
test_mat_mul         {grn}-> PASS{res}
```

## Capturing the output

But what happens when a test fails? We can make `test_dummy.c` fail and see. While we're
at it we can also print some debug info like a real world test might do:

```c title="test/test_dummy.c" hl_lines="5-6"
#include <assert.h>
#include <stdio.h>

void test_that_fails(void) {
  puts("Some debug info");
  assert(0);
}

int main(void) {
  test_that_fails();

  return 0;
}
```

When we run it, we get this mess:

```console
$ make test
test_dummy           Some debug info
Assertion failed: (0), function test_that_fails, file test_dummy.c, line 6.
test/run_tests.sh: line 6: 23556 Abort trap: 6           $test
{red}-> FAIL{res}
test_mat_mul         {grn}-> PASS{res}
```

The test is vomiting all its output straight into the terminal, before we get a chance
to print the red "FAIL".

What we actually want:

*   When a test **passes**, hide the output, just say `PASS` in green.
*   When a test **fails**, show all the output and error messages, for debugging.

So we have to capture the output. In bash, `$(...)` runs a command and gives back
whatever it printed:

```bash
if output=$($test)
```

This is a way to "catch" everything that `$test` spits out, and store it into `output`.

The `if` still looks at the exit code of the test, so that logic still works.

```console
$ make test
test_dummy           Assertion failed: (0), function test_that_fails, file test_dummy.c, line 6.
{red}-> FAIL{res}
test_mat_mul         {grn}-> PASS{res}
```

The debug info from `puts()` is gone, but the assert error message still weasels its way
through. That's because `$(...)` only captures `stdout` (standard output), and
`assert()` writes to `stderr` (standard error).

Every process has three streams, each with a number (a file descriptor):

| Stream | File descriptor |
| ------ | --------------: |
| stdin  |               0 |
| stdout |               1 |
| stderr |               2 |

With `$(...)` we're catching only `stdout`. But we want to catch both `stdout` and
`stderr`. To achieve this, we can redirect `stderr` into `stdout` first, and then catch
everything that ended up in `stdout`.

So we want to redirect stream 2 into stream 1. A first humble attempt at this might look
like `2>1` (redirect stream 2 into stream 1). But this redirects stderr into a _file_
called `1`. To redirect into a file descriptor, you need an `&`. So we use `2>&1`.

```bash
if output=$($test 2>&1)
```

Now both stdout and stderr are captured. All that's left is printing the output when the
test fails:

```bash hl_lines="6"
  if output=$($test 2>&1)
  then
    print_grn "-> PASS\n"
  else
    print_red "-> FAIL\n"
    echo "$output"
  fi
```

And that fixes our formatting:

```console
$ make test
test_dummy           {red}-> FAIL{res}
Assertion failed: (0), function test_that_fails, file test_dummy.c, line 6.
Some debug info
test_mat_mul         {grn}-> PASS{res}
```

And when everything passes, all output is hidden:

```console
$ make test
test_dummy           {grn}-> PASS{res}
test_mat_mul         {grn}-> PASS{res}
```

### Fail fast

One more thing. When a test fails, I don't want to see the rest of the results. I want
to fix that one test first. So after printing the output of a failing test, we bail out
with `exit`.

If we make it to the end of the loop, every test passed, and we deserve some
encouragement.

Here's the full script:

```bash title="test/run_tests.sh"
#!/usr/bin/env bash

print_red() { printf "\033[31m$1\033[0m"; }
print_grn() { printf "\033[32m$1\033[0m"; }

for test in $@
do
  printf "%-20s " $(basename "$test")

  if output=$($test 2>&1)
  then
    print_grn "-> PASS\n"
  else
    print_red "-> FAIL\n"
    echo "$output"
    exit 0
  fi
done

print_grn "\nALL GOOD\n"
```

20 lines, including blank lines. That's our entire "test framework".

Note that I `exit 0`, even on failure. The script handles and reports the failure
itself, so I don't want make to add its own error message on top. If you run your tests
in CI, you'll want `exit 1` here so the pipeline actually stops and doesn't deploy any
garbage into production.

## Testing the real mat.c library

Time to put it to the test (no pun intended). Let's write a real unit test for
`mat_mul()`.

### Including the library

First problem: how do we include `mat.h` from a test file? In `main.c`, we write:

```c
#include "mat/mat.h"
```

But from inside the `test` directory, that path doesn't exist. The path inside double
quotes is relative to the file doing the including. So we need this:

```c
#include "../src/mat/mat.h"
```

That works, but it's ugly. Instead, let's tell the compiler to also look in `src` for
includes, with the `-I` flag:

```makefile
CFLAGS = -Wall -Wextra -O3 -I$(SRC)
```

(This line needs to come after `SRC` is defined.)

Now `#include "mat/mat.h"` works the same in tests as it does in `main.c`.

If your editor uses `clangd` like mine, it doesn't know about the Makefile, so it will
still complain. Add the same flag to `compile_flags.txt` in the project root:

```text title="compile_flags.txt"
-Wall
-Wextra
-Isrc
```

### The first real test

Let's multiply the same two 2x2 matrices as in the previous article:

$$
\begin{bmatrix} 1 & 2 \\ 3 & 4 \end{bmatrix}
\begin{bmatrix} 4 & 3 \\ 2 & 1 \end{bmatrix}
=
\begin{bmatrix} 8 & 5 \\ 20 & 13 \end{bmatrix}
$$

In C that looks like:

```c title="test/test_mat_mul.c"
#include "mat/mat.h"
#include <assert.h>
#include <stddef.h>

void test_mat_mul_square(void) {
  // clang-format off
  Mat a = {2, 2, (float[]) {
    1, 2,
    3, 4,
  }};
  Mat b = {2, 2, (float[]) {
    4, 3,
    2, 1,
  }};
  Mat dst = {2, 2, (float[4]) {0}};
  Mat exp = {2, 2, (float[]) {
    8,    5,
    20,   13,
  }};
  // clang-format on

  mat_mul(dst, a, b);

  assert(dst.rows == exp.rows);
  assert(dst.cols == exp.cols);
  for (size_t i = 0; i < exp.rows * exp.cols; ++i) {
    assert(dst.data[i] == exp.data[i]);
  }
}

int main(void) {
  test_mat_mul_square();

  return 0;
}
```

Same pattern as before: set up, run, assert.

The `// clang-format off` comments stop my formatter from flattening the matrices into a
single line. I like being able to see the 2D shape of the data.

The destination matrix is initialised with zeros. All matrices sit on the stack which is
fine because they're so small. Without the `{0}`, it would be filled with whatever
garbage was in memory, and I want the test to be completely deterministic.

You might have noticed I compare floats with `==`. Normally that's a bad idea. But all
these values are small whole numbers, which floats represent
[exactly](../2026-10-02_how-floats-work/index.md), and there's no rounding happening in
the multiplication. If that ever becomes a problem, I'll add an epsilon.

```console
$ make test
test_dummy           {grn}-> PASS{res}
test_mat_mul         {grn}-> PASS{res}

{grn}ALL GOOD{res}
```

Does it actually test anything? Let's change the expected `13` to `13.1`:

```console
$ make test
test_dummy           {grn}-> PASS{res}
test_mat_mul         {red}-> FAIL{res}
Assertion failed: (dst.data[i] == exp.data[i]), function test_mat_mul_square, file test_mat_mul.c, line 27.
```

It does. I always like to break a test on purpose once, just to make sure it can fail.

### A second test

Let's add another test case: multiplying a column vector with a row vector.

```c
void test_mat_mul_vec(void) {
  // clang-format off
  Mat a = {3, 1, (float[]) {
    3,
    2,
    1,
  }};
  Mat b = {1, 4, (float[]) {
    1, 2, 3, 4,
  }};
  Mat dst = {3, 4, (float[3 * 4]) {0}};
  Mat exp = {3, 4, (float[]) {
    3,    6,    9,   12,
    2,    4,    6,    8,
    1,    2,    3,    4,
  }};
  // clang-format on

  mat_mul(dst, a, b);

  assert(dst.rows == exp.rows);
  assert(dst.cols == exp.cols);
  for (size_t i = 0; i < exp.rows * exp.cols; ++i) {
    assert(dst.data[i] == exp.data[i]);
  }
}

int main(void) {
  test_mat_mul_square();
  test_mat_mul_vec();

  return 0;
}
```

I like how `main()` turns into a little table of contents of the test file. And turning
off a single test is as easy as commenting out one line.

But those assertions at the bottom are now copy-pasted. Time to DRY this up.

## Removing duplication

It's just C, so the obvious fix is a function:

```c
void assert_mat_eq(Mat a, Mat b) {
  assert(a.rows == b.rows);
  assert(a.cols == b.cols);
  for (size_t i = 0; i < a.rows * a.cols; ++i) {
    assert(a.data[i] == b.data[i]);
  }
}
```

Works fine, until a test fails:

```console
Assertion failed: (a.data[i] == b.data[i]), function assert_mat_eq, file test_mat_mul.c, line 9.
```

The assertion now reports `assert_mat_eq` as the failing function. But which test called
it? `test_mat_mul_square` or `test_mat_mul_vec`? The useful error output from `assert()`
is gone.

You could solve this by turning the helper into a macro, since `assert()` itself is a
macro. But there's a simpler way: let the helper _check_, and let the test _assert_:

```c
assert(mat_eq(dst, exp));
```

So `mat_eq()` returns whether two matrices are equal. I could return an `int`, but
then 1 means success and 0 means failure, which is the opposite of what an exit code
means. A `bool` (from `stdbool.h`) makes the intent clear:

```c
bool mat_eq(Mat a, Mat b) {
  if (a.rows != b.rows) {
    return false;
  }
  if (a.cols != b.cols) {
    return false;
  }

  for (size_t i = 0; i < a.rows * a.cols; ++i) {
    if (a.data[i] != b.data[i]) {
      return false;
    }
  }

  return true;
}
```

Now the error message gives us the right failing test function:

```console
Assertion failed: (mat_eq(dst, exp)), function test_mat_mul_square, file test_mat_mul.c, line 42.
```

### Better failure messages

Remember that our bash script hides all output unless a test fails? That means we can be
super verbose with `printf()` calls without worrying about cluttering up the terminal.
It's hidden until you need it.

So let's say _why_ the matrices aren't equal:

```c
bool mat_eq(Mat a, Mat b) {
  if (a.rows != b.rows) {
    printf("rows mismatch (a: %u != b: %u)\n", a.rows, b.rows);
    return false;
  }
  if (a.cols != b.cols) {
    printf("cols mismatch (a: %u != b: %u)\n", a.cols, b.cols);
    return false;
  }

  for (size_t i = 0; i < a.rows * a.cols; ++i) {
    if (a.data[i] != b.data[i]) {
      printf("a:\n");
      mat_print(a);
      printf("b:\n");
      mat_print(b);
      printf("data mismatch @%zu (a: %f != b: %f)\n", i, a.data[i], b.data[i]);
      return false;
    }
  }

  return true;
}
```

We even get to reuse `mat_print()` from the matrix library. Now a failing test looks like
this:

```console
$ make test
test_dummy           {grn}-> PASS{res}
test_mat_mul         {red}-> FAIL{res}
Assertion failed: (mat_eq(dst, exp)), function test_mat_mul_square, file test_mat_mul.c, line 49.
a:
   8.00   5.00
  20.00  13.00
b:
   8.00   5.00
  20.00  13.10
data mismatch @3 (a: 13.000000 != b: 13.100000)
```

We see which test failed, on which line, what both matrices look like, and exactly which
element is off.

## Sharing helpers between test files

Let's test another function from the library: `mat_fun()`. It fills every element of a
matrix with the result of a function you pass in. In `main.c` we use it with an RNG
function to create random matrices.

If you're gonna rely on random numbers in your unit tests, you're gonna have a bad time.
So I'll pass in a function that does nothing but return an underwhelming `1.0f` float:

```c title="test/test_mat_fun.c"
#include "mat/mat.h"
#include <assert.h>

float one(void) { return 1.0f; }

void test_mat_fun_ones(void) {
  // clang-format off
  Mat dst = {2, 2, (float[4]) {0}};
  Mat exp = {2, 2, (float[4]) {
    1, 1,
    1, 1,
  }};
  // clang-format on

  mat_fun(dst, one);

  assert(mat_eq(dst, exp));
}

int main(void) {
  test_mat_fun_ones();

  return 0;
}
```

Except `mat_eq()` lives in `test_mat_mul.c`. Copy-pasting it into every test would be
pretty dumb, so let's fix that.

One option is to move `mat_eq()` into the matrix library itself. But I'm only using it
in tests, and I don't want the library to change just because it's being tested. The
tests should adapt to the source code, not the other way around.

So instead, let's give the tests their own little header: `test/helpers.h`. And let
`mat_eq()` live there:

```c title="test/helpers.h"
#ifndef _TEST_HELPERS_H
#define _TEST_HELPERS_H

#include "mat/mat.h"
#include <stdbool.h>
#include <stdio.h>

static inline bool mat_eq(Mat a, Mat b) {
  if (a.rows != b.rows) {
    printf("rows mismatch (a: %u != b: %u)\n", a.rows, b.rows);
    return false;
  }
  if (a.cols != b.cols) {
    printf("cols mismatch (a: %u != b: %u)\n", a.cols, b.cols);
    return false;
  }

  for (size_t i = 0; i < a.rows * a.cols; ++i) {
    if (a.data[i] != b.data[i]) {
      printf("a:\n");
      mat_print(a);
      printf("b:\n");
      mat_print(b);
      printf("data mismatch @%zu (a: %f != b: %f)\n", i, a.data[i], b.data[i]);
      return false;
    }
  }

  return true;
}

#endif // _TEST_HELPERS_H
```

A few notes:

*   The include guard is prefixed with `_TEST_`, to make sure it never collides with a
    header from the real source code called `helpers.h`.
*   It's header-only. It's simple enough that a `.c` + `.h` pair would be overkill.
*   Implementing functions in a header isn't conventional, but with `static inline` it's
    acceptable. `static` gives every test file its own copy, so there are no duplicate
    symbol errors at link time. `inline` keeps the compiler from warning about it when a
    test file doesn't use it.

Because the Makefile includes the `.d` files generated by `-MMD`, every test that
includes `helpers.h` gets recompiled when the helper changes.

Now both test files start like this:

```c
#include "helpers.h"
#include "mat/mat.h"
#include <assert.h>
```

And the `stdbool.h`, `stddef.h` and `stdio.h` includes can go, because `helpers.h` brings
them in.

```console
$ make test
test_mat_fun         {grn}-> PASS{res}
test_mat_mul         {grn}-> PASS{res}

{grn}ALL GOOD{res}
```

## The full setup

This is the final project structure:

```text
├── Makefile
├── compile_flags.txt
├── src
│   ├── main.c
│   ├── mat
│   │   ├── mat.c
│   │   └── mat.h
│   └── rng
│       └── ...
└── test
    ├── helpers.h
    ├── run_tests.sh
    ├── test_mat_fun.c
    └── test_mat_mul.c
```

Adding a new test means adding a function and calling it from `main()`. Adding a new
test file means dropping a `.c` file in `test`. Make picks it up automatically.

And this is the full Makefile:

```makefile title="Makefile"
NAME = main
SRC = src
OBJ = obj
BIN = bin
TEST = test

CFLAGS = -Wall -Wextra -O3 -I$(SRC)
LDFLAGS =
LDLIBS =

EXE = $(BIN)/$(NAME)

BIN_SRCS = $(wildcard $(SRC)/*.c)
LIB_SRCS = $(wildcard $(SRC)/*/*.c)
ALL_SRCS = $(BIN_SRCS) $(LIB_SRCS)

LIB_OBJS = $(patsubst $(SRC)/%.c,$(OBJ)/%.o,$(LIB_SRCS))
BIN_OBJS = $(patsubst $(SRC)/%.c,$(OBJ)/%.o,$(BIN_SRCS))
BINS = $(patsubst $(SRC)/%.c,$(BIN)/%,$(BIN_SRCS))
DEPS = $(patsubst $(SRC)/%.c,$(OBJ)/%.d,$(ALL_SRCS))

TEST_SRCS = $(wildcard $(TEST)/*.c)
TEST_BINS = $(patsubst $(TEST)/%.c,$(BIN)/$(TEST)/%,$(TEST_SRCS))
TEST_DEPS = $(patsubst $(TEST)/%.c,$(BIN)/$(TEST)/%.d,$(TEST_SRCS))

all: $(BINS)

$(BIN)/%: $(OBJ)/%.o $(LIB_OBJS)
	@mkdir -p $(@D)
	$(CC) $(LDFLAGS) $^ $(LDLIBS) -o $@

$(OBJ)/%.o: $(SRC)/%.c
	@mkdir -p $(@D)
	$(CC) $(CFLAGS) $< -c -MMD -o $@

run: $(EXE)
	@$(EXE)

test: $(TEST_BINS)
	@$(TEST)/run_tests.sh $^

$(BIN)/$(TEST)/%: $(TEST)/%.c $(LIB_OBJS)
	@mkdir -p $(@D)
	$(CC) $(CFLAGS) $(LDFLAGS) $< $(LIB_OBJS) -MMD -o $@

hot:
	@find $(SRC) $(TEST) -type f | entr -c make test

clean:
	@rm -rf $(BIN) $(OBJ)

-include $(DEPS) $(TEST_DEPS)

.PHONY: all run test hot clean
.SECONDARY: $(LIB_OBJS) $(BIN_OBJS)
```

The `.SECONDARY` line fixes an unrelated annoyance: on a fresh build, make treated the
`.o` files as means-to-an-end files and deleted them, so the next build had to start
over. Marking them as secondary keeps them around.

And the `hot` target re-runs `make test` (using
[entr](https://github.com/eradman/entr)) every time a file in `src` or `test` changes.
Save a file, and you immediately see green or red.

---

No frameworks, no magic black boxes. Just cozy, pure C functions, `assert()`, a Makefile
target and 20 lines of bash.

Everything in this setup is something you can read and understand in a few minutes, and
change whenever you want it to behave differently.

You can grab the code from [GitHub](https://github.com/vanderoost/mat.c).
