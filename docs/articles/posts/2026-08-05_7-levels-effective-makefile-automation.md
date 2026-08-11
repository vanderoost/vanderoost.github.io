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
description: Learn how to write a full-on Makefile from scratch to automate building C projects.
slug: levels-of-effective-makefile-cheatsheet
---

# The 7 levels of highly effective Makefiles

Rumor has it that all Makefiles in use today were written in a time when dinosaurs
roamed the earth. Nobody *actually* writes new Makefiles anymore, right?

They remain among the most anxiety-inducing files you can find in a codebase. But
in this article, I will walk you through the humbling experience of writing a Makefile
to set up a C build system.

<!-- more -->

If you don't know what I'm talking about, Make is a tool for *making files* based on
certain *rules*. It can be abused to do more, and to automate other terminal
shenanigans. Think of running your tests, deploying, building Docker images, etc.

Once you find yourself running certain commands repeatedly in a codebase, your first
instinct might be to stash them away in some bash script.

This works, but Makefiles give you some extra tech: `make` automatically creates a
dependency graph of all the files you want to "make", and then uses the last
modification timestamps of each file to determine what actually has to be made.

So it's more efficient, and it has some other cool tricks that we'll dive into.

**TL;DR** (spoiler alert): these are the Makefiles we're going to write, one per level:

=== "L1"

	```makefile title="Makefile" linenums="1"
	CFLAGS = -Wall -Wextra

	all: main

	run: main
		./main

	clean:
		$(RM) main

	.PHONY: all run clean
	```

=== "L2"

	```makefile title="Makefile" linenums="1"
	CFLAGS = -Wall -Wextra

	all: main

	run: main
		./main

	watch:
		ls *.c | entr -c make run

	clean:
		$(RM) main

	.PHONY: all run watch clean
	```

=== "L3"

	```makefile title="Makefile" linenums="1"
	CFLAGS = -Wall -Wextra

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

=== "L4"

	```makefile title="Makefile" linenums="1"
	CFLAGS = -Wall -Wextra

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

=== "L5"

	```makefile title="Makefile" linenums="1"
	CFLAGS = -Wall -Wextra

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

=== "L6"

	```makefile title="Makefile" linenums="1"
	CFLAGS = -Wall -Wextra

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

===+ "L7"

	```makefile title="Makefile" linenums="1"
	CFLAGS = -Wall -Wextra

	NAME = main
	BIN = bin
	OBJ = obj
	SRC = src

	EXEC = $(BIN)/$(NAME)

	BIN_SRCS = $(wildcard $(SRC)/*.c)
	LIB_SRCS = $(wildcard $(SRC)/*/*.c)
	ALL_SRCS = $(BIN_SRCS) $(LIB_SRCS)

	BINS = $(patsubst $(SRC)/%.c,$(BIN)/%,$(BIN_SRCS))
	OBJS = $(patsubst $(SRC)/%.c,$(OBJ)/%.o,$(LIB_SRCS))
	DEPS = $(patsubst $(SRC)/%.c,$(OBJ)/%.d,$(ALL_SRCS))

	all: $(BINS)

	$(BINS): $(BIN)/%: $(OBJ)/%.o $(OBJS)
		@mkdir -p $(@D)
		$(CC) $(LDFLAGS) $^ $(LDLIBS) -o $@

	$(OBJ)/%.o: $(SRC)/%.c
		@mkdir -p $(@D)
		$(CC) $(CFLAGS) -MMD -c $< -o $@

	run: $(EXEC)
		$<

	watch:
		find $(SRC) -type f | entr -c make run

	clean:
		$(RM) -r $(BIN) $(OBJ)

	-include $(DEPS)

	.PHONY: all run watch clean
	```

If this looks a bit intimidating, not to worry. We'll start from zero with only a
`main.c` file and build it up step by step, to multiple `.c` and `.h` files in a proper
project setup with subdirectories. I use this post myself as a Makefile cheatsheet.


## Level 0 - Nothing

Literally no `Makefile` at all, so this one doesn't count. But even without a
`Makefile`, we can already start using `make` because it has a bunch of default rules.

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
a prerequisite of `main.c` where the `%` is the pattern. We happen to have a `main.c`,
which is why this works. Then the actual "recipe" for making it is a bunch of variables
that end up running `cc     main.c   -o main`.

