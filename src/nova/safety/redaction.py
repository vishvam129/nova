"""Secret redaction middleware.

Strips secrets (API keys, tokens, emails, phone numbers, credit-card
numbers, SSH keys) from text before it hits persistent storage or
egresses the device. The regex pass is always on; an optional ML
detector (``detect-secrets`` or a custom callable) can be layered for
better recall on uncommon formats.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class Pattern:
    name: str
    regex: re.Pattern[str]
    replacement: str


DEFAULT_PATTERNS: tuple[Pattern, ...] = (
    Pattern(
        "anthropic_key",
        re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}"),
        "[REDACTED:anthropic_key]",
    ),
    Pattern(
        "openai_key",
        re.compile(r"sk-(?:proj-)?[A-Za-z0-9_-]{20,}"),
        "[REDACTED:openai_key]",
    ),
    Pattern(
        "generic_api_key",
        re.compile(
            r"(?i)(?:api[_-]?key|access[_-]?token|bearer)\s*[:=]\s*['\"]?([A-Za-z0-9_\-\.]{16,})"
        ),
        "[REDACTED:api_key]",
    ),
    Pattern(
        "jwt",
        re.compile(r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"),
        "[REDACTED:jwt]",
    ),
    Pattern(
        "aws_access_key",
        re.compile(r"AKIA[0-9A-Z]{16}"),
        "[REDACTED:aws_key]",
    ),
    Pattern(
        "private_key_block",
        re.compile(
            r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----[\s\S]+?"
            r"-----END (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"
        ),
        "[REDACTED:private_key]",
    ),
    Pattern(
        "email",
        re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
        "[REDACTED:email]",
    ),
    Pattern(
        "phone",
        re.compile(r"\+?\d{1,3}[-.\s]?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{4}"),
        "[REDACTED:phone]",
    ),
    Pattern(
        "credit_card",
        re.compile(r"\b(?:\d[ -]*?){13,19}\b"),
        "[REDACTED:credit_card]",
    ),
)


MlDetector = Callable[[str], list[tuple[int, int, str]]]
"""Return a list of (start, end, label) spans to redact."""


@dataclass(frozen=True, slots=True)
class RedactionReport:
    text: str
    hits: tuple[str, ...]


@dataclass
class Redactor:
    patterns: tuple[Pattern, ...] = DEFAULT_PATTERNS
    ml_detector: MlDetector | None = None
    _hit_labels: list[str] = field(default_factory=list, init=False)

    def redact(self, text: str) -> RedactionReport:
        self._hit_labels = []
        out = text
        for pattern in self.patterns:
            new_out, count = pattern.regex.subn(pattern.replacement, out)
            if count:
                self._hit_labels.extend([pattern.name] * count)
            out = new_out
        if self.ml_detector is not None:
            spans = sorted(self.ml_detector(out), reverse=True)
            for start, end, label in spans:
                out = f"{out[:start]}[REDACTED:{label}]{out[end:]}"
                self._hit_labels.append(label)
        return RedactionReport(text=out, hits=tuple(self._hit_labels))


def redact(text: str) -> str:
    """Convenience one-shot redaction with default patterns."""
    return Redactor().redact(text).text


__all__ = [
    "DEFAULT_PATTERNS",
    "MlDetector",
    "Pattern",
    "RedactionReport",
    "Redactor",
    "redact",
]
