"""A markdown file, cut into slides."""

import pytest

from pypresent.deck import front_matter, markdown_meta, parse, parse_markdown


def deck(tmp_path, text, **kw):
    (tmp_path / "talk.md").write_text(text, encoding="utf-8")
    return parse_markdown(tmp_path / "talk.md", **kw)


class TestCutting:
    def test_a_heading_starts_a_slide_and_names_it(self, tmp_path):
        slides = deck(tmp_path, "# One\n\n## Two\n\n## Three\n")
        assert [s.title for s in slides] == ["One", "Two", "Three"]

    def test_a_rule_starts_an_unnamed_slide(self, tmp_path):
        slides = deck(tmp_path, "## One\n\nfirst\n\n---\n\nsecond\n")
        assert len(slides) == 2
        assert slides[1].title == ""

    def test_split_level_decides_how_deep_a_heading_still_cuts(self, tmp_path):
        text = "# One\n\n#### Deep\n"
        assert len(deck(tmp_path, text, split_level=3)) == 1
        assert len(deck(tmp_path, text, split_level=4)) == 2

    def test_a_deep_heading_becomes_a_subhead(self, tmp_path):
        slides = deck(tmp_path, "## One\n\n#### Deep\n")
        assert slides[0].elements[0]["kind"] == "subhead"

    def test_an_empty_file_is_no_slides(self, tmp_path):
        assert deck(tmp_path, "") == []


class TestBlocks:
    def test_a_paragraph_is_a_lead(self, tmp_path):
        el = deck(tmp_path, "## T\n\nSome prose.\n")[0].elements[0]
        assert el["kind"] == "lead"
        assert el["text"] == "Some prose."

    def test_bullets_keep_their_nesting(self, tmp_path):
        slides = deck(tmp_path, "## T\n\n- one\n  - under\n- two\n")
        el = slides[0].elements[0]
        assert el["kind"] == "bullets"
        assert el["raw"] == ["one", "under", "two"]
        assert el["levels"] == [0, 1, 0]

    def test_a_numbered_list_is_ordered(self, tmp_path):
        el = deck(tmp_path, "## T\n\n1. one\n2. two\n")[0].elements[0]
        assert el["ordered"] is True

    def test_a_wrapped_bullet_is_one_bullet(self, tmp_path):
        el = deck(tmp_path, "## T\n\n- one that goes\n  on a while\n")[0].elements[0]
        assert el["raw"] == ["one that goes on a while"]

    def test_a_fence_is_code_and_keeps_its_language(self, tmp_path):
        el = deck(tmp_path, "## T\n\n```sql\nSELECT 1\n```\n")[0].elements[0]
        assert (el["kind"], el["lang"], el["text"]) == ("code", "sql", "SELECT 1")

    def test_a_table(self, tmp_path):
        el = deck(tmp_path, "## T\n\n| a | b |\n| --- | --- |\n| 1 | 2 |\n")[0].elements[0]
        assert el["kind"] == "table"
        assert el["head_raw"] == ["a", "b"]
        assert el["rows_raw"] == [["1", "2"]]

    def test_a_blockquote(self, tmp_path):
        el = deck(tmp_path, "## T\n\n> said so\n> twice\n")[0].elements[0]
        assert (el["kind"], el["text"]) == ("quote", "said so twice")

    def test_an_image_is_embedded_as_a_data_uri(self, tmp_path):
        (tmp_path / "pic.png").write_bytes(b"\x89PNG\r\n\x1a\n fake")
        el = deck(tmp_path, "## T\n\n![](pic.png)\n")[0].elements[0]
        assert el["kind"] == "image"
        assert el["src"].startswith("data:image/png;base64,")

    def test_a_missing_image_is_reported_and_skipped(self, tmp_path, capsys):
        slides = deck(tmp_path, "## T\n\n![](nope.png)\n")
        assert slides[0].elements == []
        assert "no such image" in capsys.readouterr().err

    def test_images_off_leaves_the_picture_out(self, tmp_path):
        (tmp_path / "pic.png").write_bytes(b"\x89PNG\r\n\x1a\n fake")
        assert deck(tmp_path, "## T\n\n![](pic.png)\n", images=False)[0].elements == []


class TestFrontMatter:
    def test_is_taken_off_the_front(self, tmp_path):
        slides = deck(tmp_path, "---\ntitle: A talk\n---\n\n# One\n")
        assert [s.title for s in slides] == ["One"]

    def test_is_read_back(self, tmp_path):
        (tmp_path / "talk.md").write_text("---\ntitle: A talk\ntheme: dark\n---\n\n# One\n", encoding="utf-8")
        assert markdown_meta(tmp_path / "talk.md") == {"title": "A talk", "theme": "dark"}

    def test_a_deck_that_opens_with_a_break_keeps_it(self):
        meta, body = front_matter("---\n\n# One\n")
        assert meta == {}
        assert body.startswith("---")

    def test_quotes_come_off_the_value(self):
        assert front_matter('---\ntitle: "A talk"\n---\nx\n')[0]["title"] == "A talk"


class TestParse:
    def test_takes_a_markdown_file(self, tmp_path):
        (tmp_path / "a.md").write_text("# One\n", encoding="utf-8")
        assert len(parse(tmp_path / "a.md")) == 1

    def test_refuses_anything_else(self, tmp_path):
        (tmp_path / "a.txt").write_text("# One\n", encoding="utf-8")
        with pytest.raises(ValueError, match="ipynb"):
            parse(tmp_path / "a.txt")
