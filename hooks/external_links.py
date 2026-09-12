"""Open every link that leaves the site in a new tab.

Writing { target="_blank" rel="noopener" } after each external link works, but
it is easy to forget and clutters the Markdown. This hook decides it once, on
the final HTML, so it also covers links the theme renders (social icons in the
footer) and links written as raw HTML.

A link counts as external when its href starts with http:// or https:// and
does not point at site_url. Relative links, anchors and mailto: are untouched.
"""

import re
from urllib.parse import urlsplit

# The opening tag of every <a> element. Code blocks are HTML-escaped by the
# time this runs, so examples inside them (&lt;a ...) do not match.
ANCHOR = re.compile(r"<a\b(?P<attrs>[^>]*)>", re.IGNORECASE)

HREF = re.compile(r"""\shref\s*=\s*(["'])(?P<url>https?://[^"']*)\1""", re.I)
TARGET = re.compile(r"\starget\s*=", re.IGNORECASE)
REL = re.compile(r"\srel\s*=", re.IGNORECASE)


def _rewrite(match: re.Match, own_host: str) -> str:
    attrs = match.group("attrs")
    href = HREF.search(attrs)
    if not href or urlsplit(href.group("url")).hostname == own_host:
        return match.group(0)

    # An explicit target or rel written by hand wins.
    if not TARGET.search(attrs):
        attrs += ' target="_blank"'
    if not REL.search(attrs):
        # noopener stops the new tab from reaching back via window.opener.
        attrs += ' rel="noopener"'
    return f"<a{attrs}>"


def on_post_page(output: str, page, config) -> str:
    own_host = urlsplit(config.site_url or "").hostname
    return ANCHOR.sub(lambda m: _rewrite(m, own_host), output)
