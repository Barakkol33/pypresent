# Changelog

The format is [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the
versions are [semantic](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] — unreleased

The first release. It began as a single `present.py` that built one lecture's
deck, and is now a package.

### Added

- **Markdown decks.** A `.md` file is a source in its own right: headings and
  `---` lines cut it into slides, and a `key: value` front matter block declares
  the deck the way a notebook's first cell does.
- **Markdown output.** `--format md` writes the same slides as a markdown
  document — a readable handout that `pypresent` can read straight back in.
  Pictures are data URIs by default, or written out beside the file with
  `render_markdown(assets=…)`.
- **Themes.** Every colour, size and font is a named token; the stylesheet is
  written entirely in terms of them. A theme is a name, a `.toml`/`.json`/`.yaml`
  file, a dict, or a `Theme` — with `base` to build on a built-in. Four ship:
  `warm`, `office`, `dark`, `slate`. `pypresent themes NAME` prints one as a file
  you can edit.
- **`pypresent check`** as a command of its own, so drift can be found without
  rendering.
- **`notes()`**, and `notes=` on a slide: speaker notes that stay in the deck and
  never reach the slide.
- **`kernel="auto"`** (the default): a notebook is executed by the very
  interpreter `pypresent` is installed in, so a fresh virtualenv and a CI runner
  both work with no kernelspec registered anywhere.
- Images beyond PNG — jpg, gif, webp, svg — embedded by their real type.
- A test suite, a demo folder, and CI on Linux, macOS and Windows.

### Changed

- `present.py` is now the `pypresent` package, and the tool is `pypresent`
  rather than `python present.py`.
- `lecture=` is now `source=`, since the notebook being quoted need not be a
  lecture. `lecture=` still works, and a deck whose declaration was stored under
  the old name still loads.
- The command's first positional is the deck, and it may be a `.md`.
- `export --mode slide --format md` now uses this package's own renderer rather
  than nbconvert, so it writes the slides rather than the notebook.
- `-o` on the command line is relative to the shell's directory rather than the
  deck's.

### Fixed

- `trim={'head': n, 'tail': n}` on a block that already fits no longer truncates
  it and drops the tail.
- The cell that declares the presentation is no longer rendered as a slide of its
  own source, and `check` no longer complains that it declares no slide.

[Unreleased]: https://github.com/Barakkol33/pypresent/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/Barakkol33/pypresent/releases/tag/v0.1.0
