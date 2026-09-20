"""Turn a post's MkDocs-flavored Markdown into Markdown a platform can render.

The site leans on Material and pymdownx for things neither dev.to nor Hashnode
understands: content tabs, admonitions, attribute lists, and the two pseudo
images this repository invents in hooks/youtube.py and hooks/drawings.py. Left
alone, every one of those ships to the remote as literal punctuation in the
middle of an article.

Nothing here guesses. A construct is either translated or it is an error, and
lint.py re-reads the finished text to catch anything that slipped through. A
cross-post that renders wrong is worse than one that never went out, because
nobody checks a post they believe already succeeded.

The fence walker below is the one in hooks/youtube.py, written once. Hooks
cannot import their siblings, which is why that file and hooks/drawings.py each
carry a copy; this package has no such excuse.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterator
from dataclasses import dataclass

from .. import tldraw_theme
from .posts import Post

# Every construct below is matched only outside fenced and inline code, so an
# article explaining this syntax keeps its examples intact.
FENCE = re.compile(r"^\s*(?P<fence>```+|~~~+)")
INLINE_CODE = re.compile(r"(`+[^`]*`+)")

# An opening fence carrying pymdownx attributes: ```c title="main.c" linenums="1"
FENCE_OPEN = re.compile(
    r"^(?P<indent>\s*)(?P<fence>```+|~~~+)"
    r"(?P<lang>[\w+#.-]*)"
    r"(?P<attrs>[ \t]+\S.*?)?[ \t]*$"
)
FENCE_TITLE = re.compile(r'\btitle="(?P<title>[^"]*)"')

# Material's content tabs. "===+" only means the tab opens selected.
TAB = re.compile(r'^(?P<marker>===\+?)[ \t]+"(?P<label>[^"]*)"[ \t]*$')

# Admonitions, collapsible or not, with an optional quoted title.
ADMONITION = re.compile(
    r'^(?P<marker>!!!|\?\?\?\+?)[ \t]+(?P<type>[\w-]+)'
    r'(?:[ \t]+"(?P<title>[^"]*)")?[ \t]*$'
)

# An image or embed, with pymdownx's optional "title" and attr_list suffix.
IMAGE = re.compile(
    r'!\[(?P<alt>[^\]]*)\]\((?P<target>[^)\s]+)(?:[ \t]+"(?P<title>[^"]*)")?\)'
    r"(?P<attrs>\{[^}]*\})?"
)

# A link, not an image -- hence the lookbehind -- with the same attr suffix.
LINK = re.compile(
    r'(?<!!)\[(?P<text>[^\]]*)\]\((?P<target>[^)\s]+)(?:[ \t]+"[^"]*")?\)'
    r"(?P<attrs>\{[^}]*\})?"
)

# Same check hooks/youtube.py makes: 11 characters of URL-safe base64.
VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")

MORE = re.compile(r"^[ \t]*<!--[ \t]*more[ \t]*-->[ \t]*$", re.MULTILINE)
H1 = re.compile(r"^#[ \t]+.+?[ \t]*$", re.MULTILINE)

# Material's icon shortcodes, plus the attribute list that usually follows one.
ICON = re.compile(r":(?:material|fontawesome|octicons|simple)-[\w-]+:(?:\{[^}]*\})?")

# pymdownx.critic and pymdownx.keys.
CRITIC = [
    (re.compile(r"\{\+\+(.+?)\+\+\}", re.DOTALL), r"\1"),
    (re.compile(r"\{--.+?--\}", re.DOTALL), ""),
    (re.compile(r"\{~~.+?~>(.+?)~~\}", re.DOTALL), r"\1"),
    (re.compile(r"\{==(.+?)==\}", re.DOTALL), r"**\1**"),
]
KEYS = re.compile(r"\+\+([\w+-]+)\+\+")

SNIPPET = re.compile(r"^[ \t]*--8<--")

# A line that opens its own block rather than continuing the paragraph above
# it: heading, list item, numbered item, quote, table row, fence, rule, raw
# HTML, or an image sitting on a line of its own.
BLOCK_START = re.compile(
    r"^(?:#{1,6}[ \t]|[-*+][ \t]|\d+[.)][ \t]|>|\||```|~~~|---|\*\*\*|___|<|!\[)"
)

# Markdown's two ways of asking for a line break on purpose. Both are left
# alone; it is only the incidental newlines from wrapping that get joined.
HARD_BREAK = re.compile(r"(?:[ \t]{2,}|\\)$")

# The "> " markers a line carries, so wrapped prose inside a quote can be
# joined the same way as prose outside one. Admonitions become blockquotes
# here, so their bodies arrive wrapped exactly like any other paragraph.
QUOTE = re.compile(r"^(?P<prefix>(?:>[ \t]?)+)(?P<rest>.*)$")

# Tab and admonition bodies are indented by one unit. This site's source uses
# literal tabs; pymdownx also accepts four spaces, so both are recognised.
INDENTS = ("\t", "    ")


class TransformError(RuntimeError):
    """Markdown this module refuses to guess at. Always names the post."""


@dataclass(frozen=True)
class Dialect:
    """The handful of things each platform spells differently."""

    name: str
    youtube: Callable[[str, str], str]
    mermaid: bool = True


def _linked_thumbnail(video_id: str, caption: str) -> str:
    """Fallback embed: a poster frame that links to the video.

    Used by "render" and by any platform without an embed syntax, so previewing
    a post never silently drops a video that the real cross-post would keep.
    """
    return (
        f"[![{caption}](https://i.ytimg.com/vi/{video_id}/maxresdefault.jpg)]"
        f"(https://www.youtube.com/watch?v={video_id})"
    )


PLAIN = Dialect(name="plain", youtube=_linked_thumbnail)


def scan(text: str) -> Iterator[tuple[str, bool]]:
    """Yield (line, inside_fence) for every line, tracking nested fences."""
    fence = None
    for line in text.split("\n"):
        opening = FENCE.match(line)
        if fence is None and opening:
            fence = opening.group("fence")
            yield line, True
        elif fence is not None and opening and opening.group("fence") >= fence:
            fence = None
            yield line, True
        else:
            yield line, fence is not None


def walk_prose(text: str, rewrite: Callable[[str], str]) -> str:
    """Apply rewrite to everything that is not code."""
    out = []
    for line, in_code in scan(text):
        if not in_code:
            line = "".join(
                part if part.startswith("`") else rewrite(part)
                for part in INLINE_CODE.split(line)
            )
        out.append(line)
    return "\n".join(out)


def unwrap(text: str) -> str:
    """Join lines that the author wrapped, so a paragraph is one line again.

    dev.to renders Markdown with hard breaks on, meaning a single newline
    inside a paragraph becomes a <br> rather than a space. The source here is
    wrapped at 88 columns like the rest of the repository, so every paragraph
    arrived broken at exactly the column the author's editor happened to wrap
    at. A paragraph that is one long line renders the same everywhere, so this
    is done for every platform rather than only for the one that needs it.

    Deliberate breaks -- two trailing spaces or a backslash -- survive, as
    does anything that opens a block of its own.
    """
    out: list[str] = []
    previous_code = True
    for line, in_code in scan(text):
        prefix, rest = _quoted(line)
        if out and not in_code and not previous_code:
            above_prefix, above_rest = _quoted(out[-1])
        else:
            above_prefix, above_rest = None, None

        joinable = (
            above_rest is not None
            and prefix == above_prefix
            and rest.strip()
            and above_rest.strip()
            # An indented line is a list continuation or an indented code
            # block, neither of which may be folded into the line above.
            and not rest[:1].isspace()
            and not above_rest[:1].isspace()
            and not BLOCK_START.match(rest)
            and not BLOCK_START.match(above_rest)
            and not HARD_BREAK.search(above_rest)
        )
        if joinable:
            out[-1] = f"{prefix}{above_rest.rstrip()} {rest.strip()}"
        else:
            out.append(line)
        previous_code = in_code
    return "\n".join(out)


def _quoted(line: str) -> tuple[str, str]:
    """Split a line into its blockquote markers and the text after them."""
    match = QUOTE.match(line)
    return (match.group("prefix"), match.group("rest")) if match else ("", line)


def _dedent(lines: list[str]) -> list[str]:
    """Strip one level of indentation, accepting a tab or four spaces."""
    unit = next(
        (i for line in lines if line.strip() for i in INDENTS if line.startswith(i)),
        None,
    )
    if unit is None:
        return lines
    return [line[len(unit) :] if line.startswith(unit) else line for line in lines]


def _take_body(lines: list[str], start: int) -> tuple[list[str], int]:
    """Collect the indented block following a tab or admonition marker."""
    body, index = [], start
    while index < len(lines):
        line = lines[index]
        if line.strip() and not line.startswith(INDENTS):
            break
        body.append(line)
        index += 1
    while body and not body[-1].strip():
        body.pop()
    return _dedent(body), index


def _tab_group(
    lines: list[str], states: list[bool], start: int
) -> tuple[list[str], int]:
    """Read a run of content tabs and keep only the one that matters.

    Neither platform has tabs, and flattening a group into every tab in turn
    buries the article: the Makefile piece became seven near-identical
    Makefiles, pages of scrolling for a reader who wanted one. So the group
    collapses to the tab Material would have opened on -- the one marked
    "===+", or the first when none is -- and the alternatives are dropped.

    The label goes with them. It named a choice between tabs, and once there
    is nothing to choose it is a heading over a single block, cluttering the
    article outline without telling the reader anything.
    """
    bodies: list[list[str]] = []
    selected = None
    index = start
    while index < len(lines):
        match = None if states[index] else TAB.match(lines[index])
        if not match:
            break
        body, index = _take_body(lines, index + 1)
        if match.group("marker").endswith("+") and selected is None:
            selected = len(bodies)
        bodies.append(body)

    if not bodies:
        return [], index
    return bodies[selected if selected is not None else 0], index


def _blocks(text: str, where: str, depth: int = 0) -> str:
    """Flatten content tabs and admonitions into plain headings and quotes.

    Both are marker-plus-indented-body constructs, so both are handled here and
    their bodies are re-processed: the Makefile article is seven content tabs
    that each wrap a fenced code block.
    """
    if depth > 4:
        raise TransformError(f"{where}: blocks nested more than four deep")

    lines = list(text.split("\n"))
    states = [in_code for _, in_code in scan(text)]
    out: list[str] = []
    index = 0
    while index < len(lines):
        line, in_code = lines[index], states[index]
        tab = None if in_code else TAB.match(line)
        note = None if in_code else ADMONITION.match(line)

        if tab:
            body, index = _tab_group(lines, states, index)
            out += [""]
            out += _blocks("\n".join(body), where, depth + 1).split("\n")
            out += [""]
        elif note:
            body, index = _take_body(lines, index + 1)
            title = note.group("title") or note.group("type").capitalize()
            quoted = _blocks("\n".join(body), where, depth + 1).split("\n")
            out += ["", f"> **{title}**", ">"]
            out += [f"> {line}".rstrip() for line in quoted]
            out += [""]
        else:
            out.append(line)
            index += 1
    return "\n".join(out)


def _fences(text: str, dialect: Dialect, where: str) -> str:
    """Drop fence attributes, keeping the filename as a caption.

    Neither platform understands title= or linenums=, and both mis-lex the
    fence rather than ignoring the extras. The filename is real information,
    so it survives as a bold line above the block.
    """
    out, fence = [], None
    for line in text.split("\n"):
        opening = FENCE.match(line)
        if fence is not None:
            if opening and opening.group("fence") >= fence:
                fence = None
            out.append(line)
            continue
        if not opening:
            out.append(line)
            continue

        match = FENCE_OPEN.match(line)
        if not match:
            fence = opening.group("fence")
            out.append(line)
            continue

        fence = match.group("fence")
        lang = match.group("lang") or ""
        if lang == "mermaid" and not dialect.mermaid:
            lang = ""
        title = FENCE_TITLE.search(match.group("attrs") or "")
        if title:
            out += [f"**{title.group('title')}**", ""]
        out.append(f"{match.group('indent')}{fence}{lang}")
    return "\n".join(out)


def _asset_url(post: Post, name: str) -> str:
    """The public URL of a file sitting next to the post's index.md.

    Deliberately no cache-busting query. dev.to's proxy stops converting an
    image the moment its URL carries one, and serves the original bytes under
    the wrong content type instead. Drawings get a fingerprint in the filename
    instead -- see tldraw_theme.published_name().
    """
    return f"{post.asset_base}{name}"


# YouTube always has this one, at a size worth using as a cover.
THUMBNAIL = "https://i.ytimg.com/vi/{video}/maxresdefault.jpg"


def cover_url(post: Post) -> str | None:
    """The image a platform should show above the article, if any.

    Deliberately not the site's generated Open Graph card. That card exists to
    carry the title into a link preview, so on a platform that prints the
    title underneath it, the reader meets the same words twice in the site's
    own font -- which looks like a mistake, because it is one.

    A video's thumbnail is the best cover a post can have, and the first image
    in the article is the next best. A post with neither gets no cover at all,
    which reads better than a picture of its own title.
    """
    video, image = None, None
    for line, in_code in scan(post.body):
        if in_code:
            continue
        for match in IMAGE.finditer(line):
            target = match.group("target")
            if target.startswith("youtube:") and video is None:
                video = target[len("youtube:") :]
            elif image is None and not target.startswith("youtube:"):
                image = target

    if video and VIDEO_ID.match(video):
        return THUMBNAIL.format(video=video)
    if image:
        return _local_asset(post, image)
    return None


def _local_asset(post: Post, target: str) -> str | None:
    """The published URL of an image in the post folder, or None if remote."""
    if "://" in target or target.startswith(("/", "#", "data:")):
        return None
    if target.startswith("drawing:"):
        name = target[len("drawing:") :]
        if not (post.folder / name).is_file():
            return None
        return _asset_url(post, tldraw_theme.published_name(post.folder / name))
    name = target[2:] if target.startswith("./") else target
    return _asset_url(post, name) if (post.folder / name).is_file() else None


def _image(match: re.Match, post: Post, dialect: Dialect) -> str:
    alt, target = match.group("alt"), match.group("target")

    if target.startswith("youtube:"):
        video_id = target[len("youtube:") :]
        if not VIDEO_ID.match(video_id):
            raise TransformError(
                f"{post.source}: {video_id!r} is not a YouTube video id. Expected "
                "the 11 characters after 'v=' in the watch URL."
            )
        return dialect.youtube(video_id, alt)

    if target.startswith("drawing:"):
        name = target[len("drawing:") :]
        if not (post.folder / name).is_file():
            raise TransformError(f"{post.source}: no such drawing: {name}")
        # hooks/drawings.py publishes drawings as a fingerprinted PNG, not
        # SVG -- see the note in its docstring about dev.to mislabelling the
        # content type of anything it did not convert.
        published = tldraw_theme.published_name(post.folder / name)
        return f"![{alt}]({_asset_url(post, published)})"

    if "://" in target or target.startswith(("/", "#", "data:")):
        return f"![{alt}]({target})"

    name = target[2:] if target.startswith("./") else target
    if not (post.folder / name).is_file():
        raise TransformError(f"{post.source}: no such image: {target}")
    return f"![{alt}]({_asset_url(post, name)})"


def _link(match: re.Match, post: Post, by_path: dict[str, Post]) -> str:
    text, target = match.group("text"), match.group("target")
    if "://" in target or target.startswith(("#", "mailto:")):
        return f"[{text}]({target})"
    return f"[{text}]({_resolve(target, post, by_path)})"


def _resolve(target: str, post: Post, by_path: dict[str, Post]) -> str:
    """Turn a link to another post into that post's public URL.

    A relative .md path means nothing off this site, and passing one through
    would publish a dead link, so an unresolvable target is an error.
    """
    if "://" in target:
        return target
    if target.startswith("/"):
        return post.canonical_url.split("/articles/")[0] + target

    key = target.split("#")[0].strip("/")
    for candidate in (key, f"{post.folder.name}/{key}"):
        found = by_path.get(candidate)
        if found:
            return found.canonical_url
    raise TransformError(
        f"{post.source}: link target {target!r} does not resolve to a post. "
        "Cross-posts cannot carry site-relative links."
    )


def _footer(post: Post, by_path: dict[str, Post]) -> str:
    """Send the reader home, and say plainly where the article came from."""
    origin = f"*Originally published at [vanderoost.com]({post.canonical_url}).*"
    lines = ["", "---", "", origin]
    related = []
    for label, target in post.links:
        url = _resolve(target, post, by_path)
        if label is None:
            found = next((p for p in by_path.values() if p.canonical_url == url), None)
            label = found.title if found else url
        related.append(f"- [{label}]({url})")
    if related:
        lines += ["", "**Related**", ""] + related
    return "\n".join(lines)


def _index(posts: list[Post]) -> dict[str, Post]:
    """Index every post by the docs-relative paths a link might spell it with."""
    index = {}
    for post in posts:
        docs_relative = f"articles/posts/{post.key}/index.md"
        index[docs_relative] = post
        index[f"{post.key}/index.md"] = post
        index[post.key] = post
    return index


def to_portable(
    post: Post,
    posts: list[Post],
    dialect: Dialect = PLAIN,
    *,
    footer: bool = True,
) -> str:
    where = str(post.source)
    by_path = _index(posts)

    body = post.body
    if SNIPPET.search(body):
        raise TransformError(
            f"{where}: pymdownx.snippets (--8<--) is not supported. Inline the "
            "snippet, or the cross-post would ship the literal marker."
        )

    # The H1 becomes the platform's title field, and both platforms render
    # their own heading above the body, so leaving it here duplicates it.
    body = H1.sub("", body, count=1)
    body = MORE.sub("", body)

    body = _blocks(body, where)
    body = _fences(body, dialect, where)

    def inline(part: str) -> str:
        part = IMAGE.sub(lambda m: _image(m, post, dialect), part)
        part = LINK.sub(lambda m: _link(m, post, by_path), part)
        part = ICON.sub("", part)
        for pattern, replacement in CRITIC:
            part = pattern.sub(replacement, part)
        return KEYS.sub(lambda m: f"`{m.group(1)}`", part)

    body = walk_prose(body, inline)
    body = unwrap(body)

    # Three or more blank lines are a side effect of removing block markers,
    # and Hashnode renders them as visible gaps.
    body = re.sub(r"\n{3,}", "\n\n", body).strip()
    if footer:
        body += "\n" + _footer(post, by_path)
    return body + "\n"
