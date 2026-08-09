---
date: 2026-08-05
authors:
  - richard
categories:
  - Automation
  - Development
tags:
  - Makefile
  - C
description: Makefile cheatsheet for automating C builds from simple to advanced
slug: levels-of-effective-makefile-cheatsheet
---

# The 7 levels of highly effective Makefiles

Make is a great tool for automating our life in the terminal.

The original use case of `make` is creating literal files. And a `Makefile` consists of
rules on how to make certain files.

But what `make` is also great at is just creating useful shortcuts to common terminal
commands. For example, running tests, deploying, building Docker images, etc.

In this article we'll walk through 7 levels of Makefiles, from simple to advanced in the
context of some C source code that needs to be compiled. I use it myself as a cheatsheet
when I need to write a new `Makefile`.

<!-- more -->

This is the final `Makefile` we'll end up with:

```makefile title="Makefile" linenums="1"
CFLAGS = -Wall -Werror -pedantic

EXEC = main
SRC = src
OBJ = obj

LIBS = $(wildcard $(SRC)/*/*.c)
OBJS = $(patsubst $(SRC)/%.c,$(OBJ)/%.o,$(LIBS))

VPATH = $(SRC)

all: $(EXEC)

$(EXEC): $(OBJS)

$(OBJ)/%.o: $(SRC)/%.c
	@mkdir -p $(@D)
	$(CC) $(CFLAGS) -c $< -o $@

run: $(EXEC)
	./$(EXEC)

watch:
	find $(SRC) -type f | entr -c make run

clean:
	$(RM) -r $(EXEC) $(OBJ)

.PHONY: all run watch clean
```

If this looks a bit intimidating, not to worry. We'll literally start from zero with
only a `main.c` file and build it up step by step, to multiple `.c` and `.h` files in a
proper project setup with subdirectories.


## Level 0 - Nothing

Literally no `Makefile` at all, so this one doesn't count. But even without a
`Makefile`, we can already start using `make` because it has some sensible default
rules.

So without a `Makefile`, our project directory contains only a single file:

```
└── main.c
```

Before we knew about `make`, we would compile it into a `main` executable like this:

```console title="Terminal"
% cc main.c -o main
```

But with `make`, we can simply run `make main` to do the same:

```console title="Terminal"
% make main
cc     main.c   -o main
```

That output on the last line shows the command that `make` runs for us.

It compiles `main.c` into an executable called `main` which we can run to verify it's
all working:

```console title="Terminal"
% ./main
hello world
```

And that works, but how did `make` know what to do without a `Makefile`?

There are some default pattern matching rules, and `make` magically figures it out.

You don't need to understand this right now, but the rule that applies here looks like
this:

```makefile
%: %.c
	$(LINK.c) $^ $(LOADLIBES) $(LDLIBS) -o $@
```

The `%` picks up the target we want to make, `main` in this case. The `%.c` means it has
a prerequisite of `main.c` where the `%` is the pattern. We happen to have a `main.c`
that's why this works. Then the actual "recipe" for making it is a bunch of variables
that ends up running `cc     main.c   -o main`.

You can see all the implicit rules and default variables with `make -p` if you're
curious.

If your file would be called `program.c` instead, you can run `make program`, and it
spits out the file `program` as the executable.

Making without a `Makefile` is a bit of a party trick, so would I ever use this in
practice? In fact, yes. Every time I quickly whip up a `main.c` to test something, all I
have to do is type `make main` and it's compiled.

What if you want to change the compiler, or add flags? No problem. The default behaviour
of `make` is to compile with whatever is set in the `CC` environment variable, and it
uses the flags from `CFLAGS`.

So if you want to compile with `gcc` instead of `cc`, you can run it like this:

```console title="Terminal"
% CC=gcc make main
gcc     main.c   -o main
```
Adding flags can be done with variable `CFLAGS`:

```console title="Terminal"
% CC=gcc CFLAGS="-Wall -Wextra" make main
gcc -Wall -Wextra    main.c   -o main
```

But at this point it's easier to just use a `Makefile`. So let's check out the next
level.


## Level 1 - Bare minimum

Now we actually write a `Makefile`, the configuration for `make`. For our "bare minimum"
level I want to add three features:

