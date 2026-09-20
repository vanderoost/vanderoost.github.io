"""Decide what each platform needs, and do it.

The ordering here is the whole safety argument. Before creating anything, the
adapter is asked whether the platform already holds an article with this
canonical URL, so a syndication.json that was lost, stale, or never committed
costs one extra read instead of publishing a duplicate to somebody's feed.
"""

from __future__ import annotations

import logging
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from .lint import check
from .platforms import ADAPTERS
from .platforms.base import Article, MissingCredentials, TransportError
from .portable import to_portable
from .posts import Post
from .state import State, payload_hash

log = logging.getLogger("syndication.sync")

ABSOLUTE_IMAGE = re.compile(r"!\[[^\]]*\]\((?P<url>https?://[^)\s]+)\)")

CREATE, UPDATE, SKIP = "create", "update", "skip (unchanged)"


@dataclass
class Plan:
    post: Post
    platform: str
    action: str
    remote_id: str | None
    article: Article
    digest: str


def article_for(post: Post, posts: list[Post], adapter, *, published: bool) -> Article:
    body = to_portable(post, posts, adapter.dialect)
    check(body, str(post.source), liquid_tags=adapter.liquid_tags)
    return Article(
        title=post.title,
        body=body,
        description=post.description,
        canonical_url=post.canonical_url,
        cover_url=post.cover_url,
        tags=post.tags,
        slug=post.slug,
        published=published,
    )


def configured(names: list[str], env=os.environ) -> list:
    """The adapters that have credentials. A missing token skips, not fails."""
    ready = []
    for name in names:
        adapter = ADAPTERS[name]
        try:
            adapter.configure(env)
        except MissingCredentials as error:
            log.warning("%s: skipped, %s", name, error)
            continue
        ready.append(adapter)
    return ready


def verify_assets(article: Article, root: Path, site_url: str) -> list[str]:
    """Confirm every image in the body actually exists before a platform caches it.

    dev.to and Hashnode fetch images at publish time and cache what they get,
    including a 404, so an image that is missing for the few seconds around a
    deploy stays missing in the cross-post afterwards. A local build answers
    this for free; without one, ask the live site.
    """
    site = root / "site"
    missing = []
    for match in ABSOLUTE_IMAGE.finditer(article.body):
        url = match.group("url")
        if not url.startswith(site_url):
            continue
        relative = url[len(site_url) :].lstrip("/")
        if site.is_dir():
            if not (site / relative).is_file():
                missing.append(f"{url} (not in the local site/ build)")
            continue
        try:
            call = urllib.request.Request(url, method="HEAD")
            urllib.request.urlopen(call, timeout=15).close()
        except urllib.error.URLError as error:
            missing.append(f"{url} ({error})")
    return missing


def plan_for(
    post: Post,
    posts: list[Post],
    adapter,
    state: State,
    *,
    force: bool,
    published: bool,
) -> Plan:
    article = article_for(post, posts, adapter, published=published)
    digest = payload_hash(adapter.payload(article))
    record = state.get(post.key, adapter.name)

    if record and record.payload_hash == digest and not force:
        return Plan(post, adapter.name, SKIP, record.id, article, digest)

    remote_id = record.id if record else None
    if remote_id is None:
        # No record here does not mean no post there: this is what makes the
        # state file a cache rather than the thing duplicates depend on.
        found = adapter.find_existing(post.canonical_url)
        remote_id = found.id if found else None

    action = UPDATE if remote_id else CREATE
    return Plan(post, adapter.name, action, remote_id, article, digest)


def orphans(state: State, posts: list[Post]) -> list[str]:
    """Articles that were cross-posted and are no longer published here.

    Flipping a post back to draft: true takes it off the site but leaves the
    copies up, which is a surprise worth naming out loud rather than acting on.
    """
    live = {post.key for post in posts}
    return sorted(key for key in state.data["posts"] if key not in live)


def run(
    posts: list[Post],
    selected: list[Post],
    adapters: list,
    state: State,
    root: Path,
    site_url: str,
    *,
    dry_run: bool,
    force: bool,
    published: bool,
    verify: bool,
) -> tuple[int, list[str]]:
    """Returns (number of changes, failures)."""
    changed, failures = 0, []

    for key in orphans(state, posts):
        log.warning(
            "%s was cross-posted but is no longer published here; the copies are "
            "still live",
            key,
        )

    for post in selected:
        for adapter in adapters:
            if published is False and not adapter.supports_drafts:
                log.warning("%s: no draft mode, skipping %s", adapter.name, post.key)
                continue
            try:
                plan = plan_for(
                    post, posts, adapter, state, force=force, published=published
                )
            except Exception as error:
                failures.append(f"{post.key} -> {adapter.name}: {error}")
                continue

            print(f"{plan.action:<20} {adapter.name:<10} {post.key}")
            if plan.action == SKIP or dry_run:
                continue

            if verify:
                missing = verify_assets(plan.article, root, site_url)
                if missing:
                    failures.append(
                        f"{post.key} -> {adapter.name}: missing assets:\n  "
                        + "\n  ".join(missing)
                    )
                    continue
            try:
                if plan.remote_id:
                    remote = adapter.update(plan.remote_id, plan.article)
                else:
                    remote = adapter.create(plan.article)
            except TransportError as error:
                failures.append(f"{post.key} -> {adapter.name}: {error}")
                continue

            state.record(
                post.key, post.canonical_url, adapter.name, remote, plan.digest
            )
            changed += 1
            print(f"{'':20} {'':10} -> {remote.url}")

    return changed, failures
