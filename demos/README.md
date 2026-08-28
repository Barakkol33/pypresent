# Demos

Every capability, as a deck you can open. Build them all:

```bash
pip install -e ".[dev]"
./demos/build.sh
```

Everything lands in `demos/out/`, which is disposable — nothing in it is
committed, and `build.sh` rebuilds all of it.

| demo | what it shows |
| --- | --- |
| [`01-every-block.md`](01-every-block.md) | every block there is: prose, bullets and sub-bullets, numbered lists, code in two languages, output, tables, quotes, subheads, section breaks |
| [`02-themes.md`](02-themes.md) | one file rendered four times, once per built-in theme |
| [`03-rtl.md`](03-rtl.md) | a right-to-left deck: the layout mirrors, the code does not |
| [`04-custom-theme.toml`](04-custom-theme.toml) | a theme written by hand — palette, weights, bullet glyphs, and the `css` escape hatch |
| [`05-notebook-slides.ipynb`](05-notebook-slides.ipynb) | the notebook case: a deck that quotes a lecture by name and never pastes it |

## What each one is worth looking at for

**`01-every-block`** is the reference. If you want to know what a table or a
sub-bullet looks like before you write one, it is on a slide here. It is also
rendered to markdown (`out/01-every-block.export.md`), so you can see that the
same slides go out as prose as well as as a deck.

**`02-themes`** is the argument for tokens. The four files differ only in the
`--theme` flag that made them — same markdown, same renderer.

**`03-rtl`** is worth opening even if you never write Hebrew: it shows what does
*not* mirror. Code, output and tables of numbers stay left to right, because
Python does not read right to left.

**`04-custom-theme`** is the one to copy. It is commented, it uses `base` to
start from a built-in, and it ends with the `css` block for the one selector no
token covers.

**`05-notebook-*`** is the reason the library exists. The lecture names cells
with `# slide: name` comments; the deck quotes them with `code()`, `result()`
and `figure()`. Look at slide 4: the chart on it is read out of the lecture's
stored output at render time, so there is no PNG beside the deck to go stale.

Both notebooks are committed already executed, so `build.sh` renders them with
`--skip-source-run --skip-slides-run` and needs no kernel. To regenerate them
from scratch (this is the only thing here that needs matplotlib):

```bash
python demos/make_notebook_demo.py
pypresent build demos/05-notebook-slides.ipynb     # for real, with a kernel
```

## Once one is open

| key | |
| --- | --- |
| `→` `space` `page down` | next (`←` in a right-to-left deck) |
| `←` `page up` | back |
| `home` `end` | the ends |
| `f` | fullscreen |
| swipe | on a touchscreen |

The slide number is in the URL, so a link goes to a slide, and the browser's
back button works. `ctrl+P` prints one slide per page.
