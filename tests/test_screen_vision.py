"""Tests for nova.tools.builtin.screen_vision."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from nova.tools.builtin.screen_vision import ScreenVision


class _FakeClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []
        self.answer = "I see a code editor"

    def ask(self, question: str, image_b64: str, mime: str = "image/png") -> str:
        self.calls.append((question, image_b64[:8]))
        return self.answer


def test_ask_about_screen(tmp_path: Path) -> None:
    fake = _FakeClient()
    sv = ScreenVision(client=fake)
    fake_png = tmp_path / "fake.png"
    fake_png.write_bytes(b"\x89PNG\r\n\x1a\nfakefake")

    with patch("nova.tools.builtin.screen_vision.capture", return_value=fake_png):
        ans = sv.ask_about_screen("what's on screen?", tmp_path=fake_png)
    assert ans == "I see a code editor"
    assert fake.calls[0][0] == "what's on screen?"


def test_frame_count_increments(tmp_path: Path) -> None:
    fake = _FakeClient()
    sv = ScreenVision(client=fake)
    fake_png = tmp_path / "f.png"
    fake_png.write_bytes(b"\x89PNG")

    with patch("nova.tools.builtin.screen_vision.capture", return_value=fake_png):
        sv.ask_about_screen("q1", tmp_path=fake_png)
        sv.ask_about_screen("q2", tmp_path=fake_png)
    assert sv.frame_count == 2


def test_stream_yields_per_frame(tmp_path: Path) -> None:
    fake = _FakeClient()
    sv = ScreenVision(client=fake, interval_s=0.0)
    fake_png = tmp_path / "f.png"
    fake_png.write_bytes(b"\x89PNG")

    with (
        patch("nova.tools.builtin.screen_vision.capture", return_value=fake_png),
        patch("nova.tools.builtin.screen_vision._temp_png", return_value=fake_png),
    ):
        answers = list(sv.stream("describe", frames=3))
    assert len(answers) == 3
    assert all(a == "I see a code editor" for a in answers)


def test_temp_path_cleaned_when_implicit(tmp_path: Path) -> None:
    fake = _FakeClient()
    sv = ScreenVision(client=fake)
    fake_png = tmp_path / "f.png"
    fake_png.write_bytes(b"\x89PNG")

    with (
        patch("nova.tools.builtin.screen_vision.capture", return_value=fake_png),
        patch("nova.tools.builtin.screen_vision._temp_png", return_value=fake_png),
    ):
        sv.ask_about_screen("q")
    assert not fake_png.exists()
