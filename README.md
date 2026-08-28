# pypresent

**The notebook is the slides.** `pypresent` turns a Jupyter notebook — or a plain
markdown file — into one self-contained HTML deck: no server, no build folder, no
`_files/` directory, nothing to upload. One file you can mail, open from a memory
stick, or commit next to the notebook it came from.

[![CI](https://github.com/Barakkol33/pypresent/actions/workflows/ci.yml/badge.svg)](https://github.com/Barakkol33/pypresent/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/pypresent.svg)](https://pypi.org/project/pypresent/)
[![Python](https://img.shields.io/pypi/pyversions/pypresent.svg)](https://pypi.org/project/pypresent/)
[![License](https://img.shields.io/pypi/l/pypresent.svg)](LICENSE)

```bash
pip install pypresent            # rendering only - no Jupyter needed
pip install "pypresent[jupyter]" # and executing the notebooks
```

## The shortest version

A markdown file is already a deck:

```bash
pypresent render talk.md         # -> talk.html
```

Headings and `---` lines cut it into slides, and the front matter says the rest:

```markdown
---
title: A talk
theme: office
---

# A talk

The lead line under the title.

---

## What it does

- the code on the slide is the code that ran
- the number on the slide is the number it printed
```

## The point of it, for a notebook

A lecture notebook and its deck usually drift apart: the code is pasted onto a
slide, the number beside it was true three runs ago, and the chart is a PNG
somebody exported in March.

`pypresent` never pastes. A cell in the lecture is named with a comment:

```python
# slide: tokenize
def tokenize(text):
    return text.lower().split()

print(len(tokenize("A short sentence")))
```

and the deck quotes it by that name:

```python
slide('''
## Tokenizing

- split on whitespace, lowercased
- **three** tokens out of that sentence
''',
    code('tokenize', trim=['# noise']),
    result('tokenize'),
    figure('lengths'),
)
```

`code()` is the listing, `result()` is what it printed, `figure()` is what it
drew. All three are read out of the lecture at build time, so a listing, a
number and a chart on a slide are the ones that actually ran — and a name that
stops matching is reported by the build rather than going quietly stale.

Then:

```bash
pypresent build                  # run the slide notebook, check it, write the deck
```

## What a deck declares

The slide notebook says everything about itself in its first cell, so the
command line needs nothing but the file:

```python
from pypresent import Presentation, slide, code, result, figure

deck = Presentation(
    slides='talk-slides.ipynb',   # this notebook: nothing but slide() calls
    source='talk.ipynb',          # what code(), result() and figure() quote
    output='out/talk.html',
    title='A talk', lang='en', theme='office',
)
deck                              # the last line, so the cell stores it
```

The declaration is kept as a cell output, the way a slide is. A flag still wins
over it: `pypresent build --theme dark -o /tmp/x.html`.

## Themes

Every colour, size and font is a named token, and the stylesheet is written
entirely in terms of them — so restyling is changing values, never forking a
renderer.

```python
Presentation(..., theme='dark')                       # a built-in
Presentation(..., theme={'base': 'office', 'accent': '#a8441f'})
Presentation(..., theme='themes/house-style.toml')    # a file
Presentation(..., theme=Theme.named('slate').replace(bullet_size='4.6cqh'))
```

Four built-ins ship with it — `warm`, `office`, `dark`, `slate`. To start from
one, print it as a file you can edit:

```bash
pypresent themes                 # what there is
pypresent themes dark > mine.toml
pypresent render talk.md --theme mine.toml
```

`css=` is still there for the one selector no token covers.
See [the theme reference](docs/README.md#themes) for every token.

## Right to left

`lang='he'` implies `dir="rtl"`, which mirrors the whole layout — bullets, the
two-tone title rule, the cover band, the arrow keys — and switches to a
Hebrew-first font stack, while keeping code and output left to right, because
Python does not read right to left.

## Commands

| | |
| --- | --- |
| `pypresent build` | run the source notebook, then the slide notebook, check, render |
| `pypresent build --skip-source-run` | leave the source notebook alone |
| `pypresent build --skip-slides-run` | check and render the stored outputs |
| `pypresent render` | render only, no kernel and no check |
| `pypresent render -f md` | the same slides as markdown |
| `pypresent check` | what has drifted, said and not corrected |
| `pypresent export --mode nb --format html` | the source notebook through nbconvert |
| `pypresent themes [name]` | the built-in themes |

## Documentation

**[The documentation is one page](docs/README.md)**, with everything on it:

- [Quickstart](docs/README.md#quickstart) — from nothing to a deck
- [Writing slides](docs/README.md#writing-slides) — every block, and what it is for
- [Themes](docs/README.md#themes) — every token, and how to ship your own
- [The command line](docs/README.md#the-command-line)
- [The Python API](docs/README.md#the-python-api)

And [`demos/`](demos/) is the same thing as decks you can open — every block, the
four themes, a right-to-left deck, a hand-written theme, and a notebook deck that
quotes its lecture.

## Why not reveal.js / Quarto / RISE

Those are all good, and all bigger. `pypresent` is for one case: a lecture
notebook that must stay the single source of the code, and a deck of it that
must be one file with no toolchain to reproduce. If you want speaker view,
fragments, plugins and a themeing ecosystem, use reveal.js.

## License

MIT — see [LICENSE](LICENSE).
