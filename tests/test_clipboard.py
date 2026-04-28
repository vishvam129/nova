"""Tests for nova.tools.builtin.clipboard."""

from __future__ import annotations

from unittest.mock import patch

from nova.tools.builtin.clipboard import (
    ClipboardHistory,
    clipboard_read,
    clipboard_write,
)


def test_history_push_and_latest() -> None:
    h = ClipboardHistory(capacity=5)
    h.push("a")
    h.push("b")
    assert h.latest() == "b"
    assert len(h) == 2


def test_history_dedupe_consecutive() -> None:
    h = ClipboardHistory()
    h.push("x")
    h.push("x")
    assert len(h) == 1


def test_history_skip_empty() -> None:
    h = ClipboardHistory()
    h.push("")
    assert len(h) == 0


def test_history_capacity_evicts_oldest() -> None:
    h = ClipboardHistory(capacity=2)
    h.push("a")
    h.push("b")
    h.push("c")
    assert h.items() == ["b", "c"]


def test_history_clear() -> None:
    h = ClipboardHistory()
    h.push("a")
    h.clear()
    assert len(h) == 0
    assert h.latest() == ""


def test_clipboard_write_falls_back_to_inproc() -> None:
    with patch("nova.tools.builtin.clipboard._write_native", return_value=False):
        clipboard_write("inproc-text")
    with patch("nova.tools.builtin.clipboard._read_native", return_value=None):
        assert clipboard_read() == "inproc-text"


def test_clipboard_write_native_success() -> None:
    with patch("nova.tools.builtin.clipboard._write_native", return_value=True):
        assert clipboard_write("hi") is True


def test_clipboard_read_native_takes_precedence() -> None:
    with patch("nova.tools.builtin.clipboard._read_native", return_value="from-native"):
        assert clipboard_read() == "from-native"