1. Automatically run after compiling
2. Configure compile flags
3. Cleanup to get back to the initial state

The filename is literally `Makefile` so our project directory looks like:

```
├── Makefile
└── main.c
```

A filename of `makefile` also works, but `Makefile` is the convention I'm sticking to.

A `Makefile` mainly consists of a bunch of *rules*. This is what a rule looks like:

```makefile
target: prerequisites
	recipe
```

So we have a `target` that's typically a file, like `main`. It can have prerequisites
which are typically other files, but can also be other non-file targets. And finally the
`recipe` which is the command to build the `target`, like a `cc` compile command.

To automatically run our program, feature 1, I'm going to add a target called `run`,
with a prerequisite `main` because we need the main executable to run it. And the action
of running it is just calling `./main`.

```makefile title="Makefile" linenums="1"
run: main
	./main
```

Now we can run `make run`, and this is what happens:

```console title="Terminal"
% make run
cc     main.c   -o main
./main
hello world
```

First it gets compiled, then it runs main. Why does `make` know to compile it? Because
we said that `main` is a prerequisite of `run`. So it will try to `make main` first,
before running it. And since `make main` already worked without a `Makefile`, this still
works.

But even better, when we run it a second time:

```console title="Terminal"
% make run
./main
hello world
```

Now it only runs `main`, without compiling. Why? Because `make` is smart enough to look
at the prerequisites of our `run` target, `main`. And since it already exists, it's not
going to "make" it again.

We know that the targets in a `Makefile` are usually files, but `run` is not supposed to
be a file. What if there is a file in our project directory that's literally called
`run`? Let's see what happens:

```console title="Terminal"
% make main
cc     main.c   -o main
% touch run
% make run
make: `run' is up to date.
```

Now `make run` doesn't do anything, because the target `run` is "up to date". That
happens because the target file `run` is newer than the prerequisite file `main`.

To tell make that our `run` target is not really referencing a file, we can mark it with
`.PHONY` like so:

```makefile title="Makefile" linenums="1" hl_lines="4"
run: main
	./main

.PHONY: run
```

Now `make run` works again, regardless of our accidental `run` file:

```console title="Terminal"
% make run
./main
hello world
```

Even though we probably never have a `run` file in the root of our project directory,
it's good practice to mark all the non-file targets with `.PHONY` to clarify intent.

Feature 2 is adding custom compiler flags, easy:

```makefile title="Makefile" linenums="1" hl_lines="1"
CFLAGS = -Wall -Werror -pedantic

run: main
	./main

.PHONY: run
```

That's all. Because we're using the default rule to make `main`, the flags will be
picked up automatically:

```console title="Terminal"
% make main
cc -Wall -Werror -pedantic    main.c   -o main
```

Feature 3 is adding a cleanup shortcut to undo everything. I'll call it `clean` and you
see this in 9 out of 10 `Makefile`s so we're just sticking to the convention. This
target is, like `run` not supposed to be a file, so we mark it as `.PHONY`, and all I
want it to do is remove our `main` executable:

```makefile title="Makefile" linenums="1" hl_lines="6-7 9"
CFLAGS = -Wall -Werror -pedantic

run: main
	./main

clean:
	rm main

.PHONY: run clean
```

So the target is `clean`, it has no prerequisites, and all it does is run `rm main`:

```console title="Terminal"
% make clean
rm main
```
But what if we run `make clean` and `main` doesn't exist?

```console title="Terminal"
% make clean
rm main
rm: main: No such file or directory
make: *** [clean] Error 1
```

That's an error. It doesn't really matter, but for good measure we can change the recipe
to `rm -f main` or use the `$(RM)` variable that `make` has for us:

```makefile title="Makefile" linenums="1" hl_lines="7"
CFLAGS = -Wall -Werror -pedantic

run: main
	./main

clean:
	$(RM) main

.PHONY: run clean
```

Now `make clean` runs without errors, even if there is nothing to clean:

```console title="Terminal"
% make clean
rm -f main
```

Before we go to the next level, I want to add one finishing touch here to change the
behaviour of running just `make` without anything else.

When you have a `Makefile`, running `make` will run the first rule specified in the
file, which is `run` in our case.

That's a bit confusing. I want to run the program with `make run`, but when I type
`make`, it makes more sense to only compile (make) it, without running it.

A common pattern to achieve this is using an `all` target at the top of the `Makefile`:

```makefile title="Makefile" linenums="1" hl_lines="3 11"
CFLAGS = -Wall -Werror -pedantic

