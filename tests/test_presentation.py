"""A deck, described once - and read back out of the notebook that described it."""

import json

import pytest

from conftest import code_cell, config_cell, slide_cell, write_notebook
from pypresent import Presentation, Theme
from pypresent.context import active


class TestPaths:
    def test_are_relative_to_the_slide_file_by_default(self, tmp_path, slides_notebook):
        deck = Presentation(slides=slides_notebook, source="lecture.ipynb")
        assert deck.base == tmp_path
        assert deck.source == tmp_path / "lecture.ipynb"

    def test_base_moves_all_of_them_at_once(self, tmp_path, slides_notebook):
        (tmp_path / "sub").mkdir()
        deck = Presentation(slides="talk-slides.ipynb", base=tmp_path, output="sub/x.html")
        assert deck.slides == slides_notebook
        assert deck.output == tmp_path / "sub" / "x.html"

    def test_the_output_defaults_to_the_deck_beside_the_notebook(self, slides_notebook):
        assert Presentation(slides=slides_notebook).output.name == "talk-slides.html"

    def test_an_absolute_path_is_left_alone(self, tmp_path, slides_notebook):
        deck = Presentation(slides=slides_notebook, output=tmp_path / "abs.html")
        assert deck.output == tmp_path / "abs.html"


class TestDeclaration:
    def test_hebrew_implies_right_to_left(self, slides_notebook):
        assert Presentation(slides=slides_notebook, lang="he").direction == "rtl"

    def test_anything_else_is_left_to_right(self, slides_notebook):
        assert Presentation(slides=slides_notebook, lang="fr").direction == "ltr"

    def test_a_direction_that_is_not_one_is_an_error(self, slides_notebook):
        with pytest.raises(ValueError, match="ltr or rtl"):
            Presentation(slides=slides_notebook, direction="sideways")

    def test_the_theme_is_resolved_once(self, slides_notebook):
        assert Presentation(slides=slides_notebook, theme="dark").theme == Theme.named("dark")

    def test_it_becomes_the_notebook_s_active_presentation(self, slides_notebook):
        deck = Presentation(slides=slides_notebook)
        assert active() is deck

    def test_unless_it_says_not_to(self, slides_notebook):
        first = Presentation(slides=slides_notebook)
        Presentation(slides=slides_notebook, activate=False)
        assert active() is first

    def test_lecture_still_means_source(self, tmp_path, slides_notebook, source_notebook):
        deck = Presentation(slides=slides_notebook, lecture=source_notebook)
        assert deck.source == source_notebook
        assert deck.lecture == source_notebook


class TestRoundTrip:
    def test_a_declaration_survives_being_stored_in_the_notebook(self, tmp_path,
                                                                 source_notebook):
        deck = Presentation(slides=tmp_path / "t-slides.ipynb", source=source_notebook,
                            title="A talk", lang="he", theme="dark", output="out/t.html")
        write_notebook(tmp_path / "t-slides.ipynb",
                       [config_cell(json.loads(json.dumps(deck.payload())))])
        again = Presentation.from_notebook(tmp_path / "t-slides.ipynb")
        assert (again.title, again.lang, again.direction) == ("A talk", "he", "rtl")
        assert again.theme == Theme.named("dark")
        assert again.source == source_notebook
        assert again.output == tmp_path / "out" / "t.html"

    def test_a_flag_wins_over_what_is_written_down(self, tmp_path):
        deck = Presentation(slides=tmp_path / "t-slides.ipynb", title="written", lang="he")
        write_notebook(tmp_path / "t-slides.ipynb",
                       [config_cell(json.loads(json.dumps(deck.payload())))])
        again = Presentation.from_notebook(tmp_path / "t-slides.ipynb",
                                           title="insisted", lang=None)
        assert (again.title, again.lang) == ("insisted", "he")

    def test_a_deck_written_against_the_old_name_still_loads(self, tmp_path, source_notebook):
        write_notebook(tmp_path / "t-slides.ipynb",
                       [config_cell({"title": "old", "lecture": "lecture.ipynb"})])
        assert Presentation.from_notebook(tmp_path / "t-slides.ipynb").source == source_notebook

    def test_a_markdown_deck_declares_itself_in_its_front_matter(self, tmp_path):
        (tmp_path / "t.md").write_text("---\ntitle: A talk\ntheme: dark\n---\n\n# One\n")
        deck = Presentation.from_notebook(tmp_path / "t.md")
        assert deck.title == "A talk"
        assert deck.theme.name == "dark"


class TestRender:
    def test_writes_the_deck_and_makes_the_folder(self, tmp_path, slides_notebook):
        deck = Presentation(slides=slides_notebook, output=tmp_path / "out" / "t.html")
        assert deck.render() == 0
        assert "<!doctype html>" in deck.output.read_text()

    def test_markdown_goes_beside_it_with_the_other_suffix(self, tmp_path, slides_notebook):
        deck = Presentation(slides=slides_notebook, output=tmp_path / "out" / "t.html")
        assert deck.render("md") == 0
        assert (tmp_path / "out" / "t.md").exists()

    def test_a_format_that_is_not_one_is_an_error(self, slides_notebook):
        with pytest.raises(ValueError, match="html or md"):
            Presentation(slides=slides_notebook).render("pptx")

    def test_a_source_with_no_slides_says_so(self, tmp_path, capsys):
        write_notebook(tmp_path / "empty-slides.ipynb", [])
        deck = Presentation(slides=tmp_path / "empty-slides.ipynb")
        assert deck.render() == 1
        assert "no slides" in capsys.readouterr().err

    def test_the_title_falls_back_to_the_first_slide(self, tmp_path, slides_notebook):
        deck = Presentation(slides=slides_notebook, output=tmp_path / "t.html")
        deck.render()
        assert "<title>A talk</title>" in deck.output.read_text()


