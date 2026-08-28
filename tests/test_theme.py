import json

import pytest

from pypresent.theme import VARIABLES, Theme, available


def test_the_defaults_are_the_warm_built_in():
    # warm.toml is generated from these defaults; this is what keeps them in step
    assert Theme.named("warm") == Theme()


def test_every_built_in_loads():
    assert set(available()) >= {"warm", "office", "dark", "slate"}
    for name in available():
        assert Theme.named(name).name == name


def test_a_built_in_inherits_what_it_does_not_say():
    # office.toml sets no sizes, so it keeps the base ones
    assert Theme.named("office").title_size == Theme().title_size
    assert Theme.named("office").accent != Theme().accent


class TestResolve:
    def test_none_is_the_default(self):
        assert Theme.resolve(None) == Theme()

    def test_a_name_is_a_built_in(self):
        assert Theme.resolve("dark").name == "dark"

    def test_a_theme_is_itself(self):
        theme = Theme().replace(accent="#000")
        assert Theme.resolve(theme) is theme

    def test_a_dict_is_tokens_over_the_default(self):
        assert Theme.resolve({"accent": "#123456"}).accent == "#123456"

    def test_a_dict_may_name_a_base(self):
        got = Theme.resolve({"base": "dark", "accent": "#123456"})
        assert got.accent == "#123456"
        assert got.canvas == Theme.named("dark").canvas

    def test_an_unknown_name_says_what_there_is(self):
        with pytest.raises(KeyError, match="office"):
            Theme.resolve("nonesuch")


class TestReplace:
    def test_changes_one_token_and_keeps_the_rest(self):
        got = Theme().replace(accent="#000000")
        assert got.accent == "#000000"
        assert got.ink == Theme().ink

    def test_an_unknown_token_is_an_error_that_lists_the_real_ones(self):
        with pytest.raises(TypeError, match="accent"):
            Theme().replace(acccent="#000000")


class TestFiles:
    def test_toml(self, tmp_path):
        (tmp_path / "mine.toml").write_text('base = "dark"\naccent = "#abcdef"\n', encoding="utf-8")
        got = Theme.load(tmp_path / "mine.toml")
        assert (got.name, got.accent, got.canvas) == ("mine", "#abcdef",
                                                      Theme.named("dark").canvas)

    def test_json(self, tmp_path):
        (tmp_path / "mine.json").write_text(json.dumps({"accent": "#abcdef"}), encoding="utf-8")
        assert Theme.load(tmp_path / "mine.json").accent == "#abcdef"

    def test_a_theme_table_is_optional(self, tmp_path):
        (tmp_path / "mine.toml").write_text('[theme]\naccent = "#abcdef"\n', encoding="utf-8")
        assert Theme.load(tmp_path / "mine.toml").accent == "#abcdef"

    def test_resolve_takes_a_path(self, tmp_path):
        (tmp_path / "mine.toml").write_text('accent = "#abcdef"\n', encoding="utf-8")
        assert Theme.resolve(str(tmp_path / "mine.toml")).accent == "#abcdef"

    def test_to_toml_round_trips(self, tmp_path):
        theme = Theme.named("slate").replace(accent="#101010", css="body{opacity:1}")
        (tmp_path / "out.toml").write_text(theme.to_toml(), encoding="utf-8")
        again = Theme.load(tmp_path / "out.toml", name="slate")
        assert again == theme


class TestStylesheet:
    def test_every_token_reaches_the_page(self):
        css = Theme().stylesheet()
        for name, var in VARIABLES.items():
            assert f"{var}: {getattr(Theme(), name)};" in css

    def test_direction_decides_the_font_and_the_rule(self):
        assert "270deg" in Theme().stylesheet("rtl")
        assert "90deg" in Theme().stylesheet("ltr")
        assert Theme().font_rtl in Theme().stylesheet("rtl")

    def test_custom_css_comes_last_so_it_wins(self):
        css = Theme().replace(css=".title{color:red}").stylesheet()
        assert css.rindex(".title{color:red}") > css.rindex("--pp-accent")


class TestToDict:
    def test_carries_only_what_differs(self):
        got = Theme.named("dark").replace(accent="#123456").to_dict()
        assert got["accent"] == "#123456"
        assert "canvas" not in got            # unchanged from dark
        assert got["name"] == "dark"

    def test_survives_the_round_trip_through_json(self):
        theme = Theme.named("office").replace(bullet_size="5cqh")
        assert Theme.resolve(json.loads(json.dumps(theme.to_dict()))) == theme
