"""Tests for nova.i18n.translate."""

from __future__ import annotations

from dataclasses import dataclass

from nova.i18n.translate import IdentityTranslator, TranslateTool


@dataclass
class _RecordingTranslator:
    suffix: str = ""

    def translate(self, text: str, *, source: str, target: str) -> str:
        return f"[{source}->{target}] {text}{self.suffix}"


def test_identity_passes_through() -> None:
    out = IdentityTranslator().translate("hi", source="en", target="fr")
    assert out == "hi"


def test_translate_tool_auto_detects_source() -> None:
    tool = TranslateTool(backend=_RecordingTranslator())
    out = tool.translate("le chat est sur la table", target="en")
    assert out.startswith("[fr->en]")


def test_translate_tool_skips_when_same_lang() -> None:
    tool = TranslateTool(backend=_RecordingTranslator())
    out = tool.translate("the quick brown fox", target="en")
    assert out == "the quick brown fox"  # no backend call needed


def test_translate_tool_explicit_source_overrides_detection() -> None:
    tool = TranslateTool(backend=_RecordingTranslator())
    out = tool.translate("hello", source="es", target="en")
    assert out.startswith("[es->en]")


def test_translate_tool_default_target() -> None:
    tool = TranslateTool(backend=_RecordingTranslator(), default_target="fr")
    out = tool.translate("hello world the quick fox")
    # default detected as 'en', translates to 'fr'
    assert "->fr" in out


def test_translate_many() -> None:
    tool = TranslateTool(backend=_RecordingTranslator())
    out = tool.translate_many(["hello there", "goodbye world"], source="en", target="fr")
    assert len(out) == 2
    assert all("[en->fr]" in t for t in out)
