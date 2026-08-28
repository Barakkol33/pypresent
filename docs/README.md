# pypresent documentation

Everything on one page. [The project README](../README.md) is the short version;
[`demos/`](../demos/) is the same thing as decks you can open.

- [Quickstart](#quickstart) — install, and a deck from markdown or a notebook
- [Writing slides](#writing-slides) — every block, and what it is for
- [Themes](#themes) — every token, and how to ship your own
- [The command line](#the-command-line) — every command and flag
- [The Python API](#the-python-api) — using it from Python rather than the shell

---

## Quickstart

### Install

```bash
pip install pypresent              # render a stored notebook or a markdown file
pip install "pypresent[jupyter]"   # and execute notebooks (nbclient, nbconvert)
```

Rendering needs nothing but Python: a notebook is a JSON file, and everything a
deck quotes is already in it. Jupyter is only needed to *run* one.

### A deck from markdown, in one minute

```markdown
---
title: A talk
theme: office
date: March 2026
---

## A talk

The line under the title on the cover.

---

### What it does

- one point
- another, with `code` in it
- a third

---

### And some code

```python
def tokenize(text):
    return text.lower().split()
```
```

```bash
pypresent render talk.md
```

`talk.html` is beside it: one file, no assets folder. Open it and use `→` /
`space` to move, `f` for fullscreen, `home` / `end` for the ends. The slide
number is in the URL, so a link goes to a slide.

### A deck from a notebook

Two notebooks, and the deck never pastes from the lecture.

**`talk.ipynb`** — the lecture. A cell that a slide will quote is named:

```python
## slide: tokenize
def tokenize(text):
    return text.lower().split()

print(len(tokenize("A short sentence")))
```

**`talk-slides.ipynb`** — the deck. The first cell declares it:

```python
from pypresent import Presentation, slide, code, result, figure

deck = Presentation(
    slides='talk-slides.ipynb',
    source='talk.ipynb',
    output='out/talk.html',
    title='A talk', theme='office',
)
deck                          # the last line, so the cell stores the declaration
```

and every cell after it is one slide:

```python
slide('''
### Tokenizing

- split on whitespace, lowercased
- **three** tokens out of that sentence
''',
    code('tokenize'),
    result('tokenize'),
)
```

Then:

```bash
pypresent build               # run the notebook, check it, write out/talk.html
```

### The loop while you are writing

```bash
pypresent build --no-run      # skip the kernel; check and render what is stored
pypresent render              # skip the check too - the fast one
pypresent check               # only what has drifted
pypresent audit               # did any slide have to shrink to fit?
```

`audit` needs Chrome, and is the one worth running before you present:

```
talk.html at 1920x1080
    4  scale 0.812  Tokenizing  <<< TOO SMALL
    9  fills 8%  A short slide  <<< nearly empty
1 slide(s) below 0.90
```

### Where to go next

- [Writing slides](#writing-slides) — every block and what it is for
- [Themes](#themes) — every token
- [The CLI](#the-command-line) — every command and flag
- [The API](#the-python-api) — using it from Python rather than the shell

---

## Writing slides

### The two ways in

#### A markdown file

A heading up to `--split-level` (3 by default, so `###`) starts a slide and
names it. A `---` line starts one without a name. Everything else — paragraphs,
bullets, fenced code, tables, blockquotes, images — lands on the slide that is
open.

A leading `---` block of `key: value` lines is front matter, not the first
slide. It can set `title`, `date`, `lang`, `direction`, `theme`, `split_level`
and `output`.

#### A notebook

The same rules apply to markdown cells, with two differences: `---` is an
ordinary horizontal rule (write `<!-- slide -->` for a break), and code cells
put their source and their output on the open slide.

Cell tags decide what a code cell contributes:

| tag | what it does |
| --- | --- |
| `skip-slide` | the cell contributes nothing |
| `hide-input` | the output, not the source |
| `hide-output` | the source, not the output |
| `new-slide` | starts a slide of its own — how to stop a long listing from crowding the prose above it |

A `new-slide` cell takes its title from `metadata.slide_title` if that is set.

### `slide()`: a cell that is one slide

The looser cutting above is for a notebook that was written as a lecture. When
the notebook *is* the deck, one cell declares one slide and nothing is inferred:

```python
slide(
    '''
    ## What it does

    - one point
    - another
    ''',
    code('tokenize'),
    result('tokenize'),
    layout='split',
    notes='the bit to say out loud, which never reaches the slide',
)
```

The first heading in the call names the slide; any further heading is a
subhead, because the call — not a heading — decides where the slide ends.

A bare string is prose. Everything else is a block:

| block | what it is |
| --- | --- |
| `md(text)` | prose. A bare string means this |
| `out(text, trim=…)` | a result to show, as typed |
| `image(path)` | a picture by path, embedded as a data URI |
| `notes(text)` | speaker notes; kept in the deck, never on the slide |
| `code(name, …)` | the listing from the source cell called `name` |
| `result(name, …)` | what that cell printed |
| `figure(name, which=0)` | what that cell drew |

`{'en': …, 'he': …}` in place of a string is one block in two languages; the
deck's `lang` picks.

### Quoting, so nothing is pasted twice

The source notebook names a cell with a comment and says nothing else about the
deck:

```python
## slide: tokenize
GENRES = ['a', 'b']

def tokenize(text):
    # a line the room does not need
    return text.lower().split()
```

A name is given on purpose and survives every rename and reformat inside the
cell, which matching a distinctive line does not. Matching a line is still
accepted as a fallback — and reported, so nothing goes stale in silence.

What the room reads is the slide's decision, not the source's:

```python
code('tokenize', trim=['# a line the room'])         # take that line out
code('tokenize', trim=[('GENRES =', 'GENRES =')])    # take out a span
code('tokenize', keep=['def tokenize'])              # only these lines
code('tokenize', drop=['GENRES'])                    # all but these
```

`trim` says *what to find*, not where to look, so an edit elsewhere in the cell
does not move it. A `(first, last)` pair takes out everything from the line
holding `first` through the next line holding `last` and leaves one `...` in its
place. An anchor that matches nothing — or more than one line — is reported by
`check` rather than guessed at.

`result()` takes the same `keep` / `drop`, plus `trim={'width': …, 'head': …,
'tail': …}` for output too wide or too long to project.

`figure()` stores only the name; the picture is read out of the source
notebook's stored output at render time, so neither notebook carries a second
copy of the bytes and there is no image file to update by hand.

### Layout

`layout='split'` puts the prose on the reading side and the code or picture on
the other, prose first in the DOM so `dir="rtl"` puts it on the right. The
column widths are worked out from how tall each side is; `split=(40, 60)`
overrides that.

It is off by default: a slide of a few short bullets does not need two columns,
and reading order is easier to follow than two parallel tracks.

### The cover

The first slide is the cover if it is a level-1 heading — centred, no footer,
with the two-tone band along the bottom.

### What `check` complains about

- a cell that declares no slide and is not tagged `skip-slide`
- a reference that stopped matching
- more than `max_bullets` (5) top-level bullets on one slide
- a bullet longer than `max_words` (20) words — a bullet is a headline, not a sentence
- a `lang='he'` deck whose text is still mostly Latin
- a listing that is no longer in the source notebook at all

None of it is corrected for you. All of it is worth knowing before the room does.

### Right to left

`lang='he'` implies `direction='rtl'`, which mirrors the layout — bullets, the
title rule, the cover band, which arrow key goes forward — and switches to a
Hebrew-first font stack, while keeping code, output and tables of numbers left
to right.

---

## Themes

Every colour, size and font in a deck is a named token, and the stylesheet is
written entirely in terms of them. Restyling is therefore changing values —
never forking a renderer.

### The four ways to say it

```python
from pypresent import Presentation, Theme

Presentation(..., theme='dark')                        # a built-in, by name
Presentation(..., theme={'base': 'office', 'accent': '#a8441f'})
Presentation(..., theme='themes/house-style.toml')     # a file
Presentation(..., theme=Theme.named('slate').replace(bullet_size='4.6cqh'))
```

From the command line, and in a markdown deck's front matter:

```bash
pypresent render talk.md --theme dark
pypresent render talk.md --theme mine.toml
```

```markdown
---
theme: dark
---
```

Whatever it is given, the declaration stores only what differs from the base, so
the record in the notebook stays readable and a later version of a built-in
still reaches the deck.

### The built-ins

| name | what it is for |
| --- | --- |
| `warm` | the default: warm paper, rust and teal accents |
| `office` | a default PowerPoint deck — blue on white, for a room that should not notice the tool |
| `dark` | a bright room with a dim projector, and screenshots for a dark README |
| `slate` | quiet, cool and typographic — square bullets, more air, for a talk that is mostly prose |

```bash
pypresent themes            # what there is
pypresent themes dark       # that theme as a file you can edit
```

### Writing one

Start from a built-in and change what you want:

```bash
pypresent themes slate > themes/house-style.toml
```

A theme file is TOML (or JSON, or YAML with `pypresent[yaml]`). `base` names the
built-in to start from; everything else is a token:

```toml
base = "office"

accent  = "#7b2d26"
accent2 = "#2f4858"
font    = "\"Source Sans 3\", \"Segoe UI\", system-ui, sans-serif"

bullet_size = "4.4cqh"
bullet_gap  = "2.8cqh"
radius      = "0"

## the last resort, for the one selector no token covers
css = """
.slide.cover .title { text-transform: uppercase; letter-spacing: .06em }
"""
```

A `[theme]` table around it is accepted, so a theme can live inside a larger
config file.

### Sizes are in `cqh`

`1cqh` is 1% of the slide's height. Everything on a slide is sized that way, so
the deck scales like a projected slide rather than reflowing like a web page —
the same at 1280×720 and on a 4K screen. Use `cqh` for anything that should
scale with the slide, and `px` only for the chrome outside it.

### Every token

#### Palette

| token | css variable | default |
| --- | --- | --- |
| `accent` | `--pp-accent` | `#a8441f` |
| `accent2` | `--pp-accent2` | `#1f5f6b` |
| `ink` | `--pp-ink` | `#1a1815` |
| `muted` | `--pp-muted` | `#6f6a61` |
| `line` | `--pp-line` | `#e2ddd3` |
| `canvas` | `--pp-canvas` | `#faf7f2` |
| `backdrop` | `--pp-backdrop` | `#e8e0d4` |
| `soft` | `--pp-soft` | `#f2e7de` |
| `inline_ink` | `--pp-inline-ink` | `#5c2a12` |
| `code_bg` | `--pp-code-bg` | `#2b2723` |
| `code_fg` | `--pp-code-fg` | `#f0ebe3` |
| `out_bg` | `--pp-out-bg` | `#f4f1ea` |
| `out_fg` | `--pp-out-fg` | `#33302b` |
| `row_alt` | `--pp-row-alt` | `#f6efe7` |
| `head_fg` | `--pp-head-fg` | `#fdfbf7` |
| `frame` | `--pp-frame` | `#ffffff` |

`accent` is titles and emphasis; `accent2` is bullets, table headers and rules.
`canvas` is the slide, `backdrop` is the letterbox around it.

#### Type

| token | css variable | default |
| --- | --- | --- |
| `font` | `--pp-font` (ltr) | `Calibri, Candara, "Segoe UI", Carlito, system-ui, …` |
| `font_rtl` | `--pp-font` (rtl) | `Calibri, "Segoe UI", "Noto Sans Hebrew", …` |
| `mono` | `--pp-mono` | `Consolas, "Cascadia Mono", ui-monospace, Menlo, monospace` |
| `title_size` | `--pp-title` | `6.4cqh` |
| `cover_title_size` | `--pp-cover-title` | `8.4cqh` |
| `lead_size` | `--pp-lead` | `4cqh` |
| `subhead_size` | `--pp-subhead` | `4.4cqh` |
| `bullet_size` | `--pp-bullet` | `4.2cqh` |
| `quote_size` | `--pp-quote` | `4.2cqh` |
| `code_size` | `--pp-code` | `2.6cqh` |
| `table_size` | `--pp-table` | `3.2cqh` |
| `footer_size` | `--pp-footer` | `2cqh` |
| `title_weight` | `--pp-title-weight` | `400` |
| `cover_title_weight` | `--pp-cover-weight` | `300` |
| `title_tracking` | `--pp-title-tracking` | `-.01em` |

Only web-safe and system fonts: the deck is one file with no request to
anywhere, so a font it does not carry is a font that will not be there.

#### Shape

| token | css variable | default |
| --- | --- | --- |
| `padding` | `--pp-pad` | `6cqh 7cqh 8cqh` |
| `radius` | `--pp-radius` | `.9cqh` |
| `rule` | `--pp-rule` | `.42cqh` |
| `bullet_gap` | `--pp-bullet-gap` | `2.4cqh` |
| `bullet_glyph` | `--pp-bullet-glyph` | `"\25CF"` |
| `subbullet_glyph` | `--pp-subbullet-glyph` | `"\2013"` |
| `image_max` | `--pp-image-max` | `46cqh` |
| `frame_width` | `--pp-frame-width` | `.5cqh` |
| `frame_shadow` | `--pp-frame-shadow` | `0 1.2cqh 3cqh rgba(0,0,0,.18)` |
| `stage_shadow` | `--pp-stage-shadow` | `0 0 30px rgba(90,70,50,.18)` |
| `motion` | `--pp-motion` | `.45s` |

A glyph is a CSS `content` value, so it needs its quotes: `'"\\25AA"'` in
Python, `"\"\\25AA\""` in TOML.

#### Text the page carries

| token | what it is |
| --- | --- |
| `hint` | the key legend in the corner, left to right |
| `hint_rtl` | the same, right to left |
| `css` | appended after the whole stylesheet |

### The class names, for `css`

If you do reach for `css=`, these are the hooks:

| selector | what it is |
| --- | --- |
| `.deck` | the 16:9 stage |
| `.slide`, `.slide.active`, `.slide.cover` | one slide |
| `.title`, `.title-rule`, `.cover-rule`, `.cover-band` | the heading area |
| `.body`, `.body.split`, `.col`, `.fit` | the body, and the box that shrinks |
| `p.lead`, `p.subhead`, `ul.bullets`, `ol.bullets`, `.bullets.sub` | prose |
| `blockquote.quote`, `table`, `figure.image` | the rest |
| `pre.code`, `pre.output`, `code` | code, output, inline code |
| `.footer`, `.progress`, `.chrome`, `.hint` | the chrome |

`.fit` is the box the deck scales down when a slide says too much — which is
what `pypresent audit` measures.

### Per-deck overrides

`fonts=`, `hint=` and `css=` on a `Presentation` sit on top of whatever theme it
has, each falling back to the theme. They are for one deck's exception; a change
you want twice belongs in a theme file.

---

## The command line

```
pypresent [command] [file] [options]
```

The deck declares itself, so a command names an action and, at most, the file to
act on. With no file, `pypresent` looks for exactly one `*-slides.ipynb`,
`*-slides.md` or `*.slides.md` in the current folder — one is unambiguous, more
than one is not, and it says so rather than picking. With no command at all it
builds.

### Commands

#### `build`

Execute the slide notebook, check it, render the deck.

| flag | |
| --- | --- |
| `--no-run` | skip the kernel; still check and render the stored outputs |
| `--source` | run the source notebook first, then the deck — in that order, because the deck quotes what the source printed |
| `-f html\|md` | what to write (default `html`) |

A markdown deck has nothing to run, so `build` on one is just `render`.

#### `render`

Render the stored outputs. No kernel, no check — the fast one.

| flag | |
| --- | --- |
| `-f html\|md` | `md` writes the same slides as a markdown document, beside the deck |

#### `check`

What has drifted, said and not corrected. Exits 1 if there is anything.
See [writing-slides.md](#what-check-complains-about).

#### `audit`

Did any slide have to be shrunk to fit? The deck scales an over-full slide down
rather than breaking it, so a slide that says too much just becomes unreadable —
which only a real browser can see. Opens the built deck in headless Chrome.

| flag | |
| --- | --- |
| `--size W H` | the screen to measure against (default 1920×1080) |

```
talk.html at 1920x1080
    4  scale 0.812  Tokenizing  <<< TOO SMALL
    7  scale 0.964  Results  <<< shrunk a little
    9  fills 8%  A short slide  <<< nearly empty
1 slide(s) below 0.90
```

Exits 1 if any slide is below `fit_floor`. Set `chrome=` on the presentation if
the browser is not `google-chrome-stable`.

#### `export`

Two flags rather than four command names: **what** to write, and **how**.

| | `--format html` | `--format md` |
| --- | --- | --- |
| `--mode slide` | the deck (this library's renderer) | the deck as markdown |
| `--mode nb` | the source notebook through nbconvert | the source notebook as markdown |

`--mode nb` is plain `jupyter nbconvert` — the ordinary notebook export everyone
else's looks like: source cells kept, images embedded, one file. Markdown drops
the source cells instead; `--code` / `--no-code` overrides either. `--also
other.ipynb` converts more notebooks beside it.

Everything written lands in the folder the deck's `output` names, so the source
folder keeps to itself and one directory holds every file that can be deleted
and rebuilt.

#### `themes`

```bash
pypresent themes            # the built-ins
pypresent themes dark       # that one as a file you can edit
```

### Options on every command

| flag | |
| --- | --- |
| `--theme NAME\|FILE` | a built-in or a theme file |
| `--lang CODE` | `he` implies right to left |
| `--dir ltr\|rtl` | overrides what the language implies |
| `--title TEXT` | |
| `--date TEXT` | printed in the footer |
| `--split-level N` | markdown headings up to this level start a slide |
| `--no-images` | leave pictures out — a much smaller file while you are writing |
| `-o, --output PATH` | |
| `--version` | |

A flag always wins over what the declaration says; its absence is not an
instruction, so leaving one off keeps whatever the deck wrote down.

### Exit codes

`0` is fine. `1` is: a file that is not there, a source that produced no slides,
`check` finding something, `audit` finding a slide below the floor, or a Chrome
that could not be started.

---

## The Python API

```python
from pypresent import Presentation, Theme, slide, md, out, image, notes
from pypresent import code, result, figure
from pypresent import parse, render_deck, render_markdown
```

### `Presentation`

A deck, described once. Every action is a method on it, and nothing about any
particular deck lives in the library — so two can be built side by side without
either knowing about the other.

```python
deck = Presentation(
    slides='talk-slides.ipynb',   # the notebook of slide() calls, or a .md file
    source='talk.ipynb',          # what code(), result() and figure() quote
    output='out/talk.html',
    base=None,                    # what relative paths are relative to
    title='A talk',
    lang='en', direction='',      # '' takes rtl for he, ltr otherwise
    date='March 2026',
    theme='office',               # a name, a file, a dict, or a Theme
    split_level=3,
    images=True,
    max_bullets=5, max_words=20,  # what check() complains about
    fit_floor=0.90, sparse=0.15,  # what audit() complains about
    audit_size=(1920, 1080),
    chrome='google-chrome-stable',
    hint='', fonts='', css='',    # per-deck overrides on top of the theme
    activate=True,                # become this notebook's active presentation
)
```

Paths are taken relative to `base`, which defaults to the slide file's own
directory — so a deck reads the same from wherever the build is run.

#### Actions

| | |
| --- | --- |
| `deck.build(run=True, source=False, fmt='html')` | execute, check, render |
| `deck.render(fmt='html', output=None)` | render the stored outputs |
| `deck.check(nb=None)` | how many things have drifted |
| `deck.audit(width=0, height=0)` | how many slides had to shrink |
| `deck.read_slides()` | the `Slide` objects, for doing something else with |
| `deck.run_source()` | execute the source notebook in place |
| `deck.convert(notebooks, fmt, code=None)` | straight through nbconvert |

All of them return an exit code, so a build script is `sys.exit(deck.build())`.

#### Declaring and reading back

| | |
| --- | --- |
| `deck.payload()` | the declaration, as JSON-able data |
| `deck.to_json()` | the same, as text |
| `Presentation.from_notebook(path, **override)` | read it back; a given override wins |
| `deck.current()` | a context manager making this the active presentation |

In Jupyter, a `Presentation` as a cell's last expression stores its declaration
as a cell output, which is how the command line needs nothing but the file.

### Blocks

```python
slide(*blocks, title='', layout='stack', split=(46, 54), notes='')
```

A bare string is `md()`. See [writing-slides.md](#writing-slides) for each
block. `SlideSpec.errors` lists every reference on the slide that stopped
matching.

The bare `code()`, `result()` and `figure()` act on the active presentation —
the one the notebook declared. `deck.code(...)` is the explicit form, and works
when more than one deck is in play.

### `Theme`

A frozen dataclass of tokens. See [themes.md](#themes) for all of them.

| | |
| --- | --- |
| `Theme()` | the default (`warm`) |
| `Theme.named('dark')` | a built-in |
| `Theme.load(path)` | a `.toml`, `.json` or `.yaml` file |
| `Theme.resolve(spec)` | whatever a deck was given — name, path, dict, Theme, or None |
| `theme.replace(**tokens)` | a new theme with some tokens changed |
| `theme.stylesheet(direction)` | what goes in the deck's one `<style>` |
| `theme.to_dict(full=False)` | as data; by default only what differs from the base |
| `theme.to_toml()` | as a file you can edit |
| `available_themes()` | the built-in names |

`replace()` rejects an unknown token name and lists the real ones, so a typo is
an error rather than a setting that quietly does nothing.

### Reading and rendering on their own

```python
slides = parse('talk.md')                     # or a .ipynb -> list[Slide]
page   = render_deck(slides, title='A talk', direction='ltr', theme='dark')
text   = render_markdown(slides, title='A talk', assets='img')
```

`parse_notebook()` and `parse_markdown()` are the two behind `parse()`.
`render_markdown(assets=…)` writes the pictures out to that folder instead of
inlining them as data URIs.

A `Slide` is `title`, `level`, `section`, `layout`, `split`, `notes` and
`elements` — a list of plain dicts, each with a `kind`. They are dicts and not
classes on purpose: that is what lets a slide survive the round trip through a
notebook cell output as JSON.

### No Jupyter needed to render

`nbformat`, `nbclient` and `nbconvert` are imported inside the methods that
execute or convert notebooks — never at import time. A notebook that imports
`pypresent` to declare its own slides does not drag them in, and a machine that
only renders a stored deck does not need them installed at all.
