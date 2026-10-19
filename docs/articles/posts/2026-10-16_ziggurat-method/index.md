---
date: 2026-10-19
authors:
  - richard
slug: ziggurat-method-for-gaussian-rng
categories:
  - Tutorials
tags:
  - C
  - From scratch
links:
  - rng.c on Github: https://github.com/vanderoost/rng.c
  - articles/posts/2026-09-14_stop-using-rand/index.md

---

# The Ziggurat method

In this article I document my journey down the Gaussian random numbers rabbit hole.

## Gaussian random numbers

While creating the RNG library, I knew it had to have an `rng_norm()` function.

Gaussian (or normal) random numbers are a very common type of random number. You need them to initialise neural network weights for example.

So I created a basic `rng_norm()` function using a trick I learned form throwing dice:

If you throw two or more dice, and take the sum, the mean will be  more common than the outliers.

For example: When you throw 2 dice, the mean is 7, which has a probability of 1/6\. The outliers 2 and 12 have a probability of 1/36.

[probability distribution of throwing 2 dice]

## The central limit theorem

The probability distribution of two dice looks pyramid shaped. If you sum two random floats between 0-1, you'll get a similar distribution.

[pyramid histogram]

But as the sample size increases, the distribution starts to approach a bell curve. This is the idea of **the central limit theorem**.

It turns out if you take 12 random floats in range [0-1) you end up with standard deviation of 1\. And the histogram looks a lot like the classic bell curve:

[bell curve histogram]

The more random numbers you sample, the closer you get to a true normal distribution. So 12 is not giving us a "true" normal distribution. Even though the mean is 0.0 and the standard deviation is 1.0.

So how can we measure the "quality" of our distribution?

## Kurtosis

There is another way to measure a distribution besides mean and standard deviation. The metric "kurtosis" measures the "tails" of a distribution. The way it's calculated is very similar to variance.

The variance is the average of all squared deviations (taking them to the 2nd power). The kurtosis is the average of all deviations to the _4th_ power.

This means that kurtosis focuses a lot on the tails of the distribution. The samples close to the mean contribute very little to the final outcome.

So what is the kurtosis of our `rng_rand()` function when it sums up 12 random floats? It's around 2.9... ish

The kurtosis of a "true" normal distribution is exactly 3.0\. So although it's not far off, we can tell it's not perfect.

A common way to represent the kurtosis is by subtracting 3.0\. This way, a 0.0 means a perfect Gaussian distribution. Our function is giving a -0.1 which means the tails are too "thin" because it's below zero.

We can improve the kurtosis by taking a lot more than 12 samples. Here are a few results:

samples, kurtosis

12, -0.1

16, ...

32, ...

64, ...

128, ...

As you can see, it gets better, but we are trading accuracy for performance. So let's benchmark the run time as well.

## Benchmarking performance

I'm using `clock_get_..._ns` to measure the elapsed nanoseconds. So let's do that before and after the loop, and take 10 million samples in between.

```c

```

Turns out it takes around 12 nanoseconds per `rng_norm()` call (which uses 12 rng_f() samples). So about 1 ns per rng_f call.

Increasing the samples increases run time more or less linearly.

So this is our baseline:

Accuracy: -0.1

Speed: 12ns

Let's look at alternatives and see if we can improve this.

## Rejection sampling

There are many alternative ways to achieve Gaussian RNG. One very simple approach is **rejection sampling**.

This is a very simple and flexible method. As long as you can specify your probability distribution as a function, you can sample from it.

The way it works is:

1\. Get a random x sample in the range you want to sample

2\. Get a random y sample from 0 to the max of the probability density function

3\. If the y sample is under the curve at x, you accept the sample, and return x. If not, you go back to step 1 and repeat.

The problem with this method is the "repeat" step. If it rejects a sample (which takes two random numbers), you have to start over.

We can implement this to see how well it performs.

There is one variable we have to choose up front: The x range. Let's start with a range of [-3.0, 3.0].

This gives us a kurtosis of ... and a sample time of ... ns. If we want a better kurtosis, we have to include more of the tails, so increase the x range.

If we try a range from -6.0 to 6.0 for example, the kurtosis becomes ...

But the efficiency goes down. We reject a higher % of samples and have to try again a lot more.

Here's how rejection sampling stacks up against the rng_f() sum approach:

[graph]

Rejection sampling looks pretty bad

## Divide and conquer

The reason I brought up rejection sampling is that we can do some things to make it more efficient. This is where the Ziggurat method comes in.

The first principle reminded me a lot of divide and conquer, which is a cool concept used in many algorithms.

We can divide our 2D sample area into layers. Then we can resize these layers such that they "hug" the probability distribution. This allows us to throw away a lot of "dead" space that only held rejected samples anyways.

