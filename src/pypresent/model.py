"""What a slide is, once every source has been read."""

from __future__ import annotations

from dataclasses import dataclass, field

LAYOUTS = ("stack", "split")

#: Element kinds that are prose, and so go on the reading side of a split slide.
PROSE = frozenset({"lead", "subhead", "bullets", "quote"})


@dataclass
class Slide:
    """One slide: a title and an ordered list of elements.

    An element is a plain dict with a ``kind`` - ``lead``, ``subhead``,
    ``bullets``, ``quote``, ``table``, ``code``, ``output``, ``image`` or
    ``rawhtml`` - and whatever that kind needs. Keeping them dicts rather than
    classes is what lets a slide survive a round trip through a notebook cell
    output as JSON.
    """

    title: str = ""
    level: int = 2
    section: str = ""
    elements: list[dict] = field(default_factory=list)
    layout: str = "auto"                 # auto | split | stack
    split: tuple[int, int] = (46, 54)    # prose %, figure % when split
    notes: str = ""

    @property
    def is_empty(self) -> bool:
        return not self.title and not self.elements

    def add(self, kind: str, **kw) -> None:
        self.elements.append({"kind": kind, **kw})

    @property
    def prose(self) -> list[dict]:
        return [el for el in self.elements if el["kind"] in PROSE]

    @property
    def figures(self) -> list[dict]:
        return [el for el in self.elements if el["kind"] not in PROSE]
