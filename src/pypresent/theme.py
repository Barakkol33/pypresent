"""How a deck looks, as data.

A :class:`Theme` is a flat set of named tokens - colours, sizes, font stacks -
and the stylesheet is written entirely in terms of them.  Restyling a deck is
therefore changing values, not forking a renderer::

    Presentation(..., theme="office")                     # a built-in, by name
    Presentation(..., theme=Theme.named("dark").replace(accent="#7fd1c1"))
    Presentation(..., theme="themes/house-style.toml")    # a file
    Presentation(..., theme={"accent": "#a8441f"})        # tokens over the default

`css` stays the last resort: whatever it holds is appended after the stylesheet,
so a deck can still reach a selector no token covers.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, fields, replace
from pathlib import Path

try:                                     # tomllib is stdlib from 3.11
    import tomllib
except ModuleNotFoundError:              # pragma: no cover - 3.10 only
    import tomli as tomllib  # type: ignore[no-redef]

ASSETS = Path(__file__).parent / "assets"
THEMES = Path(__file__).parent / "themes"

#: Every token, and the CSS custom property it sets.  Adding a token means
#: adding a field below and a line here; the stylesheet then just uses it.
VARIABLES = {
    # palette
    "accent": "--pp-accent",
    "accent2": "--pp-accent2",
    "ink": "--pp-ink",
    "muted": "--pp-muted",
    "line": "--pp-line",
    "canvas": "--pp-canvas",
    "backdrop": "--pp-backdrop",
    "soft": "--pp-soft",
    "inline_ink": "--pp-inline-ink",
    "code_bg": "--pp-code-bg",
    "code_fg": "--pp-code-fg",
    "out_bg": "--pp-out-bg",
    "out_fg": "--pp-out-fg",
    "row_alt": "--pp-row-alt",
    "head_fg": "--pp-head-fg",
    "frame": "--pp-frame",
    # type
    "mono": "--pp-mono",
    "title_size": "--pp-title",
    "cover_title_size": "--pp-cover-title",
    "lead_size": "--pp-lead",
    "subhead_size": "--pp-subhead",
    "bullet_size": "--pp-bullet",
    "quote_size": "--pp-quote",
    "code_size": "--pp-code",
    "table_size": "--pp-table",
    "footer_size": "--pp-footer",
    "title_weight": "--pp-title-weight",
    "cover_title_weight": "--pp-cover-weight",
    "title_tracking": "--pp-title-tracking",
    # shape
    "padding": "--pp-pad",
    "radius": "--pp-radius",
    "rule": "--pp-rule",
    "bullet_gap": "--pp-bullet-gap",
    "bullet_glyph": "--pp-bullet-glyph",
    "subbullet_glyph": "--pp-subbullet-glyph",
    "image_max": "--pp-image-max",
    "frame_width": "--pp-frame-width",
    "frame_shadow": "--pp-frame-shadow",
    "stage_shadow": "--pp-stage-shadow",
    "motion": "--pp-motion",
}

#: Tokens that are not CSS variables of their own: the font stack depends on the
#: direction, and these two are plain text the page carries.
META = ("name", "font", "font_rtl", "css", "hint", "hint_rtl")


@dataclass(frozen=True)
class Theme:
    """A deck's look, as tokens.  The defaults are the ``warm`` built-in."""

    name: str = "warm"

    # -- palette ----------------------------------------------------------
    accent: str = "#a8441f"
    accent2: str = "#1f5f6b"
    ink: str = "#1a1815"
    muted: str = "#6f6a61"
    line: str = "#e2ddd3"
    canvas: str = "#faf7f2"
    backdrop: str = "#e8e0d4"
    soft: str = "#f2e7de"
    inline_ink: str = "#5c2a12"
    code_bg: str = "#2b2723"
    code_fg: str = "#f0ebe3"
    out_bg: str = "#f4f1ea"
    out_fg: str = "#33302b"
    row_alt: str = "#f6efe7"
    head_fg: str = "#fdfbf7"
    frame: str = "#ffffff"

    # -- type -------------------------------------------------------------
    font: str = ('Calibri, Candara, "Segoe UI", Carlito, system-ui, '
                 "-apple-system, sans-serif")
    font_rtl: str = ('Calibri, "Segoe UI", "Noto Sans Hebrew", "Arial Hebrew", '
                     "Carlito, system-ui, sans-serif")
    mono: str = 'Consolas, "Cascadia Mono", ui-monospace, Menlo, monospace'
    title_size: str = "6.4cqh"
    cover_title_size: str = "8.4cqh"
    lead_size: str = "4cqh"
    subhead_size: str = "4.4cqh"
    bullet_size: str = "4.2cqh"
    quote_size: str = "4.2cqh"
    code_size: str = "2.6cqh"
    table_size: str = "3.2cqh"
    footer_size: str = "2cqh"
    title_weight: str = "400"
    cover_title_weight: str = "300"
    title_tracking: str = "-.01em"

    # -- shape ------------------------------------------------------------
    padding: str = "6cqh 7cqh 8cqh"
    radius: str = ".9cqh"
    rule: str = ".42cqh"
    bullet_gap: str = "2.4cqh"
    bullet_glyph: str = '"\\25CF"'
    subbullet_glyph: str = '"\\2013"'
    image_max: str = "46cqh"
    frame_width: str = ".5cqh"
    frame_shadow: str = "0 1.2cqh 3cqh rgba(0,0,0,.18)"
    stage_shadow: str = "0 0 30px rgba(90,70,50,.18)"
    motion: str = ".45s"

    # -- text the page carries --------------------------------------------
    hint: str = "← → · SPACE · F fullscreen"
    hint_rtl: str = "← → · רווח · F מסך מלא"
    css: str = ""                       # appended after the stylesheet

    # -- building on one ---------------------------------------------------

    def replace(self, **tokens) -> Theme:
        """This theme with some tokens changed.  Unknown names are an error."""
        unknown = set(tokens) - {f.name for f in fields(self)}
        if unknown:
            raise TypeError(
                f"no such theme token: {', '.join(sorted(unknown))}.  "
                f"Known tokens: {', '.join(sorted(f.name for f in fields(self)))}")
        return replace(self, **tokens)

    def font_for(self, direction: str) -> str:
        return self.font_rtl if direction == "rtl" else self.font

    def hint_for(self, direction: str) -> str:
        return self.hint_rtl if direction == "rtl" else self.hint

    # -- becoming a stylesheet ---------------------------------------------

    def variables(self, direction: str = "ltr") -> str:
        """The ``:root`` block: every token, plus what the direction decides."""
        rtl = direction == "rtl"
        lines = [f"  {css}: {getattr(self, name)};" for name, css in VARIABLES.items()]
        lines += [
            f"  --pp-font: {self.font_for(direction)};",
            f"  --pp-start: {'right' if rtl else 'left'};",
            f"  --pp-rule-dir: {'270deg' if rtl else '90deg'};",
        ]
        return ":root{\n" + "\n".join(lines) + "\n}"

    def stylesheet(self, direction: str = "ltr") -> str:
        """Everything that goes inside the deck's one ``<style>``."""
        base = (ASSETS / "deck.css").read_text(encoding="utf-8")
        return f"{self.variables(direction)}\n{base}\n{self.css}"

    # -- travelling as data -------------------------------------------------

    def to_dict(self, full: bool = False) -> dict:
        """The theme as plain data.  By default only what differs from the base.

        A deck's declaration is stored in a notebook cell output, so it has to
        be JSON; and storing only the changes keeps that record readable and
        lets a later version of a built-in theme still reach the deck.
        """
        d = asdict(self)
        if full:
            return d
        base = asdict(Theme.named(self.name)) if self.name in available() else asdict(Theme())
        return {"name": self.name, **{k: v for k, v in d.items()
                                      if k != "name" and v != base[k]}}

    def to_toml(self) -> str:
        """The theme as a file you can edit - every token, with its value."""
        out = [f"# {self.name}: a pypresent theme.  Load it with",
               f"#     Presentation(..., theme='{self.name}.toml')", ""]
        for f in fields(self):
            if f.name == "name":
                continue
            value = getattr(self, f.name)
            if f.name == "css" and not value:
                continue
            out.append(f"{f.name} = {json.dumps(value)}")
        return "\n".join(out) + "\n"

    # -- getting one --------------------------------------------------------

    @classmethod
    def named(cls, name: str) -> Theme:
        """A built-in theme."""
        path = THEMES / f"{name}.toml"
        if not path.exists():
            raise KeyError(f"no such built-in theme: {name!r}.  "
                           f"There is {', '.join(available())}")
        return cls.load(path, name=name)

    @classmethod
    def load(cls, path: str | Path, name: str = "") -> Theme:
        """A theme from a ``.toml``, ``.json`` or ``.yaml`` file."""
        path = Path(path)
        text = path.read_text(encoding="utf-8")
        if path.suffix == ".json":
            data = json.loads(text)
        elif path.suffix in (".yaml", ".yml"):
            import yaml  # an extra: pypresent[yaml]
            data = yaml.safe_load(text) or {}
        else:
            data = tomllib.loads(text)
        data = dict(data.get("theme", data))         # a [theme] table is optional
        base = cls.named(data.pop("base")) if "base" in data else cls()
        return base.replace(name=name or data.pop("name", path.stem),
                            **{k: v for k, v in data.items() if k != "name"})

    @classmethod
    def resolve(cls, spec: Theme | str | dict | Path | None) -> Theme:
        """Whatever a deck was given, as a Theme.

        A name is a built-in, anything that looks like a path is a file, a dict
        is tokens over the default, and ``None`` is the default.
        """
        if spec is None:
            return cls()
        if isinstance(spec, Theme):
            return spec
        if isinstance(spec, dict):
            data = dict(spec)
            base = cls.named(data.pop("base")) if "base" in data else cls()
            if data.get("name") in available() and "base" not in spec:
                base = cls.named(data["name"])
            return base.replace(**data)
        text = str(spec)
        if text in available():
            return cls.named(text)
        path = Path(text)
        if path.exists():
            return cls.load(path)
        raise KeyError(f"no theme {text!r}: not a built-in ({', '.join(available())}) "
                       f"and no such file")


def available() -> list[str]:
    """The built-in themes, by name."""
    return sorted(p.stem for p in THEMES.glob("*.toml"))


def deck_js() -> str:
    return (ASSETS / "deck.js").read_text(encoding="utf-8")

