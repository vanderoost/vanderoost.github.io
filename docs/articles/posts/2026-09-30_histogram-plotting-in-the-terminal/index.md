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

When I was experimenting with random number generators in C, I really felt a need to
visualize what I was doing. Especially when you apply some transormations to your
numbers, resulting on non-uniform distributions, it's key to have a way to visualize
things.

In Python I normally grab Matplotlib for this, but when you're in C what can you do?

We write a plot library from scratch of course :)

<!-- more -->

For random numbers, a histogram is one of the most useful tools to get a sense of your
distribution. And I knew about these unicode block characters that allow you to get a
lot of different heights, so I decided to do some plotting in the terminal with these
characters.

This is the final result:



