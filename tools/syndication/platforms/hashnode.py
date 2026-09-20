"""Hashnode, through its GraphQL API.

Two things here differ from dev.to enough to be worth naming. Hashnode answers
a failed mutation with HTTP 200 and an "errors" array, so the status code alone
never means success; and it sometimes answers with an HTML error page, which is
why base._decode refuses to parse a non-JSON body.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping

from ..portable import Dialect
from .base import (
    Article,
    MissingCredentials,
    Remote,
    TransportError,
    request,
    slugify_tag,
)

log = logging.getLogger("syndication.hashnode")

API = "https://gql.hashnode.com/"

MAX_TAGS = 5

DIALECT = Dialect(
    name="hashnode",
    youtube=lambda video_id, caption: (
        f"%[https://www.youtube.com/watch?v={video_id}]"
    ),
)

PUBLISH = """
mutation Publish($input: PublishPostInput!) {
  publishPost(input: $input) { post { id url slug } }
}
"""

UPDATE = """
mutation Update($input: UpdatePostInput!) {
  updatePost(input: $input) { post { id url slug } }
}
"""

# originalArticleURL is Hashnode's canonical field, so this is also how a post
# published by an earlier run is recognised without syndication.json.
MINE = """
query Mine($id: ObjectId!, $after: String) {
  publication(id: $id) {
    posts(first: 50, after: $after) {
      edges { node { id url slug canonicalUrl } }
      pageInfo { hasNextPage endCursor }
    }
  }
}
"""


class Hashnode:
    name = "hashnode"
    dialect = DIALECT
    liquid_tags = False
    # publishPost publishes. Hashnode keeps drafts behind a separate
    # mutation that cannot be updated the same way, so "--remote-draft"
    # skips this platform rather than quietly publishing it live.
    supports_drafts = False

    def __init__(self) -> None:
        self._token = ""
        self._publication = ""
        self._mine: dict[str, Remote] | None = None

    def configure(self, env: Mapping[str, str]) -> None:
        self._token = (env.get("HASHNODE_TOKEN") or "").strip()
        self._publication = (env.get("HASHNODE_PUBLICATION_ID") or "").strip()
        if not self._token:
            raise MissingCredentials("HASHNODE_TOKEN is not set")
        if not self._publication:
            raise MissingCredentials("HASHNODE_PUBLICATION_ID is not set")

    def graphql(self, query: str, variables: dict) -> dict:
        data = request(
            "POST",
            API,
            headers={"Authorization": self._token},
            payload={"query": query, "variables": variables},
        )
        # A GraphQL failure arrives as HTTP 200 with an errors array, so this
        # check is the only thing standing between a failed mutation and a run
        # that reports success.
        if data.get("errors"):
            messages = "; ".join(
                error.get("message", str(error)) for error in data["errors"]
            )
            raise TransportError(f"hashnode: {messages}", 200, str(data)[:500])
        return data["data"]

    def tags(self, tags: tuple[str, ...]) -> list[dict[str, str]]:
        """Hashnode wants tag objects, not strings."""
        out, seen = [], set()
        for tag in tags[: MAX_TAGS * 2]:
            slug = slugify_tag(tag)
            if not slug or slug in seen:
                continue
            seen.add(slug)
            out.append({"slug": slug, "name": tag})
        return out[:MAX_TAGS]

    def payload(self, article: Article) -> dict:
        body = {
            "publicationId": self._publication,
            "title": article.title,
            "contentMarkdown": article.body,
            "slug": article.slug,
            "originalArticleURL": article.canonical_url,
            "tags": self.tags(article.tags),
            "metaTags": {
                "title": article.title,
                "description": article.description,
                "image": article.cover_url,
            },
        }
        if article.cover_url:
            body["coverImageOptions"] = {"coverImageURL": article.cover_url}
        return body

    def create(self, article: Article) -> Remote:
        data = self.graphql(PUBLISH, {"input": self.payload(article)})
        return self._remote(data["publishPost"]["post"])

    def update(self, remote_id: str, article: Article) -> Remote:
        # updatePost replaces tags wholesale rather than merging them, so the
        # full set goes over every time.
        body = self.payload(article)
        body.pop("publicationId", None)
        data = self.graphql(UPDATE, {"input": {"id": remote_id, **body}})
        return self._remote(data["updatePost"]["post"])

    def find_existing(self, canonical_url: str) -> Remote | None:
        if self._mine is None:
            self._mine = {}
            cursor = None
            for _ in range(20):
                page = self.graphql(
                    MINE, {"id": self._publication, "after": cursor}
                )["publication"]["posts"]
                for edge in page["edges"]:
                    node = edge["node"]
                    url = node.get("canonicalUrl")
                    if url:
                        self._mine[url.rstrip("/")] = self._remote(node)
                if not page["pageInfo"]["hasNextPage"]:
                    break
                cursor = page["pageInfo"]["endCursor"]
        return self._mine.get(canonical_url.rstrip("/"))

    @staticmethod
    def _remote(node: dict) -> Remote:
        return Remote(id=str(node["id"]), url=node["url"])