You can see all the implicit rules and default variables with `make -p` if you're
curious.

If your file is called `program.c` instead, you can run `make program`, and it
spits out the file `program` as the executable.

Making without a `Makefile` is a bit of a party trick, but would I ever use this in
practice? Actually, yes. Every time I quickly write a `main.c` to test something, all I
have to do is type `make main` and it's compiled.

What if you want to change the compiler, or add flags? No problem. The default behavior
of `make` is to compile with whatever is set in the `CC` environment variable, and it
uses the flags from `CFLAGS`.

So if you want to compile with `gcc` instead of `cc`, you can run it like this:

```console title="Terminal"
% CC=gcc make main
gcc     main.c   -o main
```

Adding flags can be done with the `CFLAGS` variable:

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

The filename is just `Makefile` so our project directory looks like:

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

One thing to watch out for: that indentation before the recipe has to be a literal tab
character. Spaces will get you `Makefile:2: *** missing separator.  Stop.`, which is the
most common way to break a fresh `Makefile`.

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

First it gets compiled, then it runs `./main`. How does `make` know that it needs to
compile? Because we said that `main` is a prerequisite of `run` (i.e. `run` depends on
`main`). So it will try to `make main` first, before running it. And since `make main`
already worked without a `Makefile`, this still works.

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

Even though we'll probably never have a `run` file in the root of our project directory,
it's good practice to mark all the non-file targets with `.PHONY` to clarify intent.

Feature 2 is adding custom compiler flags, easy:

```makefile title="Makefile" linenums="1" hl_lines="1"
CFLAGS = -Wall -Wextra

run: main
	./main

.PHONY: run
```

That's all. Because we're using the default rule to make `main`, the flags will be
picked up automatically:

```console title="Terminal"
% make main
cc -Wall -Wextra    main.c   -o main
```

Feature 3 is adding a cleanup shortcut to undo everything. I'll call it `clean` and you
see this in 9 out of 10 `Makefile`s, so we're just sticking to the convention. This
target is, like `run`, not supposed to be a file, so we mark it as `.PHONY`, and all I
want it to do is remove our `main` executable:

```makefile title="Makefile" linenums="1" hl_lines="6-7 9"
CFLAGS = -Wall -Wextra

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
CFLAGS = -Wall -Wextra

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
behavior of running just `make` without anything else.

When you have a `Makefile`, running `make` will run the first rule specified in the
file, which is `run` in our case.

That's a bit confusing. I want to run the program with `make run`, but when I type
`make`, it makes more sense to only compile (make) it, without running it.

A common pattern to achieve this is using an `all` target at the top of the `Makefile`:

```makefile title="Makefile" linenums="1" hl_lines="3 11"
CFLAGS = -Wall -Wextra

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
cc -Wall -Wextra    main.c   -o main
```

It just "makes" our program, which is the most intuitive thing to do after typing `make`
(or `make all`). And again, `all` is not referring to a file, so it's added to the
`.PHONY` list.


## Level 2 - Immediate feedback

For me, programming is more productive and fun with a tight feedback loop. So when I
make an edit, I want it to instantly compile and run (or crash).

To do this, we can use a "file watcher" utility. I always use
[`entr`](https://github.com/eradman/entr){ target="_blank" rel="noopener" } for this,
and set it up as a new rule in the `Makefile`.

So let's add a `watch` rule to the `Makefile`, because it "watches" our source files for
changes:

```makefile title="Makefile" linenums="1" hl_lines="8-9 14"
CFLAGS = -Wall -Wextra

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
cc -Wall -Wextra    main.c   -o main
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
cc -Wall -Wextra    main.c   -o main
./main
hello world
cc -Wall -Wextra    main.c   -o main
./main
Hello, world!
```

Which is super useful. One thing I usually like to pass to `entr` is the `-c` flag which
clears the screen before it updates:

```makefile title="Makefile" linenums="1" hl_lines="9"
CFLAGS = -Wall -Wextra

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

