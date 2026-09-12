#!/usr/bin/env python3
"""Rewrite a tldraw SVG export so the site's theme drives its colors.

tldraw exports a snapshot of whichever mode the canvas was in: the colors are
baked in as literal hex, so a drawing exported in dark mode stays dark on a
light page. This replaces each baked color with a CSS variable naming the
tldraw palette entry it came from — #40c057 becomes
var(--rvo-draw-light-green, #4cb05e) — so one set of definitions in
extra.css re-themes every drawing on the site at once.

The variables only resolve if the SVG is part of the page's DOM, which is what
hooks/drawings.py is for. An <img src="drawing.svg"> is a separate document
that cannot see the page's CSS, and would fall back to the literal after the
comma.

    tools/tldraw_theme.py convert docs/**/drawing.svg   # rewrite in place
    tools/tldraw_theme.py css                           # print definitions

tldraw-palette.json is lifted verbatim from tldraw's own defaultThemes.ts. To
refresh it after a tldraw release, re-read that file from their repo; the
converter fails on any color it cannot find there, so a palette change shows
up as a failed conversion rather than a drawing that quietly stops theming.
"""

import argparse
import json
import re
import sys
from pathlib import Path

PALETTE = json.loads((Path(__file__).parent / "tldraw-palette.json").read_text())

# Every color literal tldraw writes into an export: "#rgb", "#rrggbb" and the
# wide-gamut "color(display-p3 r g b)" it uses for highlighter strokes.
COLOR = re.compile(
    r'(?P<attr>fill|stroke)="(?P<value>#[0-9a-fA-F]{3,8}|color\([^)]*\))"'
)

# tldraw writes solid and fill identically for every palette entry, so they
# collapse to one variable. The rest keep a suffix. Order is priority: a value
# like dark #f2f2f2 is both black.solid and every color's frameText, and the
# earliest match wins, which is what a drawing (rather than a frame) means.
VARIANTS = [
    ("solid", ""),
    ("fill", ""),
    ("semi", "-semi"),
    ("pattern", "-pattern"),
    ("highlightSrgb", "-highlight"),
    ("highlightP3", "-highlight"),
    ("linedFill", "-lined-fill"),
    ("noteFill", "-note-fill"),
    ("frameFill", "-frame-fill"),
    ("frameStroke", "-frame-stroke"),
    ("frameHeadingFill", "-frame-heading-fill"),
    ("frameHeadingStroke", "-frame-heading-stroke"),
    ("frameText", "-text"),
    ("noteText", "-text"),
]

# The 12 drawing colors. "white" is excluded: it is a fixed sheet color in
# tldraw rather than a palette entry that flips with the theme.
COLORS = [c for c in sorted(PALETTE["light"]) if c != "white"]


def variable(color: str, variant: str) -> str:
    suffix = dict(VARIANTS)[variant]
    return f"--rvo-draw-{color}{suffix}"


def lookup(mode: str) -> dict[str, tuple[str, str]]:
    """Map every literal in one mode back to the palette entry that wrote it."""
    index: dict[str, tuple[str, str]] = {}
    for variant, _ in VARIANTS:
        for color in COLORS:
            value = PALETTE[mode][color][variant].lower()
            index.setdefault(value, (color, variant))
    return index


def detect_mode(svg: str) -> str:
    """Read the mode off the root element tldraw stamps it on."""
    match = re.search(r'data-color-mode="(light|dark)"', svg)
    if not match:
        raise SystemExit(
            "no data-color-mode on the root <svg>: is this a tldraw export?"
        )
    return match.group(1)


def convert(svg: str, path: Path) -> tuple[str, set[str]]:
    # Converting strips the mode attribute, so a second run would otherwise
    # fail detect_mode() rather than reporting the file as already done.
    if "var(--rvo-draw-" in svg:
        return svg, set()

    mode = detect_mode(svg)
    index = lookup(mode)
    used: set[str] = set()
    unknown: set[str] = set()

    def replace(match: re.Match) -> str:
        value = match.group("value")
        entry = index.get(value.lower())
        if entry is None:
            unknown.add(value)
            return match.group(0)
        name = variable(*entry)
        used.add(name)
        # The fallback is the light value, so the file still renders sensibly
        # on its own — opened directly, or if the variables ever go missing.
        fallback = PALETTE["light"][entry[0]][entry[1]]
        return f'{match.group("attr")}="var({name}, {fallback})"'

    converted = COLOR.sub(replace, svg)
    if unknown:
        raise SystemExit(
            f"{path}: not in tldraw's palette: {', '.join(sorted(unknown))}\n"
            "If tldraw has changed its colors, refresh tools/tldraw-palette.json."
        )

    # The export is no longer mode-specific, so drop the attributes that claim
    # it is. Left in place they would be a lie, and tl-theme__dark is a real
    # class that tldraw's own stylesheet would style if it were ever loaded.
    converted = re.sub(r'\sdata-color-mode="(light|dark)"', "", converted, count=1)
    converted = converted.replace(" tl-theme__dark", "").replace(" tl-theme__light", "")
    return converted, used


# Every variable name a converted drawing can reference, back to the palette
# entry behind it, so "css" can define exactly what the drawings on disk use.
def entries() -> dict[str, tuple[str, str]]:
    return {
        variable(color, variant): (color, variant)
        for variant, _ in reversed(VARIANTS)
        for color in COLORS
    }


def emit_css(paths: list[Path]) -> str:
    """The 12 drawing colors, plus any other variant the given files use.

    Highlighter and pattern fills only need defining once something actually
    draws with them, so the common case stays at 12 variables per scheme
    instead of the 150-odd the full palette would produce.
    """
    known = entries()
    extra: set[str] = set()
    for path in paths:
        for name in re.findall(r"var\((--rvo-draw-[a-z-]+)", path.read_text()):
            if name in known and known[name][1] not in ("solid", "fill"):
                extra.add(name)

    wanted = [variable(c, "solid") for c in COLORS] + sorted(extra)
    lines = [
        "/* tldraw drawing colors, lifted from tldraw's own light and dark",
        "   themes so a drawing looks the same here as it does on the canvas.",
        "   Written into exports by tools/tldraw_theme.py; edit the values here",
        "   to restyle every drawing on the site at once. */",
    ]
    for scheme, mode in (("default", "light"), ("slate", "dark")):
        lines.append(f'[data-md-color-scheme="{scheme}"] {{')
        for name in wanted:
            color, variant = known[name]
            lines.append(f"  {name}: {PALETTE[mode][color][variant]};")
        lines.append("}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("convert", help="rewrite exports in place")
    run.add_argument("paths", nargs="+", type=Path)
    show = sub.add_parser("css", help="print the variable definitions")
    show.add_argument("paths", nargs="*", type=Path)

    args = parser.parse_args()
    if args.command == "css":
        print(emit_css(args.paths))
        return 0

    for path in args.paths:
        original = path.read_text()
        converted, used = convert(original, path)
        if converted == original:
            print(f"{path}: already themed, unchanged")
            continue
        path.write_text(converted)
        print(f"{path}: {len(used)} variables -> {', '.join(sorted(used))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
