"""Re-read finished Markdown and refuse anything portable.py did not translate.

This is the cheapest insurance in the package. Every construct portable.py
handles was added because a post used it; the ones it does not handle yet will
arrive the same way, in an article written months from now, and the failure
mode without this check is silent -- the cross-post publishes with "!!! note"
sitting in the middle of a paragraph and nobody looks, because the run said it
succeeded.

So the rule is the one mkdocs --strict already applies to this site: an
unrecognised construct stops the run and names the post and the line.
"""

from __future__ import annotations

import re

from .portable import scan

# Each entry is (pattern, what to tell the author). The patterns run only
# outside code, so an article quoting this syntax is not flagged for it.
SUSPECTS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"^(!!!|\?\?\?)"), "an untranslated admonition"),
    (re.compile(r'^===\+?[ \t]+"'), "an untranslated content tab"),
    (re.compile(r"--8<--"), "a pymdownx.snippets marker"),
    (re.compile(r":(?:material|fontawesome|octicons|simple)-[\w-]+:"), "an icon"),
    (re.compile(r"\]\((?:drawing|youtube):"), "an untranslated pseudo image"),
    (re.compile(r"\{[ \t]*[.#][\w-]"), "an attr_list"),
    (re.compile(r"\{(?:\+\+|--|~~|==)"), "a pymdownx.critic mark"),
    # Narrow on purpose: a shell shebang, `#!/bin/bash`, is legitimate inline
    # code and must not be reported. Only a bare language name followed by the
    # code it highlights is inlinehilite.
    (re.compile(r"`#![\w+#.-]+[ \t]"), "a pymdownx.inlinehilite marker"),
    (re.compile(r"(?<!\+)\+\+[\w+-]+\+\+"), "a pymdownx.keys shortcut"),
    # Relative image targets. Anything without a scheme would resolve against
    # the platform's own domain and 404 there.
    (
        re.compile(r"!\[[^\]]*\]\((?!https?://|data:)[^)]*\)"),
        "a relative image path",
    ),
    # The lookbehind keeps an image from being reported as a link as well.
    (
        re.compile(r"(?<!!)\[[^\]]*\]\((?!https?://|#|mailto:)[^)]*\)"),
        "a relative link",
    ),
]

# dev.to renders body_markdown through Liquid, so a stray {% is not a typo in
# the output -- it is a 422 from the API, or worse, a rendered template.
LIQUID = re.compile(r"\{%")


class LintError(RuntimeError):
    """Markdown that must not be published. Names the post and the line."""


def check(body: str, where: str, *, liquid_tags: bool = False) -> None:
    problems = []
    for number, (line, in_code) in enumerate(scan(body), start=1):
        if in_code:
            continue
        stripped = line.strip()
        for pattern, describe in SUSPECTS:
            if pattern.search(stripped):
                problems.append(f"  line {number}: {describe}: {stripped[:70]}")
        if not liquid_tags and LIQUID.search(stripped):
            problems.append(f"  line {number}: a Liquid tag: {stripped[:70]}")

    # dev.to reads a leading --- block as article frontmatter and swallows it.
    if body.lstrip().startswith("---"):
        problems.append("  line 1: starts with ---, which dev.to reads as frontmatter")

    if problems:
        raise LintError(
            f"{where}: {len(problems)} thing(s) a platform cannot render:\n"
            + "\n".join(problems)
        )