all: main

run: main
	./main

clean:
	$(RM) main

.PHONY: all run clean
```

We give it a prerequisite of `main` just like we did for `run`, so running it will make
sure that `main.c` is compiled into `main`. But then the recipe is empty, so it doesn't
do anything else:

```console title="Terminal"
% make
cc -Wall -Werror -pedantic    main.c   -o main
```

It just "makes" our program, which is the most intuitive thing to do after typing `make`
(or `make all`). And again, `all` is not referring to a file, so it's added to the
`.PHONY` list.


## Level 2 - Immediate feedback

For me, programming is more productive and fun with a tight feedback loop. So when I
make an edit, I want it to instantly compile and run (or crash).

To do this, we can use a "file watcher" utility. I always use
[`entr`](https://github.com/eradman/entr) for this, and set it up as a new rule in
the `Makefile`.

So let's add a `watch` rule to the `Makefile`, because it "watches" our source files for
changes:

```makefile title="Makefile" linenums="1" hl_lines="8-9 14"
CFLAGS = -Wall -Werror -pedantic

all: main

run: main
	./main

watch:
	ls *.c | entr make run

clean:
	$(RM) main

.PHONY: all run watch clean
```

This is what happens when we run `make watch`:

```console title="Terminal"
% make watch
ls *.c | entr make run
cc -Wall -Werror -pedantic    main.c   -o main
./main
hello world
```

The first part, `ls *.c` just lists out all `.c` files in our project directory. All we
have is `main.c` for now.

Then it pipes that list of files to `entr`, which starts watching the file names that
got passed in. When a file changes, it runs the command `make run` which compiles
and runs our `main` executable.

After running `make watch`, it stays "active", waiting for changes. So if we edit
`main.c` and add some punctuation, we instantly see this:

```console title="Terminal" hl_lines="6-8"
% make watch
ls *.c | entr make run
cc -Wall -Werror -pedantic    main.c   -o main
./main
hello world
cc -Wall -Werror -pedantic    main.c   -o main
./main
Hello, world!
```

Which is super useful. One thing I usually like to pass to `entr` is the `-c` flag which
clears the screen before it updates:

```makefile title="Makefile" linenums="1" hl_lines="9"
CFLAGS = -Wall -Werror -pedantic

all: main

run: main
	./main

watch:
	ls *.c | entr -c make run

clean:
	$(RM) main

.PHONY: all run watch clean
```

This prevents the terminal from cluttering up too much.

Now, whenever we mess up, there is instant feedback. Like a subtle slap on the wrist
that instantly catches errors and bugs.

It also allows for faster experimentation, just try something, hit save, and the
instant compile + run shows you the result.

Also good to know when using `entr`: Hitting <kbd>Space</kbd> re-runs the command.
Hitting <kbd>Q</kbd> will quit.


## Level 3 - Compiling multiple files

So far we've just been using `main.c` as our source file. This is great for quick tools
or testing some new concept. But most projects are organized across multiple files.

Let's say I want to implement some tools for generating random numbers. I have an
`rng.h` header file, and an implementation in `rng.c`.

To keep it simple, I'm still storing everything in the root of our project:

```
├── Makefile
├── main.c
├── rng.c
└── rng.h
```

Our `main.c` file now has an `#!c #include "rng.h"`.

We could compile this by hand like so:

```console title="Terminal"
% cc main.c rng.c -o main
```
Integrating this into the `Makefile` looks like this:

```makefile title="Makefile" linenums="1" hl_lines="5"
CFLAGS = -Wall -Werror -pedantic

all: main

main: main.c rng.c

run: main
	./main

watch:
	ls *.c | entr -c make run

clean:
	$(RM) main

.PHONY: all run watch clean
```

All we did was specify our target `main` and give it the prerequisites `main.c` and
`rng.c`. We don't give it a recipe, because we can still rely on the implicit recipe
that `make` comes with by default. So this now works:

