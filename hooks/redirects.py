"""Turn redirects.yml into short vanderoost.com URLs that forward elsewhere.

GitHub Pages only serves static files: there is nowhere to configure a real
301, so every redirect has to be an HTML page that sends the browser onward by
itself. This hook writes one such page per entry, which keeps the list of short
links in a single flat file instead of a directory of near-identical HTML.

Deliberately not the mkdocs-redirects plugin. It does the same job, but this
site keeps exactly one runtime dependency so the build stays reproducible for
years, and that plugin's keys have to be spelled as Markdown files that do not
exist — it was built for pages that moved, not for short links.
"""

import json
import logging
from pathlib import Path

import yaml
from mkdocs.exceptions import PluginError

log = logging.getLogger("mkdocs.hooks.redirects")

REDIRECTS_FILE = "redirects.yml"

# location.replace() rather than a plain assignment: the stub never becomes a
# history entry, so Back from the target returns the visitor to wherever they
# came from instead of bouncing them forward again. The meta refresh covers
# browsers running without JavaScript. "noindex" keeps the stub itself out of
# search results, while the canonical link points crawlers at the real target.
TEMPLATE = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>Redirecting…</title>
    <link rel="canonical" href="{url}">
    <meta name="robots" content="noindex">
    <meta http-equiv="refresh" content="0; url={url}">
    <script>location.replace({url_js})</script>
  </head>
  <body>
    <p>Redirecting to <a href="{url}">{url}</a>…</p>
  </body>
</html>
"""


class _StrictLoader(yaml.SafeLoader):
    """SafeLoader that refuses a slug listed twice instead of keeping the last."""


def _no_duplicate_keys(loader, node, deep=False):
    seen = set()
    for key_node, _ in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in seen:
            raise PluginError(f"{REDIRECTS_FILE}: '{key}' is listed twice")
        seen.add(key)
    return yaml.SafeLoader.construct_mapping(loader, node, deep)


_StrictLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _no_duplicate_keys
)


def _redirects_file(config):
    return Path(config["config_file_path"]).parent / REDIRECTS_FILE


def _load(source):
    entries = yaml.load(source.read_text(encoding="utf-8"), Loader=_StrictLoader)
    if entries is None:  # An empty file is a valid "no redirects".
        return {}
    if not isinstance(entries, dict):
        raise PluginError(f"{REDIRECTS_FILE}: expected a mapping of slug to URL")
    return entries


def _check(slug, url, site_dir):
    """Fail the build on an entry that would not do what it looks like it does."""
    if not isinstance(slug, str) or not slug.strip("/"):
        raise PluginError(f"{REDIRECTS_FILE}: '{slug}' is not a usable slug")
    if slug != slug.strip("/") or "://" in slug or ".." in slug:
        raise PluginError(
            f"{REDIRECTS_FILE}: '{slug}' must be a bare path, e.g. 'ai-tools'"
        )
    if not isinstance(url, str) or not url.startswith(("http://", "https://")):
        raise PluginError(
            f"{REDIRECTS_FILE}: target for '{slug}' must be an absolute "
            f"http(s) URL, got {url!r}"
        )
    # The site is already fully built by the time this runs, so anything still
    # standing on the slug is a real page. Silently overwriting it would take a
    # published URL off the site without a trace in the diff.
    if (site_dir / slug).exists():
        raise PluginError(
            f"{REDIRECTS_FILE}: '{slug}' collides with a page the site already "
            f"builds at /{slug}/"
        )


def on_post_build(config):
    source = _redirects_file(config)
    if not source.exists():
        return

    site_dir = Path(config["site_dir"])
    entries = _load(source)
    for slug, url in entries.items():
        _check(slug, url, site_dir)
        page = site_dir / slug / "index.html"
        page.parent.mkdir(parents=True, exist_ok=True)
        # The URL lands in HTML attributes and in a JavaScript string literal,
        # which need different escaping. json.dumps() supplies the quotes.
        page.write_text(
            TEMPLATE.format(url=url.replace("&", "&amp;"), url_js=json.dumps(url)),
            encoding="utf-8",
        )

    if entries:
        log.info("Built %d redirect(s) from %s", len(entries), REDIRECTS_FILE)


def on_serve(server, config, builder):
    """Rebuild on edits to redirects.yml, the way a docs page would."""
    source = _redirects_file(config)
    if source.exists():
        server.watch(str(source), builder)
    return server
