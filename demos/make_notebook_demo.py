#!/usr/bin/env python3
"""Write the two notebooks of the notebook demo, already executed.

The point of the demo is that a deck quotes a *lecture* rather than pasting it -
so the demo needs a lecture with real stored outputs: a printed number and a
drawn chart.  Rather than ask everyone who clones this to have a kernel and
matplotlib, the notebooks are generated here once, with their outputs already
in them, and committed.  A build with both runs skipped then renders the deck
with no kernel anywhere near it, which is itself the thing being demonstrated.

    python demos/make_notebook_demo.py      # needs matplotlib; nothing else does
"""

from __future__ import annotations

import base64
import io
import json
from pathlib import Path

HERE = Path(__file__).parent

LECTURE_CELLS = [
    ("markdown", "# The lecture\n\nEvery tool, runnable, in reading order.  The deck\n"
                 "quotes cells of this notebook by name and never pastes them.\n"),
    ("code", "# slide: tokenize\n"
             "STOPWORDS = {'a', 'the', 'of', 'and'}\n"
             "\n"
             "def tokenize(text):\n"
             "    # the deck trims this line away\n"
             "    return [w for w in text.lower().split() if w not in STOPWORDS]\n"
             "\n"
             "print(tokenize('A short sentence of the corpus'))\n"),
    ("code", "# slide: counts\n"
             "from collections import Counter\n"
             "\n"
             "CORPUS = 'the cat sat on the mat and the cat sat again'\n"
             "counts = Counter(tokenize(CORPUS))\n"
             "print(counts.most_common(3))\n"
             "print(f'{len(counts)} distinct tokens')\n"),
    ("code", "# slide: lengths\n"
             "import matplotlib.pyplot as plt\n"
             "\n"
             "lengths = [len(w) for w in tokenize(CORPUS)]\n"
             "plt.figure(figsize=(6, 3.2))\n"
             "plt.hist(lengths, bins=range(1, 8), rwidth=.86, color='#1f5f6b')\n"
             "plt.title('Token length')\n"
             "plt.xlabel('characters')\n"
             "plt.tight_layout()\n"
             "plt.show()\n"),
]

SLIDES_CELLS = [
    ("code", "from pypresent import Presentation, code, figure, result, slide\n"
             "\n"
             "deck = Presentation(\n"
             "    slides='05-notebook-slides.ipynb',\n"
             "    source='05-notebook-lecture.ipynb',\n"
             "    output='out/05-notebook.html',\n"
             "    title='A deck that quotes its lecture',\n"
             "    date='A pypresent demo',\n"
             "    theme='office',\n"
             ")\n"
             "deck\n"),
    ("code", "slide('''\n"
             "# A deck that quotes its lecture\n"
             "\n"
             "Nothing on these slides was pasted.\n"
             "''')\n"),
    ("code", "slide('''\n"
             "## The cell, quoted by name\n"
             "\n"
             "- the lecture names it `# slide: tokenize`\n"
             "- `trim` drops the line the room does not need\n"
             "- rename anything inside it and the slide still finds it\n"
             "''',\n"
             "    code('tokenize', trim=['# the deck trims']),\n"
             ")\n"),
    ("code", "slide('''\n"
             "## And what it printed\n"
             "\n"
             "- `result()` is the cell's own output, not a number typed twice\n"
             "- re-run the lecture and the slide changes with it\n"
             "''',\n"
             "    code('counts', drop=['from collections']),\n"
             "    result('counts'),\n"
             "    layout='split',\n"
             ")\n"),
    ("code", "slide('''\n"
             "## And what it drew\n"
             "\n"
             "- `figure()` stores only the name\n"
             "- the picture is read out of the lecture when the deck is rendered\n"
             "- so there is no PNG beside the deck to go stale or be lost\n"
             "''',\n"
             "    figure('lengths'),\n"
             "    layout='split',\n"
             ")\n"),
    ("code", "slide('''\n"
             "## What the build says\n"
             "\n"
             "- a name that stops matching is **reported**, not guessed at\n"
             "- so is a bullet that has become a sentence\n"
             "- `pypresent audit` says whether every slide still fit\n"
             "''',\n"
             "    notes='the bit to say out loud, which never reaches the slide',\n"
             ")\n"),
]


def chart_png() -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    corpus = "the cat sat on the mat and the cat sat again"
    stop = {"a", "the", "of", "and"}
    lengths = [len(w) for w in corpus.split() if w not in stop]
    plt.figure(figsize=(6, 3.2))
    plt.hist(lengths, bins=range(1, 8), rwidth=.86, color="#1f5f6b")
    plt.title("Token length")
    plt.xlabel("characters")
    plt.tight_layout()
    buffer = io.BytesIO()
    plt.savefig(buffer, format="png", dpi=110)
    plt.close()
    return base64.b64encode(buffer.getvalue()).decode()


def cell(kind: str, source: str, index: int, outputs=None) -> dict:
    base = {"cell_type": kind, "id": f"cell{index}", "metadata": {},
            "source": source.splitlines(keepends=True)}
    if kind == "code":
        base |= {"execution_count": index, "outputs": outputs or []}
    return base


def notebook(cells: list[dict]) -> str:
    return json.dumps({
        "cells": cells,
        "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python",
                                    "name": "python3"},
                     "language_info": {"name": "python", "version": "3.12.0"}},
        "nbformat": 4, "nbformat_minor": 5}, indent=1, ensure_ascii=False) + "\n"


def stream(text: str) -> dict:
    return {"output_type": "stream", "name": "stdout", "text": [text]}


def main() -> None:
    printed = {
        "tokenize": stream("['short', 'sentence', 'corpus']\n"),
        "counts": stream("[('cat', 2), ('sat', 2), ('mat', 1)]\n6 distinct tokens\n"),
        "lengths": {"output_type": "display_data", "metadata": {},
                    "data": {"image/png": chart_png(), "text/plain": ["<Figure>"]}},
    }
    cells = []
    for i, (kind, source) in enumerate(LECTURE_CELLS, start=1):
        name = next((k for k in printed if f"# slide: {k}\n" in source), None)
        cells.append(cell(kind, source, i, [printed[name]] if name else []))
    (HERE / "05-notebook-lecture.ipynb").write_text(notebook(cells), encoding="utf-8")

    # The slide notebook is written unexecuted: `pypresent build` fills in its
    # outputs, and that run is what resolves code(), result() and figure().
    slides = [cell(kind, source, i) for i, (kind, source) in enumerate(SLIDES_CELLS, start=1)]
    (HERE / "05-notebook-slides.ipynb").write_text(notebook(slides), encoding="utf-8")
    print("wrote 05-notebook-lecture.ipynb and 05-notebook-slides.ipynb")


if __name__ == "__main__":
    main()