```console title="Terminal"
% make run
cc -Wall -Werror -pedantic    main.c rng.c   -o main
./main
random float: 0.633477
```
But there is a way to simplify this even more. We don't need to write out the `main.c`
prerequisite, because that's also implied by `make` already. So the more compact version
of the rule looks like this:

```makefile title="Makefile" linenums="1" hl_lines="5"
CFLAGS = -Wall -Werror -pedantic

all: main

main: rng.c

run: main
	./main

watch:
	ls *.c | entr -c make run

clean:
	$(RM) main

.PHONY: all run watch clean
```

And everything still works:

```console title="Terminal"
% make run
cc -Wall -Werror -pedantic    main.c rng.c   -o main
./main
random float: 0.503928
```

## Level 4 - Source directory

Let's take the first step into organizing our project a bit more, by moving our source
code into a `src` directory:

```
├── Makefile
└── src
    ├── main.c
    ├── rng.c
    └── rng.h
```

That breaks our build, because `make` can't find our source files anymore:

```console title="Terminal"
% make run
make: *** No rule to make target `rng.c', needed by `main'.  Stop.
```

Fixing this in our `Makefile` is surprisingly simple. We just have to tell it about the
new `src` directory by adding it to the `VPATH` variable:

```makefile title="Makefile" linenums="1" hl_lines="3 13"
CFLAGS = -Wall -Werror -pedantic

VPATH = src

all: main

main: rng.c

run: main
	./main

