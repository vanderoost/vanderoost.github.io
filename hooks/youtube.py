"""Turn ![Caption](youtube:VIDEO_ID) in Markdown into a responsive embed.

Writing the <iframe> by hand works, but it is eight attributes of boilerplate
per video and every one of them is a chance to forget loading="lazy" or the
no-cookie domain. This hook keeps that decision in one place, so changing how
every video on the site is embedded is a one-file edit.

Deliberately not the mkdocs-video plugin, for the same reason as
hooks/redirects.py: this site keeps exactly one runtime dependency.

The syntax borrows Markdown's image form on purpose. The caption lands in the
iframe's title attribute, which is what screen readers announce, so the
accessible name cannot be forgotten separately from the embed.
"""

import re

from mkdocs.exceptions import PluginError

# Any ![...](youtube:...) at all, so a malformed id fails the build loudly
# instead of silently rendering as a broken image.
EMBED = re.compile(r"!\[(?P<title>[^\]]*)\]\(youtube:(?P<id>[^)\s]*)\)")

# YouTube ids are exactly 11 characters of URL-safe base64.
VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")

# Fence tracking, so documenting this syntax inside a code block in an article
# does not turn the example into an actual video.
FENCE = re.compile(r"^\s*(?P<fence>```+|~~~+)")

# Splits a line into alternating non-code / inline-code segments.
INLINE_CODE = re.compile(r"(`+[^`]*`+)")

# youtube-nocookie.com defers YouTube's tracking cookies until the visitor
# actually presses play. loading="lazy" keeps the ~1MB player off the initial
# page load for videos below the fold.
TEMPLATE = (
    '<div class="rvo-video">'
    '<iframe src="https://www.youtube-nocookie.com/embed/{id}"'
    ' title="{title}"'
    ' loading="lazy"'
    ' referrerpolicy="strict-origin-when-cross-origin"'
    ' allow="accelerometer; clipboard-write; encrypted-media; gyroscope;'
    ' picture-in-picture; web-share"'
    " allowfullscreen></iframe>"
    "</div>"
)


def _embed(match: re.Match, page_file: str) -> str:
    video_id = match.group("id")
    if not VIDEO_ID.match(video_id):
        raise PluginError(
            f"{page_file}: {video_id!r} is not a YouTube video id. Expected the "
            "11 characters after 'v=' in the watch URL."
        )

    # The title becomes an HTML attribute, so quotes in it would end the
    # attribute early.
    title = match.group("title").replace('"', "&quot;")
    return TEMPLATE.format(id=video_id, title=title)


def on_page_markdown(markdown: str, page, config, files) -> str:
    out, fence = [], None
    for line in markdown.split("\n"):
        opening = FENCE.match(line)
        if fence is None and opening:
            fence = opening.group("fence")
        elif fence is not None and opening and opening.group("fence") >= fence:
            fence = None
        elif fence is None:
            # Only the segments outside inline code are rewritten.
            line = "".join(
                part
                if part.startswith("`")
                else EMBED.sub(lambda m: _embed(m, page.file.src_path), part)
                for part in INLINE_CODE.split(line)
            )
        out.append(line)
    return "\n".join(out)
