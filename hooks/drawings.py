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

Inlining leaves the SVG itself with no public URL, which is fine for this
site and useless for a cross-post: dev.to and Hashnode take an image URL, not
markup. So on_post_build() writes a standalone copy of every drawing an
article actually referenced, themed to follow the reader's system preference
on its own. Only referenced drawings are written, which is what keeps this
from undoing the exclude_docs rule in mkdocs.yml.

The fence walker below is deliberately a copy of the one in hooks/youtube.py
rather than a shared import: MkDocs loads each hook by file path without
putting the directory on sys.path, so siblings cannot import each other.
"""

import importlib.util
import logging
import re
from pathlib import Path

from mkdocs.exceptions import PluginError

log = logging.getLogger("mkdocs.hooks.drawings")

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

# Destination path inside site_dir -> the drawing that should be written there.
# Filled while pages are rendered and drained by on_post_build(). Cleared at
# the start of every build so a drawing removed from an article during
# "mkdocs serve" stops being published.
_REFERENCED: dict[str, Path] = {}


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


def _inline(match: re.Match, page_dir: Path, src_path: str, dest_dir: str) -> str:
    source = page_dir / match.group("src")
    if not source.is_file():
        raise PluginError(f"{src_path}: no such drawing: {match.group('src')}")

    _REFERENCED[f"{dest_dir}/{source.name}"] = source

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


def on_files(files, config):
    """Forget the previous build's references, so "mkdocs serve" stays honest."""
    _REFERENCED.clear()
    return files


def on_page_markdown(markdown: str, page, config, files) -> str:
    page_dir = Path(page.file.abs_src_path).parent
    src_path = page.file.src_path

    # Material's blog plugin publishes a post's media by dropping the "posts"
    # segment from its source path and keeping the folder name, so
    # articles/posts/2026-09-11_x/y.svg is served at articles/2026-09-11_x/y.svg.
    # Deriving the destination the same way keeps the standalone copy beside
    # the PNGs the same article already links to.
    source_dir = Path(page.file.src_uri).parent
    dest_dir = (source_dir.parent.parent / source_dir.name).as_posix()

    def rewrite(part: str) -> str:
        for match in PLAIN_SVG.finditer(part):
            _refuse_plain(match, page_dir, src_path, config)
        return EMBED.sub(lambda m: _inline(m, page_dir, src_path, dest_dir), part)

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


def on_post_build(config):
    """Publish a standalone copy of every drawing an article referenced.

    Written straight into site_dir rather than added to the file list, because
    exclude_docs in mkdocs.yml keeps post SVGs out of that list on purpose --
    the same reason hooks/redirects.py writes its stubs here.
    """
    site_dir = Path(config["site_dir"])
    for dest, source in _REFERENCED.items():
        svg = tldraw_theme.standalone(_themed(source, dest))
        page = site_dir / dest
        page.parent.mkdir(parents=True, exist_ok=True)
        page.write_text(svg, encoding="utf-8")

    if _REFERENCED:
        log.info("Published %d referenced drawing(s)", len(_REFERENCED))
