"""Tests for nova.quality.gaia_lite."""

from __future__ import annotations

import json
from pathlib import Path

from nova.quality.gaia_lite import (
    GaiaLiteRunner,
    diff_releases,
    gaia_lite_cases,
)


class _Cheater:
    """Always returns the literal expected substring of every case."""

    def run(self, prompt: str) -> str:
        if "17 * 24" in prompt:
            return "408"
        if "New Zealand" in prompt:
            return "wellington is the capital"
        if "100 days" in prompt:
            return "Friday"
        if "Spanish" in prompt:
            return "buenos días"
        if "ls -lh" in prompt:
            return "list directory contents"
        if "100 km" in prompt:
            return "62 mph"
        if "list and a tuple" in prompt:
            return "tuples are immutable"
        if "mississippi" in prompt:
            return "ippississim"
        return ""


class _Wrong:
    def run(self, prompt: str) -> str:
        return "no idea"


def test_gaia_lite_cases_non_empty() -> None:
    cases = gaia_lite_cases()
    assert len(cases) >= 5
    assert all(c.id.startswith("gaia-") for c in cases)


def test_runner_writes_release_tagged_report(tmp_path: Path) -> None:
    runner = GaiaLiteRunner(output_dir=tmp_path)
    out = runner.run(_Cheater(), release_tag="v1.0.0")
    assert out.exists()
    assert out.name == "gaia_lite-v1.0.0.json"
    data = json.loads(out.read_text())
    assert data["release_tag"] == "v1.0.0"
    assert data["pass_rate"] >= 0.5


def test_runner_records_failures(tmp_path: Path) -> None:
    runner = GaiaLiteRunner(output_dir=tmp_path)
    out = runner.run(_Wrong(), release_tag="v0.0.1")
    data = json.loads(out.read_text())
    assert data["pass_rate"] == 0.0


def test_history_lists_all_runs(tmp_path: Path) -> None:
    runner = GaiaLiteRunner(output_dir=tmp_path)
    runner.run(_Cheater(), release_tag="v1.0.0")
    runner.run(_Wrong(), release_tag="v1.1.0")
    hist = runner.history()
    assert len(hist) == 2


def test_trend_returns_release_pairs(tmp_path: Path) -> None:
    runner = GaiaLiteRunner(output_dir=tmp_path)
    runner.run(_Cheater(), release_tag="v1.0.0")
    runner.run(_Wrong(), release_tag="v1.1.0")
    trend = runner.trend()
    assert len(trend) == 2
    assert all(isinstance(t[1], float) for t in trend)


def test_diff_releases_delta(tmp_path: Path) -> None:
    runner = GaiaLiteRunner(output_dir=tmp_path)
    runner.run(_Cheater(), release_tag="v1.0.0")
    runner.run(_Wrong(), release_tag="v1.1.0")
    deltas = diff_releases(runner.history())
    # Second release was worse → negative delta
    assert deltas[1][1] < 0.0


def test_diff_releases_first_is_zero() -> None:
    out = diff_releases([{"release_tag": "v1", "pass_rate": 0.8}])
    assert out == [("v1", 0.0)]
