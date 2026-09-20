"""Command line entry point. Run from the repository root.

    uv run python -m tools.syndication list
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

from . import state as state_module
from . import sync as sync_module
from .lint import LintError, check
from .platforms import ADAPTERS
from .platforms.base import MissingCredentials, TransportError
from .portable import PLAIN, TransformError, cover_url, to_portable
from .sync import article_for
from .posts import Post, PostError, discover, resolve, site_config

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
        "cover": cover_url(post) or "-",
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
    """Show what a platform would receive. Makes no network calls at all."""
    posts = discover(ROOT, include_drafts=True)
    adapter = ADAPTERS[args.platform] if args.platform else None
    if adapter is not None:
        # --json prints a real request body, which needs the credentials that
        # carry the publication id. Without them, show the Markdown only.
        try:
            adapter.configure(os.environ)
        except MissingCredentials as error:
            if args.json:
                raise PostError(f"--json for {args.platform} needs {error}") from error

    for post in resolve(ROOT, args.posts, include_drafts=True):
        dialect = adapter.dialect if adapter else PLAIN
        body = to_portable(post, posts, dialect, footer=not args.no_footer)
        check(body, str(post.source), liquid_tags=bool(adapter and adapter.liquid_tags))

        if len(args.posts) != 1:
            print(f"\n{'=' * 72}\n{post.key}\n{'=' * 72}\n")
        if args.json:
            article = article_for(post, posts, adapter, published=True)
            print(json.dumps(adapter.payload(article), indent=2, sort_keys=True))
        else:
            print(body, end="")
    return EXIT_OK


def _adapters(args):
    names = [name.strip() for name in args.platform.split(",") if name.strip()]
    unknown = [name for name in names if name not in ADAPTERS]
    if unknown:
        raise PostError(
            f"unknown platform(s): {', '.join(unknown)}. "
            f"Known: {', '.join(ADAPTERS)}"
        )
    return sync_module.configured(names)


def _sync(args) -> int:
    posts = discover(ROOT)
    selected = resolve(ROOT, args.posts)
    adapters = _adapters(args)
    if not adapters:
        print("no platform is configured; nothing to do", file=sys.stderr)
        return EXIT_OK

    state = state_module.load(ROOT)
    changed, failures = sync_module.run(
        posts,
        selected,
        adapters,
        state,
        ROOT,
        site_config(ROOT)["site_url"],
        dry_run=args.dry_run,
        force=args.force,
        published=not args.remote_draft,
        verify=not args.skip_asset_check,
    )

    if failures:
        print(f"\n{len(failures)} failure(s):", file=sys.stderr)
        for failure in failures:
            print(f"  {failure}", file=sys.stderr)
        return EXIT_API
    if not args.dry_run:
        print(f"\n{changed} article(s) changed")
    return EXIT_OK


def _reconcile(args) -> int:
    """Rebuild syndication.json from what the platforms already hold."""
    posts = discover(ROOT)
    adapters = _adapters(args)
    state = state_module.load(ROOT)
    found = 0
    for post in posts:
        for adapter in adapters:
            remote = adapter.find_existing(post.canonical_url)
            if remote is None:
                continue
            # An empty digest never matches, so the next sync re-sends the
            # article rather than trusting a body nobody here has seen.
            state.record(post.key, post.canonical_url, adapter.name, remote, "")
            found += 1
            print(f"{adapter.name:<10} {post.key} -> {remote.url}")
    print(f"\n{found} remote post(s) recorded in {state.path.name}")
    return EXIT_OK


def _status(args) -> int:
    posts = discover(ROOT)
    state = state_module.load(ROOT)
    names = sorted(ADAPTERS)
    print(f"{'post':<48}" + "".join(f"{name:<12}" for name in names))
    for post in posts:
        cells = ""
        for name in names:
            record = state.get(post.key, name)
            cells += f"{'yes' if record else '-':<12}"
        print(f"{post.key[:46]:<48}{cells}")

    for key in sync_module.orphans(state, posts):
        print(f"{key[:46]:<48}(no longer published here)")
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
    render.add_argument(
        "--platform",
        choices=sorted(ADAPTERS),
        help="render in one platform's dialect rather than plain Markdown",
    )
    render.add_argument(
        "--json",
        action="store_true",
        help="print the literal request body instead of the Markdown",
    )
    render.set_defaults(run=_render)

    def add_platform(parser):
        parser.add_argument(
            "--platform",
            default=",".join(sorted(ADAPTERS)),
            help="comma separated platform names",
        )

    sync = commands.add_parser("sync", help="create or update the cross-posts")
    sync.add_argument("posts", nargs="*", help="folder name, slug, or path")
    add_platform(sync)
    sync.add_argument(
        "--dry-run",
        action="store_true",
        help="only read from the platforms, and print what would change",
    )
    sync.add_argument(
        "--force", action="store_true", help="re-send even an unchanged article"
    )
    sync.add_argument(
        "--remote-draft",
        action="store_true",
        help="publish as a draft where the platform supports one",
    )
    sync.add_argument(
        "--skip-asset-check",
        action="store_true",
        help="publish without checking that every image is live first",
    )
    sync.set_defaults(run=_sync)

    reconcile = commands.add_parser(
        "reconcile", help="rebuild the state file from the platforms"
    )
    add_platform(reconcile)
    reconcile.set_defaults(run=_reconcile)

    status = commands.add_parser("status", help="show what is cross-posted where")
    status.set_defaults(run=_status)

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
    except TransportError as error:
        print(f"error: {error}", file=sys.stderr)
        return EXIT_API
