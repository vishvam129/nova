"""Translate tool: on-demand translate clipboard / selection / speech.

The ``Translator`` Protocol decouples backend (LibreTranslate, Google,
Argos…) from the higher-level ``TranslateTool`` which handles source
detection (via nova.i18n.language) and routing.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol

from nova.i18n.language import HeuristicDetector


class Translator(Protocol):
    def translate(self, text: str, *, source: str, target: str) -> str: ...


@dataclass
class IdentityTranslator:
    """Returns the input verbatim — useful for tests / offline mode."""

    def translate(self, text: str, *, source: str, target: str) -> str:
        del source, target
        return text


@dataclass
class TranslateTool:
    """Glue between auto-detect language → translator backend."""

    backend: Translator
    detector: HeuristicDetector | None = None
    default_target: str = "en"

    def translate(self, text: str, *, target: str | None = None, source: str | None = None) -> str:
        target = target or self.default_target
        if source is None:
            detector = self.detector or HeuristicDetector()
            source = detector.detect(text)
        if source == target:
            return text
        return self.backend.translate(text, source=source, target=target)

    def translate_many(
        self,
        texts: Iterable[str],
        *,
        target: str | None = None,
        source: str | None = None,
    ) -> list[str]:
        return [self.translate(t, target=target, source=source) for t in texts]


__all__ = ["IdentityTranslator", "TranslateTool", "Translator"]
