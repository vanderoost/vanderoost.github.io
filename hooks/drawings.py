"""Inline ![Caption](drawing:file.svg), themed, so the page's CSS colors it.

An <img src="drawing.svg"> is a separate document: it cannot see the page's
stylesheet, so the CSS variables that carry the theme would never resolve and
every drawing would keep the colors it was exported with. Inlining the SVG
into the page makes it part of the same DOM as the variables, which is the
same trick the header logo uses — see theme.icon.logo in mkdocs.yml and
overrides/.icons/branding.

Drawings are themed here, at build time, rather than on disk. A raw tldraw
export can be dropped into a post folder and simply works: there is no
conversion step to forget, and re-exporting a drawing produces a git diff of
what actually changed on the canvas instead of a rewrite of every colour.
Already-converted files still work, so exports themed by hand earlier are left
alone.

The fence walker below is deliberately a copy of the one in hooks/youtube.py
rather than a shared import: MkDocs loads each hook by file path without
putting the directory on sys.path, so siblings cannot import each other.
"""

import importlib.util
import re
from pathlib import Path

from mkdocs.exceptions import PluginError

# tools/ is not a package and is not on sys.path — see the note above — so the
# converter is loaded by the path it actually lives at. Keeping the colour
# logic in one file means the CLI and the build cannot drift apart.
_TOOL = Path(__file__).resolve().parent.parent / "tools" / "tldraw_theme.py"
_spec = importlib.util.spec_from_file_location("tldraw_theme", _TOOL)
tldraw_theme = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(tldraw_theme)

# A drawing is converted once per build, not once per reference, and survives
# across the rebuilds of "mkdocs serve" unless the file itself changes.
_CACHE: dict[tuple[str, int], str] = {}


def _themed(source: Path, src_path: str) -> str:
    key = (str(source), source.stat().st_mtime_ns)
    if key not in _CACHE:
        try:
            converted, _ = tldraw_theme.convert(source.read_text(), source)
        except SystemExit as error:
            # The converter is a CLI first: it exits rather than raising, which
            # inside a hook would end the build without saying which page.
            raise PluginError(f"{src_path}: {error}") from error
        _CACHE[key] = converted
    return _CACHE[key]

EMBED = re.compile(r"!\[(?P<title>[^\]]*)\]\(drawing:(?P<src>[^)\s]+)\)")

# A drawing referenced as a plain image. No colon in the target, so this skips
# drawing: and absolute URLs, and only relative paths to local files remain.
PLAIN_SVG = re.compile(r'!\[[^\]]*\]\((?P<src>[^)\s:]+\.svg)(?:\s+"[^"]*")?\)')
FENCE = re.compile(r"^\s*(?P<fence>```+|~~~+)")
INLINE_CODE = re.compile(r"(`+[^`]*`+)")

# Matches the opening <svg ...> tag, so the accessible name can be injected.
SVG_OPEN = re.compile(r"<svg\b[^>]*>")


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _inline(match: re.Match, page_dir: Path, src_path: str) -> str:
    source = page_dir / match.group("src")
    if not source.is_file():
        raise PluginError(f"{src_path}: no such drawing: {match.group('src')}")

    svg = _themed(source, src_path).strip()
    open_tag = SVG_OPEN.search(svg)
    if not open_tag:
        raise PluginError(f"{src_path}: {match.group('src')} is not an SVG")

    # role="img" plus a <title> is what makes the drawing announce itself as a
    # single image with a name, instead of as a pile of anonymous paths.
    title = _escape(match.group("title"))
    labelled = (
        open_tag.group(0).rstrip(">")
        + ' role="img" aria-label="' + title.replace('"', "&quot;") + '">'
        + f"<title>{title}</title>"
    )
    svg = svg[: open_tag.start()] + labelled + svg[open_tag.end() :]
    return f'<div class="rvo-drawing">{svg}</div>'


def _refuse_plain(match: re.Match, page_dir: Path, src_path: str, config) -> None:
    """Fail on ![...](file.svg) when exclude_docs keeps that file off the site.

    The <img> would 404, and MkDocs only reports a link to an excluded file at
    INFO level, so even --strict lets the broken image through to production.
    The fix is always the same missing prefix, so the message spells it out.
    """
    docs_dir = Path(config.docs_dir).resolve()
    try:
        target = (page_dir / match.group("src")).resolve().relative_to(docs_dir)
    except ValueError:
        return  # Outside docs/: MkDocs' own link validation covers that.

    if config.exclude_docs and config.exclude_docs.match_file(target.as_posix()):
        fixed = match.group(0).replace("](", "](drawing:", 1)
        raise PluginError(
            f"{src_path}: {match.group('src')} is referenced as a plain image, "
            "but post SVGs are excluded from the built site, so it would 404. "
            f"Use the drawing: prefix instead: {fixed}"
        )


def on_page_markdown(markdown: str, page, config, files) -> str:
    page_dir = Path(page.file.abs_src_path).parent
    src_path = page.file.src_path

    def rewrite(part: str) -> str:
        for match in PLAIN_SVG.finditer(part):
            _refuse_plain(match, page_dir, src_path, config)
        return EMBED.sub(lambda m: _inline(m, page_dir, src_path), part)

    out, fence = [], None
    for line in markdown.split("\n"):
        opening = FENCE.match(line)
        if fence is None and opening:
            fence = opening.group("fence")
        elif fence is not None and opening and opening.group("fence") >= fence:
            fence = None
        elif fence is None:
            line = "".join(
                part if part.startswith("`") else rewrite(part)
                for part in INLINE_CODE.split(line)
            )
        out.append(line)
    return "\n".join(out)
