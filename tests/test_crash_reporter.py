"""Tests for nova.devops.crash_reporter."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from nova.devops.crash_reporter import CrashReport, CrashReporter, summarise


def _raise() -> None:
    raise RuntimeError("api key sk-AAAAAAAAAAAAAAAAAAAAAAAA leaked")


def test_disabled_does_nothing(tmp_path: Path) -> None:
    r = CrashReporter(enabled=False, output_dir=tmp_path)
    try:
        _raise()
    except RuntimeError as exc:
        assert r.capture(exc) is None
    assert r.list_local() == []


def test_enabled_writes_local_file(tmp_path: Path) -> None:
    r = CrashReporter(enabled=True, output_dir=tmp_path)
    try:
        _raise()
    except RuntimeError as exc:
        path = r.capture(exc)
    assert path is not None
    assert path.exists()
    data = json.loads(path.read_text())
    assert data["exception_type"] == "RuntimeError"


def test_secrets_redacted_in_dump(tmp_path: Path) -> None:
    r = CrashReporter(enabled=True, output_dir=tmp_path)
    try:
        _raise()
    except RuntimeError as exc:
        path = r.capture(exc)
    text = path.read_text()  # type: ignore[union-attr]
    assert "sk-AAAAAAAA" not in text
    assert "sk-***" in text


def test_extras_recorded_and_redacted(tmp_path: Path) -> None:
    r = CrashReporter(enabled=True, output_dir=tmp_path)
    try:
        raise ValueError("plain")
    except ValueError as exc:
        path = r.capture(exc, extras={"auth": "Bearer abc.def-123"})
    data = json.loads(path.read_text())  # type: ignore[union-attr]
    assert "Bearer ***" in data["extras"]["auth"]


def test_list_local_returns_files(tmp_path: Path) -> None:
    r = CrashReporter(enabled=True, output_dir=tmp_path)
    try:
        raise ValueError("a")
    except ValueError as exc:
        r.capture(exc)
    assert len(r.list_local()) == 1


def test_clear_removes_all(tmp_path: Path) -> None:
    r = CrashReporter(enabled=True, output_dir=tmp_path)
    try:
        raise ValueError("a")
    except ValueError as exc:
        r.capture(exc)
    assert r.clear() == 1
    assert r.list_local() == []


def test_upload_disabled_by_default(tmp_path: Path) -> None:
    r = CrashReporter(enabled=True, output_dir=tmp_path, upload=False)
    with patch("nova.devops.crash_reporter.urllib.request.urlopen") as urlopen:
        try:
            raise ValueError("a")
        except ValueError as exc:
            r.capture(exc)
    urlopen.assert_not_called()


def test_upload_when_enabled_calls_url(tmp_path: Path) -> None:
    r = CrashReporter(
        enabled=True,
        upload=True,
        upload_url="https://crashes.example/v1",
        output_dir=tmp_path,
    )
    fake = MagicMock(status=202)
    fake.__enter__ = MagicMock(return_value=fake)
    fake.__exit__ = MagicMock(return_value=False)
    with patch("nova.devops.crash_reporter.urllib.request.urlopen", return_value=fake) as urlopen:
        try:
            raise ValueError("a")
        except ValueError as exc:
            r.capture(exc)
    urlopen.assert_called_once()


def test_summarise_counts() -> None:
    from datetime import datetime as _dt

    reports = [
        CrashReport(
            timestamp=_dt.now(),
            platform="x",
            python_version="3.13",
            nova_version="0.1",
            exception_type="ValueError",
            exception_message="x",
            traceback_text="",
        ),
        CrashReport(
            timestamp=_dt.now(),
            platform="x",
            python_version="3.13",
            nova_version="0.1",
            exception_type="ValueError",
            exception_message="x",
            traceback_text="",
        ),
        CrashReport(
            timestamp=_dt.now(),
            platform="x",
            python_version="3.13",
            nova_version="0.1",
            exception_type="RuntimeError",
            exception_message="x",
            traceback_text="",
        ),
    ]
    out = summarise(reports)
    assert out == {"ValueError": 2, "RuntimeError": 1}
