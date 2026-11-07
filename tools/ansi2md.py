#!/usr/bin/env python3
"""Turn colored terminal output into {grn}...{res} marks for console blocks.

Reads output with real ANSI escape codes on stdin and prints it with the marks
hooks/console_colors.py understands, ready to paste into a ```console block:

    make test 2>&1 | tools/ansi2md.py | pbcopy

Most programs drop their colors when they see a pipe instead of a terminal.
Running them under script(1) gives them a terminal to write to:

    script -q /dev/null make test | tools/ansi2md.py | pbcopy

Only the six basic foreground colors (and their bright variants) become marks.
Bold, backgrounds and cursor movement are dropped, since a console block has
nowhere to put them. A color still open at the end of a line is closed there
and reopened on the next, because marks cannot span lines.
"""

import re
import sys

COLORS = {
    30 + i: name
    for i, name in enumerate(
        ("blk", "red", "grn", "yel", "blu", "mag", "cyn", "wht"),
    )
}
COLORS |= {code + 60: name for code, name in COLORS.items()}  # bright 90-97

# Every escape sequence. SGR (the m-terminated ones) set colors; the rest move
# the cursor or clear the line and are stripped.
ESCAPE = re.compile(r"\x1b\[(?P<params>[0-9;]*)(?P<cmd>[A-Za-z])")

# hooks/console_colors.py has no mark for these, so they print uncolored.
UNMARKED = {"blk", "wht"}


def convert(line: str, color: str | None) -> tuple[str, str | None]:
    out, pos = [], 0
    if color:
        out.append(f"{{{color}}}")

    for match in ESCAPE.finditer(line):
        out.append(line[pos : match.start()])
        pos = match.end()
        if match.group("cmd") != "m":
            continue

        new = color
        for param in (match.group("params") or "0").split(";"):
            code = int(param or 0)
            if code in (0, 39):
                new = None
            elif code in COLORS:
                new = None if COLORS[code] in UNMARKED else COLORS[code]
        if new != color:
            if color:
                out.append("{res}")
            if new:
                out.append(f"{{{new}}}")
            color = new

    out.append(line[pos:])
    if color:
        out.append("{res}")
    # Drop marks that ended up wrapping nothing, e.g. a reset right after a set.
    text = re.sub(r"\{[a-z]{3}\}\{res\}", "", "".join(out))
    return text, color


def main() -> None:
    color, lines = None, []
    for line in sys.stdin.read().replace("\r\n", "\n").split("\n"):
        text, color = convert(line.replace("\r", ""), color)
        lines.append(text)
    sys.stdout.write("\n".join(lines))


if __name__ == "__main__":
    main()
