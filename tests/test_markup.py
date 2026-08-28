from pypresent.markup import clean, clean_html, inline, trim_text


class TestInline:
    def test_renders_the_four_things_a_slide_uses(self):
        got = inline("**bold**, *thin*, `x = 1` and [a link](http://e.com)")
        assert "<strong>bold</strong>" in got
        assert "<em>thin</em>" in got
        assert "<code>x = 1</code>" in got
        assert '<a href="http://e.com">a link</a>' in got

    def test_escapes_markup_outside_code(self):
        assert inline("a < b & c") == "a &lt; b &amp; c"

    def test_a_code_span_may_hold_anything(self):
        # the span is lifted out before escaping, so its < is not read as a tag
        assert inline("`List[int] & <T>`") == "<code>List[int] &amp; &lt;T&gt;</code>"

    def test_a_star_inside_a_word_is_not_italic(self):
        assert "<em>" not in inline("2 * 3 * 4")

    def test_newlines_become_spaces(self):
        assert inline("one\ntwo") == "one two"


class TestTrimText:
    def test_no_trim_is_no_change(self):
        assert trim_text("a\nb", {}) == "a\nb"

    def test_width_clips_and_marks(self):
        assert trim_text("abcdefgh", {"width": 4}) == "abc…"

    def test_head_keeps_the_first_lines(self):
        assert trim_text("1\n2\n3\n4", {"head": 2}) == "1\n2\n…"

    def test_head_and_tail_drop_the_middle(self):
        assert trim_text("1\n2\n3\n4\n5", {"head": 1, "tail": 1}) == "1\n…\n5"

    def test_nothing_is_dropped_when_it_already_fits(self):
        assert trim_text("1\n2", {"head": 1, "tail": 1}) == "1\n2"


def test_clean_dedents_an_inline_block():
    assert clean("\n    one\n    two\n") == "one\ntwo"


def test_clean_html_drops_the_style_pandas_writes():
    got = clean_html("<style>td{color:red}</style><table><tr><td>1</td></tr></table>")
    assert got.startswith("<table>")
    assert "style" not in got
