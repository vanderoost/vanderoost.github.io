---
date: 2024-09-15
authors:
  - daveebbelaar
categories:
  - Tools
  - Quick Tips
description: A quick fix for macOS users
---

# Opening VS Code Workspace Files with Cursor on macOS

I recently switched to Cursor, a new AI-enhanced code editor that's been getting a lot of attention lately. While it's been a great experience so far, there was one small hiccup on macOS with `.code-workspace` files. Here's how I solved it.

<!-- more -->

## Why Cursor?

If you're a developer, you might have noticed Cursor IDE popping up everywhere. It's a fork of VS Code but with added AI capabilities like autocomplete, inline edits, and a composer. After five years with VS Code, I decided to give Cursor a try. The transition was seamless since Cursor is built on top of VS Code, so all my settings, themes, and extensions worked right out of the box.

## The macOS Workspace Issue

One issue I ran into was with opening `.code-workspace` files on macOS. By default, Cursor couldn't open these files directly, which was pretty annoying. Fortunately, there's a straightforward fix.

## How to Make Cursor the Default for Workspace Files

Here's how to make Cursor the default application for `.code-workspace` files:

<div class="annotate" markdown>
1. Locate a `.code-workspace` file in Finder.
2. Right-click on the file and select “Get Info” from the context menu.
3. In the “Get Info” window, look for the “Open with:” section.
4. Click on the selection field and choose "Other".
5. In the Finder selection window, change the setting "Enable" to "All Applications" instead of the default "Recommended Applications"(1)
6. You can now select Cursor from the list.
7. After making the selection, click "Change All..." to make Cursor the default for all your `.code-workspace` files.
</div>
 
 1. This is where you need to change the setting to "All Applications".
    ![Enable All Applications](images/CleanShot%202024-09-15%20at%2012.03.17@2x.png)