"""Tests for nova.ui.dictation."""

from __future__ import annotations

from nova.ui.dictation import DictationSession


class _FakeTranscriber:
    def __init__(self, text: str = "hello world") -> None:
        self.text = text
        self.last_pcm = b""

    def transcribe(self, pcm: bytes) -> str:
        self.last_pcm = pcm
        return self.text


class _FakeInjector:
    def __init__(self) -> None:
        self.injected: list[str] = []

    def inject(self, text: str) -> bool:
        self.injected.append(text)
        return True


def test_start_activates() -> None:
    s = DictationSession(transcriber=_FakeTranscriber(), injector=_FakeInjector())
    assert s.active is False
    s.start()
    assert s.active is True


def test_feed_buffers_audio() -> None:
    t = _FakeTranscriber()
    s = DictationSession(transcriber=t, injector=_FakeInjector())
    s.start()
    s.feed(b"\x01\x02")
    s.feed(b"\x03")
    s.stop()
    assert t.last_pcm == b"\x01\x02\x03"


def test_stop_injects_transcript() -> None:
    inj = _FakeInjector()
    s = DictationSession(transcriber=_FakeTranscriber("hi there"), injector=inj)
    s.start()
    s.feed(b"\x00")
    text = s.stop()
    assert text == "hi there"
    assert inj.injected == ["hi there"]


def test_stop_when_inactive_returns_empty() -> None:
    s = DictationSession(transcriber=_FakeTranscriber(), injector=_FakeInjector())
    assert s.stop() == ""


def test_feed_when_inactive_is_noop() -> None:
    t = _FakeTranscriber("?")
    s = DictationSession(transcriber=t, injector=_FakeInjector())
    s.feed(b"\x01")  # not active
    s.start()
    s.stop()
    assert t.last_pcm == b""


def test_empty_text_not_injected() -> None:
    inj = _FakeInjector()
    s = DictationSession(transcriber=_FakeTranscriber(""), injector=inj)
    s.start()
    s.stop()
    assert inj.injected == []


def test_on_text_callback_fires() -> None:
    captured: list[str] = []
    s = DictationSession(
        transcriber=_FakeTranscriber("xyz"),
        injector=_FakeInjector(),
        on_text=captured.append,
    )
    s.start()
    s.stop()
    assert captured == ["xyz"]


def test_last_text() -> None:
    s = DictationSession(transcriber=_FakeTranscriber("memo"), injector=_FakeInjector())
    s.start()
    s.stop()
    assert s.last_text == "memo"


def test_buffer_cleared_after_stop() -> None:
    t = _FakeTranscriber("a")
    s = DictationSession(transcriber=t, injector=_FakeInjector())
    s.start()
    s.feed(b"\x01")
    s.stop()
    s.start()
    s.stop()  # second cycle
    assert t.last_pcm == b""
