"""The README shows a real example, and says so - this is what keeps that true.

Its walkthrough quotes a cell of `demos/05-notebook-lecture.ipynb`, the output
that cell printed, and the `slide()` call from `demos/05-notebook-slides.ipynb`.
All three are pasted into the README, which is the one place in this project
where pasting is unavoidable - so it is the one place that needs a test.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
README = REPO / "README.md"
LECTURE = REPO / "demos" / "05-notebook-lecture.ipynb"
SLIDES = REPO / "demos" / "05-notebook-slides.ipynb"

pytestmark = pytest.mark.skipif(
    not (README.exists() and LECTURE.exists()),
    reason="run from a checkout: the README and the demos are not in the wheel")


def blocks() -> list[tuple[str, str]]:
    """Every fenced code block in the README, as (language, body)."""
    return re.findall(r"```(\w*)\n(.*?)```", README.read_text(encoding="utf-8"), re.S)


def block_holding(needle: str, lang: str | None = None) -> str:
    """The first fenced block containing `needle`, of `lang` if one is named.

    The language matters: the listing and the output it produced can share a
    phrase, and an f-string in the code is not the text it printed.
    """
    found = [body for tag, body in blocks()
             if needle in body and (lang is None or tag == lang)]
    assert found, f"the README no longer has a {lang or 'code'} block with {needle!r}"
    return found[0].strip()


def sources(notebook: Path) -> list[str]:
    nb = json.loads(notebook.read_text(encoding="utf-8"))
    return ["".join(c["source"]).strip() for c in nb["cells"]]


def printed(notebook: Path, name: str) -> str:
    nb = json.loads(notebook.read_text(encoding="utf-8"))
    for cell in nb["cells"]:
        if f"# slide: {name}" in "".join(cell["source"]):
            return "".join("".join(o.get("text", []))
                           for o in cell.get("outputs", [])).strip()
    raise AssertionError(f"no cell named {name!r} in {notebook.name}")


def test_the_lecture_cell_is_quoted_verbatim():
    assert block_holding("# slide: counts", "python") in sources(LECTURE)


def test_the_output_is_the_one_that_cell_actually_printed():
    assert block_holding("distinct tokens", "") == printed(LECTURE, "counts")


def test_the_slide_call_is_quoted_verbatim():
    assert block_holding("code('counts'", "python") in sources(SLIDES)


def test_the_pictures_it_points_at_exist():
    text = README.read_text(encoding="utf-8")
    local = [src for _, src in re.findall(r"!\[([^\]]*)\]\(([^)]+)\)", text)
             if not src.startswith("http")]
    assert local, "the README no longer shows the deck it describes"
    for src in local:
        assert (REPO / src).exists(), f"{src} is missing; run ./demos/screenshot.sh"


def test_every_picture_is_described():
    text = README.read_text(encoding="utf-8")
    for alt, src in re.findall(r"!\[([^\]]*)\]\(([^)]+)\)", text):
        if src.startswith("http"):
            continue                      # a badge describes itself
        assert len(alt) > 20, f"{src} needs alt text that says what is on the slide"


def test_the_files_it_sends_you_to_are_there():
    text = README.read_text(encoding="utf-8")
    links = re.findall(r"(?<!!)\[[^\]]+\]\(([^)#]+)(?:#[^)]*)?\)", text)
    for link in links:
        if link.startswith(("http", "mailto:")):
            continue
        assert (REPO / link).exists(), f"the README links to {link}, which is not there"
