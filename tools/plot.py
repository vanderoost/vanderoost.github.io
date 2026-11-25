#!/usr/bin/env python3
"""Plot a function or data points as an SVG the site themes like a drawing.

Usually not run by hand: an article describes a plot in a fenced block, and
hooks/drawings.py renders it with this module on every build, so tweaking a
plot is editing a line of the article.

    ```plot title="The sigmoid function"
    f: 1 / (1 + exp(-x))
    x: [-6, 6]
    y: [0, 1]
    ylabel: σ(x)
    ```

The title is the plot's accessible name, and the alt text of the PNG that
cross-posts receive. The body is YAML, with the keys in KEYS:

    f       an expression, or a list of them, in Python syntax with everything
            from math in scope, x as the variable and ** for powers
    csv     a file of x,y rows in the post folder, or a list of them, for data
            points rather than a function: a loss per epoch, say
    x, y    the visible range, as [min, max]
    xstep, ystep    tick spacing; picked automatically when left out
    xlabel, ylabel  axis names, "x" and "y" unless given

Every series gets the next color in SERIES. The output colors everything with
--rvo-plot-* variables, Tokyo Night Day and Night in extra.css, so a plot
switches with light and dark mode like the code blocks around it.

Written by hand rather than with matplotlib: a function plot is a few dozen
elements, and matplotlib's SVG would bake in literal colors that then need
converting.

Run directly, it writes the same SVG to a file, for a plot that is needed
outside an article:

    tools/plot.py spec.yml -o plot.svg
"""

import argparse
import csv
import hashlib
import json
import math
import sys
from html import escape
from pathlib import Path

import yaml

# Matches the drawing area of .rvo-drawing (28rem at Material's 20px rem), so
# a font size here is a font size on the page.
WIDTH, HEIGHT = 560, 320
FONT = 'font-family="Ubuntu, sans-serif" font-size="14"'
SAMPLES = 400

KEYS = {"f", "csv", "x", "y", "xstep", "ystep", "xlabel", "ylabel"}

# Tokyo Night, like the code blocks and console colors: --rvo-plot-* is set
# per color scheme in extra.css, and the fallback after the comma is the Day
# value. It has to be a plain sRGB hex: tldraw_theme.flatten() takes it as is
# for the PNG that cross-posts get, which is drawn in the light palette.
INK = "var(--rvo-plot-fg, #3760bf)"
GRID = "var(--rvo-plot-grid, #848cb5)"
SERIES = [
    "var(--rvo-plot-blue, #2e7de9)",
    "var(--rvo-plot-red, #f52a65)",
    "var(--rvo-plot-green, #587539)",
    "var(--rvo-plot-orange, #b15c00)",
    "var(--rvo-plot-magenta, #9854f1)",
    "var(--rvo-plot-cyan, #007197)",
]


class PlotError(Exception):
    """A plot spec that cannot be drawn. The message says why."""


def parse(text: str) -> dict:
    """Read and check a spec, so a typo fails here rather than looking odd."""
    try:
        spec = yaml.safe_load(text)
    except yaml.YAMLError as error:
        raise PlotError(f"not valid YAML: {error}") from error
    if not isinstance(spec, dict):
        raise PlotError("expected keys like f: and x:, one per line")

    unknown = set(spec) - KEYS
    if unknown:
        raise PlotError(
            f"unknown key(s) {', '.join(sorted(unknown))}; "
            f"expected {', '.join(sorted(KEYS))}"
        )
    for key in ("x", "y"):
        value = spec.get(key)
        if not (
            isinstance(value, list)
            and len(value) == 2
            and all(isinstance(v, (int, float)) for v in value)
            and value[0] < value[1]
        ):
            raise PlotError(f"{key}: needs a range like [-6, 6], got {value!r}")
    if "f" not in spec and "csv" not in spec:
        raise PlotError("nothing to plot: give f: or csv:")
    return spec


def _many(value) -> list[str]:
    if value is None:
        return []
    return [str(v) for v in value] if isinstance(value, list) else [str(value)]


def ticks(low: float, high: float, step: float) -> list[float]:
    first = math.ceil(low / step - 1e-9)
    last = math.floor(high / step + 1e-9)
    return [round(i * step, 10) for i in range(first, last + 1)]


def nice_step(span: float) -> float:
    """A 1, 2 or 5 times a power of ten that gives about six ticks."""
    raw = span / 6
    power = 10 ** math.floor(math.log10(raw))
    return next(m * power for m in (1, 2, 5, 10) if m * power >= raw)


def label(value: float) -> str:
    text = f"{value:g}"
    # A real minus sign, not a hyphen, is what typeset math uses.
    return text.replace("-", "−")


def sample(expression: str, low: float, high: float) -> list[tuple[float, float]]:
    try:
        code = compile(expression, "<expression>", "eval")
    except SyntaxError as error:
        raise PlotError(f"f: {expression!r} is not a valid expression") from error
    scope = {name: getattr(math, name) for name in dir(math) if not name.startswith("_")}

    points = []
    for i in range(SAMPLES + 1):
        x = low + (high - low) * i / SAMPLES
        try:
            points.append((x, float(eval(code, scope, {"x": x}))))
        except (ValueError, ZeroDivisionError, OverflowError):
            # Undefined here, like log(x) for x <= 0: the line breaks.
            points.append((x, math.nan))
        except Exception as error:
            raise PlotError(f"f: {expression!r} fails: {error}") from error
    return points


