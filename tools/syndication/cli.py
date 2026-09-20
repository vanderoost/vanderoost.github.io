"""Command line entry point. Run from the repository root.

    uv run python -m tools.syndication list
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from .lint import LintError, check
from .portable import PLAIN, TransformError, to_portable
from .posts import Post, PostError, discover, resolve

# The package lives at tools/syndication/, so the repository root is two
# directories up. Deriving it from __file__ rather than the working directory
# means the commands behave the same from anywhere.
ROOT = Path(__file__).resolve().parent.parent.parent

EXIT_OK, EXIT_CONTENT, EXIT_API = 0, 1, 2


def _describe(post: Post) -> str:
    fields = {
        "title": post.title,
        "canonical": post.canonical_url,
        "assets": post.asset_base,
        "cover": post.cover_url,
        "tags": ", ".join(post.tags) or "-",
        "description": post.description or "-",
    }
    lines = [post.key + ("  (draft)" if post.draft else "")]
    lines += [f"  {name:<12}{value}" for name, value in fields.items()]
    return "\n".join(lines)


def _list(args) -> int:
    posts = resolve(ROOT, args.posts, include_drafts=args.drafts)
    print("\n\n".join(_describe(post) for post in posts))
    return EXIT_OK


def _render(args) -> int:
    posts = discover(ROOT, include_drafts=True)
    for post in resolve(ROOT, args.posts, include_drafts=True):
        body = to_portable(post, posts, PLAIN, footer=not args.no_footer)
        check(body, str(post.source))
        if len(args.posts) != 1:
            print(f"\n{'=' * 72}\n{post.key}\n{'=' * 72}\n")
        print(body, end="")
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m tools.syndication")
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="show debug logging"
    )
    commands = parser.add_subparsers(dest="command", required=True)

    listing = commands.add_parser(
        "list", help="show every post and the URLs a cross-post will point at"
    )
    listing.add_argument("posts", nargs="*", help="folder name, slug, or path")
    listing.add_argument(
        "--drafts", action="store_true", help="include posts marked draft: true"
    )
    listing.set_defaults(run=_list)

    render = commands.add_parser(
        "render", help="print the portable Markdown a platform would receive"
    )
    render.add_argument("posts", nargs="*", help="folder name, slug, or path")
    render.add_argument(
        "--no-footer", action="store_true", help="omit the 'originally published' note"
    )
    render.set_defaults(run=_render)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )
    try:
        return args.run(args)
    except (PostError, TransformError, LintError) as error:
        print(f"error: {error}", file=sys.stderr)
        return EXIT_CONTENT
