"""Cutting a source - a notebook or a markdown file - into slides."""

from __future__ import annotations

import base64
import re
import sys
from pathlib import Path

from . import nbio
from .blocks import MIME, slide_payload
from .markup import clean_html, inline, trim_text
from .model import Slide

CONFIG_MIME = "application/x-presentation+json"   # a deck's parameters, in a cell output

_HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
_SLIDE_MARK = re.compile(r"^<!--\s*slide\s*-->\s*$", re.I)
_BULLET = re.compile(r"^\s*[-*]\s+(.*)$")
_NUMBERED = re.compile(r"^\s*\d+[.)]\s+(.*)$")
_RULE = re.compile(r"^\s*(-{3,}|\*{3,}|_{3,})\s*$")
_TABLE_SEP = re.compile(r"^\s*\|?[\s:|-]+\|[\s:|-]*$")


def _cells(row: str) -> list[str]:
    row = row.strip()
    if row.startswith("|"):
        row = row[1:]
    if row.endswith("|"):
        row = row[:-1]
    return [c.strip() for c in row.split("|")]


class Deck:
    """Accumulates slides while walking a source."""

    def __init__(self, split_level: int = 3, lang: str = "en", base: Path | None = None,
                 source: Path | None = None) -> None:
        self.split_level = split_level
        self.lang = lang
        self.base = base or Path(".")
        self.source = source          # where a figure() block reads its picture from
        self.one_slide = False        # set while a slide() call is being rendered
        # In a markdown file a `---` line is the usual way to end a slide; in a
        # notebook it is an ordinary horizontal rule, and the cut is by heading.
        self.hr_breaks = False
        self.slides: list[Slide] = []
        self.section = ""
        self.current = Slide()
        self.warnings: list[str] = []

    def warn(self, message: str) -> None:
        self.warnings.append(message)
        print(f"  ! {message}", file=sys.stderr)

    def flush(self) -> None:
        if not self.current.is_empty:
            self.slides.append(self.current)
        self.current = Slide(section=self.section)

    def start(self, title: str = "", level: int = 2) -> None:
        self.flush()
        if level == 1 and title:
            self.section = title
        self.current = Slide(title=title, level=level, section=self.section)

    def add(self, kind: str, **kw) -> None:
        self.current.add(kind, **kw)

    # -- markdown ---------------------------------------------------------

    def add_markdown(self, text: str) -> None:
        """Walk a block of markdown, adding what it says to the current slide.

        A heading up to ``split_level`` starts a new slide and names it; a
        ``---`` or ``<!-- slide -->`` line starts one without a name.  Inside a
        ``slide()`` call neither applies: the call decides where the slide ends,
        so the first heading names it and the rest become subheads.
        """
        lines = text.splitlines()
        i, n = 0, len(lines)
        para: list[str] = []

        def flush_para() -> None:
            if para:
                raw = "\n".join(para).strip()
                self.add("lead", html=inline(raw), text=raw)
                para.clear()

        while i < n:
            line = lines[i]

            if _SLIDE_MARK.match(line) or (self.hr_breaks and _RULE.match(line)):
                flush_para()
                if not self.one_slide:
                    self.start()
                i += 1
                continue

            m = _HEADING.match(line)
            if m:
                flush_para()
                level, title = len(m.group(1)), m.group(2).strip()
                if self.one_slide:
                    if not self.current.title:
                        self.current.title = title
                        self.current.level = level
                        if level == 1:
                            self.section = self.current.section = title
                    else:
                        self.add("subhead", html=inline(title), text=title)
                elif level <= self.split_level:
                    self.start(title=title, level=level)
                else:
                    self.add("subhead", html=inline(title), text=title)
                i += 1
                continue

            if _RULE.match(line):
                flush_para()
                i += 1
                continue

            if not line.strip():
                flush_para()
                i += 1
                continue

            if line.strip().startswith("```"):              # fenced code
                flush_para()
                lang = line.strip()[3:].strip() or "python"
                i += 1
                buf = []
                while i < n and not lines[i].strip().startswith("```"):
                    buf.append(lines[i])
                    i += 1
                i += 1
                self.add("code", text="\n".join(buf), lang=lang)
                continue

            if line.lstrip().startswith("![") and line.rstrip().endswith(")"):
                found = re.match(r"^\s*!\[[^\]]*\]\(([^)]+)\)\s*$", line)
                if found:
                    flush_para()
                    self.add_image_file(found.group(1))
                    i += 1
                    continue

            if line.lstrip().startswith("|") and i + 1 < n and _TABLE_SEP.match(lines[i + 1]):
                flush_para()
                head = _cells(line)
                i += 2
                rows = []
                while i < n and lines[i].lstrip().startswith("|"):
                    rows.append(_cells(lines[i]))
                    i += 1
                self.add("table", head=[inline(c) for c in head],
                         rows=[[inline(c) for c in r] for r in rows],
                         head_raw=head, rows_raw=rows)
                continue

            if line.lstrip().startswith(">"):               # blockquote
                flush_para()
                buf = []
                while i < n and lines[i].lstrip().startswith(">"):
                    q = re.sub(r"^#{1,6}\s+", "", lines[i].lstrip()[1:].strip())
                    buf.append(q)
                    i += 1
                raw = " ".join(buf).strip()
                self.add("quote", html=inline(raw), text=raw)
                continue

            if _BULLET.match(line) or _NUMBERED.match(line):
                flush_para()
                items: list[str] = []
                levels: list[int] = []
                ordered = bool(_NUMBERED.match(line))
                while i < n:
                    m2 = _NUMBERED.match(lines[i]) if ordered else _BULLET.match(lines[i])
                    if m2:
                        indent = len(lines[i]) - len(lines[i].lstrip())
                        items.append(m2.group(1).strip())
                        levels.append(min(indent // 2, 2))     # two spaces is one level in
                        i += 1
                    elif lines[i].startswith(("  ", "\t")) and lines[i].strip() and items:
                        # a wrapped line, not a sub-bullet
                        items[-1] += " " + lines[i].strip()
                        i += 1
                    else:
                        break
                floor = min(levels) if levels else 0
                self.add("bullets", items=[inline(t) for t in items], raw=items,
                         levels=[lv - floor for lv in levels], ordered=ordered)
                continue

            para.append(line)
            i += 1

        flush_para()

    # -- code cells -------------------------------------------------------

    def add_code_cell(self, cell: dict, embed_images: bool = True) -> None:
        meta = cell.get("metadata", {})
        tags = set(meta.get("tags", []))
        # the cell that declares the presentation is the build's, not the room's
        if nbio.payload(cell, CONFIG_MIME) is not None:
            return
        spec = slide_payload(cell)

        # A cell that declares a slide *is* that slide: an ordered list of
        # blocks, text or code, laid out in the order they were written.
        if spec is not None:
            self.start(title=spec.get("title", ""), level=2)
            self.one_slide = True
            self.current.layout = spec.get("layout", "stack")
            self.current.split = tuple(spec.get("split", (46, 54)))
            self.current.notes = spec.get("notes", "")
            for block in spec.get("blocks", []):
                self._add_block(block, embed_images)
            self.one_slide = False
            return

        if "new-slide" in tags:
            self.start(title=meta.get("slide_title", ""), level=3)
        source = nbio.source(cell).rstrip()
        if source and "hide-input" not in tags:
            self.add("code", text=source, lang="python")
        if "hide-output" in tags:
            return
        for output in cell.get("outputs", []):
            self.add_output(output, embed_images)

    def _add_block(self, block: dict, embed_images: bool) -> None:
        kind = block.get("kind")
        if kind == "md":
            text = block.get(self.lang) or block.get("text") or ""
            if not text:                      # a translated block with no text for this lang
                text = next((v for k, v in block.items()
                             if k != "kind" and isinstance(v, str)), "")
            if text:
                self.add_markdown(text)
        elif kind == "code":
            self.add("code", text=block["text"], lang=block.get("lang", "python"))
        elif kind == "out":
            text = trim_text(block.get("text", ""), block.get("trim") or {})
            if text:
                self.add("output", text=text)
        elif kind == "image":
            self.add_image_file(block["path"], embed_images)
        elif kind == "figure":
            self.add_figure(block, embed_images)
        elif kind == "notes":
            self.current.notes = (self.current.notes + "\n" + block["text"]).strip()

    def add_image_file(self, path: str, embed: bool = True) -> None:
        """A picture the slide names by path, embedded so the deck stays one file."""
        if not embed:
            return
        f = Path(path)
        if not f.is_absolute():
            f = self.base / f
        if not f.exists():
            self.warn(f"no such image: {path}")
            return
        kind = {".png": "png", ".jpg": "jpeg", ".jpeg": "jpeg", ".gif": "gif",
                ".webp": "webp", ".svg": "svg+xml"}.get(f.suffix.lower(), "png")
        data = base64.b64encode(f.read_bytes()).decode()
        self.add("image", src=f"data:image/{kind};base64,{data}")

    def add_figure(self, block: dict, embed: bool = True) -> None:
        """A picture the slide names by source cell, read fresh out of that cell."""
        if not embed:
            return
        name = block.get("name", "")
        if self.source is None or not Path(self.source).exists():
            self.warn(f"no source notebook to take the {name!r} figure from")
            return
        cell, _ = nbio.find_cell(Path(self.source), name)
        drawn = nbio.figures(cell) if cell else []
        which = block.get("which", 0)
        if which >= len(drawn):
            self.warn(f"the source cell {name!r} drew no figure {which}")
            return
        self.add("image", src="data:image/png;base64," + drawn[which].replace("\n", ""))

    def add_output(self, output: dict, embed_images: bool = True,
                   trim: dict | None = None) -> None:
        kind = output.get("output_type")
        trim = trim or {}
        if kind == "stream":
            text = trim_text("".join(output.get("text", [])).rstrip(), trim)
            if text:
                self.add("output", text=text)
            return
        if kind == "error":
            text = "\n".join(output.get("traceback", []))
            self.add("output", text=re.sub(r"\x1b\[[0-9;]*m", "", text).rstrip())
            return
        data = output.get("data", {})
        if MIME in data or CONFIG_MIME in data:   # a declaration, not something to show
            return
        if "text/markdown" in data:               # a plain markdown output is slide prose
            self.add_markdown("".join(data["text/markdown"]))
            return
        if "image/png" in data and embed_images:
            png = data["image/png"]
            if isinstance(png, list):
                png = "".join(png)
            self.add("image", src="data:image/png;base64," + png.strip().replace("\n", ""))
            return
        if "text/html" in data:
            self.add("rawhtml", html=clean_html("".join(data["text/html"])))
            return
        if "text/plain" in data:
            text = trim_text("".join(data["text/plain"]).rstrip(), trim)
            if text:
                self.add("output", text=text)


# --------------------------------------------------------------------------
# the two sources
# --------------------------------------------------------------------------

def front_matter(text: str) -> tuple[dict, str]:
    """A leading `---` block of `key: value` lines, and the rest of the file.

    It is metadata and not the first slide - `title`, `date`, `lang`, `theme` -
    so it is taken off the front and handed to the presentation.  Only a fence
    whose first line reads like `key: value` counts, so a deck that genuinely
    opens with a slide break keeps it.  This is deliberately not YAML: a flat
    string map is all a deck needs, and it costs no dependency.
    """
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---", 4)
    if end == -1:
        return {}, text
    block = text[4:end]
    first = block.lstrip().splitlines()[:1]
    if not first or not re.match(r"^[\w-]+\s*:", first[0]):
        return {}, text
    meta = {}
    for line in block.splitlines():
        if ":" in line and not line.lstrip().startswith("#"):
            key, value = line.split(":", 1)
            meta[key.strip()] = value.strip().strip("\"'")
    after = text[end + 4:]
    return meta, (after.split("\n", 1)[1] if "\n" in after else "")


def markdown_meta(path: str | Path) -> dict:
    """What a markdown deck says about itself in its front matter."""
    return front_matter(Path(path).read_text(encoding="utf-8"))[0]


def parse_notebook(path: str | Path, split_level: int = 3, images: bool = True,
                   lang: str = "en", source: Path | None = None) -> list[Slide]:
    """The slides a notebook holds."""
    path = Path(path)
    nb = nbio.read(path)
    deck = Deck(split_level, lang, path.parent, source)
    for cell in nb.get("cells", []):
        if "skip-slide" in set(cell.get("metadata", {}).get("tags", [])):
            continue
        if cell.get("cell_type") == "markdown":
            deck.add_markdown(nbio.source(cell))
        elif cell.get("cell_type") == "code":
            deck.add_code_cell(cell, images)
    deck.flush()
    return deck.slides


def parse_markdown(path: str | Path, split_level: int = 3, images: bool = True,
                   lang: str = "en") -> list[Slide]:
    """The slides a markdown file holds.

    The same cut as a notebook's markdown cells: a heading up to `split_level`
    starts a slide, and so does a ``---`` line - which is how most markdown
    slide tools mark a break, so an existing deck usually just works.
    """
    path = Path(path)
    deck = Deck(split_level, lang, path.parent)
    deck.hr_breaks = True
    text = front_matter(path.read_text(encoding="utf-8"))[1]
    if not images:
        deck.add_image_file = lambda *a, **kw: None   # type: ignore[method-assign]
    deck.add_markdown(text)
    deck.flush()
    return deck.slides


def parse(path: str | Path, split_level: int = 3, images: bool = True,
          lang: str = "en", source: Path | None = None) -> list[Slide]:
    """The slides in whatever this file is."""
    path = Path(path)
    if path.suffix == ".ipynb":
        return parse_notebook(path, split_level, images, lang, source)
    if path.suffix in (".md", ".markdown"):
        return parse_markdown(path, split_level, images, lang)
    raise ValueError(f"a deck is made of a .ipynb or a .md, not {path.suffix!r}")
