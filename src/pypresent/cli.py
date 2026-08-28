"""The `pypresent` command.

The deck declares itself, so a command names an action and, at most, the file to
act on.  A flag always wins over what the declaration says.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .presentation import Presentation
from .theme import Theme, available

SOURCES = ("*-slides.ipynb", "*.slides.md", "*-slides.md")


def find_deck(where: Path | None = None) -> Path | None:
    """The deck to act on when the command line names none.

    Exactly one slide file in the folder is unambiguous; more than one is not,
    and saying so beats picking one.
    """
    where = where or Path.cwd()
    found = sorted({p for pattern in SOURCES for p in where.glob(pattern)})
    if len(found) == 1:
        return found[0]
    if not found:
        print(f"no slide file in {where} - name the one you mean "
              f"(looked for {', '.join(SOURCES)})", file=sys.stderr)
    else:
        print(f"{len(found)} slide files in {where} - name the one you mean: "
              + ", ".join(f.name for f in found), file=sys.stderr)
    return None


def load(args) -> Presentation | None:
    named = getattr(args, "deck", None)
    path = Path(named) if named else find_deck()
    if path is None:
        return None
    if not path.exists():
        print(f"no such file: {path}", file=sys.stderr)
        return None
    # a path typed at a shell means what the shell means by it; inside the deck
    # a relative path is relative to the deck, which is a different thing
    output = getattr(args, "output", None)
    return Presentation.from_notebook(
        path,
        lang=getattr(args, "lang", None),
        direction=getattr(args, "direction", None),
        title=getattr(args, "title", None),
        date=getattr(args, "date", None),
        output=output.resolve() if output else None,
        theme=getattr(args, "theme", None),
        split_level=getattr(args, "split_level", None),
        # only the flag being present is an instruction; its absence is not
        images=False if getattr(args, "no_images", False) else None,
    )


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="pypresent",
        description="Slides from a notebook or a markdown file, as one HTML file.")
    p.add_argument("--version", action="version", version=f"pypresent {__version__}")
    sub = p.add_subparsers(dest="command")

    def common(parser):
        parser.add_argument("deck", nargs="?", default=None,
                            help="the slide notebook or markdown file "
                                 "(default: the only one here)")
        parser.add_argument("--lang", default=None, help="e.g. en, he")
        parser.add_argument("--dir", dest="direction", choices=["ltr", "rtl"], default=None)
        parser.add_argument("--theme", default=None,
                            help=f"a built-in ({', '.join(available())}) or a theme file")
        parser.add_argument("--title", default=None)
        parser.add_argument("--date", default=None)
        parser.add_argument("--split-level", type=int, default=None,
                            help="markdown headings up to this level start a slide")
        parser.add_argument("--no-images", action="store_true",
                            help="leave pictures out")
        parser.add_argument("-o", "--output", type=Path, default=None)
        return parser

    # A full build runs the source notebook and then the slide notebook, in that
    # order, so what the deck quotes is what the source last printed.  Both flags
    # take a run away; neither adds one.
    b = common(sub.add_parser(
        "build", help="run both notebooks, check the deck, render it"))
    b.add_argument("--skip-source-run", action="store_true",
                   help="do not run the source notebook; quote what it last printed")
    b.add_argument("--skip-slides-run", action="store_true",
                   help="do not run the slide notebook; check and render what is stored")
    b.add_argument("-f", "--format", dest="fmt", choices=["html", "md"], default="html")

    r = common(sub.add_parser("render", help="render the stored outputs, without executing"))
    r.add_argument("-f", "--format", dest="fmt", choices=["html", "md"], default="html")

    common(sub.add_parser("check", help="what has drifted, said and not corrected"))

    # two flags, not four command names: what to write, and how to write it
    e = common(sub.add_parser("export", help="the deck or the source notebook, as html or md"))
    e.add_argument("-m", "--mode", choices=["slide", "nb"], default="slide",
                   help="the deck the slide file declares, or the source notebook "
                        "straight through nbconvert (default: slide)")
    e.add_argument("-f", "--format", dest="fmt", choices=["html", "md"], default="html")
    e.add_argument("--code", dest="code", action="store_true", default=None,
                   help="nbconvert: keep the source cells (the default for html)")
    e.add_argument("--no-code", dest="code", action="store_false",
                   help="nbconvert: outputs only (the default for md)")
    e.add_argument("--skip-source-run", action="store_true",
                   help="slide+html: do not run the source notebook")
    e.add_argument("--skip-slides-run", action="store_true",
                   help="slide+html: do not run the slide notebook")
    e.add_argument("--also", nargs="*", default=[], metavar="NOTEBOOK",
                   help="further notebooks to convert beside the one chosen")

    t = sub.add_parser("themes", help="the built-in themes, and what is in one")
    t.add_argument("name", nargs="?", default=None,
                   help="print this theme as a file you can edit and pass to --theme")

    return p


def main(argv: list[str] | None = None) -> int:
    p = parser()
    args = p.parse_args(argv)
    if args.command is None:                   # a bare run builds the deck here
        args = p.parse_args(["build"])

    if args.command == "themes":
        if args.name:
            try:
                print(Theme.resolve(args.name).to_toml(), end="")
            except KeyError as why:
                print(why.args[0], file=sys.stderr)
                return 1
            return 0
        for name in available():
            theme = Theme.named(name)
            print(f"{name:<8} {theme.accent}  {(theme.css and 'custom css') or ''}".rstrip())
        return 0

    deck = load(args)
    if deck is None:
        return 1

    if args.command == "export":
        if args.mode == "slide":
            if args.fmt == "html":
                return deck.build(run_source=not args.skip_source_run,
                                  run_slides=not args.skip_slides_run)
            return deck.render("md")
        if deck.source is None:
            print("this presentation declares no source notebook", file=sys.stderr)
            return 1
        return deck.convert([deck.source] + [deck._at(n) for n in args.also],
                            args.fmt, code=args.code)
    if args.command == "build":
        return deck.build(run_source=not args.skip_source_run,
                          run_slides=not args.skip_slides_run, fmt=args.fmt)
    if args.command == "render":
        return deck.render(args.fmt)
    if args.command == "check":
        said = deck.check()
        print(f"{said} thing(s) to look at" if said else "nothing to report")
        return 1 if said else 0
    return deck.render()


if __name__ == "__main__":                     # pragma: no cover
    raise SystemExit(main())
