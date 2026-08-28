"""Slides out: as one HTML file, or as markdown."""

from .html import render_deck, render_element, render_slide
from .markdown import render_markdown

__all__ = ["render_deck", "render_element", "render_markdown", "render_slide"]
