"""Tests for nova.i18n.rtl."""

from __future__ import annotations

from nova.i18n.rtl import (
    direction,
    html_dir_attr,
    is_rtl,
    supported_rtl_languages,
    wrap_bidi,
)


def test_is_rtl_known() -> None:
    assert is_rtl("ar") is True
    assert is_rtl("he") is True
    assert is_rtl("fa") is True


def test_is_rtl_ltr_default() -> None:
    assert is_rtl("en") is False
    assert is_rtl("fr") is False
    assert is_rtl("ja") is False


def test_is_rtl_handles_region_suffix() -> None:
    assert is_rtl("ar-EG") is True
    assert is_rtl("ar_SA") is True


def test_is_rtl_empty() -> None:
    assert is_rtl("") is False


def test_direction_rtl() -> None:
    assert direction("he") == "rtl"


def test_direction_ltr() -> None:
    assert direction("en") == "ltr"


def test_html_dir_attr_rtl() -> None:
    assert html_dir_attr("ar") == 'dir="rtl"'


def test_html_dir_attr_ltr() -> None:
    assert html_dir_attr("en") == 'dir="ltr"'


def test_wrap_bidi_rtl_uses_rle() -> None:
    out = wrap_bidi("שלום", "he")
    assert out.endswith("‬")
    assert "‫" in out  # RLE


def test_wrap_bidi_ltr_uses_lre() -> None:
    out = wrap_bidi("hello", "en")
    assert "‪" in out  # LRE
    assert out.endswith("‬")


def test_supported_list_includes_arabic_hebrew() -> None:
    langs = supported_rtl_languages()
    assert "ar" in langs
    assert "he" in langs
    assert sorted(langs) == langs
