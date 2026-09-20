"""Find the site's articles and work out where each one lands once published.

Everything a cross-post needs about a post is derived here, from the Markdown
source alone, so the rest of the package never has to guess at a URL. The
derivations are small separate functions because each one is a place this can
be quietly wrong, and a wrong URL is the one failure a reader sees.

The sharp edge worth knowing before reading on: a post's page URL and its image
URLs are built from different things. Material's blog plugin publishes the page
at {date}/{slug}/, but it rewrites media files to articles/{folder}/, keeping
the date-prefixed folder name the post was authored in. So these two are both
correct and share nothing, for the same post:

    /articles/2026/09/11/histogram-plotting-in-the-terminal/
    /articles/2026-09-11_histogram-plotting-in-the-terminal/plt_hist-example.png
"""

from __future__ import annotations

import datetime as dt
import logging
import re
from dataclasses import dataclass
from pathlib import Path

import yaml

log = logging.getLogger("syndication.posts")

# Relative to the docs directory. Material's blog plugin fixes this layout:
# one folder per post, named however the author likes, containing index.md and
# that post's images.
POSTS_DIR = "articles/posts"

FRONTMATTER = re.compile(r"\A---\r?\n(?P<meta>.*?)\r?\n---[ \t]*\r?\n", re.DOTALL)

# The post title is the first H1 in the body, not a frontmatter key -- that is
# where Material takes it from, so taking it from anywhere else would let the
# cross-post and the original disagree about their own name.
H1 = re.compile(r"^#[ \t]+(?P<title>.+?)[ \t]*$", re.MULTILINE)

# Material's excerpt marker. Everything above it is the lede shown on the
# article index; everything below is read only on the post's own page.
MORE = re.compile(r"^[ \t]*<!--[ \t]*more[ \t]*-->[ \t]*$", re.MULTILINE)

# A paragraph consisting of nothing but an image or embed. The description
# fallback skips these: "![Histogram Plotting in C](youtube:aLNlyBNU0tw)" is
# not a summary of anything.
IMAGE_ONLY = re.compile(r"\A!\[[^\]]*\]\([^)]*\)\Z")

MAX_DESCRIPTION = 160


class PostError(RuntimeError):
    """A post that cannot be turned into a cross-post. Always names the file."""


@dataclass(frozen=True)
class Post:
    # The date-prefixed folder name, and the key every remote post is recorded
    # under. Deliberately not the slug: the slug is a published-URL decision
    # that can be revised -- this repository's history already contains one
    # such rename -- while the folder name is effectively immutable. Keying on
    # it means renaming a slug UPDATES the remote post and carries the new
    # canonical URL to it, instead of orphaning it and creating a duplicate.
    key: str
    source: Path
    title: str
    slug: str
    created: dt.date
    updated: dt.date | None
    draft: bool
    description: str
    categories: tuple[str, ...]
    tags: tuple[str, ...]
    # (label, target) pairs from the frontmatter "links" key. A label of None
    # means the target is a docs-relative .md path whose title supplies it;
    # portable.py resolves those, because only it has the full post list.
    links: tuple[tuple[str | None, str], ...]
    body: str
    canonical_url: str
    asset_base: str

    @property
    def folder(self) -> Path:
        return self.source.parent


class _Loader(yaml.SafeLoader):
    """SafeLoader that tolerates mkdocs.yml's Python tags instead of failing.

    mkdocs.yml wires up pymdownx with !!python/name: tags that only MkDocs' own
    loader resolves. Nothing here needs those values, but refusing to read the
    file over them would mean writing site_url down a second time, and a
    duplicated site_url is exactly the kind of drift that produces a cross-post
    whose canonical URL points at nothing.
    """


_Loader.add_multi_constructor("", lambda loader, suffix, node: None)


def site_config(root: Path) -> dict:
    """Read the few mkdocs.yml keys that decide where a post is published."""
    config = yaml.load((root / "mkdocs.yml").read_text(encoding="utf-8"), _Loader)
    site_url = (config.get("site_url") or "").rstrip("/")
    if not site_url:
        raise PostError("mkdocs.yml: site_url is required to build canonical URLs")

    # blog_dir is nested under the blog plugin, which mkdocs.yml spells as a
    # list of either plain names or single-key mappings.
    blog_dir = "blog"
    for plugin in config.get("plugins") or []:
        if isinstance(plugin, dict) and "blog" in plugin:
            blog_dir = (plugin["blog"] or {}).get("blog_dir", blog_dir)
    return {"site_url": site_url, "blog_dir": blog_dir.strip("/")}


def split_frontmatter(text: str) -> tuple[dict, str]:
    match = FRONTMATTER.match(text)
    if not match:
        raise PostError("no YAML frontmatter")
    meta = yaml.safe_load(match.group("meta")) or {}
    if not isinstance(meta, dict):
        raise PostError("frontmatter is not a mapping")
    return meta, text[match.end() :]


def created_date(meta: dict) -> dt.date:
    """Accept both frontmatter date shapes this site uses.

    Older posts write "date: 2026-09-11"; newer ones write a mapping with
    created and updated. PyYAML hands back a datetime.date for either.
    """
    value = meta.get("date")
    if isinstance(value, dict):
        value = value.get("created")
    if isinstance(value, dt.datetime):
        return value.date()
    if not isinstance(value, dt.date):
        raise PostError(f"date must be a date, got {value!r}")
    return value


