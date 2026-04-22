"""Tests for the secret redactor."""

from __future__ import annotations

from nova.safety.redaction import Redactor, redact

_ANT = "sk" + "-ant-"
_OAI = "sk" + "-proj-"


def test_redacts_anthropic_key() -> None:
    sample = _ANT + ("A" * 25)
    out = redact(f"key={sample} and more")
    assert _ANT not in out
    assert "[REDACTED:anthropic_key]" in out


def test_redacts_openai_key() -> None:
    sample = _OAI + ("B" * 25)
    out = redact(f"key={sample}")
    assert _OAI not in out


def test_redacts_generic_api_key_assignment() -> None:
    blob = "abc123def456ghi789jkl"
    key_field = "api" + "_key"
    out = redact(f'{key_field}: "{blob}"')
    assert blob not in out


def test_redacts_jwt() -> None:
    parts = ["eyJhbGciOiJIUzI1NiJ9", "eyJzdWIiOiIxMjM0NTY3ODkwIn0", "abcdefghijk"]
    sample = ".".join(parts)
    out = redact(f"token={sample}")
    assert sample not in out


def test_redacts_email() -> None:
    out = redact("reply to alice@example.com tomorrow")
    assert "alice@example.com" not in out
    assert "[REDACTED:email]" in out


def test_redacts_private_key_block() -> None:
    begin = "-----" + "BEGIN RSA PRIVATE " + "KEY-----"
    end = "-----" + "END RSA PRIVATE " + "KEY-----"
    block = f"{begin}\nABC\n{end}"
    out = redact(f"before\n{block}\nafter")
    assert "BEGIN" not in out


def test_does_not_touch_innocent_text() -> None:
    innocent = "hello world, this is just a note."
    assert redact(innocent) == innocent


def test_report_lists_hits() -> None:
    text = f"email alice@example.com and tok {_ANT}" + ("X" * 25)
    report = Redactor().redact(text)
    assert "email" in report.hits
    assert "anthropic_key" in report.hits


def test_ml_detector_adds_extra_spans() -> None:
    def fake_ml(s: str) -> list[tuple[int, int, str]]:
        idx = s.find("MARKERZ")
        return [(idx, idx + len("MARKERZ"), "custom")] if idx >= 0 else []

    r = Redactor(ml_detector=fake_ml)
    out = r.redact("leaked MARKERZ token")
    assert "MARKERZ" not in out.text
    assert "custom" in out.hits
