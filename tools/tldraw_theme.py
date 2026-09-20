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
import hashlib
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


# The standalone copy is flattened to literal sRGB on an opaque background,
# and deliberately does not theme itself. The temptation is to carry both
# palettes in an internal <style> and let prefers-color-scheme pick, since an
# SVG loaded through <img> does get its own stylesheet. Two things kill that.
# dev.to rasterizes the file server side, where there is no reader to ask, so
# the light palette would win anyway. And cairosvg -- the rasterizer this very
# project already depends on -- cannot parse var() at all and dies on it,
# which is a fair warning about the renderers on the other end of a
# cross-post.
#
# So: light palette, painted over white. A tldraw export is transparent with
# near-black strokes, which on dev.to's dark theme is a drawing nobody can
# see; an opaque background reads correctly on any page, the way a screenshot
# does.
BACKGROUND = "#ffffff"

# Breathing room around the drawing. Harmless on the site, where the drawing
# is inlined over the page background and the stylesheet handles spacing, and
# necessary here: once there is an opaque panel behind it, a stroke that runs
# to the edge of the canvas looks like it has been cropped.
PADDING = 0.04

VIEWBOX = re.compile(
    r'viewBox="\s*(-?[\d.]+)[\s,]+(-?[\d.]+)[\s,]+(-?[\d.]+)[\s,]+(-?[\d.]+)\s*"'
)
DIMENSION = re.compile(r'\b(width|height)="([\d.]+)"')

VAR = "var(--rvo-draw-"

# Bumped whenever standalone() starts producing a different picture from the
# same drawing. The published filename is a hash of the source file, which is
# what makes an edited drawing a new URL -- but a change in here is invisible
# to that, and platforms cache hard enough that they would go on serving the
# old rendering forever. dev.to had already re-hosted a copy of one of these
# on its own S3 by the time the colors were fixed.
RENDER = 2


def published_name(source: Path) -> str:
    """What a drawing is called once published for cross-posting.

    The name covers both the drawing and how it is rendered, so either
    changing moves the URL.

    The hash is in the name rather than a ?v= query for a reason
    found the hard way: dev.to's image proxy converts an image it is given a
    plain URL for, and silently stops converting -- passing the original bytes
    through under the wrong content type -- as soon as the URL carries a query
    string. A name that changes with the file gets both, a fresh cache entry
    for an edited drawing and a proxy that still does its job.

    Defined here so hooks/drawings.py, which writes the file, and the
    syndication tool, which writes the link, cannot disagree about it.
    """
    seed = f"{RENDER}".encode() + source.read_bytes()
    return f"{source.stem}.{hashlib.sha256(seed).hexdigest()[:8]}.png"


def _closing(text: str, opening: int) -> int:
    """Index just past the ) matching the ( at opening."""
    depth = 0
    for index in range(opening, len(text)):
        if text[index] == "(":
            depth += 1
        elif text[index] == ")":
            depth -= 1
            if depth == 0:
                return index + 1
    raise SystemExit("unbalanced var() in drawing")


def flatten(svg: str) -> str:
    """Replace every var() with the light palette's sRGB value.

    Resolved through the variable name rather than by keeping the fallback
    already written in the file, because that fallback can be a wide-gamut
    color(display-p3 ...) -- which is what tldraw writes for highlighter
    strokes, and what cairosvg silently renders as black. Every palette entry
    has an sRGB twin, so the name is the thing to trust.
    """
    known = entries()
    out, position = [], 0
    while True:
        start = svg.find(VAR, position)
        if start < 0:
            out.append(svg[position:])
            return "".join(out)

        end = _closing(svg, start + len("var"))
        name = re.match(r"var\((--rvo-draw-[a-z0-9-]+)", svg[start:end])
        if not name:
            raise SystemExit(f"cannot read a variable name in {svg[start:end][:60]!r}")
        entry = known.get(name.group(1))
        if entry is None:
            raise SystemExit(f"{name.group(1)} is not a drawing color")

        color, variant = entry
        # highlightP3 and highlightSrgb share one variable name; the sRGB one
        # is the value every renderer understands.
        if variant == "highlightP3":
            variant = "highlightSrgb"
        out.append(svg[position:start])
        out.append(PALETTE["light"][color][variant])
        position = end


def _pad(open_tag: str) -> tuple[str, str]:
    """Grow the canvas, and return the new tag plus a background covering it."""
    box = VIEWBOX.search(open_tag)
    if not box:
        return open_tag, ""

    x, y, width, height = (float(value) for value in box.groups())
    pad = max(width, height) * PADDING
    x, y, width, height = x - pad, y - pad, width + pad * 2, height + pad * 2

    tag = VIEWBOX.sub(f'viewBox="{x:.2f} {y:.2f} {width:.2f} {height:.2f}"', open_tag)
    # width and height carry the intrinsic size, so they have to grow too or
    # the padded canvas is squeezed back into the original aspect ratio.
    tag = DIMENSION.sub(
        lambda m: f'{m.group(1)}="{width if m.group(1) == "width" else height:.2f}"',
        tag,
    )
    return tag, (
        f'<rect x="{x:.2f}" y="{y:.2f}" '
        f'width="{width:.2f}" height="{height:.2f}" fill="{BACKGROUND}"/>'
    )


def standalone(svg: str) -> str:
    """Flatten a converted drawing into one a stranger's renderer can draw.

    hooks/drawings.py inlines drawings into the page because an
    <img src="drawing.svg"> is a separate document that cannot see the page's
    CSS, so the variables would never resolve. Cross-posts have no such
    option: dev.to and Hashnode take a URL, so the drawing has to arrive as a
    file that stands on its own, with no stylesheet to depend on and nothing
    clever in it.

    See the notes above BACKGROUND and PADDING for why that means literal
    colors on a padded, opaque canvas.
    """
    open_tag = re.search(r"<svg\b[^>]*>", svg)
    if not open_tag:
        raise SystemExit("not an SVG: no <svg> element")

    tag, background = _pad(open_tag.group(0))
    return tag + background + flatten(svg[open_tag.end() :])


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
