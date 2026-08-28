"""Slides out: as one HTML file, and as markdown."""

from pypresent import Theme, render_deck, render_markdown
from pypresent.deck import parse_markdown
from pypresent.model import Slide
from pypresent.render.html import _bullets_html, _ratio, render_element, render_slide


def slides_from(tmp_path, text):
    (tmp_path / "t.md").write_text(text, encoding="utf-8")
    return parse_markdown(tmp_path / "t.md")


class TestHtmlDeck:
    def test_is_one_self_contained_file(self, tmp_path):
        page = render_deck(slides_from(tmp_path, "# One\n\n## Two\n"), title="T")
        assert page.startswith("<!doctype html>")
        assert page.count("<section") == 2
        # no request to anywhere: the stylesheet and the script are inline
        assert "<link" not in page and "src=\"http" not in page

    def test_the_first_level_one_slide_is_the_cover(self, tmp_path):
        page = render_deck(slides_from(tmp_path, "# One\n\n## Two\n"))
        assert 'class="slide cover"' in page
        assert page.count('<div class="cover-band">') == 1

    def test_the_title_is_escaped(self, tmp_path):
        page = render_deck(slides_from(tmp_path, "## A\n"), title="a <b> & c")
        assert "<title>a &lt;b&gt; &amp; c</title>" in page

    def test_rtl_turns_the_whole_page_round(self, tmp_path):
        page = render_deck(slides_from(tmp_path, "## A\n"), direction="rtl")
        assert 'dir="rtl"' in page
        assert "270deg" in page
        assert Theme().font_rtl in page

    def test_the_theme_decides_the_colours(self, tmp_path):
        page = render_deck(slides_from(tmp_path, "## A\n"), theme="dark")
        assert Theme.named("dark").canvas in page

    def test_fonts_and_css_override_the_theme(self, tmp_path):
        page = render_deck(slides_from(tmp_path, "## A\n"), fonts="Comic Sans",
                           css=".title{color:red}")
        assert "--pp-font: Comic Sans;" in page
        assert ".title{color:red}" in page

    def test_the_hint_falls_back_to_the_theme(self, tmp_path):
        assert Theme().hint in render_deck(slides_from(tmp_path, "## A\n"))
        assert "press on" in render_deck(slides_from(tmp_path, "## A\n"), hint="press on")

    def test_every_slide_is_numbered_in_its_footer(self, tmp_path):
        page = render_deck(slides_from(tmp_path, "## A\n\n---\n\n## B\n"))
        assert '<span class="num">1</span>' in page
        assert '<span class="num">2</span>' in page


class TestElements:
    def test_code_is_escaped(self):
        got = render_element({"kind": "code", "text": "if a < b: print('<x>')"})
        assert "a &lt; b" in got and "<x>" not in got

    def test_output_is_escaped(self):
        assert "&amp;" in render_element({"kind": "output", "text": "a & b"})

    def test_an_unknown_kind_renders_as_nothing(self):
        assert render_element({"kind": "spinner"}) == ""

    def test_a_table_becomes_a_table(self):
        got = render_element({"kind": "table", "head": ["a"], "rows": [["1"]]})
        assert got == "<table><thead><tr><th>a</th></tr></thead><tbody><tr><td>1</td></tr></tbody></table>"


class TestBullets:
    def test_flat(self):
        assert _bullets_html(["a", "b"], [0, 0], "ul") == \
            '<ul class="bullets"><li>a</li><li>b</li></ul>'

    def test_a_sublist_lives_inside_the_bullet_it_belongs_to(self):
        got = _bullets_html(["a", "under"], [0, 1], "ul")
        assert got == ('<ul class="bullets"><li>a<ul class="bullets sub">'
                       '<li>under</li></ul></li></ul>')


class TestSplitLayout:
    def test_two_columns_when_there_is_both_prose_and_a_figure(self):
        slide = Slide(title="T", layout="split")
        slide.add("bullets", items=["a"], levels=[0])
        slide.add("code", text="x = 1")
        assert render_slide(slide, 1, 2).count('class="col"') == 2

    def test_one_column_when_there_is_only_prose(self):
        slide = Slide(title="T", layout="split")
        slide.add("bullets", items=["a"], levels=[0])
        assert 'class="col"' not in render_slide(slide, 1, 2)

    def test_the_ratio_gives_the_taller_side_the_wider_column(self):
        long_prose = [{"kind": "lead", "html": "x" * 400}]
        short_code = [{"kind": "code", "text": "x = 1"}]
        assert _ratio(long_prose, short_code)[0] > 50

    def test_the_ratio_never_goes_past_a_third(self):
        assert _ratio([{"kind": "lead", "html": "x"}],
                      [{"kind": "code", "text": "x\n" * 400}])[0] == 34


class TestMarkdownOut:
    def test_a_markdown_deck_round_trips(self, tmp_path):
        text = ("# One\n\nA lead.\n\n---\n\n## Two\n\n- a\n  - under\n- b\n\n"
                "```python\nx = 1\n```\n")
        again = render_markdown(slides_from(tmp_path, text), front_matter=False)
        assert slides_from(tmp_path, again)[1].elements[0]["raw"] == ["a", "under", "b"]
        assert "```python\nx = 1\n```" in again

    def test_slides_are_separated_the_way_a_markdown_deck_separates_them(self, tmp_path):
        got = render_markdown(slides_from(tmp_path, "## A\n\n---\n\n## B\n"),
                              front_matter=False)
        assert got.count("\n---\n") == 1

    def test_the_title_and_date_become_front_matter(self, tmp_path):
        got = render_markdown(slides_from(tmp_path, "## A\n"), title="T", date="2026")
        assert got.startswith("---\ntitle: T\ndate: 2026\n---\n")

    def test_a_picture_can_be_written_out_beside_the_file(self, tmp_path):
        (tmp_path / "pic.png").write_bytes(b"\x89PNG\r\n\x1a\n fake")
        slides = slides_from(tmp_path, "## A\n\n![](pic.png)\n")
        got = render_markdown(slides, assets=tmp_path / "img", relative_to=tmp_path)
        assert "](img/" in got
        assert len(list((tmp_path / "img").iterdir())) == 1

    def test_a_picture_is_a_data_uri_when_no_folder_is_given(self, tmp_path):
        (tmp_path / "pic.png").write_bytes(b"\x89PNG\r\n\x1a\n fake")
        got = render_markdown(slides_from(tmp_path, "## A\n\n![](pic.png)\n"))
        assert "](data:image/png;base64," in got

    def test_notes_travel_as_a_comment(self, tmp_path):
        slide = Slide(title="T", notes="say this")
        assert "<!-- notes:\nsay this\n-->" in render_markdown([slide])
