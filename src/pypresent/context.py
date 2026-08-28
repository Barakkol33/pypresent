"""Which presentation the bare functions belong to.

One kernel runs one notebook, so the presentation a notebook declares is simply
the active one - which is what lets ``code()``, ``result()`` and ``figure()``
stay bare names in the cells instead of carrying a deck around with them.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING

if TYPE_CHECKING:                                  # pragma: no cover
    from .presentation import Presentation

_ACTIVE: Presentation | None = None


def active() -> Presentation:
    """The presentation this notebook declared."""
    if _ACTIVE is None:
        raise RuntimeError(
            "no presentation declared - call Presentation(...) before slide(), "
            "code() or result()")
    return _ACTIVE


def activate(deck: Presentation | None) -> None:
    global _ACTIVE
    _ACTIVE = deck


@contextmanager
def using(deck: Presentation):
    """Make `deck` the active presentation for the duration of the block."""
    global _ACTIVE
    was, _ACTIVE = _ACTIVE, deck
    try:
        yield deck
    finally:
        _ACTIVE = was
