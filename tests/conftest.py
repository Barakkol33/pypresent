"""Notebooks, built in memory, so no test needs a kernel or a fixture file."""

from __future__ import annotations

import base64
import json
from pathlib import Path

import pytest

from pypresent.blocks import MIME
from pypresent.deck import CONFIG_MIME

# a 1x1 transparent png
PIXEL = base64.b64encode(bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
    "1f15c4890000000a49444154789c6360000002000100ffff03000006000557bfabd4"
    "0000000049454e44ae426082")).decode()


_ids = iter(range(1, 10_000))


def markdown_cell(text: str, tags=()) -> dict:
    return {"cell_type": "markdown", "id": f"c{next(_ids)}",
            "metadata": {"tags": list(tags)},
            "source": text.splitlines(keepends=True)}


def code_cell(source: str = "", outputs=None, tags=(), metadata=None) -> dict:
    return {"cell_type": "code", "execution_count": 1, "id": f"c{next(_ids)}",
            "metadata": {"tags": list(tags), **(metadata or {})},
            "source": source.splitlines(keepends=True), "outputs": list(outputs or [])}


def stream(text: str) -> dict:
    return {"output_type": "stream", "name": "stdout", "text": [text]}


def png_output(data: str = PIXEL) -> dict:
    return {"output_type": "display_data", "data": {"image/png": data}, "metadata": {}}


def plain(text: str) -> dict:
    return {"output_type": "execute_result", "execution_count": 1,
            "data": {"text/plain": [text]}, "metadata": {}}


def declared(payload: dict, mime: str = MIME) -> dict:
    """A cell output carrying a declaration - a slide, or a presentation."""
    return {"output_type": "display_data", "data": {mime: payload,
                                                    "text/plain": ["<declaration>"]},
            "metadata": {}}


def slide_cell(blocks, title="", layout="stack", split=(46, 54), notes="", source="") -> dict:
    payload = {"blocks": blocks, "title": title, "layout": layout,
               "split": list(split), "notes": notes}
    return code_cell(source or "slide(...)", [declared(payload)])


def config_cell(payload: dict) -> dict:
    return code_cell("Presentation(...)", [declared(payload, CONFIG_MIME)])


def write_notebook(path: Path, cells: list[dict]) -> Path:
    path.write_text(json.dumps({
        "cells": cells, "metadata": {"kernelspec": {"name": "python3"}},
        "nbformat": 4, "nbformat_minor": 5}), encoding="utf-8")
    return path


@pytest.fixture
def source_notebook(tmp_path: Path) -> Path:
    """A notebook standing in for the lecture a deck quotes."""
    return write_notebook(tmp_path / "lecture.ipynb", [
        markdown_cell("# The lecture\n"),
        code_cell(
            "# slide: tokenize\n"
            "GENRES = ['a', 'b']\n"
            "def tokenize(text):\n"
            "    # noise\n"
            "    return text.split()\n"
            "print(len(tokenize('a b c')))\n",
            [stream("3\n")]),
        code_cell("# slide: chart\nplt.title('A chart')\nplt.show()\n", [png_output()]),
        code_cell("# slide: quiet\nx = 1\n", []),
    ])


@pytest.fixture
def slides_notebook(tmp_path: Path) -> Path:
    return write_notebook(tmp_path / "talk-slides.ipynb", [
        slide_cell([{"kind": "md", "text": "# A talk\n\nBy someone"}]),
        slide_cell([
            {"kind": "md", "text": "## What it does\n\n- one point\n- another"},
            {"kind": "code", "text": "print('hi')", "lang": "python"},
            {"kind": "out", "text": "hi", "trim": {}},
        ]),
    ])