def read_csv(path: Path) -> list[tuple[float, float]]:
    if not path.is_file():
        raise PlotError(f"csv: no such file: {path}")
    with path.open() as file:
        rows = [row for row in csv.reader(file) if row]
    # Tolerate a header row: anything whose first cell is not a number.
    if rows:
        try:
            float(rows[0][0])
        except ValueError:
            rows = rows[1:]
    try:
        return [(float(row[0]), float(row[1])) for row in rows]
    except (ValueError, IndexError) as error:
        raise PlotError(f"csv: {path.name} needs numeric x,y rows") from error


def path(points, sx, sy) -> str:
    """One path, broken wherever the function is undefined."""
    parts, pen_down = [], False
    for x, y in points:
        if math.isnan(y) or math.isinf(y):
            pen_down = False
            continue
        parts.append(f"{'L' if pen_down else 'M'}{sx(x):.1f} {sy(y):.1f}")
        pen_down = True
    return "".join(parts)


def render(spec: dict, folder: Path) -> str:
    """The SVG for a parsed spec. csv: paths are relative to folder."""
    (x0, x1), (y0, y1) = spec["x"], spec["y"]
    xlabel, ylabel = str(spec.get("xlabel", "x")), str(spec.get("ylabel", "y"))

    series = [sample(e, x0, x1) for e in _many(spec.get("f"))]
    series += [read_csv(folder / name) for name in _many(spec.get("csv"))]

    # A clipPath id is global to the page the SVG is inlined into, so each
    # plot needs its own, or two plots on one page would share one clip.
    seed = json.dumps(spec, sort_keys=True, ensure_ascii=False).encode()
    clip = f"plot-clip-{hashlib.sha256(seed).hexdigest()[:8]}"

    # The left margin makes room for the widest y tick label.
    y_ticks = ticks(y0, y1, spec.get("ystep") or nice_step(y1 - y0))
    x_ticks = ticks(x0, x1, spec.get("xstep") or nice_step(x1 - x0))
    widest = max(len(label(tick)) for tick in y_ticks)
    left, right = 16 + widest * 8, 16
    top, bottom = 28, 32
    plot_w, plot_h = WIDTH - left - right, HEIGHT - top - bottom

    def sx(x: float) -> float:
        return left + (x - x0) / (x1 - x0) * plot_w

    def sy(y: float) -> float:
        return top + (y1 - y) / (y1 - y0) * plot_h

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" '
        f'viewBox="0 0 {WIDTH} {HEIGHT}">',
        f'<defs><clipPath id="{clip}"><rect x="{left}" y="{top}" '
        f'width="{plot_w}" height="{plot_h}"/></clipPath></defs>',
    ]

    # Grid first, so the axes and curves draw over it.
    grid = [f"M{sx(t):.1f} {top}V{top + plot_h}" for t in x_ticks]
    grid += [f"M{left} {sy(t):.1f}H{left + plot_w}" for t in y_ticks]
    out.append(
        f'<path d="{"".join(grid)}" stroke="{GRID}" stroke-opacity="0.35" '
        'stroke-width="1" fill="none"/>'
    )

    # The axes sit at zero when zero is on the chart, else on the edge.
    ax = sy(0) if y0 <= 0 <= y1 else top + plot_h
    ay = sx(0) if x0 <= 0 <= x1 else left
    out.append(
        f'<path d="M{left} {ax:.1f}H{left + plot_w}M{ay:.1f} {top}V{top + plot_h}" '
        f'stroke="{INK}" stroke-width="1.5" fill="none"/>'
    )

    # Tick labels stay on the outer edges, where no curve can run through them.
    for t in x_ticks:
        out.append(
            f'<text x="{sx(t):.1f}" y="{top + plot_h + 20}" text-anchor="middle" '
            f'fill="{INK}" {FONT}>{label(t)}</text>'
        )
    for t in y_ticks:
        out.append(
            f'<text x="{left - 8}" y="{sy(t) + 5:.1f}" text-anchor="end" '
            f'fill="{INK}" {FONT}>{label(t)}</text>'
        )
    if xlabel:
        out.append(
            f'<text x="{left + plot_w}" y="{ax - 8:.1f}" text-anchor="end" '
            f'fill="{INK}" {FONT} font-style="italic">{escape(xlabel)}</text>'
        )
    if ylabel:
        out.append(
            f'<text x="{ay:.1f}" y="{top - 10}" text-anchor="middle" fill="{INK}" '
            f'{FONT} font-style="italic">{escape(ylabel)}</text>'
        )

    for index, points in enumerate(series):
        color = SERIES[index % len(SERIES)]
        out.append(
            f'<path d="{path(points, sx, sy)}" stroke="{color}" stroke-width="2.5" '
            f'fill="none" stroke-linecap="round" stroke-linejoin="round" '
            f'clip-path="url(#{clip})"/>'
        )

    out.append("</svg>")
    return "\n".join(out) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("spec", type=Path, help="YAML file, as in a plot fence")
    parser.add_argument("-o", "--output", type=Path, required=True)
    args = parser.parse_args()

    try:
        spec = parse(args.spec.read_text())
        args.output.write_text(render(spec, args.spec.parent))
    except PlotError as error:
        sys.exit(f"{args.spec}: {error}")


if __name__ == "__main__":
    main()