watch:
	ls src/*.c | entr -c make run

clean:
	$(RM) main

.PHONY: all run watch clean
```

On line 13 we're also fixing our `watch` rule and let it know about the new `src`
directory.

And that fixes the build:

```console title="Terminal"
% make run
cc -Wall -Werror -pedantic    src/main.c src/rng.c   -o main
./main
random float: 0.621248
```

We're starting to see a bit of repetition in our `Makefile`, so let's take a moment
to add some variables to DRY things up:

```makefile title="Makefile" linenums="1" hl_lines="3-4 6 8 10 12 13 16 19"
CFLAGS = -Wall -Werror -pedantic

EXEC = main
SRC = src

VPATH = $(SRC)

all: $(EXEC)

$(EXEC): rng.c

run: $(EXEC)
	./$(EXEC)

watch:
	ls $(SRC)/*.c | entr -c make run

clean:
	$(RM) $(EXEC)

.PHONY: all run watch clean
```

We have an `EXEC` variable for our final executable. If we ever need to change this
name, we can do it in one place. Same for our source code directory, stored in `SRC`.

We've already seen the syntax for referencing a `make` variable before when we used
`#!makefile $(RM)`, and we use it to reference `EXEC` and `SRC` as well.


## Level 5 - Separate compilation

Right now we're taking all our `.c` source files, and compiling them in a single
command. For this toy example that's totally fine and probably the fastest way, but for
larger projects it could make sense to split this into multiple steps.

This way, when you make an edit to one source file, you only have to recompile that
source file, and then link all compiled assets together, instead of compiling all source
files on every edit.

Manually, you can compile your `.c` files into object `.o` files, and then link them to
get the final executable:

```console title="Terminal"
cc main.c -c -o main.o
cc rng.c -c -o rng.o
cc main.o rng.o -o main
```

It's also possible to only compile the `rng` library into an `.o` file, and then link
that in while compiling `main.c`:

```console title="Terminal"
cc rng.c -c -o rng.o
cc main.c rng.o -o main
```

Let's see what that would look like in our `Makefile`. There is one super simple
tweak we can make:

```makefile title="Makefile" linenums="1" hl_lines="10"
CFLAGS = -Wall -Werror -pedantic

EXEC = main
SRC = src

VPATH = $(SRC)

all: $(EXEC)

$(EXEC): rng.o

run: $(EXEC)
	./$(EXEC)

watch:
	ls $(SRC)/*.c | entr -c make run

clean:
	$(RM) $(EXEC)

.PHONY: all run watch clean
```

It's almost too small to spot, but we've changed `rng.c` to `rng.o`. So we're telling
`make` our `main` executable doesn't depend on `rng.c` anymore, but `rng.o`.

And `make` happens to know how to compile `.c` files into `.o` files by using another
standard pattern matching rule. So this works perfectly:

```console title="Terminal"
% make run
cc -Wall -Werror -pedantic   -c -o rng.o src/rng.c
cc -Wall -Werror -pedantic    src/main.c rng.o   -o main
./main
random float: 0.143407
```

We went from a single `cc` command to two. So if we now make an edit to `main.c` to
change the message, and run `make run` again, it will skip compiling `rng.c` because
it's `.o` file is already up to date:

```console title="Terminal"
% make run
cc -Wall -Werror -pedantic    src/main.c rng.o   -o main
./main
the chance is: 0.226574
```

For a project with two `.c` files and less than 20 lines of code, this sort of
optimization is kind of silly over-engineering. But as the project grows it starts to
make sense.

You might have noticed that we have an `rng.o` file sitting in our project directory
now:

``` hl_lines="3"
├── Makefile
├── main
├── rng.o
└── src
    ├── main.c
    ├── rng.c
    └── rng.h
```

This allows us to avoid recompiling the `rng` library, but when we run `make clean` we
should clean it up:

```makefile title="Makefile" linenums="1" hl_lines="19"
CFLAGS = -Wall -Werror -pedantic

EXEC = main
SRC = src

VPATH = $(SRC)

all: $(EXEC)

$(EXEC): rng.o

run: $(EXEC)
	./$(EXEC)

watch:
	ls $(SRC)/*.c | entr -c make run

clean:
	$(RM) $(EXEC) *.o

.PHONY: all run watch clean
```

In case we're adding more than one library, we'll use `*.o` to remove all object files
on cleanup.


## Level 6 - Detect source files

Our `Makefile` is in great shape, but one thing I don't like is that every time we
decide to write a new library in our project, we have to also remember to edit the
`Makefile`. Wouldn't it be great if `make` could dynamically detect all source files?

To make this work, we're going to use some new Makefile features like `wildcard` and
`patsubst` to find files using pattern matching.

We're also going to reorganize our source files one more time to make a better
distinction between entrypoint `.c` files and library `.c` files.

I've added a new sample library called `vec`, to show how our build system can
automatically detect multiple libraries.

The new project structure looks like this:

```
├── Makefile
└── src
    ├── main.c
    ├── rng
    │   ├── rng.c
    │   └── rng.h
    └── vec
        ├── vec.c
        └── vec.h
```

So the convention is: Entrypoints that turn into an executable directly under `src`, and
all libraries in a sub-directory of `src`. By sticking to this rule, we can configure
the `Makefile` to detect these files properly.

We also have to change any `#!c #include "rng.h"` in our `main.c` to
`#!c #include "rng/rng.h"` after this reorganisation.

Our `.o` files can be organized in their own dedicated directory `obj` to reduce clutter
in the root of the project.

Our first step will be to detect all library source files based on a wildcard pattern.
To do that, we use the `wildcard` function:

```makefile
LIBS = $(wildcard $(SRC)/*/*.c)
```

This function just expands all files that match the wildcard. So in our case, it will
match `src/rng/rng.c` and `src/vec/vec.c`.

Next, we use the function `patsubst` to derive file names of the `.o` files we want to
keep track of:

```makefile
OBJ = obj
OBJS = $(patsubst $(SRC)/%.c,$(OBJ)/%.o,$(LIBS))
```

This one is a bit more complicated: It takes three parameters. The first one is the
pattern to match, the second one is the new pattern to turn it into, and the third is
a list of paths to do this with.

So `OBJS` is created out of `LIBS`, and transforms them like this:

```
src/rng/rng.c -> obj/rng/rng.o
src/vec/vec.c -> obj/vec/vec.o
```

Now we're going to use `OBJS` as the prerequisites of our `EXEC` target:

```makefile
$(EXEC): $(OBJS)
```

Instead of listing the `.o` files of each library manually, we now have the `#!makefile
$(OBJS)` variable that dynamically updates.

This is what the second rule looks like:

```makefile
$(OBJ)/%.o: $(SRC)/%.c
	mkdir -p $(@D)
	$(CC) $(CFLAGS) -c $< -o $@
```

There's a lot more going on. The target is dynamic due to the `%`, so it matches all
`.o` files in the `obj` directory and dynamically creates a corresponding `.c`
prerequisite for each one in the `src` directory. So `obj/rng/rng.o` will match with
`src/rng/rng.c` for example.

The recipe of this rule has two commands. The first one just ensures that the directory
of the target exists. The variable `#!makefile $(@D)` magically references the directory
of the target.