It also allows for faster experimentation: just try something, hit save, and the
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
CFLAGS = -Wall -Wextra

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
cc -Wall -Wextra    main.c rng.c   -o main
./main
random float: 0.633477
```

But there is a way to simplify this even more. We don't need to write out the `main.c`
prerequisite, because that's also implied by `make` already. So the more compact version
of the rule looks like this:

```makefile title="Makefile" linenums="1" hl_lines="5"
CFLAGS = -Wall -Wextra

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
cc -Wall -Wextra    main.c rng.c   -o main
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
CFLAGS = -Wall -Wextra

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

On line 13 we're also fixing our `watch` rule and letting it know about the new `src`
directory.

And that fixes the build:

```console title="Terminal"
% make run
cc -Wall -Wextra    src/main.c src/rng.c   -o main
./main
random float: 0.621248
```

We're starting to see a bit of repetition in our `Makefile`, so let's take a moment
to add some variables to DRY things up:

```makefile title="Makefile" linenums="1" hl_lines="3-4 6 8 10 12 13 16 19"
CFLAGS = -Wall -Wextra

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
source file, and then link all compiled object files together, instead of compiling all
source files on every edit.

There's a second payoff too: because every `.o` file becomes an independent target with
no dependencies on the others, `make -j` can compile them in parallel across multiple
CPU cores.

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
CFLAGS = -Wall -Wextra

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
cc -Wall -Wextra   -c -o rng.o src/rng.c
cc -Wall -Wextra    src/main.c rng.o   -o main
./main
random float: 0.143407
```

We went from a single `cc` command to two. So if we now make an edit to `main.c` to
change the message, and run `make run` again, it will skip compiling `rng.c` because
its `.o` file is already up to date:

```console title="Terminal"
% make run
cc -Wall -Wextra    src/main.c rng.o   -o main
./main
the chance is: 0.226574
```

For a project with two `.c` files and fewer than 20 lines of code, this sort of
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
CFLAGS = -Wall -Wextra

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

Since we might add more than one library, we'll use `*.o` to remove all object files
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

So the convention is: Entrypoints that turn into an executable go directly under `src`,
and all libraries in a subdirectory of `src`. By sticking to this rule, we can configure
the `Makefile` to detect these files properly.

We also have to change any `#!c #include "rng.h"` in our `main.c` to
`#!c #include "rng/rng.h"` after this reorganization.

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
CFLAGS = -Wall -Wextra

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
cc -Wall -Wextra -c src/rng/rng.c -o obj/rng/rng.o
mkdir -p obj/vec
cc -Wall -Wextra -c src/vec/vec.c -o obj/vec/vec.o
cc -Wall -Wextra    src/main.c obj/rng/rng.o obj/vec/vec.o   -o main
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
CFLAGS = -Wall -Wextra

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
cc -Wall -Wextra -c src/rng/rng.c -o obj/rng/rng.o
cc -Wall -Wextra -c src/vec/vec.c -o obj/vec/vec.o
cc -Wall -Wextra    src/main.c obj/rng/rng.o obj/vec/vec.o   -o main
```

And the great thing is: There is no trace of the word `rng` or `vec` anywhere in the
`Makefile`, it's fully dynamic. So if we add more libraries later, they will be
picked up and compiled automatically.


## Level 7 - Header dependencies

There is one flaw in our current `Makefile`: When you edit a header (`.h`) file, `make`
doesn't know it has to recompile that particular library.

A simple way to test this is just updating the modification timestamp of one of the `.h`
files with `touch` and running `make` again:

```console title="Terminal" hl_lines="5-7"
% make
cc -Wall -Wextra -c src/rng/rng.c -o obj/rng/rng.o
cc -Wall -Wextra -c src/vec/vec.c -o obj/vec/vec.o
cc -Wall -Wextra    src/main.c obj/rng/rng.o obj/vec/vec.o   -o main
% touch src/rng/rng.h
% make
make: Nothing to be done for `all'.
```

It says "Nothing to be done", but we could have completely changed the header file.

This is actually to be expected. We're not mentioning `.h` files in the `Makefile`. All
we do is say that the final executable depends on its corresponding `.c` file, and all
`.o` files. Every `.o` file only depends on its corresponding `.c` file.

Fortunately, compilers and `make` can work together to fix this.

When you compile, say, `main.c` to `main.o`, you can pass the `-MMD` flag to let the
compiler spit out not just the object file `main.o` but also a dependency file `main.d`.

