---
title: Every block there is
theme: warm
date: A pypresent demo
---

# Every block there is

One markdown file, one HTML deck, no assets folder.

---

## Prose and bullets

A paragraph becomes the lead line: the sentence under the title that says what
the slide is about.

- a bullet with **bold**, *italic* and `inline code`
- a bullet with [a link](https://github.com/Barakkol33/pypresent)
  - a sub-bullet, indented two spaces
  - and another
- a bullet long enough to wrap onto a second line, which it does at the width
  the slide gives it rather than at the width you typed it

---

## Numbered, when order is the point

1. read the source
2. quote it by name
3. never paste it

---

## Code, in whatever language

```python
def tokenize(text: str) -> list[str]:
    return text.lower().split()
```

```sql
SELECT genre, count(*) FROM books GROUP BY genre ORDER BY 2 DESC;
```

---

## Output, as it came out

Output is styled as output and not as code, so a slide can show both and the
room can tell which is which.

```python
print(tokenize("A short sentence"))
```

> The block below is `out()` in a notebook deck — a result, quoted verbatim.

```
['a', 'short', 'sentence']
3 tokens
```

---

## Tables

| block | what it is | quoted from |
| --- | --- | --- |
| `md` | prose | the slide itself |
| `code` | a listing | the source notebook |
| `result` | what it printed | the source notebook |
| `figure` | what it drew | the source notebook |

---

## A quote, when someone else said it better

> A slide is a headline with evidence under it, not a paragraph with bullets
> in front of it.

And prose after it, to show the two do not collide.

---

## Headings inside a slide

Anything deeper than `--split-level` is a subhead rather than a new slide.

#### First subhead

Some prose under it.

#### Second subhead

More prose, on the same slide.

---

# A section break

A level-one heading anywhere is a section. The first one is the cover.

---

## What it does not do

- no fragments, no builds within a slide, no speaker view
- no plugins
- one file, which is the whole point
