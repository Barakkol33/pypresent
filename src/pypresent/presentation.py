"""A deck, described once: what it is made of, and how it is rendered."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar

from . import nbio
from .blocks import code as _code
from .blocks import figure as _figure
from .blocks import image, md, notes, out, slide, slide_payload
from .blocks import result as _result
from .console import say
from .context import activate as _activate
from .context import using
from .deck import CONFIG_MIME, markdown_meta, parse
from .render.html import render_deck
from .render.markdown import render_markdown
from .theme import Theme

HEBREW = re.compile(r"[֐-׿]")
LATIN = re.compile(r"[A-Za-z]")
SLIDE_CALL = re.compile(r"(?:\A|\n)[ \t]*slide[ \t]*\(.*", re.S)
ANSI = re.compile(r"\x1b\[[0-9;]*m")        # a traceback a terminal already coloured

# What a stored declaration carries back to the builder.  `slides` is not among
# them - it is the notebook being read - and `source` travels as a path relative
# to it, so a checkout anywhere still resolves.
CARRIED = ("title", "source", "output", "lang", "direction", "date", "split_level",
           "images", "max_bullets", "max_words", "hint", "fonts", "css", "theme",
           "kernel")


def _short(path: Path) -> str:
    """A path as short as it can be said from where the command was run."""
    try:
        return str(Path(path).resolve().relative_to(Path.cwd().resolve()))
    except ValueError:
        return str(path)


@dataclass
class Presentation:
    """A deck: the files it is made of, and how it is rendered.

    The slide notebook declares one of these in its first cell, and every
    action - build, check, render, export - is a method on it.  Nothing
    about any particular deck lives in the library, so two presentations can be
    built side by side without either knowing about the other::

        deck = Presentation(
            slides='talk-slides.ipynb',   # nothing but slide() calls
            source='talk.ipynb',          # what code() and result() quote
            output='out/talk.html',
            title='...', lang='en', theme='office',
        )

    Paths are taken relative to `base`, which defaults to the slide notebook's
    own directory, so a deck reads the same from wherever the build is run.
    """

    slides: Path                              # the notebook of slide() calls, or a .md
    title: str = ""
    source: Path | None = None                # quoted by code()/result()/figure()
    output: Path | None = None                # the deck; defaults to slides.html
    base: Path | None = None                  # what relative paths are relative to
    lang: str = "en"
    direction: str = ""                       # "" takes rtl for he, ltr otherwise
    date: str = ""
    split_level: int = 3                      # headings up to this level start a slide
    images: bool = True
    theme: Theme | str | dict | None = None   # a name, a file, tokens, or a Theme

    # what `check` complains about: a bullet is a headline, not a sentence
    max_bullets: int = 5
    max_words: int = 20
    # "auto" runs a notebook with the very interpreter pypresent is installed in,
    # which needs no kernelspec registered anywhere - so a fresh virtualenv and a
    # CI runner both work with nothing set up.  Name one to use it instead.
    kernel: str = "auto"

    # per-deck overrides on top of the theme
    hint: str = ""                            # the key legend on the backdrop
    fonts: str = ""                           # a css font stack
    css: str = ""                             # appended after the stylesheet

    activate: bool = True                     # become this notebook's presentation
    lecture: Path | None = None               # deprecated alias for `source`

    # What the command line insisted on; re-reading the declaration must not
    # undo it.  Deliberately unannotated, so it is a plain attribute, not a field.
    _override: ClassVar[dict] = {}
    _warnings: list[str] = field(default_factory=list, repr=False, compare=False, init=False)

    def __post_init__(self) -> None:
        # `base` given: every path is relative to it, the slide notebook
        # included.  `base` not given: the slide notebook is found from where
        # you are and its own directory becomes the base - so a notebook
        # declaring `slides='x.ipynb'` means the one beside it, whatever the
        # working directory is.
        if self.base:
            self.base = Path(self.base).resolve()
            self.slides = self._at(self.slides)
        else:
            self.slides = Path(self.slides).resolve()
            self.base = self.slides.parent
        if self.source is None and self.lecture is not None:
            self.source = self.lecture
        self.source = self._at(self.source) if self.source is not None else None
        self.lecture = self.source            # the old name still reads
        self.output = self._at(self.output) if self.output else self.slides.with_suffix(".html")
        self.direction = self.direction or ("rtl" if self.lang == "he" else "ltr")
        if self.direction not in ("ltr", "rtl"):
            raise ValueError(f"direction must be ltr or rtl, not {self.direction!r}")
        self.theme = Theme.resolve(self.theme)
        if self.activate:
            _activate(self)

    def _at(self, path) -> Path:
        p = Path(path)
        return p if p.is_absolute() else (self.base / p)

    # -- what the notebook calls ------------------------------------------

    slide = staticmethod(slide)
    md = staticmethod(md)
    out = staticmethod(out)
    image = staticmethod(image)
    notes = staticmethod(notes)

    def code(self, name: str, keep=(), drop=(), trim=(), lang: str = "python") -> dict:
        """The listing from the source cell named `name`."""
        with self.current():
            return _code(name, keep, drop, trim, lang)

    def result(self, name: str, keep=(), drop=(), trim: dict | None = None) -> dict:
        """What that same named source cell printed."""
        with self.current():
            return _result(name, keep, drop, trim)

    def figure(self, name: str, which: int = 0) -> dict:
        """The picture that same named source cell drew."""
        with self.current():
            return _figure(name, which)

    def current(self):
        """Make this the active presentation for the duration of the block."""
        return using(self)

    # -- so the builder can read the declaration back out of the notebook --

    def payload(self) -> dict:
        d = {k: getattr(self, k) for k in CARRIED}
        d["theme"] = self.theme.to_dict()
        # paths as the notebook wrote them: both are absolute by now, and a
        # checkout somewhere else has to resolve them against its own folder
        d["source"] = self._relative(self.source)
        d["output"] = self._relative(self.output)
        return d

    def _relative(self, path: Path | None) -> str | None:
        if path is None:
            return None
        try:
            return str(Path(path).resolve().relative_to(Path(self.base).resolve()))
        except ValueError:
            return str(path)

    def _repr_mimebundle_(self, include=None, exclude=None) -> dict:
        quoting = f" · quoting {self.source.name}" if self.source else ""
        return {"text/plain": (f"{self.output.name} · {self.lang}/{self.direction} · "
                               f"{self.theme.name}{quoting}"),
                CONFIG_MIME: self.payload()}

    @classmethod
    def from_notebook(cls, slides: Path, **override) -> Presentation:
        """The presentation a slide notebook declared, read back from its outputs.

        The declaration is stored the way a slide is - as a cell output - so the
        builder needs nothing but the notebook, and `--lang` or `-o` on the
        command line still win over what is written down.
        """
        slides = Path(slides)
        found: dict = {}
        if slides.suffix == ".ipynb":
            for cell in nbio.read(slides).get("cells", []):
                carried = nbio.payload(cell, CONFIG_MIME)
                if carried is not None:
                    found = carried
        else:
            # a markdown deck declares itself in its front matter
            found = {k: v for k, v in markdown_meta(slides).items() if k in CARRIED}
            if "split_level" in found:
                found["split_level"] = int(found["split_level"])
        if "lecture" in found and "source" not in found:      # a deck built before 0.2
            found["source"] = found.pop("lecture")
        insisted = {k: v for k, v in override.items() if v not in (None, "")}
        kw = {k: v for k, v in found.items() if k in CARRIED and v is not None}
        kw.update(insisted)
        deck = cls(slides=slides, activate=False, **kw)
        deck._override = insisted
        return deck

    # -- the actions ------------------------------------------------------

    def check(self, nb=None) -> int:
        """The ways a hand-maintained slide notebook drifts, all reported.

        Returns how many complaints were made.  A slide notebook can drift from
        the source it quotes, say more than a slide can hold, or be left half
        translated; none of that is an error the renderer would catch.
        """
        said = 0

        def warn(message: str) -> None:
            nonlocal said
            said += 1
            self._warnings.append(message)
            say(f"  ! {message}")

        if self.slides.suffix != ".ipynb":
            return 0
        cells = (nb.cells if nb is not None else nbio.read(self.slides).get("cells", []))

        source_text = ""
        if self.source and self.source.exists():
            source_text = "\n".join(nbio.source(c) for c in nbio.read(self.source)["cells"])

        for i, cell in enumerate(cells):
            if cell.get("cell_type") != "code":
                continue
            if nbio.payload(cell, CONFIG_MIME) is not None:
                continue                       # the cell that declares the deck
            spec = slide_payload(cell)
            source = nbio.source(cell)
            if spec is None:
                if "skip-slide" not in cell.get("metadata", {}).get("tags", []):
                    first = source.strip().splitlines()[:1]
                    warn(f"cell {i} declares no slide and is not skipped: {first}")
                continue

            for block in spec.get("blocks", []):        # a reference that stopped matching
                if block.get("error"):
                    warn(f"cell {i}: {block['error']}")

            text = "\n".join(b.get(self.lang) or b.get("text", "")
                             for b in spec.get("blocks", []) if b["kind"] == "md")
            if not text.strip() and not spec.get("blocks"):
                warn(f"cell {i}: nothing on the slide")
                continue
            for part in re.split(r"(?m)^(?:<!--\s*slide\s*-->\s*|#{1,3} .*)$", text):
                # only top-level bullets count: the rule is how many points a
                # slide makes, and an indented bullet is a detail under one
                n = sum(1 for ln in part.splitlines() if ln.startswith(("- ", "* ")))
                if n > self.max_bullets:
                    warn(f"cell {i}: {n} bullets on one slide, more than {self.max_bullets}")
            for line in text.splitlines():          # a bullet is a headline, not a sentence
                words = len(re.sub(r"[*`>_]", "", line).replace("- ", "", 1).split())
                if line.lstrip().startswith(("- ", "* ")) and words > self.max_words:
                    warn(f"cell {i}: {words} words in one bullet: {line.strip()[:52]!r}")
            if self.lang == "he" and len(HEBREW.findall(text)) * 3 < len(LATIN.findall(text)):
                first = next((ln for ln in text.splitlines() if ln.strip()), "")
                warn(f"cell {i}: still in English: {first[:60]!r}")

            code_only = SLIDE_CALL.sub("", source).strip()
            head = code_only.splitlines()[0] if code_only else ""
            if source_text and len(head) > 24 and head not in source_text:
                warn(f"cell {i}: code is no longer in the source notebook: {head[:56]!r}")
        return said

    def read_slides(self):
        """The slides this presentation is made of, whatever it is made of."""
        return parse(self.slides, self.split_level, self.images, self.lang, self.source)

    def render(self, fmt: str = "html", output: Path | None = None) -> int:
        """The stored source, as one file: `html` for the deck, `md` for prose."""
        slides = self.read_slides()
        if not slides:
            print(f"{self.slides.name} produced no slides", file=sys.stderr)
            return 1
        title = self.title or slides[0].title or self.slides.stem
        target = Path(output) if output else (
            self.output if fmt == "html" else self.output.with_suffix(".md"))
        if fmt == "html":
            page = render_deck(slides, title, self.direction, self.date, theme=self.theme,
                               fonts=self.fonts, hint=self.hint, css=self.css, lang=self.lang)
        elif fmt == "md":
            page = render_markdown(slides, title, self.date)
        else:
            raise ValueError(f"a deck is written as html or md, not {fmt!r}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(page, encoding="utf-8")
        say(f"{_short(target)}  ·  {len(slides)} slides  ·  {self.lang}  ·  "
            f"{self.direction}  ·  {self.theme.name}  ·  "
            f"{target.stat().st_size / 1024:.0f} KB")
        return 0

    @contextmanager
    def _kernel(self):
        """The kernel to execute with, made to exist for the duration if need be.

        `kernel="auto"` writes a throwaway kernelspec pointing at this very
        interpreter, so the notebook runs in the environment that has pypresent
        and its imports in it.  That is nearly always what is wanted, and it is
        the only option that needs nothing registered on the machine.
        """
        if self.kernel != "auto":
            yield self.kernel
            return
        with tempfile.TemporaryDirectory() as tmp:
            spec = Path(tmp) / "kernels" / "pypresent"
            spec.mkdir(parents=True)
            (spec / "kernel.json").write_text(json.dumps({
                "argv": [sys.executable, "-m", "ipykernel_launcher",
                         "-f", "{connection_file}"],
                "display_name": "pypresent (this interpreter)",
                "language": "python"}), encoding="utf-8")
            was = os.environ.get("JUPYTER_PATH")
            os.environ["JUPYTER_PATH"] = tmp + (os.pathsep + was if was else "")
            try:
                yield "pypresent"
            finally:
                if was is None:
                    os.environ.pop("JUPYTER_PATH", None)
                else:
                    os.environ["JUPYTER_PATH"] = was

    def _execute(self, nb, where: Path, what: str = "") -> bool:
        """Run a notebook.  True if it ran; False if a cell raised, said plainly.

        A cell that raises is an ordinary thing to happen during a build - a
        missing import, a moved data file - and what you need is the cell and
        the error, not nbclient's own traceback through this call stack on top
        of the notebook's.
        """
        from nbclient import NotebookClient
        from nbclient.exceptions import CellExecutionError, CellTimeoutError

        with self._kernel() as kernel:
            client = NotebookClient(nb, timeout=1800, kernel_name=kernel,
                                    resources={"metadata": {"path": str(where)}})
            try:
                client.execute()
            except (CellExecutionError, CellTimeoutError) as failure:
                self._report_failure(nb, failure, what or "the notebook")
                return False
        return True

    @staticmethod
    def _report_failure(nb, failure, what: str) -> None:
        """The cell that stopped the run, and why - and nothing else.

        The exception does not carry the cell, but the notebook does: the run
        left an error output on it, which is also where the colour codes a
        terminal already interpreted end up written down.
        """
        ename = getattr(failure, "ename", "") or ""
        evalue = getattr(failure, "evalue", "") or ""
        why = f"{ename}: {evalue}".strip(": ") or ANSI.sub(
            "", str(failure)).strip().splitlines()[-1]
        say(f"{what} stopped on a cell - {ANSI.sub('', why)}", sys.stderr)

        failed = next((c for c in nb.cells
                       if any(o.get("output_type") == "error"
                              for o in c.get("outputs", []))), None)
        if failed is None:
            return
        lines = nbio.source(failed).strip().splitlines()
        shown = lines[:6] + (["…"] if len(lines) > 6 else [])
        for line in shown:
            say(f"    {line}", sys.stderr)

    def run_source(self) -> int:
        """Execute the source notebook in place, so what the deck quotes is current.

        `code()`, `result()` and `figure()` are resolved when the slide notebook
        runs, out of whatever the source last printed - so a source that has
        been edited but not re-run puts new code beside an old number on a
        slide.  Which is why a build does this first, and why skipping it is a
        flag you have to type.  This is the one path that writes the source
        notebook.
        """
        import nbformat

        if self.source is None or not self.source.exists():
            print("this presentation declares no source notebook to run", file=sys.stderr)
            return 1
        nb = nbformat.read(self.source, as_version=4)
        if not self._execute(nb, self.source.parent, self.source.name):
            return 1                      # and the notebook on disk is left alone
        nbformat.write(nb, self.source)
        say(self.source.name)
        return 0

    # the old name, for a notebook written against 0.1
    run_lecture = run_source

    def build(self, run_source: bool = True, run_slides: bool = True,
              fmt: str = "html") -> int:
        """Run both notebooks, check the deck, render it.

        The source notebook runs first and the slide notebook second, because
        the deck quotes what the source printed: `code()`, `result()` and
        `figure()` are resolved while the slide notebook executes, out of
        whatever the source last wrote.  Running them the other way round, or
        not running the source at all, is how new code ends up beside an old
        number on a slide - so a full build does both, every time.

        Either run can be skipped when you know it is not needed:
        `run_source=False` while you are only moving slides about,
        `run_slides=False` to check and render what is already stored.  A deck
        that declares no source notebook simply has nothing to run first.
        """
        if not self.slides.exists():
            print(f"no such file: {self.slides}", file=sys.stderr)
            return 1
        if self.slides.suffix != ".ipynb":       # a markdown deck has nothing to run
            return self.render(fmt)

        # only the build needs jupyter installed; a notebook importing this does not
        import nbformat

        if run_source and self.source is not None and self.run_source():
            return 1
        nb = nbformat.read(self.slides, as_version=4)
        deck = self
        if run_slides:
            if not self._execute(nb, self.base, self.slides.name):
                return 1
            nbformat.write(nb, self.slides)
            say(self.slides.name)
            # the notebook declares itself as it runs, so the parameters to
            # check and render with are the ones the run just wrote
            deck = Presentation.from_notebook(self.slides, **self._override)
        deck.check(nb)
        return deck.render(fmt)

    def convert(self, notebooks, fmt: str = "md", code: bool | None = None) -> int:
        """Notebooks straight through nbconvert, into the deck's own output folder.

        This is plain `jupyter nbconvert --to html|markdown` and nothing else,
        so what comes out is what anyone else's notebook export looks like.  Two
        things are chosen for you, and `--code` / `--no-code` overrides the first:

        * **html keeps the source cells, markdown drops them.**  An HTML export
          is the notebook itself, which is the notebook with its code; a
          Markdown one is here to be read as prose.
        * **html is embedded** (`--embed-images`), so the export is one file
          that survives being moved or mailed, with no `_files/` folder beside it.
        """
        targets = [str(n) for n in notebooks if n is not None]
        if not targets:
            print("nothing to export", file=sys.stderr)
            return 1
        self.output.parent.mkdir(parents=True, exist_ok=True)
        cmd = [sys.executable, "-m", "nbconvert",
               "--to", {"md": "markdown"}.get(fmt, fmt),
               "--output-dir", str(self.output.parent)]
        if fmt == "html":
            cmd.append("--embed-images")
        if not (fmt == "html" if code is None else code):
            cmd.append("--no-input")
        done = subprocess.run(cmd + targets, capture_output=True, text=True)
        for line in done.stderr.splitlines():
            if nbio.ALT_MISSING[:20] not in line and "Alternative text" not in line:
                print(line, file=sys.stderr)      # its warning; we are about to fix it
        if done.returncode or fmt != "html":
            return done.returncode
        for target in targets:
            page = self.output.parent / (Path(target).stem + ".html")
            if not page.exists():
                continue
            undescribed = nbio.describe(page, nbio.alt_texts(Path(target)))
            say(f"{_short(page)}  ·  {page.stat().st_size / 1024:.0f} KB")
            if undescribed:
                print(f"  ! {undescribed} image(s) with no description: give the cell "
                      f"an `alt_text` in its metadata, or the plot a title", file=sys.stderr)
        return 0

    def markdown(self, *also, no_input: bool = True) -> int:
        """The source notebook as Markdown, plus any notebook named."""
        return self.convert([self.source] + [self._at(n) for n in also],
                            "md", code=not no_input)

    def to_json(self) -> str:
        """The declaration, as the notebook stores it."""
        return json.dumps(self.payload(), indent=2, ensure_ascii=False)
