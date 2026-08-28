"""Slides -> one self-contained HTML file.

Everything the deck needs travels inside it: the stylesheet the theme builds,
the navigation script, and every picture as a data URI.  A deck is one file you
can mail, open from a memory stick, or keep in a repository next to its source.
"""

from __future__ import annotations

import html

from ..markup import inline
from ..model import PROSE, Slide
from ..theme import Theme, deck_js


def _bullets_html(items: list[str], levels: list[int], tag: str) -> str:
    """A bullet list, nested - a sublist lives inside the <li> it belongs to."""
    i = 0

    def build(depth: int) -> str:
        nonlocal i
        parts: list[str] = []
        while i < len(items) and levels[i] >= depth:
            if levels[i] > depth:
                inner = build(depth + 1)
                if parts and parts[-1].endswith("</li>"):
                    parts[-1] = parts[-1][: -len("</li>")] + inner + "</li>"
                else:
                    parts.append(f"<li>{inner}</li>")
            else:
                parts.append(f"<li>{items[i]}</li>")
                i += 1
        klass = "bullets" if depth == 0 else "bullets sub"
        return f'<{tag} class="{klass}">' + "".join(parts) + f"</{tag}>"

    return build(0)


def render_element(el: dict) -> str:
    kind = el["kind"]
    if kind == "lead":
        return f'<p class="lead">{el["html"]}</p>'
    if kind == "subhead":
        return f'<p class="subhead">{el["html"]}</p>'
    if kind == "quote":
        return f'<blockquote class="quote">{el["html"]}</blockquote>'
    if kind == "bullets":
        tag = "ol" if el.get("ordered") else "ul"
        return _bullets_html(el["items"], el.get("levels") or [0] * len(el["items"]), tag)
    if kind == "table":
        head = "".join(f"<th>{c}</th>" for c in el["head"])
        body = "".join(
            "<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>" for row in el["rows"]
        )
        return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"
    if kind == "code":
        return f'<pre class="code"><code>{html.escape(el["text"])}</code></pre>'
    if kind == "output":
        return f'<pre class="output">{html.escape(el["text"])}</pre>'
    if kind == "image":
        alt = html.escape(el.get("alt", ""), quote=True)
        return f'<figure class="image"><img src="{el["src"]}" alt="{alt}"></figure>'
    if kind == "rawhtml":
        return f'<div class="rawhtml">{el["html"]}</div>'
    return ""


def _height(elements: list[dict]) -> float:
    """Roughly how many lines tall a column of these elements will be.

    Prose wraps, so it is measured in characters; code and output do not, so
    they are measured in lines.  Both are converted to lines-at-half-width,
    which is all the ratio needs.
    """
    lines = 0.0
    for el in elements:
        kind = el["kind"]
        if kind == "bullets":
            levels = el.get("levels") or [0] * len(el["items"])
            lines += sum(len(t) / (42 + 8 * lv) + (0.6 if lv == 0 else 0.5)
                         for t, lv in zip(el["items"], levels))
        elif kind in ("lead", "subhead", "quote"):
            lines += len(el["html"]) / 42 + 0.6
        elif kind in ("code", "output"):
            lines += len(el["text"].splitlines()) * 0.8
        elif kind == "image":
            lines += 12
        elif kind == "table":
            lines += len(el["rows"]) * 1.6 + 2
        elif kind == "rawhtml":
            lines += el["html"].count("<tr") * 1.6 + 2
    return max(lines, 1.0)


def _ratio(prose: list[dict], figure: list[dict]) -> tuple[int, int]:
    """Give each column the width that makes the two the same height."""
    share = _height(prose) / (_height(prose) + _height(figure))
    share = min(max(share, 0.34), 0.66)
    a = round(share * 100)
    return a, 100 - a


def _render_body(slide: Slide) -> str:
    """One column, in reading order: the code sits among the bullets.

    ``layout="split"`` puts the prose on the reading side and the code on the
    other - prose first in the DOM, so ``dir="rtl"`` puts it on the right.  It
    is off by default: a slide of a few short bullets does not need two columns,
    and reading order is easier to follow than two parallel tracks.
    """
    prose = [el for el in slide.elements if el["kind"] in PROSE]
    figure = [el for el in slide.elements if el["kind"] not in PROSE]

    if slide.layout != "split" or not prose or not figure:
        body = "".join(render_element(el) for el in slide.elements)
        return f'<div class="body reveal"><div class="fit">{body}</div></div>'

    a, b = _ratio(prose, figure) if tuple(slide.split) == (46, 54) else slide.split
    left = "".join(render_element(el) for el in prose)
    right = "".join(render_element(el) for el in figure)
    return (
        f'<div class="body split reveal">'
        f'<div class="col" style="flex:0 0 {a}%"><div class="fit">{left}</div></div>'
        f'<div class="col" style="flex:0 0 {b}%"><div class="fit">{right}</div></div>'
        f"</div>"
    )


def render_slide(slide: Slide, index: int, total: int, deck_title: str = "",
                 date: str = "") -> str:
    """One <section> per slide: title, two-tone rule, body, footer."""
    cover = index == 0 and slide.level == 1
    notes = f'<div class="notes">{html.escape(slide.notes)}</div>' if slide.notes else ""

    if cover:
        body = "".join(render_element(el) for el in slide.elements)
        title = f'<h1 class="title reveal">{inline(slide.title)}</h1>' if slide.title else ""
        return (
            f'<section class="slide cover">{title}'
            f'<div class="cover-rule reveal"></div>'
            f'<div class="body reveal"><div class="fit">{body}</div></div>'
            f'<div class="cover-band"></div>{notes}</section>'
        )

    title = f'<h2 class="title reveal">{inline(slide.title)}</h2>' if slide.title else ""
    # the deck name is on the cover; repeating it on every slide is noise
    footer = (
        f'<div class="footer"><span>{html.escape(date)}</span>'
        f'<span class="num">{index + 1}</span></div>'
    )
    return (
        f'<section class="slide">{title}<div class="title-rule reveal"></div>'
        f"{_render_body(slide)}{footer}{notes}</section>"
    )


def render_deck(slides: list[Slide], title: str = "", direction: str = "ltr",
                date: str = "", theme: Theme | str | dict | None = None,
                fonts: str = "", hint: str = "", css: str = "",
                lang: str = "") -> str:
    """The whole deck as one file.

    `theme` decides how it looks; `fonts`, `hint` and `css` are per-deck
    overrides on top of it, each falling back to what the theme says.
    """
    theme = Theme.resolve(theme)
    if fonts:
        theme = theme.replace(font=fonts, font_rtl=fonts)
    if css:
        theme = theme.replace(css=theme.css + "\n" + css)
    rtl = direction == "rtl"
    sections = "\n".join(
        render_slide(s, i, len(slides), title, date) for i, s in enumerate(slides)
    )
    hint = hint or theme.hint_for(direction)
    lang = lang or ("he" if rtl else "en")
    return f"""<!doctype html>
<html lang="{lang}" dir="{direction}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="generator" content="pypresent">
<title>{html.escape(title)}</title>
<style>
{theme.stylesheet(direction)}
</style>
</head>
<body>
<div class="progress"><i style="width:0"></i></div>
<main class="deck">
{sections}
</main>
<div class="hint">{html.escape(hint)}</div>
<div class="chrome"><span class="num">1 / {len(slides)}</span><span class="dots"></span></div>
<script>
{deck_js()}
</script>
</body>
</html>
"""
