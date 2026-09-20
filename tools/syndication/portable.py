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

import hashlib
import re
from collections.abc import Callable, Iterator
from dataclasses import dataclass

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
            body, index = _take_body(lines, index + 1)
            out += ["", f"#### {tab.group('label')}", ""]
            out += _blocks("\n".join(body), where, depth + 1).split("\n")
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
    """The public URL of a file in the post folder, fingerprinted by content.

    The ?v= is not decoration. Both platforms fetch an image once and cache
    what they get behind their own proxy, keyed on this URL -- dev.to served a
    cached "image no longer exists" placeholder for a drawing that had since
    gone live, because the URL had not changed. Naming the file by what is in
    it means an edited image is a new URL, so a corrected picture actually
    reaches readers instead of being masked by a cache nobody here controls.
    """
    digest = hashlib.sha256((post.folder / name).read_bytes()).hexdigest()[:8]
    return f"{post.asset_base}{name}?v={digest}"


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
        return f"![{alt}]({_asset_url(post, name)})"

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

    # Three or more blank lines are a side effect of removing block markers,
    # and Hashnode renders them as visible gaps.
    body = re.sub(r"\n{3,}", "\n\n", body).strip()
    if footer:
        body += "\n" + _footer(post, by_path)
    return body + "\n"
