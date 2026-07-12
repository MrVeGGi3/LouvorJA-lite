import re

from app.db.colors import delphi_color_to_css


def test_hex_format_matches_mirror_html_example():
    assert delphi_color_to_css("$000b4ef") == "#efb400"


def test_named_colors():
    assert delphi_color_to_css("clWhite") == "#FFFFFF"
    assert delphi_color_to_css("clBlack") == "#000000"


def test_none_uses_default():
    assert delphi_color_to_css(None, default="#123456") == "#123456"


def test_empty_string_uses_default():
    assert delphi_color_to_css("", default="#123456") == "#123456"


def test_unrecognized_format_uses_default():
    assert delphi_color_to_css("not-a-color", default="#123456") == "#123456"


def test_negative_integer_string_does_not_crash():
    resultado = delphi_color_to_css("-1250067")
    assert re.fullmatch(r"#[0-9a-f]{6}", resultado)
