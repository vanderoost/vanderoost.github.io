---
date: 2026-11-20T12:00:00
authors:
  - richard
categories:
  - Tutorials
  - Machine Learning
tags:
  - C
draft: true
---

# Coding a neural network in C

Neural networks are driving the current state of the art in AI and machine learning.
Let's see how they work by writing one from scratch in C.

<!-- more -->

## Mathematical functions

From the outside, a neural network is basically a function like $f(x) = y$ that takes an
input $x$ and spits out $y$. And under the hood, there's just a bunch of math going on,
so there's nothing magical about them.

The $x$ and $y$ can be single numbers, but they can also be arrays of numbers (vectors,
matrices, etc.)

Take this function for example:

$$
f(x) = ax
$$

Assuming that $x$ and $y$ are single numbers (scalars), the function describes a
straight line. The parameter $a$ can be used to adjust the slope of the line.

We can turn it into a mini neural network like this:

![Mini neural network](drawing:mini-neural-network.svg)

Calling this a *network* is pushing it, but technically this is can be considered a
neural network. And this is about as small as they get.

The circles are the artificial **neurons**, the line that connects them is the
artificial "synapse" if you will, but we can just call it a **connection** to keep it
simple. The connection always has a certain "strenght" or **weight** assigned to it, $a$
in this example.

In a physical neural network I can imagine connections between neurons either being weak
or strong. In artificial neural networks, besides a large or small number, the weight
can also be a negative number, so that's slightly different.

The calculation works by taking the value of the first neuron $x$, multiplying it by
the connection weight $a$, and then collecting the resulting value at the last neuron
$y$.

And that's basically how this extremely small network works.

Many data / machine learning problems that require a function to map some input $x$ to
an output $y$ can be (re)shaped into a format that works with neural networks.

## Multiple incoming connections

What happens if multiple neurons are connected to $y$? We simply sum up the values.

So if we add a new neuron with a value of 1, and a connection with a weight $b$ we get
this:

![Neural network with bias](drawing:neural-network-bias.svg)

So with that, we can model a function like this:

$$
f(x) = ax + b
$$

The extra $1$ node allows us to simply add a constant $b$ to the final output. ($1 \cdot b$ is just $b$)

The constant $b$ allows us to shift the final value up or down, regardless of what came
in through $x$. Later we will call this *bias*.

## Activation functions

One final component we will add is the concept of an *activation function*. This is a
function that belongs to a neuron. Instead of only summing up all incoming values like
we did before, we typically want to pass this value trough a function first, before
routing it into the next connections.

The reason it's called an *activation* function is because this mimics the concept of
real neurons, which can be active (firing) or inactive.

In our simple example from before, the activation function was just the identity
function or $f(x) = x$. If you want to model more interesting behaviour with a neural
network, it turns out this activation function should be something non-linear.

In the rest of this article I will be using the *sigmoid* function as our activation
function. This is a very commonly used activation function. And once we get the basics,
we can implement it in a way where it's easy to swap it out for other activation
functions. The sigmoid function squeezes every value between 0 and 1 in a smooth way:

```plot title="Plot of the sigmoid function"
f: 1 / (1 + exp(-x))
x: [-8, 8]
y: [-0.5, 1.5]
xstep: 2
ystep: 0.5
ylabel: σ(x)
```

The formula is:

$$
\sigma(x) = \frac{1}{1 + e^{-x}}
$$

If we would apply this to the last neuron of our mini-neural network, the function would
become something like:

$$
f(x) = \sigma(wx + b) = \frac{1}{1 + e^{-(wx + b)}}
$$

I like using sigmoid, especially for the output layer of a neural network, because this
way we always get a clean output between 0 and 1. This allows us to model problems in a
"binary" way, where the input is just 0's and 1's, and the output is, too.

## Layers of neurons

To create functions that can model more complex and interesting things, we just use a
bigger network by adding more neurons and connections.

Instead of randomly drawing circles and connections, we're going to organise the neurons
in vertical layers. We'll have an input layer on the left that corresponds to the input
$x$. It can be a single neuron for a single input number, or multiple neurons if $x$ is
a vector.

In the same way we'll have an output layer on the right that represents the $y$, if $y$
is a single number, it's one neuron, but it can be multiple as well just like $x$.

With this layered approach, the input and output layers are mandatory, so we need at
least two layers. Then, we have some optional in-beteen layers. They're called hidden
layers. You usually want to have at least one hidden layer to be able to model some
intersting behaviour with your network.

![Neural network with hidden layer](drawing:neural-network-layers.svg)

As you can see, connections only go from neurons one layer to neurons in the next layer.
There are more exotic neural network architectures possible where we break this rule,
but in the rest of the article I'll assume the simple rule of connections only going
from one layer to the next.

Also, I'm going to assume that every neuron is connected with every neuron in the next
layer. This is also known as a *fully connected* neural network. Again, this rule can
definitely be broken, but for simplicity we'll stick to fully connected networks for the
sake of fitting this into one article instead of an entire ebook.

## Notation

Now that we have all the building blocks to build neural networks, let's figure out a
consistent notation for all the moving parts.

We need three different types of variables. Something called $a$, which is the
activation of a neuron (the number that comes out of a neuron). We'll use $w$ for the
weights (the strength of a connection). And we need $z$, which is the sum
of all the activations $a$ multiplied by the weights $w$ that are incoming into a
neuron.

"Sum" doesn't start with a $z$, but this the convention of most of the literature.
Instead of $w$ for weights, $\theta$ (theta) is more common. But I'm more of a
programmer than a mathematician, so I'll use $w$ which will correspond to variable name
`w` in the code.

## The hello world of neural nets

We're going to get the concept down with a simple toy example: a neural network that
mimics the behaviour of  **XOR** (exclusive OR).

