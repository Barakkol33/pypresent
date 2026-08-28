"""Inline markdown -> html, and the small text helpers everything else shares."""

from __future__ import annotations

import html
import re
import textwrap

_CODE_SPAN = re.compile(r"`([^`]+)`")
_BOLD = re.compile(r"\*\*(.+?)\*\*", re.S)
_ITALIC = re.compile(r"(?<!\*)\*(?!\s)(.+?)(?<!\s)\*(?!\*)", re.S)
_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def inline(text: str) -> str:
    """Render the inline markdown a slide actually uses: code, links, bold, italic.

    Code spans are lifted out before escaping and put back afterwards, so a
    backtick span can hold `<`, `&` and quotes without any of it being read as
    markup by the passes that follow.
    """
    protected: list[str] = []

    def stash(m: re.Match) -> str:
        protected.append(f"<code>{html.escape(m.group(1))}</code>")
        return f"\x00{len(protected) - 1}\x00"

    text = _CODE_SPAN.sub(stash, text)
    text = html.escape(text, quote=False)
    text = _LINK.sub(r'<a href="\2">\1</a>', text)
    text = _BOLD.sub(r"<strong>\1</strong>", text)
    text = _ITALIC.sub(r"<em>\1</em>", text)
    text = text.replace("\n", " ")
    return re.sub(r"\x00(\d+)\x00", lambda m: protected[int(m.group(1))], text)


def clean(text: str) -> str:
    """Accept indented triple-quoted blocks written inline in a cell."""
    return textwrap.dedent(text or "").strip("\n")


def trim_text(text: str, trim: dict) -> str:
    """Clip long lines, drop the middle of a long block.

    `trim` is `{'width': n, 'head': n, 'tail': n}`; anything missing is off.
    """
    if not trim or not text:
        return text
    width, head, tail = trim.get("width", 0), trim.get("head", 0), trim.get("tail", 0)
    lines = text.splitlines()
    if width:
        lines = [ln if len(ln) <= width else ln[: width - 1] + "…" for ln in lines]
    if head and tail:
        # eliding one line into an ellipsis saves nothing, so leave it alone
        if len(lines) > head + tail + 1:
            lines = [*lines[:head], "…", *lines[-tail:]]
    elif head and len(lines) > head:            # the first few lines, and no more
        lines = [*lines[:head], "…"]
    return "\n".join(lines)


_STYLE_BLOCK = re.compile(r"<style.*?</style>", re.S | re.I)
_SCRIPT_BLOCK = re.compile(r"<script.*?</script>", re.S | re.I)


def clean_html(fragment: str) -> str:
    """pandas writes a scoped <style> with every frame - drop it, we style tables."""
    fragment = _STYLE_BLOCK.sub("", fragment)
    return _SCRIPT_BLOCK.sub("", fragment).strip()
