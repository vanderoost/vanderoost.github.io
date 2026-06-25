---
date: 2024-03-20
authors:
  - daveebbelaar
categories:
  - Tools
  - Python
  - Development
description: A lightning-fast Python package manager that will change how you work
---

# Getting Started with UV: The Ultra-Fast Python Package Manager

If you're tired of slow package installations and complex dependency management in Python, [uv](https://docs.astral.sh/uv/) might be exactly what you need. Written in Rust, uv is a blazing-fast package manager that aims to replace pip, pip-tools, pipx, poetry, and more. Let's dive into why it's awesome and how to get started.

<!-- more -->

## Why UV?

After years of wrestling with different Python package managers, uv caught my attention for a few key reasons:

- It's 10-100x faster than pip
- Single tool to replace multiple package managers
- Universal lockfile support for consistent environments
- Built-in Python version management

## Installation

Getting started with uv is straightforward. Here are the installation methods I recommend for each platform:

### macOS (using Homebrew)
```bash
brew install uv
```

### Linux/macOS (using curl)
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Windows (using PowerShell)
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

## Managing Python Versions

While you probably already have Python installed on your system, uv can manage Python versions for you. Here's how:

```bash
# List available Python versions
uv python list

# Install a specific version
uv python install 3.12

# Use a specific version for your project
uv python pin 3.12
```

## Creating a New Project

Let's create a new project and see uv in action:

```bash
# Create a new project directory
mkdir my-awesome-project
cd my-awesome-project

# Initialize a new project
uv init

# Create and activate a virtual environment
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

This creates a basic project structure with a `pyproject.toml` file, which is similar to package.json for Node.js developers.

## Managing Dependencies

Here's where uv really shines. Let's add some common packages:

```bash
# Add a single package
uv add requests

# Add multiple packages with specific versions
uv add 'fastapi>=0.100.0' pytest

# Add development dependencies
uv add --dev black ruff
```

### Working with requirements.txt

If you're working with an existing project that uses requirements.txt, uv has got you covered:

```bash
# Install from requirements.txt
uv pip install -r requirements.txt

# Generate a requirements.txt from your project
uv pip freeze > requirements.txt
```

## Understanding the Lock File

One of uv's best features is its lockfile system. When you run `uv add` or `uv sync`, it creates/updates a `uv.lock` file that ensures consistent installations across all environments. This is similar to package-lock.json in Node.js or Cargo.lock in Rust.

```bash
# Manually update the lockfile
uv lock

# Sync your environment with the lockfile
uv sync
```

## Daily Usage Tips

Here are some common commands you'll use regularly:

```bash
# Remove a package
uv remove requests

# Update a specific package
uv lock --upgrade-package requests

# Run a Python script in your environment
uv run script.py

# Install a tool globally (like pipx)
uv tool install ruff
```

## Why I Switched to UV

After using uv for several weeks, the speed difference is incredible. What used to take minutes with pip now takes seconds. The unified interface for managing both packages and Python versions has simplified my workflow significantly.

Here's a quick comparison installing a complex package:

```bash
# With pip
time pip install tensorflow  # ~2-3 minutes

# With uv
time uv pip install tensorflow  # ~15-20 seconds
```

## Next Steps

To get the most out of uv, I recommend:

1. Adding `.venv` to your `.gitignore`
2. Committing both `pyproject.toml` and `uv.lock` to version control
3. Using `uv sync` instead of `pip install` to ensure consistent environments

Uv is actively maintained by the team behind Ruff (another amazing Python tool), and it's quickly becoming the go-to package manager in the Python ecosystem. You can find more resources and documentation [here](https://docs.astral.sh/uv/).
