"""Tests for nova.i18n.language."""

from __future__ import annotations

from nova.i18n.language import (
    HeuristicDetector,
    LanguagePreference,
    LanguageRouter,
    default_router,
)


def test_detect_english() -> None:
    d = HeuristicDetector()
    assert d.detect("the quick brown fox is jumping over the lazy dog") == "en"


def test_detect_spanish() -> None:
    d = HeuristicDetector()
    assert d.detect("el sol que brilla y un dia que es muy bonito") == "es"


def test_detect_french() -> None:
    d = HeuristicDetector()
    assert d.detect("le chat est sur la table et un autre est ici") == "fr"


def test_detect_german() -> None:
    d = HeuristicDetector()
    assert d.detect("der hund ist nicht das problem ich denke") == "de"


def test_detect_empty_returns_default() -> None:
    d = HeuristicDetector(default="en")
    assert d.detect("") == "en"
    assert d.detect("   ") == "en"


def test_detect_no_match_returns_default() -> None:
    d = HeuristicDetector(default="en")
    assert d.detect("xyz qqq zzz") == "en"


def test_router_resolve_known() -> None:
    r = LanguageRouter()
    r.add(LanguagePreference("es", "whisper-small", "piper-es-female"))
    p = r.resolve("es")
    assert p.tts_voice == "piper-es-female"


def test_router_resolve_default_for_unknown() -> None:
    r = LanguageRouter()
    p = r.resolve("xx")
    assert p.code == "en"


def test_default_router_has_common_languages() -> None:
    r = default_router()
    sup = list(r.supported())
    assert "en" in sup
    assert "es" in sup
    assert "ja" in sup


def test_router_supported_dedupes() -> None:
    r = LanguageRouter()
    r.add(LanguagePreference("en", "x", "y"))  # same code as default
    sup = list(r.supported())
    assert sup.count("en") == 1
