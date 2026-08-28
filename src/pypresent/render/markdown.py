"""Slides -> markdown.

The same slides the HTML renderer draws, written as prose: one `##` heading per
slide, separated by a `---` line, which is how most markdown slide tools mark a
break.  So the output is both a readable handout and a deck another tool can
open - and `pypresent` can read it straight back in.

A picture is a data URI by default, which keeps the export one file; pass
``assets=`` a directory to write the images out beside it instead.
"""

from __future__ import annotations

import base64
import hashlib
import re
from pathlib import Path

from ..model import Slide

_DATA_URI = re.compile(r"^data:image/([\w.+-]+);base64,(.*)$", re.S)


def _image(el: dict, assets: Path | None, relative_to: Path | None) -> str:
    src = el.get("src", "")
    alt = el.get("alt", "")
    found = _DATA_URI.match(src)
    if not found or assets is None:
        return f"![{alt}]({src})"
    kind, payload = found.group(1), found.group(2)
    raw = base64.b64decode(payload)
    suffix = {"svg+xml": "svg", "jpeg": "jpg"}.get(kind, kind)
    name = f"{hashlib.sha1(raw).hexdigest()[:12]}.{suffix}"
    assets.mkdir(parents=True, exist_ok=True)
    (assets / name).write_bytes(raw)
    where = assets if relative_to is None else Path(_relative(assets, relative_to))
    return f"![{alt}]({where.as_posix()}/{name})"


def _relative(path: Path, start: Path) -> str:
    try:
        return str(path.resolve().relative_to(start.resolve()))
    except ValueError:
        return str(path)


def _table(el: dict) -> str:
    head = el.get("head_raw") or el["head"]
    rows = el.get("rows_raw") or el["rows"]
    out = ["| " + " | ".join(head) + " |",
           "| " + " | ".join("---" for _ in head) + " |"]
    out += ["| " + " | ".join(r) + " |" for r in rows]
    return "\n".join(out)


def _bullets(el: dict) -> str:
    items = el.get("raw") or el["items"]
    levels = el.get("levels") or [0] * len(items)
    mark = (lambda i: f"{i + 1}.") if el.get("ordered") else (lambda i: "-")
    return "\n".join(f"{'  ' * lv}{mark(i)} {t}"
                     for i, (t, lv) in enumerate(zip(items, levels)))


def render_element(el: dict, assets: Path | None = None,
                   relative_to: Path | None = None) -> str:
    kind = el["kind"]
    if kind in ("lead", "subhead", "quote"):
        text = el.get("text") or el.get("html", "")
        if kind == "subhead":
            return f"### {text}"
        if kind == "quote":
            return "\n".join(f"> {line}" for line in text.splitlines())
        return text
    if kind == "bullets":
        return _bullets(el)
    if kind == "table":
        return _table(el)
    if kind == "code":
        return f"```{el.get('lang', '')}\n{el['text']}\n```"
    if kind == "output":
        return f"```\n{el['text']}\n```"
    if kind == "image":
        return _image(el, assets, relative_to)
    if kind == "rawhtml":
        return el["html"]
    return ""


def render_slide(slide: Slide, index: int = 0, assets: Path | None = None,
                 relative_to: Path | None = None, notes: bool = True) -> str:
    parts = []
    if slide.title:
        parts.append(("# " if index == 0 and slide.level == 1 else "## ") + slide.title)
    parts += [render_element(el, assets, relative_to) for el in slide.elements]
    if notes and slide.notes:
        parts.append("<!-- notes:\n" + slide.notes + "\n-->")
    return "\n\n".join(p for p in parts if p)


def render_markdown(slides: list[Slide], title: str = "", date: str = "",
                    assets: Path | str | None = None, relative_to: Path | str | None = None,
                    notes: bool = True, front_matter: bool = True) -> str:
    """The whole deck as one markdown document."""
    assets = Path(assets) if assets else None
    relative_to = Path(relative_to) if relative_to else None
    head = ""
    if front_matter and (title or date):
        lines = ["---"]
        if title:
            lines.append(f"title: {title}")
        if date:
            lines.append(f"date: {date}")
        lines += ["---", ""]
        head = "\n".join(lines)
    body = "\n\n---\n\n".join(
        render_slide(s, i, assets, relative_to, notes) for i, s in enumerate(slides))
    return head + body + "\n"
