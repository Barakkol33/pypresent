"""The command line: what each command writes, and what it returns."""

import subprocess
import sys

import pytest

from conftest import config_cell, slide_cell, write_notebook
from pypresent.cli import find_deck, main


@pytest.fixture
def here(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return tmp_path


def a_markdown_deck(path, text="---\ntitle: A talk\n---\n\n# One\n\n---\n\n## Two\n"):
    path.write_text(text, encoding="utf-8")
    return path


class TestFindDeck:
    def test_one_slide_file_is_unambiguous(self, here):
        a_markdown_deck(here / "talk-slides.md")
        assert find_deck(here).name == "talk-slides.md"

    def test_none_says_so(self, here, capsys):
        assert find_deck(here) is None
        assert "no slide file" in capsys.readouterr().err

    def test_two_will_not_be_guessed_between(self, here, capsys):
        a_markdown_deck(here / "one-slides.md")
        a_markdown_deck(here / "two-slides.md")
        assert find_deck(here) is None
        assert "name the one you mean" in capsys.readouterr().err


class TestRender:
    def test_writes_the_deck_beside_the_source(self, here):
        a_markdown_deck(here / "talk.md")
        assert main(["render", "talk.md"]) == 0
        assert (here / "talk.html").exists()

    def test_output_puts_it_where_asked(self, here):
        a_markdown_deck(here / "talk.md")
        assert main(["render", "talk.md", "-o", "sub/deck.html"]) == 0
        assert (here / "sub" / "deck.html").exists()

    def test_the_theme_flag_wins_over_the_front_matter(self, here):
        a_markdown_deck(here / "talk.md", "---\ntheme: dark\n---\n\n# One\n")
        main(["render", "talk.md", "--theme", "office"])
        assert "#0f6cbd" in (here / "talk.html").read_text()

    def test_markdown_out(self, here):
        a_markdown_deck(here / "talk.md")
        assert main(["render", "talk.md", "-f", "md"]) == 0
        assert (here / "talk.md").read_text().startswith("---\ntitle: A talk")

    def test_rtl(self, here):
        a_markdown_deck(here / "talk.md")
        main(["render", "talk.md", "--dir", "rtl"])
        assert 'dir="rtl"' in (here / "talk.html").read_text()

    def test_a_file_that_is_not_there(self, here, capsys):
        assert main(["render", "nope.md"]) == 1
        assert "no such file" in capsys.readouterr().err


class TestBuild:
    def test_a_markdown_deck_has_nothing_to_run_and_just_renders(self, here):
        a_markdown_deck(here / "talk.md")
        assert main(["build", "talk.md"]) == 0
        assert (here / "talk.html").exists()

    def test_a_notebook_with_no_run_renders_the_stored_outputs(self, here):
        write_notebook(here / "t-slides.ipynb",
                       [slide_cell([{"kind": "md", "text": "# One\n"}])])
        assert main(["build", "t-slides.ipynb", "--no-run"]) == 0
        assert (here / "t-slides.html").exists()

    def test_the_only_slide_notebook_here_needs_no_naming(self, here):
        write_notebook(here / "t-slides.ipynb",
                       [slide_cell([{"kind": "md", "text": "# One\n"}])])
        assert main(["build", "--no-run"]) == 0
        assert (here / "t-slides.html").exists()


class TestCheck:
    def test_a_clean_deck_returns_zero(self, here):
        write_notebook(here / "t-slides.ipynb",
                       [slide_cell([{"kind": "md", "text": "# One\n"}])])
        assert main(["check", "t-slides.ipynb"]) == 0

    def test_something_to_look_at_returns_one(self, here, capsys):
        write_notebook(here / "t-slides.ipynb", [config_cell({"title": "x"}),
                                                 slide_cell([{"kind": "code", "text": "",
                                                              "error": "gone"}])])
        assert main(["check", "t-slides.ipynb"]) == 1
        assert "gone" in capsys.readouterr().out


class TestThemes:
    def test_lists_what_there_is(self, capsys):
        assert main(["themes"]) == 0
        out = capsys.readouterr().out
        assert "warm" in out and "dark" in out

    def test_prints_one_as_a_file_you_can_edit(self, capsys):
        assert main(["themes", "dark"]) == 0
        assert 'accent = "#e8a33d"' in capsys.readouterr().out

    def test_a_theme_that_is_not_there(self, capsys):
        assert main(["themes", "nonesuch"]) == 1
        assert "no theme" in capsys.readouterr().err

    def test_a_printed_theme_can_be_used(self, here, capsys):
        main(["themes", "slate"])
        (here / "mine.toml").write_text(capsys.readouterr().out)
        a_markdown_deck(here / "talk.md")
        assert main(["render", "talk.md", "--theme", "mine.toml"]) == 0
        assert "#334155" in (here / "talk.html").read_text()


class TestExport:
    def test_the_deck_as_markdown(self, here):
        a_markdown_deck(here / "talk.md")
        assert main(["export", "talk.md", "-m", "slide", "-f", "md", "-o",
                     "out/talk.html"]) == 0
        assert (here / "out" / "talk.md").exists()

    def test_a_deck_with_no_source_notebook_says_so(self, here, capsys):
        a_markdown_deck(here / "talk.md")
        assert main(["export", "talk.md", "-m", "nb"]) == 1
        assert "no source notebook" in capsys.readouterr().err


def test_a_bare_run_builds_what_is_here(here):
    a_markdown_deck(here / "talk-slides.md")
    assert main([]) == 0
    assert (here / "talk-slides.html").exists()


def test_the_version_flag(capsys):
    with pytest.raises(SystemExit) as exit:
        main(["--version"])
    assert exit.value.code == 0
    assert "pypresent" in capsys.readouterr().out


def test_running_it_as_a_module(here):
    a_markdown_deck(here / "talk.md")
    done = subprocess.run([sys.executable, "-m", "pypresent", "render", "talk.md"],
                          cwd=here, capture_output=True)
    assert done.returncode == 0, done.stderr.decode()