This is a binary operator, operating on two bits and spitting out one. It's similar to
**OR**, except when both input bits are `true`, the output is `false`.

This is the truth table of XOR:

| $x_1$ | $x_2$ | $y$ |
| :---: | :---: | :-: |
|   0   |   0   |  0  |
|   0   |   1   |  1  |
|   1   |   0   |  1  |
|   1   |   1   |  0  |

This is a good example to start with because it's small enough to write out all the
calculations by hand, but still challenging enough of a task that requires a hidden
layer.

What would this look like in C? In the [matrix article](../2026-10-30_c-matrix-library/index.md) we created [mat.c](https://github.com/vanderoost/mat.c/).

## Architecture

The artificial neural network that we are going to build here will have the concept of neurons and connections (or synapses). Neurons are grouped together in layers. So, a layer is a one-dimensional structure of neurons and the total network consists of layers and two layers that follow each other are connected by the connections or weights.

## Activation functions

In order for a neural network to approach interesting functions and benefit from adding multiple layers. The neurons should map the input Z into the output A in a non-linear fashion. The way we map Z to A is called the activation function. And in this example, we will be using the sigmoid function for this, which is a very common function that was especially popular when neural networks started to make a comeback again in the early 2010s.

## Forward pass

In the forward path we're simply taking the X or input and moving it through the network from s front to back, step by step. So every X Will be put in the first layers A A variables the A variables are connected through W to Z var variables and Z is defined by taking all the A and W pairs that are incoming connected into the neuron and multiplying the pairs together and taking the sum of all the pairs, taking the sum of all the products.

When we have all the Z values, we can calculate the next A values by routing the Z through the activation function.

We keep doing this until we reach the final A in the output layer, and that is the output of the network also represented as Y hat.

## Vectorizing

You might have seen that calculating Z from A and W looks a lot like a matrix multiplication. 

If we represent the weights w as a n by m matrix where n is the number of neurons on the left side and m is the number of neurons on the right side. We can see that multiplying the A's as a row vector will result in the Z's as another row vector.

## Batches

We can even take this vectorization a step further by not calculating a single input through the network, but moving several input vectors through the network at the same time. If we consider Z and A not a Row vector, but a matrix as well, where every row is a different example.

## Learning

Learning, or making the neural network give better outputs, means optimizing the
weights.

## Loss function

After doing a forward pass, we end up with an output of our network. If we also have the
ground truth output, Y, we can compare them and see how well the network is doing.

In this case, the output of an XOR network is only one number but, in many other cases, the output is a vector of numbers. It would be really useful to have a single number that serves as a metric of how well the network is matching the ground truth or the label.

This can be achieved using a loss function. The loss function takes in whatever the network came up with and the ground truth label, and it uses some way to compare them and it returns a value where Where zero is a perfect match, and anything above zero is worse. So it doesn't really ma measure how well the network does, but how wrong the network is. So you could see it as the error or the cost or the loss. In the rest of this article, I'll be calling it the loss function.

One of the simplest loss functions we can come up with is called the square loss. And it's calculated by taking the difference of y hat and y and squaring it and if there are multiple y's then just taking the sum of all of them. Oftentimes this is then also multiplied by one half, such that the derivative of this function is a very clean y hat minus y.

$$
L = \frac{1}{2} \sum_i (\hat{y}_i - y_i)^2
\qquad
\frac{\partial L}{\partial \hat{y}_i} = \hat{y}_i - y_i
$$

Let's use this function for now and later look at an improved loss function that we can use.

## Gradient of the loss

So now we're at the stage where we can move an input through our network and compare it with what the output should be. The next step is to make the network learn or to improve the network. And the only way to change the behavior of a network without changing the architecture is by tuning the weights.

The way we're going to tune the weights is we're going to calculate what the weight does to the loss because the loss is a single number so it's easy to to see whether moving a weight up or down moves the loss up or down, and by how much. So this can be considered the gradient or derivative of the loss with respect to one of the weights. And if we calculate this d partial derivative of the loss. For every single weight, we get a sense of how much and in which direction we can adjust every weight to make the network a little bit better. And the definition of a little bit better means a little bit lower loss.

The first method of coming up with the gradient of the loss with respect to each weight is by simply nudging each weight by a little amount, epsilon one by one and each time we nudge a weight we recalculate the entire forward pass and the loss to see what that did to our loss, and that's a way we can approximate the slope of the loss function in the direction of each and every weight.

## Writing it in C

Let's take these theoretical concepts and make them real by coding them up in C.

TODO: Code blocks

## Gradient descent

Now that we've brute forced the gradient of the loss with respect to each weight. we can update the weights in the direction that makes the loss go down. So, the amount we will update each weight is proportional to the inverse of this gradient because that makes it go down. And then we don't want to make too much of an adjustment because this gradient only holds true for the current position of all the weights. If we move too far away from the current position, the gradient will differ and so only locally This inverse of the gradient is the right direction to move into.

## Epochs

Now that we know how to brute force calculate the gradients and do a gradient descent step, let's try to repeat that a bunch of times. And see if over time the network's performance is improving.

TODO: Show how the network is learning and outputting the correct XOR outputs.

## Gradients using back propagation

Our current brute force way of calculating gradients works, but it is very slow and it is inaccurate. So let's talk about a massive improvement to getting the gradients by using math. And using the analytical approach because we can simply start at the loss and see how the previous number, the previous variable in the chain affects the loss. And then we can go one step further back by seeing how the second previous variable affects the The second to last variable and how that one affects the loss. And we can use the chain rule to calculate everything step by step. To make it to because we're still getting the action cards to not be able to.

TOOD: Show the math with drawings and LaTeX

## Implementing back propagation

Let's take what we've calculated and put it to practice in C.
