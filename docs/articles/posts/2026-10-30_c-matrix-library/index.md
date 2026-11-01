---
date: 2026-10-30T12:00:00
authors:
  - richard
slug: c-matrix-library-from-scratch
categories:
  - Tutorials
tags:
  - C
  - From scratch
links:
  - mat.c on Github: https://github.com/vanderoost/mat.c
  - articles/posts/2026-09-14_stop-using-rand/index.md

---

# Writing a C matrix library

![Matrix multiplication from scratch in C](youtube:zJ4y_JNBRKg)

I'm toying with the idea to write a neural network library in C. Which is quite an
undertaking.

To approach it in baby steps, I want to build some smaller building blocks first.
Setting up a foundation of sorts.

<!-- more -->

The random number library is one of them. Because neural networks need random weight
initialisation.

But another important one could be: Matrix math (mostly multiplication).

You don't _need_ matrix multiplications to code a neural network. But there is a very
elegant way to vectorise a neural net with matrix multiplications.

So today that's what I want to build:

*   Representing a Matrix in a data structure in C
*   Matrix multiplication

## Data structure

In C, we pretty much have only one option if we want to group data together: structs.

So let's design a simple struct that can represent a variable size 2D matrix. We need
the dimensions (rows and columns) and the actual floating point data inside the matrix.
That's all I'm going to add for now. Later on we can add more features to this (like
stride).

Here's the implementation:

```c
typedef struct {
  uint32_t rows, cols;
  float *data;
} Mat;
```

## Memory management

Now that we have an implementation, we need to be able to initialise a matrix.

We could create a helper function that allocates memory based on the dimensions we pass
in. But this makes the library a bit less flexible. I want my matrix library to be
responsible for matrix related functionality. Not for memory management. So I prefer to
manage memory allocation outside of the matrix library, and give it existing memory to
work with.

So for now, we can get away with not worrying about any allocation at all. We can
initialise the struct the vanilla way inline like this:

```c
Mat m = {2, 3, (float[]) {
  1, 2, 3,
  4, 5, 6,
}};
```

This is an acceptable way to create a quick small matrix on the stack. And by the end of
the function, it's all cleaned up.

## Printing

After creating a matrix, I'd like to know if it actually worked. So let's create our
first matrix function: `mat_print()`.

We'll loop over the rows and columns, and print each element.

```c
void mat_print(Mat m) {
  for (size_t i = 0; i < m.rows; ++i) {
    for (size_t j = 0; j < m.cols; ++j) {
      printf(" %6.2f", m.data[i * m.cols + j]);
    }
    printf("\n");
  }
}
```

When we run this, we can see our matrix representation:

```console
   1.00   2.00   3.00
   4.00   5.00   6.00
```

## Matrix multiplication interface

Our first matrix operation will be matrix multiplication.

Let's assume we have matrices `a`, `b`, `c`. And we get `c` by multiplying `a` and `b`:

```text
a * b = c
```

In C this would look like this:

```c
mat_mul(a, b, c);
```

But I like to move `c` to the start, because then it becomes more how you would program
it.

In programming, you write `c = a * b` if `a`, `b`, and `c` were simple numbers. So
that's the order I'd like to use in my `mat_mul()` function as well:

```c
mat_mul(c, a, b);
```

This is the way I'd like to use the function.

Should we pass in the matrices by reference, or by value?

Usually I want to be passing big datastructures by reference. And matrices can get big.
But the `Mat` struct itself only holds the size and a pointer to the actual data. So
passing around `Mat` structs instead of `Mat` struct pointers doesn't make much
difference.

So let's keep it simple, and just pass the `Mat` structs by value.

This makes our `mat_mul()` function look like this:

```c
void mat_mul(Mat c, Mat a, Mat b) {
  ...
}
```

## Matrix multiplication implementation

Let's see how we multiply matrices by hand first.

I usually start by taking the final resulting matrix `c`. Let's start with the
dimensions. If the dimensions of `a` are `n x m` and the dimensions of `b` are `m x o`,
then the dimensions of `c` are `n x o`.

So with those dimensions in mind, let's loop over all elements of `c` and calculate them
one by one.

```c
void mat_mul(Mat c, Mat a, Mat b) {
  for (size_t i = 0; i < c.rows; ++i) {
    for (size_t j = 0; j < c.cols; ++j) {
      // Calculate c[i, j]
    }
  }
}
```

The value of `c[i, j]` is the dot product of row `i` of `a` and column `j` of `b`. This
can be calculated with another for loop:

```c
void mat_mul(Mat c, Mat a, Mat b) {
  for (size_t i = 0; i < c.rows; ++i) {
    for (size_t j = 0; j < c.cols; ++j) {
      c.data[i * c.cols + j] = 0.0f;
      for (size_t k = 0; k < a.cols; ++k) {
        c.data[i * c.cols + j] += a.data[i * a.cols + k] * b.data[k * b.cols + j];
      }
    }
  }
}
```

That should do it. Let's test this by multiplying two simple 2x2 matrices:

$$
\begin{bmatrix} 1 & 2 \\ 3 & 4 \end{bmatrix}
\begin{bmatrix} 4 & 3 \\ 2 & 1 \end{bmatrix}
=
\begin{bmatrix}
  1 \cdot 4 + 2 \cdot 2 & 1 \cdot 3 + 2 \cdot 1 \\
  3 \cdot 4 + 4 \cdot 2 & 3 \cdot 3 + 4 \cdot 1
\end{bmatrix}
=
\begin{bmatrix} 8 & 5 \\ 20 & 13 \end{bmatrix}
$$

```c
Mat a = {2, 2, (float[]) {
  1, 2,
  3, 4,
}};
Mat b = {2, 2, (float[]) {
  4, 3,
  2, 1,
}};
Mat c = {2, 2, (float[4]) {0}};

mat_mul(c, a, b);
mat_print(c);
```

```console
   8.00   5.00
  20.00  13.00
```

## Random initialization

Another very useful function in our matrix library would be to initialise a matrix with
random values.

We could write this ourselves by just looping over all matrix elements, and calling an
RNG function on each of them:

```c
for (size_t i = 0; i < m.rows * m.cols; ++i) {
  m.data[i] = rng_f();
}
```

But it would be nice if we can let the matrix library handle this for us.

How can we make this happen? My first thought was to create a function like this:

```c
void mat_rand(Mat m) {
  for (size_t i = 0; i < m.rows * m.cols; ++i) {
    m.data[i] = rng_f();
  }
}
```

.. which sets all matrix elements to a random number.

But this makes the matrix library depend on a specific RNG library..

What if the user of the matrix library wants to use a different random number generator?

I'd like to keep the libraries as *decoupled* as possible. So instead of letting the
matrix library decide the RNG function, I'll "bring my own".

This is what that could look like:

```c
void mat_fun(Mat m, float f(void)) {
  for (size_t i = 0; i < m.rows * m.cols; ++i) {
    m.data[i] = f();
  }
}
```

So we pass in the matrix, but we also pass in the RNG function we would like to use.

Now we can grab our own RNG library, and get a random matrix like this:

```c
Mat m = {3, 3, (float[3 * 3]) {0}};
mat_fun(m, rng_norm);
mat_print(m);
```

```console
  -0.09  -0.04  -0.37
   0.50   0.67  -0.47
   0.11  -1.04  -2.09
```

## Benchmarking mat_mul()

I don't expect this C implementation to perform anywhere close to the state of the art
BLAS libraries. But let's see how we're doing by measuring the run time of `mat_mul()`.

I'm going to multiply two 512x512 matrices together. This might not sound like much, but
this triggers ~134 million (512\*512\*512) add and multiply operations.

So let's implement the benchmarking:

```c
#include "mat/mat.h"
#include "rng/rng.h"
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

#define MAT_SIZE 512
#define BEST_OF_N 8

int main(void) {
  float *mat_data = malloc(MAT_SIZE * MAT_SIZE * 3 * sizeof(*mat_data));

  Mat a = {
      .rows = MAT_SIZE,
      .cols = MAT_SIZE,
      .data = mat_data + 0 * MAT_SIZE * MAT_SIZE,
  };
  Mat b = {
      .rows = MAT_SIZE,
      .cols = MAT_SIZE,
      .data = mat_data + 1 * MAT_SIZE * MAT_SIZE,
  };
  Mat c = {
      .rows = MAT_SIZE,
      .cols = MAT_SIZE,
      .data = mat_data + 2 * MAT_SIZE * MAT_SIZE,
  };

  mat_fun(a, rng_norm);
  mat_fun(b, rng_norm);

  uint64_t fastest_ns = UINT64_MAX;
  for (size_t i = 0; i < BEST_OF_N; ++i) {
    uint64_t start_ns = clock_gettime_nsec_np(CLOCK_MONOTONIC);
    mat_mul(c, a, b);
    uint64_t dur_ns = clock_gettime_nsec_np(CLOCK_MONOTONIC) - start_ns;
    if (dur_ns < fastest_ns) {
      fastest_ns = dur_ns;
    }
  }
  double dur_ms = fastest_ns / 1e6;
  printf("mat_mul time: %.2f ms\n", dur_ms);

  free(mat_data);

  return 0;
}
```

When we run this, we run the matrix multiplication 8 times, and pick the fastest one for
consistency.

Our current `mat_mul()` implementation takes about 470 ms to run on an M2 Pro MacBook
Pro.

The lowest hanging fruit is to add compiler optimisation. Let's try the different levels
`-O0, -O1, -O2, -O3`:

| Flag  | mat_mul() time |
| ----- | -------------: |
| `-O0` |         468 ms |
| `-O1` |         144 ms |
| `-O2` |         144 ms |
| `-O3` |         143 ms |

## Cache friendly

Another thing to consider here is the excessive amounts of reads/writes we do in a
`mat_mul()` call.

In the naive implementation we loop over each row of the output, then column, then "sum
entry".