def updated_date(meta: dict) -> dt.date | None:
    value = meta.get("date")
    if not isinstance(value, dict):
        return None
    updated = value.get("updated")
    if isinstance(updated, dt.datetime):
        return updated.date()
    return updated if isinstance(updated, dt.date) else None


def plain_title(heading: str) -> str:
    """Strip the Markdown a heading may carry; a platform title is plain text.

    "# Stop using `rand()`" has to arrive as "Stop using rand()", because both
    platforms render the title field verbatim and would show the backticks.
    """
    text = re.sub(r"`+([^`]*)`+", r"\1", heading)
    text = re.sub(r"\*\*([^*]+)\*\*|\*([^*]+)\*|_([^_]+)_", r"\1\2\3", text)
    return text.strip()


def slugify(title: str) -> str:
    """Approximate Material's slugify(case="lower") for a post without a slug.

    Every post on the site sets slug: explicitly, so this is a fallback that
    should never run silently -- load() warns when it does.
    """
    slug = re.sub(r"[^\w\- ]+", "", title.lower())
    return re.sub(r"[\s_]+", "-", slug).strip("-")


def canonical_url(site_url: str, blog_dir: str, created: dt.date, slug: str) -> str:
    return f"{site_url}/{blog_dir}/{created:%Y/%m/%d}/{slug}/"


def asset_base(site_url: str, blog_dir: str, folder: str) -> str:
    """Where a file sitting next to index.md ends up on the site.

    Material's blog plugin rewrites every media file under {blog_dir}/posts/ to
    {blog_dir}/, which drops one path segment and keeps the folder name. See
    the module docstring for why this does not match the page's own URL.
    """
    return f"{site_url}/{blog_dir}/{folder}/"


def _links(meta: dict) -> tuple[tuple[str | None, str], ...]:
    """Normalise the frontmatter "links" list, which has two spellings.

    A bare string is a docs-relative path to another post; a single-key mapping
    is an explicit label and URL.
    """
    out: list[tuple[str | None, str]] = []
    for entry in meta.get("links") or []:
        if isinstance(entry, str):
            out.append((None, entry))
        elif isinstance(entry, dict) and len(entry) == 1:
            label, target = next(iter(entry.items()))
            out.append((str(label), str(target)))
        else:
            raise PostError(f"links entry is not a path or a label: {entry!r}")
    return tuple(out)


def _lede(body: str) -> str:
    """The text above <!-- more -->, or the opening of the post if it has none."""
    match = MORE.search(body)
    return body[: match.start()] if match else body


def _summarise(lede: str) -> str:
    """Build a description from the lede for the posts that declare none.

    Two of the four posts on the site have no description: frontmatter, and
    without one both platforms fall back to an arbitrary slice of the body in
    their previews and search results.
    """
    for block in re.split(r"\n\s*\n", lede.strip()):
        text = " ".join(block.split())
        if not text or text.startswith("#") or IMAGE_ONLY.match(text):
            continue
        text = plain_title(text)
        if len(text) <= MAX_DESCRIPTION:
            return text
        # Cut at a word boundary so the preview does not end mid-word.
        return text[:MAX_DESCRIPTION].rsplit(" ", 1)[0].rstrip(",;:") + "…"
    return ""


def load(source: Path, config: dict) -> Post:
    try:
        meta, body = split_frontmatter(source.read_text(encoding="utf-8"))
        heading = H1.search(body)
        if not heading:
            raise PostError("no '# Title' heading; Material takes the title from one")
        title = plain_title(heading.group("title"))

        created = created_date(meta)
        slug = str(meta.get("slug") or "")
        if not slug:
            slug = slugify(title)
            log.warning("%s: no slug: in frontmatter, guessed %r", source, slug)

        site_url, blog_dir = config["site_url"], config["blog_dir"]
        description = str(meta.get("description") or "").strip() or _summarise(
            _lede(body)
        )
        return Post(
            key=source.parent.name,
            source=source,
            title=title,
            slug=slug,
            created=created,
            updated=updated_date(meta),
            draft=meta.get("draft") is True,
            description=description,
            categories=tuple(meta.get("categories") or []),
            tags=tuple(str(tag) for tag in meta.get("tags") or []),
            links=_links(meta),
            body=body,
            canonical_url=canonical_url(site_url, blog_dir, created, slug),
            asset_base=asset_base(site_url, blog_dir, source.parent.name),
        )
    except PostError as error:
        raise PostError(f"{source}: {error}") from error


def discover(root: Path, *, include_drafts: bool = False) -> list[Post]:
    """Every publishable post, oldest first."""
    config = site_config(root)
    posts = [
        load(source, config)
        for source in sorted((root / "docs" / POSTS_DIR).glob("*/index.md"))
    ]
    if not include_drafts:
        posts = [post for post in posts if not post.draft]
    return sorted(posts, key=lambda post: post.created)


def resolve(
    root: Path, names: list[str], *, include_drafts: bool = False
) -> list[Post]:
    """Look posts up by folder name, slug, or path, in that order of preference."""
    posts = discover(root, include_drafts=include_drafts)
    if not names:
        return posts

    by_name = {post.key: post for post in posts}
    by_name.update({post.slug: post for post in posts})
    selected = []
    for name in names:
        wanted = Path(name).resolve()
        post = by_name.get(name.strip("/")) or next(
            (p for p in posts if p.source.resolve() == wanted), None
        )
        if post is None:
            known = ", ".join(sorted(p.key for p in posts))
            raise PostError(f"no such post: {name}. Known posts: {known}")
        selected.append(post)
    return selected
