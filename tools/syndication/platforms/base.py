"""What every platform adapter shares: the article shape, and HTTP.

The transport is urllib rather than requests for the reason hooks/redirects.py
spells out about plugins: this site keeps its dependency list short so the
build still works in a few years' time. Both APIs are JSON over HTTPS with a
single auth header, and the only thing requests would really save is
retry-on-429, which has to be hand-written anyway to honour Retry-After.
"""

from __future__ import annotations

import datetime as dt
import email.utils
import json
import logging
import re
import time
import urllib.error
import urllib.request
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol

from ..portable import Dialect

log = logging.getLogger("syndication.http")

TIMEOUT = 30
ATTEMPTS = 4
MAX_BACKOFF = 120

# A runaway pagination loop would be indistinguishable from a working backfill
# until the rate limiter noticed, so the whole run gets a ceiling.
MAX_REQUESTS = 200
_sent = 0

# Both APIs sit behind Cloudflare, and urllib's default "Python-urllib/3.x"
# is on its banned-signature list -- Hashnode answers it with a 403 error 1010
# before the request ever reaches GraphQL. Identifying the tool honestly gets
# through, and gives whoever reads their logs something to recognise.
USER_AGENT = "vanderoost-syndication (+https://vanderoost.com)"


class MissingCredentials(RuntimeError):
    """A platform with no token configured. Skipped, not fatal."""


class TransportError(RuntimeError):
    """An API call that failed. Carries enough of the body to be debuggable."""

    def __init__(self, message: str, status: int = 0, body: str = "") -> None:
        super().__init__(message)
        self.status = status
        self.body = body


@dataclass(frozen=True)
class Article:
    """One post, as any platform needs it. Nothing MkDocs-shaped survives here."""

    title: str
    body: str
    description: str
    canonical_url: str
    cover_url: str | None
    tags: tuple[str, ...]
    slug: str
    published: bool


@dataclass(frozen=True)
class Remote:
    id: str
    url: str


class Platform(Protocol):
    name: str
    dialect: Dialect
    liquid_tags: bool
    supports_drafts: bool

    def configure(self, env: Mapping[str, str]) -> None: ...
    def payload(self, article: Article) -> dict: ...
    def create(self, article: Article) -> Remote: ...
    def update(self, remote_id: str, article: Article) -> Remote: ...
    def find_existing(self, canonical_url: str) -> Remote | None: ...


def slugify_tag(tag: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", tag.lower()).strip("-")


def _retry_after(headers, default: float) -> float:
    """Honour Retry-After, which arrives as seconds or as an HTTP date."""
    value = (headers.get("Retry-After") or "").strip()
    if value.isdigit():
        return min(float(value), MAX_BACKOFF)
    when = email.utils.parsedate_to_datetime(value) if value else None
    if when is None:
        return default
    delay = (when - dt.datetime.now(dt.UTC)).total_seconds()
    return min(max(delay, 0.0), MAX_BACKOFF)


def request(
    method: str,
    url: str,
    *,
    headers: Mapping[str, str],
    payload: Any = None,
    timeout: int = TIMEOUT,
) -> Any:
    """One JSON call, retried on the failures that are worth retrying."""
    global _sent
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    sent = {"Accept": "application/json", "User-Agent": USER_AGENT, **headers}
    if body is not None:
        sent["Content-Type"] = "application/json"

    for attempt in range(1, ATTEMPTS + 1):
        _sent += 1
        if _sent > MAX_REQUESTS:
            raise TransportError(f"refusing to make more than {MAX_REQUESTS} requests")

        call = urllib.request.Request(url, data=body, headers=sent, method=method)
        try:
            with urllib.request.urlopen(call, timeout=timeout) as response:
                return _decode(response.read(), response.headers, url)
        except urllib.error.HTTPError as error:
            text = error.read().decode("utf-8", "replace")
            retryable = error.code == 429 or 500 <= error.code < 600
            if not retryable or attempt == ATTEMPTS:
                raise TransportError(
                    f"{method} {url} -> {error.code}: {text[:500]}",
                    error.code,
                    text,
                ) from error
            delay = _retry_after(error.headers, 2.0 ** (attempt - 1))
            log.warning(
                "%s %s -> %s, retrying in %.0fs", method, url, error.code, delay
            )
            time.sleep(delay)
        except urllib.error.URLError as error:
            if attempt == ATTEMPTS:
                raise TransportError(f"{method} {url}: {error.reason}") from error
            time.sleep(2.0 ** (attempt - 1))
    raise TransportError(f"{method} {url}: out of attempts")


def _decode(raw: bytes, headers, url: str) -> Any:
    """Refuse to parse a body that is not JSON.

    Hashnode answers some failures with an HTML error page, and a bare
    JSONDecodeError three frames down says nothing about what went wrong.
    """
    kind = (headers.get("Content-Type") or "").split(";")[0].strip()
    if kind and "json" not in kind:
        text = raw.decode("utf-8", "replace")
        raise TransportError(f"{url}: expected JSON, got {kind}: {text[:500]}")
    return json.loads(raw) if raw else None
