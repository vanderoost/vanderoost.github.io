---
date: 2026-10-09T12:00:00
authors:
  - richard
slug: better-random-floats
categories:
  - Tutorials
tags:
  - C
  - From scratch
links:
  - articles/posts/2026-09-14_stop-using-rand/index.md
  - articles/posts/2026-10-02_how-floats-work/index.md
  - rng.c on Github: https://github.com/vanderoost/rng.c
---

# Generating random floats

![Generating better random floats in C](youtube:qa83_KrkVIM)

We've already hand-rolled our own RNG in a [previous
article](../2026-09-14_stop-using-rand/index.md), to improve on what the C standard
library `rand()` gives us.

We also talked about [how floats work](../2026-10-02_how-floats-work/index.md).

In this article, I want to combine the two. I want to find out how we can generate
random floating-point numbers between 0 and 1, and improve our rng.c library.

<!-- more -->

## The naive way

We already created an `rng_f()` function when we set up the rng.c library. But it
generates random floats by dividing a random int by the max:

```c
float rng_f(void) {
  return pcg32_random_r(&pcg32_global) / (UINT32_MAX + 1.0f);
}
```

This approach has a small bug. We want to generate in the range of [0.0, 1.0) so we
want to get arbitrarily close to 1.0, but never hit it.

Because of rounding, there is actually a chance that we hit 1.0.

About 1 in 33.5 million. Any random integer of 2^32 - 128 or above rounds up to 2^32
when it's converted to a float, and 2^32 / 2^32 is exactly 1.0. This seems
insignificant, but we were already generating millions of random numbers. The chance
of it happening is quite high in that situation.

## Looking at float bits

Let's reflect back on how floats work in memory.

The mantissa (23 bits) can get you from a base number all the way up to (but not
including) double that base number.

This means that the smallest "step" we can take from a certain float depends on the
size or _exponent_ of the float. Floats close to zero have very tiny granular steps.
Large floats have a larger step size:

![Variable float resolution](drawing:variable-float-resolution.svg)

For example, the number 1.0 has the exponent `01111111` (127) with the mantissa set to
all zeros:

```
00111111 10000000 00000000 00000000
```

The closest float before hitting 2.0 has the same exponent as 1.0, but with the
mantissa fully maxed out (all 1s):

```
00111111 11111111 11111111 11111111
```

So when we randomise the mantissa bits, we can get a random float. As long as we keep
the exponent bits constant, we know we have a consistent step size.

## Randomising the 23 mantissa bits

In the [article on how floats work](../2026-10-02_how-floats-work/index.md), we
explored what the bits of a float mean, and how we can flip them.

If we have an RNG that gives us some random bits, we can use them to randomise our
float bits.

So if we want to randomise the 23 mantissa bits of the float, this is how we can do
that:

```c
typedef union {
  float f;
  uint32_t u;
} Bits;

Bits bits = {0};

bits.u |= rng_u() >> (32 - 23);
```

Here, we use the union trick to be able to access float memory as if it's an integer.
This allows for bitwise operations. Then we take a random 32-bit integer from
`rng_u()`, and shift it 9 places to the right (32 - 23). This shift zeroes out the top
9 bits, so the OR only sets mantissa bits and leaves the sign and exponent bits of the
float alone.

If you start at the number 0, and you randomise the mantissa bits, you get a random
range between 0.0 and about 1.18 × 10⁻³⁸. That's 37 zeros after the decimal point!
These tiny values are called subnormal numbers.

Not very practical for our target range of [0, 1) I reckon. This is because of that
variable resolution that we get in floats.

If we start with the number 0.5 though, and randomise the mantissa, we achieve a range
of [0.5, 1.0). That's starting to look more like it.

But starting at 0.5 gives us a total "range length" of 0.5 (1 - 0.5 = 0.5). The target
range of 0 to 1 has a length of 1. So what if we start from 1?

Then the range becomes [1, 2). So we get the desired length of the range; it's only
shifted up by 1. If we then subtract 1, we land exactly in range [0, 1). This is what
that looks like in C:

```c
Bits bits = {.f = 1.0f};
bits.u |= rng_u() >> (32 - 23);
bits.f -= 1.0f;
```

We start from a base of 1.0f. Then randomise the lowest 23 bits (mantissa bits) to vary
our range between 1 and 2 (not including 2). Finally we subtract 1. That subtraction is
exact: no rounding happens, so every value lands precisely in [0, 1).

Now we have a very efficient way to turn a random 32-bit int into a random 32-bit float
between 0 and 1.

But we can do better.

## Doubling the resolution

Let's take a closer look at the structure of a float.