```console title="Terminal"
% cc src/main.c -MMD -c
```

It spits out two files:

``` hl_lines="2-3"
├── Makefile
├── main.d
├── main.o
└── src
    ├── main.c
    ├── rng
    │   ├── rng.c
    │   └── rng.h
    └── vec
        ├── vec.c
        └── vec.h
```

And that `main.d` file is nothing complicated at all, it's just plain text:

```makefile title="main.d"
main.o: src/main.c src/rng/rng.h src/vec/vec.h
```

This looks like a `make` rule. And it specifies that `main.o` depends on `src/main.c`
but also the two header files `src/rng/rng.h` and `src/vec/vec.h`.

The way the compiler "knows" this is by looking at the `main.c` file, which specifies
things like `#!c #include "rng/rng.h"` and `#!c #include "vec/vec.h"`.

The `-MMD` flag actually has a few variations. Plain `-M` prints the dependency list to
stdout and doesn't compile anything. `-MD` writes it to a `.d` file *and* compiles as
usual. And `-MMD` does the same as `-MD`, but leaves out system headers. So that's the
one we want, system headers are irrelevant in this case since we just want to know which
files to recompile after we change one of our own header files.

So now we want take those `.d` files, and treat them like rules in our Makefile. And
guess what, we can *include* other files in our `Makefile` using the (you guessed it)
`include`

I'd also like to make the final executable files a bit more flexible, allowing multiple
final executables. And I want to store them in a subdirectory called `bin`.

So this is the first thing I want to add:

```makefile title="Makefile"
NAME = main
BIN = bin
OBJ = obj
SRC = src

EXEC = $(BIN)/$(NAME)
```

Instead of specifying the `#!makefile EXEC` directly, we derive it from `#!makefile
$(BIN)` and `#!makefile $(NAME)`. The `main` executable will now be located at
`bin/main`.

Instead of only keeping track of the library `.c` files, I want to keep track of the
entrypoint `.c` files as well in a variable:

```makefile title="Makefile"
BIN_SRCS = $(wildcard $(SRC)/*.c)
LIB_SRCS = $(wildcard $(SRC)/*/*.c)
```

We can now distinguish between the entrypoint source files with `#!makefile
$(BIN_SRCS)`, and library source files with `#!makefile $(LIB_SRCS)`.

Now we have to modify the `patsubst` line, and we'll add another one:

```makefile title="Makefile"
BINS = $(patsubst $(SRC)/%.c,$(BIN)/%,$(BIN_SRCS))
OBJS = $(patsubst $(SRC)/%.c,$(OBJ)/%.o,$(LIB_SRCS))
```

What's happening here with `BINS` is pretty much: Take all `BIN_SRCS` (only
`src/main.c`) and substitute pattern `src/%.c` to `bin/%`. So `src/main.c` becomes
`bin/main`.

Similar for `OBJS`: Take all `LIB_SRCS` (for example `src/vec/vec.c`) and substitute
pattern `src/%.c` to `obj/%.o`. So now the `%` spans multiple directory levels. So
`src/vec/vec.c` becomes `obj/vec/vec.o` because `%` matches `vec/vec`.

With these variables we can create some `make` rules.

First of all, the `all` rule can now mean: Build all `BINS`:

```makefile title="Makefile"
all: $(BINS)
```

There is currently only one file, `src/main.c`, but if we add more `.c` files directly
under `src` they will be considered entrypoints and they will be compiled to binaries.

Because we're explicitly listing our source files like this, we don't have to specify
`#!makefile VPATH = $(SRC)` anymore.

Now we're going to be a bit more explicit about how to link all `.o` files into the
final binary.

Previously, we were relying heavily on the implicit rules that `make` comes with. But
now we've customized things enough such that we have to spell it out:

```makefile title="Makefile"
$(BINS): $(BIN)/%: $(OBJ)/%.o $(OBJS)
	@mkdir -p $(@D)
	$(CC) $^ -o $@
```

This is some new exotic syntax we haven't seen before, called a *static pattern rule*.
We have:

```makefile
targets: target-pattern: prerequisites
```

