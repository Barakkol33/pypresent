"""Saying something to whoever is running the build."""

from __future__ import annotations

import sys

# What a message loses when the terminal cannot spell it.  Anything not in here
# falls back to the encoder's own replacement, which says less.
PLAIN = {"·": "-", "…": "...", "→": "->", "←": "<-"}


def say(message: str, where=None) -> None:
    """Print a line, and survive a stream that cannot encode it.

    Progress lines carry a middle dot, and warnings quote slide text that may be
    in any script at all.  A redirected stdout under a non-UTF-8 locale - a pipe
    on a Windows runner, a cron job with LC_ALL=C - can encode neither, and a
    build must not die of its own progress message.
    """
    stream = where or sys.stdout
    try:
        print(message, file=stream)
    except UnicodeEncodeError:
        for fancy, plain in PLAIN.items():
            message = message.replace(fancy, plain)
        encoding = getattr(stream, "encoding", None) or "ascii"
        print(message.encode(encoding, "replace").decode(encoding), file=stream)
