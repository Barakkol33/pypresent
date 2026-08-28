"""Reading a notebook as JSON: finding a named cell, and taking things out of it.

Nothing here needs Jupyter installed.  A notebook is a JSON file, and everything
a deck quotes - a listing, what it printed, what it drew - is already in it, so
rendering a deck from a stored notebook costs no kernel and no dependency.
"""

from __future__ import annotations

import html
import json
import re
import textwrap
from pathlib import Path

#: How a lecture cell says what it is called, so a slide can quote it by name.
NAME = re.compile(r"^\s*#\s*slide:\s*([\w.-]+)\s*$", re.M)

ALT_MISSING = "No description has been provided for this image"
PLOT_TITLE = re.compile(r"""(?:plt|ax)\.(?:set_)?(?:sup)?title\(\s*(['"])(.+?)\1""")


def read(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def source(cell: dict) -> str:
    return "".join(cell.get("source", []))


def find_cell(notebook: str | Path, name: str) -> tuple[dict | None, bool]:
    """The cell called `name`, and whether the name had to be guessed at.

    A name is given on purpose and survives every rename and reformat inside the
    cell, which a distinctive-line marker does not.  Matching a raw line is still
    accepted as a fallback, and reported, so nothing breaks silently.
    """
    nb = read(notebook)
    for cell in nb["cells"]:
        if name in NAME.findall(source(cell)):
            return cell, False
    for cell in nb["cells"]:                       # fallback: a line of the cell
        if name in source(cell):
            return cell, True
    return None, False


def elide(text: str) -> str:
    """Drop the cell's `# slide:` name, which is for the build and not for the room."""
    lines = [line for line in text.splitlines() if not NAME.match(line)]
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(lines)


def cut(text: str, trim) -> tuple[str, str | None]:
    """Leave out the lines the deck says to leave out.

    `trim` is a list of what to find, not of where to look.  A string takes out
    the one line that contains it; a `(first, last)` pair takes out everything
    from the line holding `first` through the next line holding `last`, and puts
    a single `...` in its place.  The decision is the deck's, not the source's:
    what a room needs to read is a property of the slide, and the notebook being
    quoted stays clean Python.

    Anchors are content, so they survive an edit somewhere else in the cell - and
    an anchor that no longer matches, or that now matches more than one line, is
    reported rather than guessed at.  Blank lines left directly under an `...`
    come out with it: the ellipsis already says something was removed.
    """
    lines = text.splitlines()

    def hits(needle: str, start: int = 0) -> list[int]:
        return [i for i in range(start, len(lines)) if needle in lines[i]]

    starts, skip, bad = set(), set(), []
    for item in trim or ():
        span = isinstance(item, (tuple, list))
        opening, closing = item if span else (item, item)
        found = hits(opening)
        if not found:
            bad.append(f"{opening!r} matches no line")
            continue
        if len(found) > 1:
            bad.append(f"{opening!r} matches {len(found)} lines")
        first = found[0]
        if not span:
            last = first
        else:
            after = hits(closing, first)
            if not after:
                bad.append(f"{closing!r} matches no line after {opening!r}")
                continue
            last = after[0]
        starts.add(first)
        skip.update(range(first, last + 1))

    kept: list[str] = []
    for i, line in enumerate(lines):
        if i in starts:
            indent = len(line) - len(line.lstrip())
            kept.append(" " * indent + "...")
        elif i in skip:
            continue
        elif line.strip() or not (kept and kept[-1].strip() == "..."):
            kept.append(line)
    return "\n".join(kept), ("; ".join(bad) if bad else None)


def pick(text: str, keep=(), drop=()) -> str:
    """The lines worth showing: `keep` substrings in, `drop` substrings out."""
    lines = elide(text).splitlines()
    if keep:
        lines = [line for line in lines
                 if any(wanted in line for wanted in keep) or line.strip() == "..."]
    if drop:
        lines = [line for line in lines
                 if not any(unwanted in line for unwanted in drop)]
    return textwrap.dedent("\n".join(lines)).strip("\n")


def figures(cell: dict) -> list[str]:
    """Every picture a cell drew, as stored base64."""
    found = []
    for output in cell.get("outputs", []):
        png = output.get("data", {}).get("image/png")
        if png is not None:
            found.append(("".join(png) if isinstance(png, list) else png).strip())
    return found


def printed(cell: dict) -> str:
    """What a cell printed and what it evaluated to, as one block of text."""
    parts = []
    for output in cell.get("outputs", []):
        if output.get("output_type") == "stream":
            parts.append("".join(output.get("text", [])).rstrip())
        elif output.get("output_type") == "execute_result":
            data = output.get("data", {})
            if "text/plain" in data:
                parts.append("".join(data["text/plain"]).rstrip())
    return "\n".join(x for x in parts if x)


def payload(cell: dict, mime: str) -> dict | None:
    """A declaration a cell stored in its outputs under `mime`, if it did."""
    for output in cell.get("outputs", []):
        data = output.get("data", {})
        if mime in data:
            found = data[mime]
            if isinstance(found, list):
                found = json.loads("".join(found))
            return found
    return None


# --------------------------------------------------------------------------
# image descriptions, for the nbconvert exports
# --------------------------------------------------------------------------

def alt_texts(path: str | Path) -> list[str | None]:
    """A description for each image a notebook holds, in the order it holds them.

    nbconvert's own templates emit an output `<img>` with no `alt` at all and no
    way to give it one, so it fills in a placeholder and warns.  The description
    has to come from the notebook: `alt_text` in the cell's metadata if the
    author wrote one, and otherwise the plot's own title, which is what a chart
    is already called.
    """
    nb = read(path)
    alts: list[str | None] = []
    for cell in nb.get("cells", []):
        for output in cell.get("outputs", []):
            if "image/png" not in output.get("data", {}):
                continue
            said = cell.get("metadata", {}).get("alt_text")
            drawn = PLOT_TITLE.search(source(cell))
            alts.append(said or (drawn.group(2) if drawn else None))
    return alts


def describe(page: Path, alts: list[str | None]) -> int:
    """Put those descriptions on the images, and say how many are still without."""
    parts = page.read_text(encoding="utf-8").split(ALT_MISSING)
    if len(parts) == 1:
        return 0
    out, undescribed = parts[0], 0
    for index, part in enumerate(parts[1:]):
        alt = alts[index] if index < len(alts) else None
        undescribed += alt is None
        out += (html.escape(alt, quote=True) if alt else ALT_MISSING) + part
    page.write_text(out, encoding="utf-8")
    return undescribed
