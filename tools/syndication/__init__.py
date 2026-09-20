"""Cross-post the site's articles to dev.to and Hashnode.

Each platform gets the same article with a canonical URL pointing back at
vanderoost.com, so search engines keep treating this site as the original and
the copies cost nothing in ranking. Run it from the repository root:

    uv run python -m tools.syndication sync --dry-run

The source of truth is the Markdown under docs/articles/posts/, not the built
site and not the RSS feed. Both platforms want Markdown -- body_markdown on
dev.to, contentMarkdown on Hashnode -- and the feed's descriptions are
truncated HTML while the built pages have had every code block turned into
Pygments <span> soup by the time they reach site/. Going back to Markdown from
either is strictly worse than never leaving it. The built site still has one
job here: it is the oracle for whether an image actually exists, which is what
"sync --verify-assets" checks.

Unlike hooks/, the modules in this package can import each other normally.
MkDocs loads each hook by file path without putting its directory on sys.path,
which is why hooks/youtube.py and hooks/drawings.py each carry their own copy
of the same fence walker. That constraint does not apply here, so the walker is
written exactly once, in portable.py, and everything that rewrites Markdown
goes through it.
"""