This allows us to explicitly spell out which exact target files we're gonna make, based
on variable `#!makefile $(BINS)`. Each target is then matched against the
*target-pattern* to extract a part of the target name (called the *stem*). This stem is
substituted into each of the prerequisites that have a pattern (like `#!makefile
$(OBJ)/%.o`) to get the prerequisite names.

For example: target `bin/main`, matched with `bin/%` creates stem `main`. Substitute
stem `main` into pattern `obj/%.o` creates prerequisite `obj/main.o`.

The recipe of this rule should look familiar. Just making sure the target's directory
exists, and then linking all the `.o` files into the final binary executable.

Since we now store everything we make in either the `bin` or `obj` directories, we can
update the `clean` rule to just remove those directories entirely:

```makefile
clean:
	$(RM) -r $(BIN) $(OBJ)
```

The full Makefile now looks like this:

```makefile title="Makefile" linenums="1" hl_lines="3-4 8 10-11 13-14 16 18-20 33"
CFLAGS = -Wall -Wextra

NAME = main
BIN = bin
OBJ = obj
SRC = src

EXEC = $(BIN)/$(NAME)

BIN_SRCS = $(wildcard $(SRC)/*.c)
LIB_SRCS = $(wildcard $(SRC)/*/*.c)

BINS = $(patsubst $(SRC)/%.c,$(BIN)/%,$(BIN_SRCS))
OBJS = $(patsubst $(SRC)/%.c,$(OBJ)/%.o,$(LIB_SRCS))

all: $(BINS)

$(BINS): $(BIN)/%: $(OBJ)/%.o $(OBJS)
	@mkdir -p $(@D)
	$(CC) $^ -o $@

$(OBJ)/%.o: $(SRC)/%.c
	@mkdir -p $(@D)
	$(CC) $(CFLAGS) -c $< -o $@

run: $(EXEC)
	./$(EXEC)

watch:
	find $(SRC) -type f | entr -c make run

clean:
	$(RM) -r $(BIN) $(OBJ)

.PHONY: all run watch clean
```

Running make works as expected:

```console title="Terminal"
% make
cc -Wall -Wextra -c src/main.c -o obj/main.o
cc -Wall -Wextra -c src/rng/rng.c -o obj/rng/rng.o
cc -Wall -Wextra -c src/vec/vec.c -o obj/vec/vec.o
cc obj/main.o obj/rng/rng.o obj/vec/vec.o -o bin/main
```

First we're compiling the three source files to object files. Then we link them together
into the final executable. But what about the `.d` files?

We haven't done anything about them, *yet*. We just needed this foundation to be able to
pattern match all files. Let's add the final pieces.

We will create a `.d` file for every `.c` file, so let's make a list of all `.c` files
called `ALL_SRCS`:

```makefile
ALL_SRCS = $(BIN_SRCS) $(LIB_SRCS)
```

That's pretty simple, just concatenating the `#!makefile $(BIN_SRCS)` with the
`#!makefile $(LIB_SRCS)`.

Now we use those for another `patsubst` to get a list of `.d` files that we'll store in
`DEPS`:

```makefile
DEPS = $(patsubst $(SRC)/%.c,$(OBJ)/%.d,$(ALL_SRCS))
```

The substitution is exactly the same as the one we have for the `.o` files, except we
change the extension to `.d`. This is because the dependency files will be placed next
to their corresponding object files under the `obj` directory.

Now we need to tell the compiler to actually create those `.d` files. Specifying the
list doesn't do anything (it just helps us import them later).

All we need to do is add the `-MMD` flag to our `.o` compilation rule:

```makefile hl_lines="3"
$(OBJ)/%.o: $(SRC)/%.c
	@mkdir -p $(@D)
	$(CC) $(CFLAGS) -MMD -c $< -o $@
```

Now we're creating the `.d` files. You can see it by running make and checking the `obj`
directory:

``` hl_lines="5 8 11"
├── Makefile
├── bin
│   └── main
├── obj
│   ├── main.d
│   ├── main.o
│   ├── rng
│   │   ├── rng.d
│   │   └── rng.o
│   └── vec
│       ├── vec.d
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

Now we can include them into the Makefile with this syntax:

```makefile
-include $(DEPS)
```

And that's why we created that `#!makefile $(DEPS)` variable.