class TestBuild:
    """What a build runs, and in what order."""

    @pytest.fixture
    def spied(self, tmp_path, slides_notebook, source_notebook, monkeypatch):
        """A deck whose two kernel runs are recorded rather than performed."""
        order = []
        deck = Presentation(slides=slides_notebook, source=source_notebook,
                            output=tmp_path / "out.html")
        monkeypatch.setattr(Presentation, "run_source",
                            lambda self: order.append("source") or 0)
        monkeypatch.setattr(Presentation, "_execute",
                            lambda self, nb, where, what="": order.append("slides") or True)
        return deck, order

    def test_runs_the_source_first_and_the_slides_second(self, spied):
        # that order, because the deck quotes what the source printed
        deck, order = spied
        assert deck.build() == 0
        assert order == ["source", "slides"]

    def test_skipping_the_source_run(self, spied):
        deck, order = spied
        assert deck.build(run_source=False) == 0
        assert order == ["slides"]

    def test_skipping_the_slides_run(self, spied):
        deck, order = spied
        assert deck.build(run_slides=False) == 0
        assert order == ["source"]

    def test_skipping_both(self, spied):
        deck, order = spied
        assert deck.build(run_source=False, run_slides=False) == 0
        assert order == []

    def test_a_deck_with_no_source_has_nothing_to_run_first(self, tmp_path,
                                                            slides_notebook, monkeypatch):
        order = []
        monkeypatch.setattr(Presentation, "_execute",
                            lambda self, nb, where, what="": order.append("slides") or True)
        deck = Presentation(slides=slides_notebook, output=tmp_path / "out.html")
        assert deck.build() == 0
        assert order == ["slides"]

    def test_a_source_run_that_fails_stops_the_build(self, spied, monkeypatch):
        deck, order = spied
        monkeypatch.setattr(Presentation, "run_source", lambda self: 1)
        assert deck.build() == 1
        assert order == []            # the slide notebook never runs on stale numbers

    def test_a_markdown_deck_has_neither_run(self, tmp_path):
        (tmp_path / "t.md").write_text("# One\n")
        deck = Presentation(slides=tmp_path / "t.md", output=tmp_path / "out.html")
        assert deck.build() == 0
        assert deck.output.exists()

    def test_a_file_that_is_not_there(self, tmp_path, capsys):
        deck = Presentation(slides=tmp_path / "nope.ipynb")
        assert deck.build() == 1
        assert "no such file" in capsys.readouterr().err


class TestCheck:
    def test_says_nothing_about_a_clean_notebook(self, slides_notebook):
        assert Presentation(slides=slides_notebook).check() == 0

    def test_a_cell_that_declares_no_slide(self, tmp_path):
        write_notebook(tmp_path / "t-slides.ipynb", [code_cell("x = 1\n")])
        assert Presentation(slides=tmp_path / "t-slides.ipynb").check() == 1

    def test_unless_it_is_skipped(self, tmp_path):
        write_notebook(tmp_path / "t-slides.ipynb", [code_cell("x = 1\n", tags=["skip-slide"])])
        assert Presentation(slides=tmp_path / "t-slides.ipynb").check() == 0

    def test_too_many_bullets_on_one_slide(self, tmp_path):
        text = "## One\n\n" + "".join(f"- point {i}\n" for i in range(9))
        write_notebook(tmp_path / "t-slides.ipynb", [slide_cell([{"kind": "md", "text": text}])])
        deck = Presentation(slides=tmp_path / "t-slides.ipynb")
        deck.check()
        assert any("9 bullets" in w for w in deck._warnings)

    def test_a_bullet_that_is_a_sentence(self, tmp_path):
        text = "## One\n\n- " + " ".join(["word"] * 30) + "\n"
        write_notebook(tmp_path / "t-slides.ipynb", [slide_cell([{"kind": "md", "text": text}])])
        deck = Presentation(slides=tmp_path / "t-slides.ipynb")
        deck.check()
        assert any("words in one bullet" in w for w in deck._warnings)

    def test_a_reference_that_stopped_matching(self, tmp_path):
        block = {"kind": "code", "text": "", "error": "no source cell named 'gone'"}
        write_notebook(tmp_path / "t-slides.ipynb", [slide_cell([block])])
        deck = Presentation(slides=tmp_path / "t-slides.ipynb")
        deck.check()
        assert any("gone" in w for w in deck._warnings)

    def test_a_hebrew_deck_still_in_english(self, tmp_path):
        write_notebook(tmp_path / "t-slides.ipynb",
                       [slide_cell([{"kind": "md", "text": "## Still english here\n"}])])
        deck = Presentation(slides=tmp_path / "t-slides.ipynb", lang="he")
        deck.check()
        assert any("still in English" in w for w in deck._warnings)

    def test_a_markdown_deck_has_nothing_to_check(self, tmp_path):
        (tmp_path / "t.md").write_text("# One\n")
        assert Presentation(slides=tmp_path / "t.md").check() == 0
