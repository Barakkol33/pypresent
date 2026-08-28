"""Quoting the source notebook: code(), result(), figure() - and what they refuse."""

import pytest

from pypresent import Presentation, code, figure, image, md, out, result, slide
from pypresent.blocks import SlideSpec
from pypresent.nbio import cut, find_cell, pick


@pytest.fixture
def deck(tmp_path, source_notebook, slides_notebook):
    return Presentation(slides=slides_notebook, source=source_notebook, activate=True)


class TestPlainBlocks:
    def test_md_dedents(self):
        assert md("\n    one\n    two\n") == {"kind": "md", "text": "one\ntwo"}

    def test_out_carries_its_trim(self):
        assert out("x", {"head": 1}) == {"kind": "out", "text": "x", "trim": {"head": 1}}

    def test_image_is_a_path_and_stays_one(self):
        assert image("pics/a.png") == {"kind": "image", "path": "pics/a.png"}


class TestCode:
    def test_quotes_the_named_cell(self, deck):
        block = deck.code("tokenize")
        assert block["kind"] == "code"
        assert "def tokenize(text):" in block["text"]

    def test_leaves_the_slide_name_behind(self, deck):
        assert "# slide:" not in deck.code("tokenize")["text"]

    def test_trim_takes_a_line_out_by_what_it_contains(self, deck):
        assert "# noise" not in deck.code("tokenize", trim=["# noise"])["text"]

    def test_drop_takes_lines_out(self, deck):
        assert "GENRES" not in deck.code("tokenize", drop=["GENRES"])["text"]

    def test_keep_leaves_only_what_was_asked_for(self, deck):
        assert deck.code("tokenize", keep=["def tokenize"])["text"] == "def tokenize(text):"

    def test_a_name_that_matches_nothing_is_reported(self, deck):
        assert "no source cell named" in deck.code("nonesuch")["error"]

    def test_an_anchor_that_matches_nothing_is_reported(self, deck):
        assert "matches no line" in deck.code("tokenize", trim=["# gone"])["error"]

    def test_matching_a_line_rather_than_a_name_is_reported(self, deck):
        # the fallback works, but says so, so a rename does not pass unnoticed
        assert "matched a line" in deck.code("GENRES")["error"]

    def test_no_source_notebook_is_reported_and_not_an_exception(self, slides_notebook):
        deck = Presentation(slides=slides_notebook)
        assert "declares no source" in deck.code("tokenize")["error"]


class TestResult:
    def test_is_what_the_cell_printed(self, deck):
        assert deck.result("tokenize")["text"] == "3"

    def test_a_cell_that_printed_nothing_is_empty(self, deck):
        assert deck.result("quiet")["text"] == ""

    def test_a_missing_name_is_reported(self, deck):
        assert "no source cell named" in deck.result("nonesuch")["error"]


class TestFigure:
    def test_stores_only_the_name(self, deck):
        assert deck.figure("chart") == {"kind": "figure", "name": "chart", "which": 0}

    def test_a_cell_that_drew_nothing_is_reported(self, deck):
        assert "drew no figure" in deck.figure("quiet")["error"]

    def test_a_missing_name_is_reported(self, deck):
        assert "no source cell named" in deck.figure("nonesuch")["error"]


class TestBareFunctions:
    def test_follow_the_active_presentation(self, deck):
        # code() with no deck argument is the deck this notebook declared
        assert code("tokenize")["text"] == deck.code("tokenize")["text"]
        assert result("tokenize")["text"] == "3"
        assert figure("chart")["name"] == "chart"


class TestCut:
    def test_a_pair_takes_out_a_span_and_leaves_one_ellipsis(self):
        text = "a\nSTART\nb\nc\nEND\nd"
        assert cut(text, [("START", "END")])[0] == "a\n...\nd"

    def test_a_string_takes_out_one_line(self):
        assert cut("a\nb\nc", ["b"])[0] == "a\n...\nc"

    def test_the_ellipsis_keeps_the_indentation_of_what_it_replaced(self):
        assert cut("def f():\n    x = 1\n", ["x = 1"])[0] == "def f():\n    ..."

    def test_an_ambiguous_anchor_is_reported_rather_than_guessed_at(self):
        assert "matches 2 lines" in cut("x\nx\n", ["x"])[1]

    def test_an_unclosed_span_is_reported(self):
        assert "matches no line after" in cut("START\na\n", [("START", "END")])[1]

    def test_nothing_to_trim_is_no_change(self):
        assert cut("a\nb", [])[0] == "a\nb"


class TestSlideSpec:
    def test_a_bare_string_is_prose(self):
        assert slide("hello").blocks == [{"kind": "md", "text": "hello"}]

    def test_none_blocks_are_dropped(self):
        assert slide("a", None, "b").blocks == [{"kind": "md", "text": "a"},
                                                {"kind": "md", "text": "b"}]

    def test_an_unknown_layout_is_an_error(self):
        with pytest.raises(ValueError, match="layout"):
            slide("a", layout="carousel")

    def test_something_that_is_not_a_block_is_an_error(self):
        with pytest.raises(TypeError, match="block"):
            slide(42)

    def test_it_shows_itself_as_markdown_in_the_notebook(self):
        spec = slide("## One", {"kind": "code", "text": "x = 1", "lang": "python"})
        bundle = spec._repr_mimebundle_()
        assert "```python" in bundle["text/markdown"]
        assert bundle["application/x-slide+json"]["blocks"][1]["text"] == "x = 1"

    def test_errors_are_collected(self):
        spec = SlideSpec({"kind": "code", "text": "", "error": "gone"})
        assert spec.errors == ["gone"]


class TestFindCell:
    def test_by_name(self, source_notebook):
        cell, guessed = find_cell(source_notebook, "tokenize")
        assert guessed is False
        assert "# slide: tokenize" in "".join(cell["source"])

    def test_by_line_as_a_fallback_and_says_so(self, source_notebook):
        _, guessed = find_cell(source_notebook, "GENRES")
        assert guessed is True

    def test_not_at_all(self, source_notebook):
        assert find_cell(source_notebook, "nonesuch") == (None, False)


def test_pick_keeps_an_ellipsis_a_cut_left_behind():
    assert pick("a\n...\nb", keep=["b"]) == "...\nb"
