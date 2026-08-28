"""pypresent - the notebook *is* the slides, and this turns it into one HTML file.

A deck is declared once, in the first cell of the notebook that holds it::

    from pypresent import Presentation, slide, code, result, figure

    deck = Presentation(
        slides='talk-slides.ipynb',    # this notebook: nothing but slide() calls
        source='talk.ipynb',           # what code(), result() and figure() quote
        output='out/talk.html',
        title='A talk', lang='en', theme='office',
    )

and every cell after it is a slide::

    slide('''
    ## What it does

    - the code on the slide is the code that ran
    - the number on the slide is the number it printed
    ''', code('tokenize'), result('tokenize'))

Then ``pypresent build`` executes the notebook, says what has drifted, and
writes one self-contained HTML file - or ``--format md`` writes the same slides
as markdown.  A plain markdown file works as a source too, cut into slides by
its headings and ``---`` lines.
"""

from __future__ import annotations

__version__ = "0.1.0"

from .blocks import MIME, SlideSpec, code, figure, image, md, notes, out, result, slide
from .context import active
from .deck import CONFIG_MIME, Deck, parse, parse_markdown, parse_notebook
from .markup import inline, trim_text
from .model import Slide
from .presentation import Presentation
from .render import render_deck, render_markdown, render_slide
from .theme import Theme
from .theme import available as available_themes

__all__ = [
    "CONFIG_MIME",
    "MIME",
    "Deck",
    "Presentation",
    "Slide",
    "SlideSpec",
    "Theme",
    "__version__",
    "active",
    "available_themes",
    "code",
    "figure",
    "image",
    "inline",
    "md",
    "notes",
    "out",
    "parse",
    "parse_markdown",
    "parse_notebook",
    "render_deck",
    "render_markdown",
    "render_slide",
    "result",
    "slide",
    "trim_text",
]
