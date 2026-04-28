"""Language detection + voice/LLM auto-routing.

``detect_language(text)`` returns an ISO-639-1 code using a small
character-frequency heuristic — no external models, so it's always
available offline.  Real deployments can plug in fasttext-langid via
the ``LangDetector`` Protocol.

``LanguageRouter`` picks the appropriate STT/TTS voice + LLM prompt
language for a detected code.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Protocol

# Tiny stop-word fingerprints — enough to disambiguate common languages.
_FINGERPRINTS: dict[str, frozenset[str]] = {
    "en": frozenset({"the", "and", "you", "is", "of", "to", "in", "i"}),
    "es": frozenset({"el", "la", "que", "de", "y", "es", "los", "un"}),
    "fr": frozenset({"le", "la", "les", "et", "de", "que", "un", "est"}),
    "de": frozenset({"der", "die", "und", "ist", "das", "ich", "nicht", "den"}),
    "hi": frozenset({"है", "और", "मैं", "तुम", "वह", "में", "का", "की"}),
    "it": frozenset({"il", "la", "che", "di", "e", "un", "non", "per"}),
    "pt": frozenset({"o", "a", "que", "de", "e", "um", "para", "não"}),
    "ja": frozenset({"の", "に", "は", "を", "た", "が", "で", "て"}),
}


class LangDetector(Protocol):
    def detect(self, text: str) -> str: ...


@dataclass
class HeuristicDetector:
    """Tiny stop-word fingerprint detector.  Defaults to 'en' on tie / empty."""

    fingerprints: dict[str, frozenset[str]] = field(default_factory=lambda: dict(_FINGERPRINTS))
    default: str = "en"

    def detect(self, text: str) -> str:
        if not text or not text.strip():
            return self.default
        tokens = re.findall(r"\w+", text.lower(), flags=re.UNICODE)
        if not tokens:
            return self.default
        token_set = set(tokens)
        scores: dict[str, int] = {}
        for code, words in self.fingerprints.items():
            scores[code] = len(token_set & words)
        best = max(scores, key=lambda c: scores[c])
        if scores[best] == 0:
            return self.default
        return best


@dataclass(frozen=True, slots=True)
class LanguagePreference:
    """Per-language model + voice routing."""

    code: str
    stt_model: str
    tts_voice: str
    llm_system_addendum: str = ""


@dataclass
class LanguageRouter:
    """Looks up the LanguagePreference for a detected code."""

    preferences: dict[str, LanguagePreference] = field(default_factory=dict)
    default: LanguagePreference = field(
        default_factory=lambda: LanguagePreference(
            code="en",
            stt_model="moonshine-base",
            tts_voice="kokoro-en-female",
        )
    )

    def add(self, pref: LanguagePreference) -> None:
        self.preferences[pref.code] = pref

    def resolve(self, code: str) -> LanguagePreference:
        return self.preferences.get(code, self.default)

    def supported(self) -> Iterable[str]:
        return sorted({self.default.code, *self.preferences.keys()})


def default_router() -> LanguageRouter:
    """Router pre-loaded with sensible defaults for the top 8 languages."""
    router = LanguageRouter()
    presets = [
        LanguagePreference("en", "moonshine-base", "kokoro-en-female"),
        LanguagePreference("es", "whisper-small", "piper-es-female"),
        LanguagePreference("fr", "whisper-small", "piper-fr-female"),
        LanguagePreference("de", "whisper-small", "piper-de-female"),
        LanguagePreference("it", "whisper-small", "piper-it-male"),
        LanguagePreference("pt", "whisper-small", "piper-pt-male"),
        LanguagePreference("hi", "whisper-medium", "piper-hi-female"),
        LanguagePreference("ja", "whisper-medium", "piper-ja-female"),
    ]
    for p in presets:
        router.add(p)
    return router


__all__ = [
    "HeuristicDetector",
    "LangDetector",
    "LanguagePreference",
    "LanguageRouter",
    "default_router",
]
