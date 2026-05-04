"""GAIA-lite subset for objective per-release benchmark tracking.

A trimmed GAIA suite (10–20 tasks) that runs in <60 s.  Each task has an
expected substring or regex; the harness reuses ``EvalHarness`` from
``nova.quality.eval_harness`` and writes a release-tagged JSON report
so we can chart pass-rate over time.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from nova.quality.eval_harness import Agent, EvalHarness, Report, TaskCase

_GAIA_LITE_CASES: tuple[TaskCase, ...] = (
    TaskCase(
        id="gaia-1",
        prompt="What is 17 * 24?",
        expect_contains=("408",),
        category="math",
    ),
    TaskCase(
        id="gaia-2",
        prompt="Capital of New Zealand?",
        expect_contains=("wellington",),
        category="knowledge",
    ),
    TaskCase(
        id="gaia-3",
        prompt="If today is Wednesday, what day is it 100 days from now?",
        expect_regex=r"(friday|saturday)",
        category="reasoning",
    ),
    TaskCase(
        id="gaia-4",
        prompt="Translate 'good morning' to Spanish.",
        expect_contains=("buenos d",),
        category="i18n",
    ),
    TaskCase(
        id="gaia-5",
        prompt="What does the Unix command `ls -lh` do?",
        expect_contains=("list",),
        expect_not_contains=("don't know",),
        category="tools",
    ),
    TaskCase(
        id="gaia-6",
        prompt="Convert 100 km/h to miles per hour, rounded.",
        expect_regex=r"6[12]",
        category="math",
    ),
    TaskCase(
        id="gaia-7",
        prompt="What's the difference between a list and a tuple in Python?",
        expect_contains=("immutable",),
        category="knowledge",
    ),
    TaskCase(
        id="gaia-8",
        prompt="Spell 'mississippi' backwards.",
        expect_contains=("ippississim",),
        category="reasoning",
    ),
)


def gaia_lite_cases() -> tuple[TaskCase, ...]:
    return _GAIA_LITE_CASES


@dataclass
class GaiaLiteRunner:
    """Runs the GAIA-lite suite and persists tagged reports."""

    output_dir: Path = field(
        default_factory=lambda: Path("~/.local/share/nova/benchmarks").expanduser()
    )
    cases: tuple[TaskCase, ...] = field(default_factory=gaia_lite_cases)

    def __post_init__(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def run(self, agent: Agent, *, release_tag: str) -> Path:
        harness = EvalHarness(cases=list(self.cases))
        report = harness.run(agent)
        out = self.output_dir / f"gaia_lite-{release_tag}.json"
        out.write_text(_serialize_report(report, release_tag))
        return out

    def history(self) -> list[dict[str, Any]]:
        runs: list[dict[str, Any]] = []
        for path in sorted(self.output_dir.glob("gaia_lite-*.json")):
            try:
                runs.append(json.loads(path.read_text()))
            except (OSError, json.JSONDecodeError):
                continue
        return runs

    def trend(self) -> list[tuple[str, float]]:
        return [(str(r["release_tag"]), float(r["pass_rate"])) for r in self.history()]


def _serialize_report(report: Report, release_tag: str) -> str:
    payload = {
        "release_tag": release_tag,
        "started_at": report.started_at.isoformat(),
        "captured_at": datetime.now().isoformat(),
        "total": report.total,
        "passed": report.passed,
        "failed": report.failed,
        "pass_rate": report.pass_rate,
        "outcomes": [
            {
                "case_id": o.case_id,
                "passed": o.passed,
                "reason": o.reason,
                "duration_s": o.duration_s,
            }
            for o in report.outcomes
        ],
    }
    return json.dumps(payload, indent=2)


def diff_releases(history: Iterable[dict[str, Any]]) -> list[tuple[str, float]]:
    """Per-release deltas in pass-rate vs the previous run."""
    items = list(history)
    out: list[tuple[str, float]] = []
    prev: float | None = None
    for entry in items:
        rate = float(entry["pass_rate"])
        delta = 0.0 if prev is None else rate - prev
        out.append((str(entry["release_tag"]), delta))
        prev = rate
    return out


__all__ = ["GaiaLiteRunner", "diff_releases", "gaia_lite_cases"]
