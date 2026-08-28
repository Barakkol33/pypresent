# Contributing

Thanks for looking. This is a small library with one job, so the bar for a
change is that it makes that job better rather than that it adds a job.

## Getting set up

```bash
git clone https://github.com/Barakkol33/pypresent
cd pypresent
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

pytest -q                # the tests
ruff check .             # the lint
./demos/build.sh         # the end-to-end check: every demo has to build
```

Nothing needs Jupyter to render a deck, and the tests do not use a kernel: a
notebook is built in memory in `tests/conftest.py`. If a change makes a test need
a running kernel, that is worth a second look at the change.

## What a change should come with

- **a test that fails without it.** The suite is fast and offline; there is no
  reason not to.
- **a note in `CHANGELOG.md`**, under `Unreleased`.
- **the docs, if behaviour moved.** They are one page: `docs/README.md`.
- **a demo, if it is a capability.** `demos/` is meant to be the honest answer to
  "what can this do", and CI builds every deck in it.

## The shape of the code

| module | what is in it |
| --- | --- |
| `markup.py` | inline markdown → html, and the text helpers |
| `nbio.py` | a notebook as JSON: finding a named cell, taking things out of it |
| `blocks.py` | what a slide notebook writes: `slide()` and its blocks |
| `deck.py` | cutting a source into slides |
| `model.py` | what a slide is, once every source has been read |
| `render/html.py`, `render/markdown.py` | slides out |
| `theme.py` | how a deck looks, as tokens |
| `presentation.py` | a deck, described once; every action is a method on it |
| `cli.py` | the command |
| `assets/`, `themes/` | the stylesheet, the script, the built-in themes |

Two rules hold the design together, and are worth keeping:

1. **A slide is plain data.** Elements are dicts with a `kind`, not classes.
   That is what lets a slide survive the round trip through a notebook cell
   output as JSON, and what lets a deck be rendered later with no kernel.
2. **Jupyter is imported inside the methods that need it**, never at module
   level. Rendering a stored notebook must keep working on a machine that has
   never had `nbclient` installed.

## Style

`ruff check .` is the whole of it; the config is in `pyproject.toml`. Beyond
that: comments say *why*, not *what*, and a docstring on anything non-obvious
says what the thing is for rather than restating its signature.

## Adding a theme token

1. a field on `Theme` in `theme.py`, with the default the `warm` value
2. a line in `VARIABLES` mapping it to its CSS custom property
3. use it in `assets/deck.css`
4. `python -c "from pypresent import Theme; print(Theme().to_toml())" > src/pypresent/themes/warm.toml`
5. a row in the table in `docs/README.md`

`test_the_defaults_are_the_warm_built_in` fails if you forget step 4, and
`test_every_token_reaches_the_page` fails if you forget step 3.

## Reporting something

An issue with the markdown or the notebook cell that causes it is worth ten
without. If it is a rendering problem, the built HTML — or a screenshot — says
more than a description of it.

## Releasing

Maintainers only, and it happens on a tag and on nothing else:

```bash
# bump __version__ in src/pypresent/__init__.py, move CHANGELOG's Unreleased
git commit -am "0.2.0"
git tag v0.2.0
git push origin main --tags
```

The release workflow refuses to publish if the tag and `__version__` disagree,
goes to TestPyPI first, and uses Trusted Publishing — there is no token stored
anywhere.
