"""A notebook, cut into slides - with no kernel anywhere near it."""

from conftest import (
    code_cell,
    config_cell,
    markdown_cell,
    plain,
    png_output,
    slide_cell,
    stream,
    write_notebook,
)
from pypresent.deck import parse_notebook


def deck(tmp_path, cells, **kw):
    return parse_notebook(write_notebook(tmp_path / "d.ipynb", cells), **kw)


class TestMarkdownCells:
    def test_are_cut_by_heading(self, tmp_path):
        slides = deck(tmp_path, [markdown_cell("# One\n\n## Two\n")])
        assert [s.title for s in slides] == ["One", "Two"]

    def test_a_rule_is_a_rule_and_not_a_break(self, tmp_path):
        # unlike a markdown file, where `---` is how a slide ends
        slides = deck(tmp_path, [markdown_cell("## One\n\na\n\n---\n\nb\n")])
        assert len(slides) == 1

    def test_an_explicit_mark_is_a_break(self, tmp_path):
        slides = deck(tmp_path, [markdown_cell("## One\n\na\n\n<!-- slide -->\n\nb\n")])
        assert len(slides) == 2


class TestCodeCells:
    def test_source_and_output_land_on_the_open_slide(self, tmp_path):
        slides = deck(tmp_path, [markdown_cell("## One\n"),
                                 code_cell("x = 1\nprint(x)\n", [stream("1\n")])])
        kinds = [el["kind"] for el in slides[0].elements]
        assert kinds == ["code", "output"]

    def test_hide_input_keeps_only_the_output(self, tmp_path):
        slides = deck(tmp_path, [markdown_cell("## One\n"),
                                 code_cell("x = 1\n", [stream("1\n")], tags=["hide-input"])])
        assert [el["kind"] for el in slides[0].elements] == ["output"]

    def test_hide_output_keeps_only_the_source(self, tmp_path):
        slides = deck(tmp_path, [markdown_cell("## One\n"),
                                 code_cell("x = 1\n", [stream("1\n")], tags=["hide-output"])])
        assert [el["kind"] for el in slides[0].elements] == ["code"]

    def test_skip_slide_drops_the_cell_entirely(self, tmp_path):
        slides = deck(tmp_path, [markdown_cell("## One\n"),
                                 code_cell("x = 1\n", [stream("1\n")], tags=["skip-slide"])])
        assert slides[0].elements == []

    def test_new_slide_starts_one_and_can_name_itself(self, tmp_path):
        slides = deck(tmp_path, [
            markdown_cell("## One\n"),
            code_cell("x = 1\n", tags=["new-slide"], metadata={"slide_title": "Two"})])
        assert [s.title for s in slides] == ["One", "Two"]

    def test_a_png_output_is_embedded(self, tmp_path):
        slides = deck(tmp_path, [markdown_cell("## One\n"), code_cell("plot()", [png_output()])])
        assert slides[0].elements[-1]["src"].startswith("data:image/png;base64,")

    def test_a_png_is_left_out_when_images_are_off(self, tmp_path):
        slides = deck(tmp_path, [markdown_cell("## One\n"), code_cell("plot()", [png_output()])],
                      images=False)
        assert [el["kind"] for el in slides[0].elements] == ["code"]

    def test_an_html_output_is_kept_as_html(self, tmp_path):
        out = {"output_type": "execute_result", "execution_count": 1, "metadata": {},
               "data": {"text/html": ["<style>x</style><table><tr><td>1</td></tr></table>"]}}
        slides = deck(tmp_path, [markdown_cell("## One\n"), code_cell("df", [out])])
        raw = slides[0].elements[-1]
        assert raw["kind"] == "rawhtml"
        assert "style" not in raw["html"]

    def test_an_error_output_loses_its_colour_codes(self, tmp_path):
        out = {"output_type": "error", "ename": "ValueError", "evalue": "no",
               "traceback": ["\x1b[0;31mValueError\x1b[0m: no"]}
        slides = deck(tmp_path, [markdown_cell("## One\n"), code_cell("boom()", [out])])
        assert slides[0].elements[-1]["text"] == "ValueError: no"

    def test_a_plain_result(self, tmp_path):
        slides = deck(tmp_path, [markdown_cell("## One\n"), code_cell("1 + 1", [plain("2")])])
        assert slides[0].elements[-1]["text"] == "2"


class TestDeclaredSlides:
    def test_a_declaring_cell_is_the_slide(self, tmp_path):
        slides = deck(tmp_path, [slide_cell([{"kind": "md", "text": "## One\n\n- a\n"}])])
        assert slides[0].title == "One"
        assert slides[0].elements[0]["kind"] == "bullets"

    def test_the_call_decides_where_the_slide_ends(self, tmp_path):
        # two headings in one slide() call are a title and a subhead, not two slides
        slides = deck(tmp_path, [slide_cell([{"kind": "md", "text": "## One\n\n## Two\n"}])])
        assert len(slides) == 1
        assert slides[0].elements[0]["kind"] == "subhead"

    def test_blocks_keep_the_order_they_were_written_in(self, tmp_path):
        slides = deck(tmp_path, [slide_cell([
            {"kind": "md", "text": "## One\n\n- a\n"},
            {"kind": "code", "text": "x = 1", "lang": "python"},
            {"kind": "out", "text": "1", "trim": {}},
        ])])
        assert [el["kind"] for el in slides[0].elements] == ["bullets", "code", "output"]

    def test_layout_and_notes_travel_with_it(self, tmp_path):
        slides = deck(tmp_path, [slide_cell([{"kind": "md", "text": "## One\n"}],
                                            layout="split", notes="say this")])
        assert slides[0].layout == "split"
        assert slides[0].notes == "say this"

    def test_out_blocks_are_trimmed_as_the_slide_asked(self, tmp_path):
        slides = deck(tmp_path, [slide_cell([
            {"kind": "md", "text": "## One\n"},
            {"kind": "out", "text": "1\n2\n3\n4", "trim": {"head": 2}}])])
        assert slides[0].elements[-1]["text"] == "1\n2\n…"

    def test_a_translated_block_takes_the_deck_language(self, tmp_path):
        cells = [slide_cell([{"kind": "md", "en": "## English\n", "he": "## עברית\n"}])]
        assert deck(tmp_path, cells, lang="he")[0].title == "עברית"
        assert deck(tmp_path, cells, lang="en")[0].title == "English"

    def test_a_figure_is_read_out_of_the_source_notebook(self, tmp_path, source_notebook):
        slides = deck(tmp_path, [slide_cell([
            {"kind": "md", "text": "## One\n"},
            {"kind": "figure", "name": "chart", "which": 0}])], source=source_notebook)
        assert slides[0].elements[-1]["src"].startswith("data:image/png;base64,")

    def test_a_figure_with_no_source_is_reported(self, tmp_path, capsys):
        deck(tmp_path, [slide_cell([{"kind": "md", "text": "## One\n"},
                                    {"kind": "figure", "name": "chart"}])])
        assert "no source notebook" in capsys.readouterr().err

    def test_the_cell_that_declares_the_presentation_is_not_a_slide(self, tmp_path):
        # neither its source nor the declaration it stored is anything to show
        slides = deck(tmp_path, [markdown_cell("## One\n"),
                                 config_cell({"title": "A talk"})])
        assert slides[0].elements == []