We're using `-include` here instead of `include`. This is so that when one of the `.d`
files doesn't exist, it's silently ignored. If you use `include`, you might encounter
something like this:

```console title="Terminal"
% make
Makefile:37: obj/main.d: No such file or directory
Makefile:37: obj/rng/rng.d: No such file or directory
Makefile:37: obj/vec/vec.d: No such file or directory
make: *** No rule to make target `obj/vec/vec.d'.  Stop.
```

And now, lo and behold, we can make everything with `make`:

```console title="Terminal"
% make
cc -Wall -Wextra -MMD -c src/main.c -o obj/main.o
cc -Wall -Wextra -MMD -c src/rng/rng.c -o obj/rng/rng.o
cc -Wall -Wextra -MMD -c src/vec/vec.c -o obj/vec/vec.o
cc obj/main.o obj/rng/rng.o obj/vec/vec.o -o bin/main
```

And when we modify one of the header files, `make` knows we need to recompile:

```console title="Terminal"
% touch src/rng/rng.h
% make
cc -Wall -Wextra -MMD -c src/main.c -o obj/main.o
cc -Wall -Wextra -MMD -c src/rng/rng.c -o obj/rng/rng.o
cc obj/main.o obj/rng/rng.o obj/vec/vec.o -o bin/main
```

It recompiled `src/main.c` and `src/rng/rng.c` because they both include
`src/rng/rng.h`.

Our `watch` rule also works properly now. It was already running `make run` on a change
of any file inside the `src` directory, so that was already working. But now, when a
`.h` file is the one that's being edited, it will trigger `entr` and properly run a
recompile.

A few final tweaks before we sign off.

If your build needs linker flags, the convention is to split them across two variables.
`LDFLAGS` holds linker options like `-L/opt/lib` and goes *before* the object files.
`LDLIBS` holds the libraries themselves, like `-lm`, and goes *after* them, because the
linker resolves symbols in the order it sees them. That's the same ordering `make` uses
in its own implicit link rule:

```makefile
$(BINS): $(BIN)/%: $(OBJ)/%.o $(OBJS)
	@mkdir -p $(@D)
	$(CC) $(LDFLAGS) $^ $(LDLIBS) -o $@
```

We can simplify our `run` target:

```makefile
run: $(EXEC)
	$<
```

This is very optional, but the magic variable `$<` refers to the first prerequisite,
which is `$(EXEC)`, which is `bin/main`. So `bin/main` is executed as a command, which
runs the main executable.

---

And that's it. We've finished our Makefile!

```makefile title="Makefile" linenums="1" hl_lines="12 16 22 26 29 37"
CFLAGS = -Wall -Wextra

NAME = main
BIN = bin
OBJ = obj
SRC = src

EXEC = $(BIN)/$(NAME)

BIN_SRCS = $(wildcard $(SRC)/*.c)
LIB_SRCS = $(wildcard $(SRC)/*/*.c)
ALL_SRCS = $(BIN_SRCS) $(LIB_SRCS)

BINS = $(patsubst $(SRC)/%.c,$(BIN)/%,$(BIN_SRCS))
OBJS = $(patsubst $(SRC)/%.c,$(OBJ)/%.o,$(LIB_SRCS))
DEPS = $(patsubst $(SRC)/%.c,$(OBJ)/%.d,$(ALL_SRCS))

all: $(BINS)

$(BINS): $(BIN)/%: $(OBJ)/%.o $(OBJS)
	@mkdir -p $(@D)
	$(CC) $(LDFLAGS) $^ $(LDLIBS) -o $@

$(OBJ)/%.o: $(SRC)/%.c
	@mkdir -p $(@D)
	$(CC) $(CFLAGS) -MMD -c $< -o $@

run: $(EXEC)
	$<

watch:
	find $(SRC) -type f | entr -c make run

clean:
	$(RM) -r $(BIN) $(OBJ)

-include $(DEPS)

.PHONY: all run watch clean
```

We can now:

- Automatically compile everything with `make`
- Compile and run with `make run`
- Recompile and run on edits with `make watch`
- Clean up our mess with `make clean`

And the Makefile automatically detects our source files.

Thanks for reading. I hope this gives you the courage to go out into your codebase, whip
up a new Makefile from scratch, and automate some of those repetitive commands.
