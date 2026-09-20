"""dev.to, through Forem's v1 REST API.

Everything is one endpoint with an api-key header. The article body goes over
as Markdown, which is why portable.py exists and why nothing here reshapes
content.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping

from ..portable import Dialect
from .base import Article, MissingCredentials, Remote, request, slugify_tag

log = logging.getLogger("syndication.devto")

API = "https://dev.to/api"

# dev.to allows four tags, and they have to be plain alphanumerics.
MAX_TAGS = 4

# Forem renders body_markdown through Liquid, so this is a real embed rather
# than a literal. lint.py lets a {% through only for the platform that asked.
DIALECT = Dialect(
    name="devto",
    youtube=lambda video_id, caption: "{% embed https://youtu.be/" + video_id + " %}",
    # Forem has no Mermaid renderer, so the fence degrades to a code block.
    mermaid=False,
)


class DevTo:
    name = "devto"
    dialect = DIALECT
    liquid_tags = True
    supports_drafts = True

    def __init__(self) -> None:
        self._key = ""
        self._organization = None
        self._mine: dict[str, Remote] | None = None

    def configure(self, env: Mapping[str, str]) -> None:
        self._key = (env.get("DEVTO_API_KEY") or "").strip()
        if not self._key:
            raise MissingCredentials("DEVTO_API_KEY is not set")
        organization = (env.get("DEVTO_ORGANIZATION_ID") or "").strip()
        self._organization = int(organization) if organization else None

    def _headers(self) -> dict[str, str]:
        return {"api-key": self._key}

    def tags(self, tags: tuple[str, ...]) -> str:
        """Normalise tags, and say so when normalising loses one.

        dev.to strips everything but letters and digits, so "C" and a future
        "C++" both arrive as "c". Dropping the second silently would leave an
        article quietly less tagged than its author wrote it.
        """
        seen: dict[str, str] = {}
        for tag in tags:
            slug = slugify_tag(tag).replace("-", "")
            if not slug:
                continue
            if slug in seen and seen[slug] != tag:
                log.warning(
                    "dev.to: tags %r and %r both normalise to %r; keeping one",
                    seen[slug],
                    tag,
                    slug,
                )
                continue
            seen[slug] = tag
        return ",".join(list(seen)[:MAX_TAGS])

    def payload(self, article: Article) -> dict:
        body = {
            "title": article.title,
            "body_markdown": article.body,
            "published": article.published,
            "canonical_url": article.canonical_url,
            "description": article.description,
            "tags": self.tags(article.tags),
        }
        if article.cover_url:
            body["main_image"] = article.cover_url
        if self._organization is not None:
            body["organization_id"] = self._organization
        return {"article": body}

    def create(self, article: Article) -> Remote:
        data = request(
            "POST", f"{API}/articles", headers=self._headers(),
            payload=self.payload(article),
        )
        return Remote(id=str(data["id"]), url=data["url"])

    def update(self, remote_id: str, article: Article) -> Remote:
        data = request(
            "PUT", f"{API}/articles/{remote_id}", headers=self._headers(),
            payload=self.payload(article),
        )
        return Remote(id=str(data["id"]), url=data["url"])

    def find_existing(self, canonical_url: str) -> Remote | None:
        """Ask dev.to which of my articles already claims this canonical URL.

        This is what makes a lost syndication.json harmless, and it is not
        optional: dev.to rejects a canonical_url that another of your articles
        already uses, so creating blind would fail anyway.
        """
        if self._mine is None:
            self._mine = {}
            for page in range(1, 11):
                articles = request(
                    "GET",
                    f"{API}/articles/me/all?per_page=100&page={page}",
                    headers=self._headers(),
                )
                for item in articles or []:
                    url = item.get("canonical_url")
                    if url:
                        self._mine[url.rstrip("/")] = Remote(
                            id=str(item["id"]), url=item["url"]
                        )
                if len(articles or []) < 100:
                    break
        return self._mine.get(canonical_url.rstrip("/"))
