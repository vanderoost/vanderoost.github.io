"""Remember which remote post belongs to which article.

syndication.json sits beside redirects.yml. It is JSON rather than YAML
because it is machine-written: redirects.yml earns its YAML by carrying
comments and grouping a generated file cannot keep anyway.

This file is a cache, not the source of truth, and the distinction is what
makes the whole feature safe to run from CI. If it is lost, stale, or never
committed back, every adapter can still find its own post by asking the
platform which article carries this canonical URL. So the worst case is one
extra read, not a duplicate article on somebody's feed.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path

STATE_FILE = "syndication.json"
VERSION = 1


@dataclass(frozen=True)
class Record:
    id: str
    url: str
    payload_hash: str
    synced_at: str


class State:
    def __init__(self, path: Path, data: dict | None = None) -> None:
        self.path = path
        self.data = data or {"version": VERSION, "posts": {}}

    def get(self, key: str, platform: str) -> Record | None:
        entry = self.data["posts"].get(key, {}).get("platforms", {}).get(platform)
        return Record(**entry) if entry else None

    def record(
        self, key: str, canonical_url: str, platform: str, remote, payload_hash: str
    ) -> None:
        post = self.data["posts"].setdefault(key, {})
        post["canonical_url"] = canonical_url
        post.setdefault("platforms", {})[platform] = {
            "id": str(remote.id),
            "url": remote.url,
            "payload_hash": payload_hash,
            "synced_at": dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        self.save()

    def save(self) -> None:
        """Write through a temporary file, so an interrupted run cannot truncate it.

        Called after every single create rather than once at the end: a remote
        id that was never written down is the only failure here that costs
        anything, because it is what turns the next run into a second article.
        """
        text = json.dumps(self.data, indent=2, sort_keys=True) + "\n"
        temp = self.path.with_suffix(".json.tmp")
        temp.write_text(text, encoding="utf-8")
        os.replace(temp, self.path)


def load(root: Path) -> State:
    path = root / STATE_FILE
    if not path.exists():
        return State(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("version") != VERSION:
        raise RuntimeError(f"{path}: unknown state version {data.get('version')!r}")
    data.setdefault("posts", {})
    return State(path, data)


def payload_hash(payload: dict) -> str:
    """Fingerprint the exact request body, so an unchanged post costs nothing.

    Skipping the call when this matches keeps re-runs free and keeps a backfill
    under dev.to's ten-creates-per-thirty-seconds limit, and it makes a diff of
    syndication.json mean "this article genuinely changed".
    """
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
