"""Saying something to a stream that cannot spell it.

A deck is written as UTF-8 always; what varies is the terminal it is announced
on.  A redirected stdout under a non-UTF-8 locale - a pipe on a Windows runner,
a cron job with LC_ALL=C - can encode neither the middle dot in a progress line
nor the Hebrew in a warning, and a build must not die of its own message.
"""

import io
import os
import subprocess
import sys

from pypresent.console import say


class Narrow(io.TextIOBase):
    """A stream that can only spell ASCII, the way a cp1252 pipe cannot spell `←`."""

    encoding = "ascii"

    def __init__(self):
        self.written = []

    def write(self, text):
        text.encode("ascii")          # raises UnicodeEncodeError, as the real one does
        self.written.append(text)
        return len(text)

    @property
    def text(self):
        return "".join(self.written)


def test_a_stream_that_can_take_it_gets_the_real_thing():
    out = io.StringIO()
    say("built  ·  5 slides", out)
    assert out.getvalue() == "built  ·  5 slides\n"


def test_typography_falls_back_to_its_plain_equivalent():
    out = Narrow()
    say("built  ·  5 slides  …", out)
    assert out.text == "built  -  5 slides  ...\n"


def test_the_arrows_in_a_hint_survive_as_arrows():
    out = Narrow()
    say("← → done", out)
    assert out.text == "<- -> done\n"


def test_anything_else_is_replaced_rather_than_raising():
    out = Narrow()
    say("cell 3: 'עברית'", out)
    assert "cell 3:" in out.text          # the message still arrives
    assert "?" in out.text                # with the part it could not spell replaced


def test_nothing_is_lost_when_the_stream_has_no_encoding_at_all():
    out = Narrow()
    del Narrow.encoding
    try:
        say("a · b", out)
        assert out.text == "a - b\n"
    finally:
        Narrow.encoding = "ascii"


def test_the_command_survives_an_ascii_stdout(tmp_path):
    """The end of it: render a right-to-left deck with the terminal set to ASCII."""
    talk = tmp_path / "talk.md"
    talk.write_text("---\nlang: he\n---\n\n# מצגת\n\n- נקודה\n", encoding="utf-8")
    # the environment as it is, with only the locale turned narrow: LC_ALL for
    # posix, and UTF-8 mode off so python does not quietly rescue it
    narrow = {**os.environ, "LC_ALL": "C", "LANG": "C",
              "PYTHONUTF8": "0", "PYTHONCOERCECLOCALE": "0"}
    done = subprocess.run(
        [sys.executable, "-m", "pypresent", "render", str(talk)],
        capture_output=True, env=narrow,
    )
    assert done.returncode == 0, done.stderr.decode(errors="replace")
    # the deck itself is UTF-8 regardless of what the terminal could say
    assert "מצגת" in (tmp_path / "talk.html").read_text(encoding="utf-8")