If we consider the kinds of memory access we're doing while this is happening, we can
see it's not very cache friendly.

This is the order in which we access the matrix data in memory. I'm assuming the
matrices `a`, `b`, and `c` sit in memory next to each other.

```text
    a0 a1 a2 a3 a4 a5 a6 a7 a8 b0 b1 b2 b3 b4 b5 b6 b7 b8 c0 c1 c2 c3 c4 c5 c6 c7 c8
 0  r                          r                          rw
 1     r                                r                 rw
 2        r                                      r        rw
 3  r                             r                          rw
 4     r                                   r                 rw
 5        r                                         r        rw
 6  r                                r                          rw
 7     r                                      r                 rw
 8        r                                            r        rw
 9           r                 r                                   rw
10              r                       r                          rw
11                 r                             r                 rw
12           r                    r                                   rw
13              r                          r                          rw
14                 r                                r                 rw
15           r                       r                                   rw
16              r                             r                          rw
17                 r                                   r                 rw
18                    r        r                                            rw
19                       r              r                                   rw
20                          r                    r                          rw
21                    r           r                                            rw
22                       r                 r                                   rw
23                          r                       r                          rw
24                    r              r                                            rw
25                       r                    r                                   rw
26                          r                          r                          rw
```

As you can see, matrix `a` and `c` look fine. But we're accessing matrix `b`'s memory by
jumping all over the place. I'm showing this more interactively in the screencast in
case this is not clear enough.

Let's look at a different order. If we would swap the order of the for loops, we can
experiment with different access patterns.

Before, we used the default order, so let's call it `i,j,k`.

What if we swap the inner most loops around, so it now becomes `i,k,j`?

```text
    a0 a1 a2 a3 a4 a5 a6 a7 a8 b0 b1 b2 b3 b4 b5 b6 b7 b8 c0 c1 c2 c3 c4 c5 c6 c7 c8
 0  r                          r                          rw
 1  r                             r                          rw
 2  r                                r                          rw
 3     r                                r                 rw
 4     r                                   r                 rw
 5     r                                      r                 rw
 6        r                                      r        rw
 7        r                                         r        rw
 8        r                                            r        rw
 9           r                 r                                   rw
10           r                    r                                   rw
11           r                       r                                   rw
12              r                       r                          rw
13              r                          r                          rw
14              r                             r                          rw
15                 r                             r                 rw
16                 r                                r                 rw
17                 r                                   r                 rw
18                    r        r                                            rw
19                    r           r                                            rw
20                    r              r                                            rw
21                       r              r                                   rw
22                       r                 r                                   rw
23                       r                    r                                   rw
24                          r                    r                          rw
25                          r                       r                          rw
26                          r                          r                          rw
```

This is looking WAY better. We're reading from the same cells of `a` multiple times in a
row. We're reading from `b` in a nice order. Writing to `c` is also not looking too bad.

So let's go back to the code and figure out how we can swap these for loops. This is
what the function looks like now:

```c
void mat_mul(Mat c, Mat a, Mat b) {
  for (size_t i = 0; i < c.rows; ++i) {
    for (size_t j = 0; j < c.cols; ++j) {
      c.data[i * c.cols + j] = 0.0f;
      for (size_t k = 0; k < a.cols; ++k) {
        c.data[i * c.cols + j] += a.data[i * a.cols + k] * b.data[k * b.cols + j];
      }
    }
  }
}
```

That doesn't allow us to swap loops `j` and `k`, because we're resetting the cells of
`c` to zero in between.

If we take that functionality out of the loop, and zero out `c` with `memset()` instead,
we're left with this:

```c
void mat_mul(Mat c, Mat a, Mat b) {
  memset(c.data, 0, c.rows * c.cols * sizeof *c.data);

  for (size_t i = 0; i < c.rows; ++i) {
    for (size_t j = 0; j < c.cols; ++j) {
      for (size_t k = 0; k < a.cols; ++k) {
        c.data[i * c.cols + j] += a.data[i * a.cols + k] * b.data[k * b.cols + j];
      }
    }
  }
}
```

And now we can easily swap `k` and `j` around:

```c
void mat_mul(Mat c, Mat a, Mat b) {
  memset(c.data, 0, c.rows * c.cols * sizeof *c.data);

  for (size_t i = 0; i < c.rows; ++i) {
    for (size_t k = 0; k < a.cols; ++k) {
      for (size_t j = 0; j < c.cols; ++j) {
        c.data[i * c.cols + j] += a.data[i * a.cols + k] * b.data[k * b.cols + j];
      }
    }
  }
}
```

And lo and behold, when we benchmark it now (at `-O3`) we're seeing a subtle **15x**
speedup.

A big part of that comes from SIMD: now that the inner loop walks through `b` and `c` in
order, the compiler can vectorise it from `-O2` up, doing 4 multiply-adds at once.

Pretty crazy how memory access patterns can affect our performance that much. It's not
just about getting a faster CPU.

---

That's where I'll leave it for now. You can grab the code from
[github](https://github.com/vanderoost/mat.c).
