"""Color terminal output in ```console blocks with {grn}...{res} marks.

Articles about terminal tools talk about colored output, and a plain console
block cannot show it. Screenshots can, but they are stuck in whichever theme
they were taken in, cannot be copied or searched, and have to be re-shot for
every small change. This hook keeps the output as text and colors it with the
site's own Tokyo Night palette, so it follows the light/dark toggle.

    ```console
    test_mat_mul         {red}-> FAIL{res}
    ```

A mark opens with {red}, {grn}, {yel}, {blu}, {mag} or {cyn} and closes with
{res}, on the same line. Every mark is five characters wide, so marked lines
keep their columns lined up in the Markdown source. tools/ansi2md.py turns captured terminal
output (real ANSI escape codes) into these marks.

Only console blocks are touched, so C code like (float[4]) {0} or an article
documenting this syntax in a ```markdown block stays as written.
"""

import re

from mkdocs.exceptions import PluginError

# Mark name -> CSS color name in extra.css.
COLORS = {
    "red": "red",
    "grn": "green",
    "yel": "yellow",
    "blu": "blue",
    "mag": "magenta",
    "cyn": "cyan",
}

# The highlighted HTML of one console block. Pygments has HTML-escaped the
# text by now, so a literal < in the block is &lt; and any < here is a tag.
# Extra classes from ```console { .rvo-plot } land in the same attribute.
BLOCK = re.compile(
    r'(<div class="language-console\b[^"]*">)(.*?)(</div>)', re.DOTALL
)

MARK = re.compile(r"\{(?P<color>" + "|".join(COLORS) + r")\}(?P<text>.*?)\{res\}")

# A color mark left over after substitution: unclosed, or spanning lines.
# Limited to the known names so output like {foo} in a block is left alone.
LEFTOVER = re.compile(r"\{(?:" + "|".join(COLORS) + r"|res)\}")

# Pygments' console lexer reads any line starting with # as a root prompt, so
# output drawn with # characters (a histogram) comes out as prompt + comment
# tokens in two colors. Articles here never show a root prompt, so those lines
# are re-tagged as plain output. One line, as rendered with line_spans:
LINE = re.compile(
    r'(?P<start><span id="__span-[^"]*"><a [^>]*></a>)'
    r'(?P<content><span class="gp">\s*#[^\n]*)(?P<end>\n</span>)'
)
TAG = re.compile(r"<[^>]+>")


def _color(match: re.Match, page_file: str) -> str:
    text = match.group("text")
    # A mark wrapping a Pygments token boundary would close the token's <span>
    # inside ours and produce broken nesting. Output lines are one token each,
    # so this only fires for marks on prompt lines or across lines.
    if "<" in text:
        raise PluginError(
            f"{page_file}: console color mark {match.group(0)!r} spans more "
            "than one highlighted token. Keep marks on output lines, opened "
            "and closed on the same line."
        )
    return f'<span class="rvo-ansi-{COLORS[match.group("color")]}">{text}</span>'


def _output_line(match: re.Match) -> str:
    text = TAG.sub("", match.group("content"))
    return f'{match.group("start")}<span class="go">{text}</span>{match.group("end")}'


def _block(match: re.Match, page_file: str) -> str:
    body = LINE.sub(_output_line, match.group(2))
    body = MARK.sub(lambda m: _color(m, page_file), body)
    if leftover := LEFTOVER.search(body):
        raise PluginError(
            f"{page_file}: unmatched console color mark {leftover.group(0)!r}. "
            "Close every mark with {res} on the same line it opens."
        )
    return match.group(1) + body + match.group(3)


def on_page_content(html: str, page, config, files) -> str:
    return BLOCK.sub(lambda m: _block(m, page.file.src_path), html)