We want equally spaced out floats in the range of 0 to 1. This is not trivial, because
if you consider ALL floats between 0 and 1, you get a large variety of step sizes, as
we saw in the drawing above.

The steps close to 0.0 are a lot more fine-grained than the steps close to 1. So which
step size do we choose? We choose the smallest one that works everywhere between 0
and 1. That means we should choose the step size of the range [0.5, 1).

Because if you go down the exponent, closer to zero, you keep dividing by 2. So the
step size between [0.25, 0.5) is half the step size of [0.5, 1). This is fine; we just
have to pick every other step between [0.25, 0.5) to stick to a constant step size.
Same for the range below that, [0.125, 0.25), we pick every 4th step, and so on.

So what does this mean? The step size we can take is the smallest increment within the
[0.5, 1) range. We can calculate that by manipulating bits:

```c
Bits bits = {.f = 0.5f};
bits.u += 1;
float step_size = bits.f - 0.5f;
printf("step size: %.10f (%a)", step_size, step_size);
```

This gives us an ideal step size of around `0.0000000596`, or more exactly `0x1p-24`,
so `1 * 2 ^ -24`.

What is the step size we're currently using when we generate floats using the random
mantissa and subtract 1 method?

That step size is twice as big, because we're generating a float between [1, 2), which
is the next level up from [0.5, 1).

So although that method works, we're throwing away half of our possible floating-point
numbers between 0 and 1 that we could have had.

Instead of 23 bits of randomness, we could add a 24th bit and double our resolution.

How can we do this? We could go back to starting from 0.5, randomising the mantissa to
get the range [0.5, 1). And then with 50% chance, subtract 0.5f from that. That could
definitely work, but there is a much simpler and more boring solution that we'll
explore next.

## Back to basics

We looked at the ideal step size for the range of random numbers to pick from between 0
and 1. This turned out to be the number 2^-24 or 1 / 2^24.

We've also seen how we can generate 32 random bits, and take 23 of them to randomise
bits in a float.

What if we took an extra random bit, 24 in total? This gives us an integer range of [0,
2^24). The 2^24 is not included, because if you have 24 bits maxed out (all 1s), it
equals 2^24 - 1.

We can recognise that 2^24 / 2^24 = 1, obviously. And since we don't quite reach 2^24,
we get (2^24 - 1) / 2^24 which is almost 1 (one step below 1). You might also realise
that if we divide the integer value of our 24 random bits by 2^24, we end up in our
desired range of [0, 1).

Dividing by 2^24 is the same as multiplying by 2^-24 (our step size). Your compiler
turns either one into the same multiplication, but writing it as a multiplication makes
the step size explicit. So now it all comes together. Since the step size of our
integer range is 1, if we multiply by 2^-24, this is the new step size.

So the improved method for converting a 32-bit integer to a 32-bit float in range
[0, 1) becomes:

```c
// Generate 24 random bits
uint32_t bits = rng_u() >> (32 - 24);

// Multiply by the smallest step size to generate a float between 0-1
float f = bits * 0x1.0p-24f;
```

That's all. And it fixes the bug from earlier: every 24-bit integer fits in a float
exactly, so the conversion never rounds, and the result can never reach 1.0.

This magical-looking `0x1.0p-24f` is hexadecimal float notation (added in C99). It
allows us to specify an exact float value.

The start `0x` means we're about to write a hexadecimal number. The `1.0` is the
mantissa in hex format (but in decimal format 1.0 is the same). And finally `p-24`
means "times 2 to the power of -24" (p instead of e, because e is a hexadecimal
digit). The exponent is written in decimal, and it's always a power of 2. It ends with
an `f` to make sure it's a 32-bit float and not a 64-bit double.

## Tucking it into the library

With this method of converting 32 random bits to a clean float in [0, 1), let's
integrate it into our rng.c library.

This is what our random integer function looks like:

```c
static inline uint32_t rng_u(void) {
  return pcg32_random_r(&pcg32_global);
}
```

Let's create an `rng_f()` function in the same vein:

```c
static inline float rng_f(void) {
  return (pcg32_random_r(&pcg32_global) >> 8) * 0x1.0p-24f;
}
```

Instead of calling `rng_u()` we call `pcg32_random_r` directly. The compiler would
inline `rng_u()` anyway, but this keeps the two functions symmetrical.

And we shift 8 bits. That's like saying "discard the 8 lowest bits", so we're left
with 24 bits.

And that's it! You can check out the code in the [rng.c
repo](https://github.com/vanderoost/rng.c). If it looks a bit different by the time you
read this, that might be because I've improved some things :)
