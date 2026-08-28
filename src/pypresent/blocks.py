"""What a slide notebook writes: ``slide()`` and the blocks that go inside it.

A block is a plain dict, so a slide survives the round trip through a notebook
cell output as JSON and the deck can be rendered later with no kernel at all.

Three of them - :func:`code`, :func:`result` and :func:`figure` - do not hold
content but a reference to a cell of the *source* notebook, found by the
``# slide: name`` comment that cell carries.  Nothing is ever pasted twice, and
a reference that stops matching is reported by the build rather than going
quietly stale.
"""

from __future__ import annotations

from . import nbio
from .context import active
from .markup import clean

#: A slide, carried in a cell output.
MIME = "application/x-slide+json"

LAYOUTS = ("stack", "split")


# --------------------------------------------------------------------------
# blocks that hold their own content
# --------------------------------------------------------------------------

def md(text: str) -> dict:
    """A prose block.  A bare string in a ``slide()`` call means this."""
    return {"kind": "md", "text": clean(text)}


def out(text: str, trim: dict | None = None) -> dict:
    """A result to show.  ``trim={'width': …, 'head': …, 'tail': …}``."""
    return {"kind": "out", "text": clean(text), "trim": trim or {}}


def image(path: str) -> dict:
    """A picture, by path relative to the deck's base directory."""
    return {"kind": "image", "path": path}


def notes(text: str) -> dict:
    """Speaker notes: kept in the deck, never shown on the slide."""
    return {"kind": "notes", "text": clean(text)}


# --------------------------------------------------------------------------
# blocks quoted from the source notebook
# --------------------------------------------------------------------------

def code(name: str, keep=(), drop=(), trim=(), lang: str = "python") -> dict:
    """The listing from the source cell named `name`.

    The source names the cell with a ``# slide: name`` comment and says nothing
    else about the deck; `trim` says which of its lines the room does not need
    to read, by what they contain - ``trim=['GENRES =', ('# balance', 'seen +=
    1')]`` - and `keep` / `drop` are line substrings for the rare case that is
    not enough.
    """
    lecture = active().lecture
    if lecture is None:
        return {"kind": "code", "text": f"# no source to quote {name!r} from",
                "lang": lang, "error": "this presentation declares no source notebook"}
    cell, guessed = nbio.find_cell(lecture, name)
    if cell is None:
        return {"kind": "code", "text": f"# no source cell named {name!r}",
                "lang": lang, "error": f"no source cell named {name!r}"}
    text, error = nbio.cut(nbio.source(cell), trim)
    block = {"kind": "code", "text": nbio.pick(text, keep, drop), "lang": lang}
    if guessed:
        error = f"{name!r} matched a line, not a `# slide:` name"
    if error:
        block["error"] = error
    return block


def result(name: str, keep=(), drop=(), trim: dict | None = None) -> dict:
    """What that same named source cell printed - so a number on a slide is real."""
    lecture = active().lecture
    if lecture is None:
        return {"kind": "out", "text": f"?? {name}", "trim": {},
                "error": "this presentation declares no source notebook"}
    cell, guessed = nbio.find_cell(lecture, name)
    if cell is None:
        return {"kind": "out", "text": f"?? {name}", "trim": {},
                "error": f"no source cell named {name!r}"}
    block = out(nbio.pick(nbio.printed(cell), keep, drop), trim)
    if guessed:
        block["error"] = f"{name!r} matched a line, not a `# slide:` name"
    return block


def figure(name: str, which: int = 0) -> dict:
    """The picture that same named source cell drew.

    A plot is code output the way a printed number is, so it is quoted by name
    rather than saved next to the deck as a picture of its own: re-run the
    source and the slide shows the new chart, with nothing to update by hand and
    no file to go stale.  `which` picks among several figures.

    Only the name is stored; the image itself is read out of the source notebook
    at render time, so neither notebook carries a second copy of the bytes.
    """
    block = {"kind": "figure", "name": name, "which": which}
    lecture = active().lecture
    if lecture is None:
        block["error"] = "this presentation declares no source notebook"
        return block
    cell, guessed = nbio.find_cell(lecture, name)
    if cell is None:
        block["error"] = f"no source cell named {name!r}"
    elif not nbio.figures(cell):
        block["error"] = f"the source cell {name!r} drew no figure"
    elif guessed:
        block["error"] = f"{name!r} matched a line, not a `# slide:` name"
    return block


# --------------------------------------------------------------------------
# the slide
# --------------------------------------------------------------------------

def _as_block(item) -> dict:
    if isinstance(item, str):
        return md(item)
    if isinstance(item, dict) and "kind" in item:
        return item
    if isinstance(item, dict):                      # {"he": …, "en": …}
        return {"kind": "md", **{k: clean(v) for k, v in item.items()}}
    raise TypeError(f"a slide block is a string or a block(), not {type(item).__name__}")


class SlideSpec:
    """What a cell returns: a slide, described.

    Jupyter shows it as Markdown, so the cell reads like the slide it makes; the
    deck reads the JSON beside it.
    """

    def __init__(self, *blocks, title: str = "", layout: str = "stack",
                 split: tuple[int, int] = (46, 54), notes: str = "") -> None:
        if layout not in LAYOUTS:
            raise ValueError(f"layout must be one of {LAYOUTS}, not {layout!r}")
        self.blocks = [_as_block(b) for b in blocks if b is not None]
        self.title = title
        self.layout = layout
        self.split = list(split)
        self.notes = clean(notes)

    def payload(self) -> dict:
        return {"blocks": self.blocks, "title": self.title,
                "layout": self.layout, "split": self.split, "notes": self.notes}

    @property
    def errors(self) -> list[str]:
        """Every reference on this slide that stopped matching."""
        return [b["error"] for b in self.blocks if b.get("error")]

    def as_markdown(self, lang: str = "en") -> str:
        parts = []
        for b in self.blocks:
            kind = b["kind"]
            if kind == "md":
                parts.append(b.get(lang) or b.get("text") or next(
                    (v for k, v in b.items() if k != "kind" and isinstance(v, str)), ""))
            elif kind == "code":
                parts.append(f"```{b.get('lang', '')}\n{b['text']}\n```")
            elif kind == "out":
                parts.append(f"```\n{b['text']}\n```")
            elif kind == "image":
                parts.append(f"![]({b['path']})")
            elif kind == "figure":
                parts.append(f"*(figure: {b['name']}, drawn by the source notebook)*")
        return "\n\n".join(p for p in parts if p)

    def _repr_mimebundle_(self, include=None, exclude=None) -> dict:
        return {"text/markdown": self.as_markdown(), MIME: self.payload()}

    def __repr__(self) -> str:
        return self.as_markdown()


def slide(*blocks, **kw) -> SlideSpec:
    """Declare the slide this cell is."""
    return SlideSpec(*blocks, **kw)


def slide_payload(cell: dict) -> dict | None:
    """The slide a cell declares, read back out of its stored outputs."""
    return nbio.payload(cell, MIME)
