---
date:
  created: 2026-09-14
  updated: 2026-09-14
authors:
  - richard
slug: stop-using-rand
categories:
  - Tutorials
tags:
  - C
  - From scratch
draft: true
---

# Stop using `rand()`

In this article I will try to convince you to stop using `rand()` in your C projects,
and then write a better alternative from scratch.

Before digging into this, whenever I needed a random number, I used to reach for
`rand()` and maybe a bit of `srand(time(NULL))` when I needed it to be "unpredictable".

> *"But I'm not using it for cryptography"*

I always knew `rand()` was not a "safe" random number generator, but when you just need
some randomness for staticstics or machine learning, so who cares?

After digging a bit deeper though, I found out more good reasons to stop using `rand()`.

<!-- more -->


## Why not?

The main three reasons I don't use `rand()` anymore:

1. It's platform dependent
2. It's slow
3. It's low quality

### Platform dependent

This means that `rand()` behaves differently depending on the platform you compile it
for. What might be different? The maximum random number you can get (`RAND_MAX`) might
be different, also the sequence of random numbers after a given seed set with `srand()`
can be different. So that can be pretty annoying.

### Slow

The function is not doing any complicated math, but as far as I know, it relies on a
global state and needs to acquire a lock to be able to mutate it. This has to happen
every time you call `rand()`. So if you're using it in a hot loop, it can be pretty slow
compared to rolling your own RNG.

### Low quality

The quality of random numbers that `rand()` produces is poor, and we know that. But if
we look at some simple alternatives, we can easily get way higher quality random
numbers. (longer periods for example, so less repetition in sequences)

## Putting `rand()` to the test

Humans are really good at recognizing visual patterns. So to test a random number
generator, you can use visualization to expose flaws. Let's do that with `rand()`.

If we create a 960 x 540 pixel buffer, and pick random color values for each pixel using
`rand()` we get something like this:

![simple random](./simple-rand.png){ .pixelated }

Looks pretty random, no weird patterns or repetition to see there.

If we change the way we color in the pixels though, we can push `rand()` to its limits.

We'll take a certain amount of "samples". In every sample, we pick a random number to
decide which pixel we're coloring, then we pick a random number that sets the color.

We'll look at the code in a bit, but this is what the image looks like:

[TODO: Image with stripes full]

Looks okay at first glance, but if you zoom in you can clearly start to see some
repetition:

[TODO: Image with stipes zoomed in]

## RNG from first principles

Whenever I'm writing C I love to implement stuff from scratch, so that's what we're
gonna do here too. I will leverage some of the research from
[PCG](https://pcg-random.org) here to make sure our RNG is high quality.

The flavor of pseudo random number generator I want to use has the concept of **state**.
The random number you get when you call the generator is based on this state, and every
time you generate a random number, the state gets mutated. So the next time you generate
a random number, you will get a different one.

So the most basic example of a pseudo random number generator might be:

```c
static uint32_t rng_state = 1;

uint32_t rng_u(void) {
  return rng_state *= 12343;
}
```

The list of "random" number this generates:

```console
12343
152349649
3551009255
4260946081
982938263
3419336305
2519362119
923411777
```

Even this basic example, at first glance, looks pretty random. But of course you can see
that the first number is exactly our factor `12343` and we multiply by this amount every
time, until we wrap around the 32 bits limit of `4,294,967,296`. This also means that we
never generate an even number. So there are plenty of flaws to this approach. But the
basic principle is good. We just need to "scramble" the state more.


## Bigger state and more scrambling

What also helps, is to have a bigger state than the number you want to generate. So if
you want to generate 32-bit random numbers, having a state of 64 bits would be a good
idea.

I've searched around for different approaches to generating pseudo random numbers, and
the best one I found in terms of simplicity, performance, quality, is the [PCG
family](https://pcg-random.org). They share a basic C implementation that looks like
this:

```c
// *Really* minimal PCG32 code / (c) 2014 M.E. O'Neill / pcg-random.org
// Licensed under Apache License 2.0 (NO WARRANTY, etc. see website)

typedef struct { uint64_t state;  uint64_t inc; } pcg32_random_t;

uint32_t pcg32_random_r(pcg32_random_t* rng)
{
    uint64_t oldstate = rng->state;
    // Advance internal state
    rng->state = oldstate * 6364136223846793005ULL + (rng->inc|1);
    // Calculate output function (XSH RR), uses old state for max ILP
    uint32_t xorshifted = ((oldstate >> 18u) ^ oldstate) >> 27u;
    uint32_t rot = oldstate >> 59u;
    return (xorshifted >> rot) | (xorshifted << ((-rot) & 31));
}
```

As you can see, for the state we use a struct called `pcg32_random_t` that holds two
64-bit integers, so 128 bits in total (although only one of them is called "state").

And calling the function `pcg32_random_r` scrambles the state a lot more than simply
multiplying it by a constant.

We also need to declare our global state. The minimum C example only has a typedef of a
struct, but it's never instantiated. We can grab the following from the github repo.

```c
#define PCG32_INITIALIZER {0x853c49e6748fea9bULL, 0xda3e39cb94b95bdbULL}

pcg32_random_t pcg32_global = PCG32_INITIALIZER;
```
Now we actually have some global state, and we're properly initializing it.

## Adding our own wrappers

When I need a random number, I just want to call a simple function, and don't worry
about passing it anything. The `pcg32_random_r(pcg32_random_t* rng)` wants a pointer to
the global state, so let's wrap it with `#!c uint32_t rng_u(void)` with a `_u` for
*unsigned*.

```c
uint32_t rng_u(void) {
  return pcg32_random_r(&pcg32_global);
}
```

This adds a bit of indirection, which can slow down the code. So later on we'll look at
inlining `rng_u()` and `pcg32_random_r()`.

In addition to random integers, I'd like to get random floats too. Let's add a
`#!c float rng_f(void)`:

```c
float rng_f(void) {
  return pcg32_random_r(&pcg32_global) / (UINT32_MAX + 1.0f);
}
```

We're dividing by `UINT32_MAX + 1.0f` to make sure we get a range from 0.0 to 1.0 but we
don't include 1.0, so `[0.0, 1.0)`. This is generally a more convenient type of range to
work with for most applications where you want a random float in this range.

Getting a random float this way is quite naive and can be improved a lot, which we will
do in another article. So stay tuned if that's something you'd like to see.

## Sampling from a normal distribution

We can add one more random float flavour: a random number sampled from a normal
distribution. This can be very useful in machine learning and statistics.