I'm going to take a very simple probability function, the "pyramid shape". And I'm only going to focus on the positive side of the x axis. So we're looking at the 2D domain of x: [0, 1] y: [0, 1].

Now let's divide it into two layers, and make the layers as small as possible while still holding the curve:

[drawing of two layers]

This looks more efficient, because we're ignoring an entire quarter of our domain.

Let's try to run the code this way. We have to introduce this concept of layers. The new approach will add a new step. Besides only picking a random x and y, we need to pick, a layer as well.

So let's pick a random layer 50/50, pick x, pick y, and see if we accept the sample or reject it. If we reject it, we try again:

```c

```

Let's look at the histogram after picking 10 million of these samples:

[bad looking histogram]

Something seems off..

## Why the area matters

We have two layers of different areas, but we're picking them 50/50\.  This results in an uneven distribution of samples.

The probability of picking a layer should be proportional to its area. So either we change our probabilities, or the areas.

Picking layers with equal probability is very nice and fast, so I'd say we try to make the layers equal area.

The way I want to do this, is not by figuring out the equations for the areas of each layer, sand solving for equality. I'd much rather use a numerical method.

## Bisection method to find the area

It's quite easy to pick an estimate of an area, and find out whether it's too big or to small.

So to find the right area, I want to start with an upper and lower bound. Then take the midpoint (average) and test whether it's too small or too big. This determines our new area bounds. And we repeat. This is called the bisection method.

The only thing we need is an initial bound for the area. So we need a number that's we know for sure is smaller than the actual area, and we need a number that we know for sure is larger.

So say we have a certain area we want to test. How do we check if the area is too large or too small?

##   
**Inverse of the probability density function**

The approach goes as follows. Our x_lim point determines the lower right corner of our first layer:

Because the layer starts at x = 0, the width of the first layer is equal to x_lim.

The area is known, because that's what we're testing. So it follows that the height of the layer is simply: height = area / width.

That's the first layer done.

What's the width of the second layer? We know at what value of y the base starts. The width is simply the width of the probability density at that y value.

TODO: add more here

## More layers = more efficient

As you can imagine, adding more and more layers reduces the total area we're sampling from. Improving the ratio of accepted vs rejected samples.

I like to pick layer count by powers of two, because then we can use random bits to pick the layer:

```c

```

## Getting the most out of a 32 bit integer

We are currently calling a lot of RNG functions when creating our sample. We could be a bit more efficient with this by combining multiple things.

When we call rng_u(), we get a random 32 bit integer, in other words: 32 random bits. We can use those bits for different things.

We could use some bits for picking a random layer. We could use some bits for generating a random x float. And we can use one bit as the sign which makes our final sample flip with 50% chance.

## Refactoring into the RNG library

Now is a good time to move our experimental code into the RNG library.

For speed, we want to inline the `rng_norm()` function. So I'll make it a `static inline` in the header. Just like we did with `rng_u()` and `rng_f()`.

The coordinates of the tables will remain global variables. And I want to specify them in a separate .c file.

This C file can then be automatically "generated" by another C file.

## Procedurally generating the coordinate tables

Instead of calling the `calc_layers` function every time we want to generate gaussian numbers, I'd like to "pre generate" these layers.

We could move the entire calc_layers logic into a separate .c file with a separate binary, and let that binary write another .c file.

This way, we can run this, and generate our final .c file as part of the build process. We can configure this all in the Makefile.

## Hooking it up to the Makefile

Because our entrypoint .c file is located in `src/`, the Makefile will automatically pick this up and make its binary a target.

This target will depend on all the object files, including rng.o. Since rng.o also depends on the file that our rng_zig_layer_gen spits out, we have a circular dependency now.

So to avoid this, we can create a dedicated rule for the generator binary:

```Makefile

```

We also have to specify that the rng binary depends on the generated .c file. And we have to make a rule to tell make how to generate this .c file:

```Makefile

```

With all this in place. We can simply run `make` and everything will be taken care of:

```console

```

## Final performance tweaks

Now, let's increase our total number of "layer bits" to 8, so we get 2^8 = 256 layers. This massively improves the efficiency, and we get ~3.5 nanoseconds per sample.

But there is another massive efficiency gain we can get. In the majority of cases when picking an x sample, we don't even have to pick a y to check if it's below the curve. We can simply check the width of our next layer, and if we're below that number, we know for a fact that we are under the curve.

So a random float sample + some math to check if we're below the probability distribution becomes a simple float comparison check:

```c

```

This final tweak gets us below 2 nanoseconds per sample!

There are a few more tweaks we can do to just clean up our tables: We can do all calculations in double precision. And only at the very end, write everything out as floats.

We can also increase accuracy by writing our floats in hex notation instead of regular decimal notation. This allows for specifying the float bits exactly as they are stored in memory:

```c

```

The final layer coordinates will look like this:

```c

```

---

And with that, we've finished our gaussian random number generator.
