"""Tests for nova.tools.builtin.screenshot."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from nova.tools.builtin.screenshot import (
    Region,
    ScreenshotUnavailable,
    _capture_cmd,
    capture,
    ocr,
)


def test_region_geometry() -> None:
    r = Region(10, 20, 100, 200)
    assert r.as_geometry() == "100x200+10+20"


def test_capture_cmd_linux_grim(tmp_path: Path) -> None:
    out = tmp_path / "s.png"
    with (
        patch("nova.tools.builtin.screenshot.sys.platform", "linux"),
        patch(
            "nova.tools.builtin.screenshot.shutil.which",
            side_effect=lambda b: "/usr/bin/grim" if b == "grim" else None,
        ),
    ):
        cmd = _capture_cmd(out, None)
    assert cmd is not None
    assert cmd[0] == "grim"


def test_capture_cmd_linux_scrot_with_region(tmp_path: Path) -> None:
    out = tmp_path / "s.png"

    def which(name: str) -> str | None:
        return "/usr/bin/scrot" if name == "scrot" else None

    with (
        patch("nova.tools.builtin.screenshot.sys.platform", "linux"),
        patch("nova.tools.builtin.screenshot.shutil.which", side_effect=which),
    ):
        cmd = _capture_cmd(out, Region(0, 0, 50, 50))
    assert cmd is not None
    assert cmd[0] == "scrot"
    assert "-a" in cmd


def test_capture_cmd_macos(tmp_path: Path) -> None:
    out = tmp_path / "s.png"
    with (
        patch("nova.tools.builtin.screenshot.sys.platform", "darwin"),
        patch("nova.tools.builtin.screenshot.shutil.which", return_value="/x"),
    ):
        cmd = _capture_cmd(out, Region(1, 2, 3, 4))
    assert cmd is not None
    assert cmd[0] == "screencapture"
    assert "-R" in cmd


def test_capture_cmd_unsupported_returns_none(tmp_path: Path) -> None:
    out = tmp_path / "s.png"
    with (
        patch("nova.tools.builtin.screenshot.sys.platform", "linux"),
        patch("nova.tools.builtin.screenshot.shutil.which", return_value=None),
    ):
        assert _capture_cmd(out, None) is None


def test_capture_raises_when_unavailable(tmp_path: Path) -> None:
    with (
        patch("nova.tools.builtin.screenshot._capture_cmd", return_value=None),
        pytest.raises(ScreenshotUnavailable),
    ):
        capture(tmp_path / "s.png")


def test_capture_runs_command(tmp_path: Path) -> None:
    out = tmp_path / "s.png"
    with (
        patch("nova.tools.builtin.screenshot._capture_cmd", return_value=["echo", "ok"]),
        patch(
            "nova.tools.builtin.screenshot.subprocess.run",
            return_value=MagicMock(returncode=0, stderr=b""),
        ),
    ):
        assert capture(out) == out


def test_ocr_no_tesseract_raises(tmp_path: Path) -> None:
    with (
        patch("nova.tools.builtin.screenshot.shutil.which", return_value=None),
        pytest.raises(ScreenshotUnavailable),
    ):
        ocr(tmp_path / "x.png")


def test_ocr_returns_text(tmp_path: Path) -> None:
    p = tmp_path / "x.png"
    p.write_bytes(b"\x89PNG")
    with (
        patch("nova.tools.builtin.screenshot.shutil.which", return_value="/usr/bin/tesseract"),
        patch(
            "nova.tools.builtin.screenshot.subprocess.run",
            return_value=MagicMock(returncode=0, stdout=b"hello world\n", stderr=b""),
        ),
    ):
        assert ocr(p) == "hello world"
