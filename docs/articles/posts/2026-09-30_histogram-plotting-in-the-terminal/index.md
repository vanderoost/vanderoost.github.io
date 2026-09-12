---
date: 2026-09-30
authors:
  - richard
categories:
  - Development
tags:
  - C
description: A simple C library for plotting histograms in the terminal.
slug: histogram-plotting-in-the-terminal
---

# Plotting histograms in the terminal

I was generating random numbers the other day. And I really felt the urge to plot them
into a histogram to see what's going on. I.e. is it a uniform distribution, normal,
pyramid shaped? Noisy or smooth?

When I'm in Python, I normally grab Matplotlib for this kind of stuff. But when you're
in C what can you do?

I ended up writing a plot library from scratch of course :)

<!-- more -->

I wanted to keep it super simple, so I chose to plot in the terminal, using unicode
block characters. No need for external graphics or imaging libraries.

This is the final result looks like:

![Terminal plot example](plt_hist-example.png)

In the rest of this article, we'll walk through the process of writing this library.

I also recorded the entire process as a screencast:

![Histogram Plotting in C](youtube:aLNlyBNU0tw)

You can check out the final lib here: [plt.c](https://github.com/vanderoost/plt.c)


## Generating test data

Before we can plot anything, we need something to plot. I want my utility to work with
simple float arrays. If we need other datatypes later we can always do this.

So let's generate some random floats:

```c
#include <stdlib.h>

#define SAMPLE_COUNT 16

int main(void) {
  float data[SAMPLE_COUNT];
  for (size_t i = 0; i < SAMPLE_COUNT; ++i) {
    data[i] = (float)random() / RAND_MAX;
  }

  return 0;
}
```

## Histogram buckets

To take a list of random numbers, and turn it into a histogram, we need to decide on our
"buckets".

![Histogram buckets](drawing:histogram-buckets.svg)

Let's say all the little green dots are our random numbers, or samples. The buckets are
drawn as tall columns, and we just have to could how many samples fall in each bucket.
That will be the bar height of our histogram.

