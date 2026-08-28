---
title: The same deck, four ways
theme: slate
date: A pypresent demo
---

# The same deck, four ways

`build.sh` renders this file once per theme. Open the four side by side.

---

## Why tokens

Every colour, size and font is a named token, and the stylesheet is written
entirely in terms of them.

- restyling is changing values, never forking a renderer
- a theme is a `.toml` file, so it can be shared and reviewed like anything else
- `css=` is still there for the one selector no token covers

---

## The four built-ins

| name | for |
| --- | --- |
| `warm` | the default — warm paper, rust and teal |
| `office` | a room that should not notice the tool |
| `dark` | a bright room with a dim projector |
| `slate` | quiet and typographic, for a talk that is mostly prose |

---

## How a theme reaches a deck

```bash
pypresent render 02-themes.md --theme dark
```

```python
Presentation(..., theme={'base': 'office', 'accent': '#a8441f'})
```

```markdown
---
theme: dark
---
```

---

## Starting your own

```bash
pypresent themes slate > mine.toml
```

Then edit it, and pass it the same way a built-in is passed. `base` says which
one to start from; everything else is a token over it.

---

## What a theme cannot change

- the 16:9 stage, and that a slide never scrolls
- that an over-full slide shrinks rather than breaks
- that the deck is one file with no request to anywhere

Which is why a font has to be one the machine already has.