The second command is just compiling the `.c` file into the `.o` file. Again, it uses
two magic variables: `#!makefile $<` to match the first prerequisite, and
`#!makefile $@` to match the target.

Our `watch` rule has to look for source files recursively in `src`, so we can use `find`
for this:

```makefile
watch:
	find $(SRC) -type f | entr -c make run
```

Our `clean` rule also has to be updated to match the new directory structure:

```makefile
clean:
	$(RM) -r $(EXEC) $(OBJ)
```
We're removing the executable, and the entire `obj` directory. Because we have the
`mkdir -p` recipe, we make sure we always rebuild these `obj` directories when needed.

If we add all of this to our `Makefile`, we get this:

```makefile title="Makefile" linenums="1" hl_lines="5 7-8 14 16-18 24 27"
CFLAGS = -Wall -Werror -pedantic

EXEC = main
SRC = src
OBJ = obj

LIBS = $(wildcard $(SRC)/*/*.c)
OBJS = $(patsubst $(SRC)/%.c,$(OBJ)/%.o,$(LIBS))

VPATH = $(SRC)

all: $(EXEC)

$(EXEC): $(OBJS)

$(OBJ)/%.o: $(SRC)/%.c
	mkdir -p $(@D)
	$(CC) $(CFLAGS) -c $< -o $@

run: $(EXEC)
	./$(EXEC)

watch:
	find $(SRC) -type f | entr -c make run

clean:
	$(RM) -r $(EXEC) $(OBJ)

.PHONY: all run watch clean
```

And we can run `make` to see what happens:

```console title="Terminal"
% make
mkdir -p obj/rng
cc -Wall -Werror -pedantic -c src/rng/rng.c -o obj/rng/rng.o
mkdir -p obj/vec
cc -Wall -Werror -pedantic -c src/vec/vec.c -o obj/vec/vec.o
cc -Wall -Werror -pedantic    src/main.c obj/rng/rng.o obj/vec/vec.o   -o main
```

And it seems to work. First we make sure we have an `obj/rng` directory. Then we're
compiling `src/rng/rng.c` into `obj/rng/rng.o`.

We do the same thing for `obj/vec/vec.o`.

And finally we compile `main.c` and link `rng.o` and `vec.o` into the final executable
`main`.

After running `make`, the project directory looks like this:

```
├── Makefile
├── main
├── obj
│   ├── rng
│   │   └── rng.o
│   └── vec
│       └── vec.o
└── src
    ├── main.c
    ├── rng
    │   ├── rng.c
    │   └── rng.h
    └── vec
        ├── vec.c
        └── vec.h
```

So everything is working as expected.

One thing I'd like to clean up is those `mkdir` commands. I don't really want to see
this in the `make` output. We can prevent any recipe commands from being printed by
prepending an `@` like this:

```makefile title="Makefile" linenums="1" hl_lines="17"
CFLAGS = -Wall -Werror -pedantic

EXEC = main
SRC = src
OBJ = obj

LIBS = $(wildcard $(SRC)/*/*.c)
OBJS = $(patsubst $(SRC)/%.c,$(OBJ)/%.o,$(LIBS))

VPATH = $(SRC)

all: $(EXEC)

$(EXEC): $(OBJS)

$(OBJ)/%.o: $(SRC)/%.c
	@mkdir -p $(@D)
	$(CC) $(CFLAGS) -c $< -o $@

run: $(EXEC)
	./$(EXEC)

watch:
	find $(SRC) -type f | entr -c make run

clean:
	$(RM) -r $(EXEC) $(OBJ)

.PHONY: all run watch clean
```

Now it looks a bit cleaner:

```console title="Terminal"
% make
cc -Wall -Werror -pedantic -c src/rng/rng.c -o obj/rng/rng.o
cc -Wall -Werror -pedantic -c src/vec/vec.c -o obj/vec/vec.o
cc -Wall -Werror -pedantic    src/main.c obj/rng/rng.o obj/vec/vec.o   -o main
```

And the great thing is: There is no trace of the word `rng` or `vec` anywhere in the
`Makefile`, it's fully dynamic. So if we add more libraries later, they will be
picked up and compiled automatically.
