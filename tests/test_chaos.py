"""Tests for nova.quality.chaos."""

from __future__ import annotations

import pytest

from nova.quality.chaos import (
    ChaosController,
    ChaosScenario,
    Fault,
    FaultKind,
    chaos_call,
    common_scenarios,
)


def test_no_faults_passes_through() -> None:
    c = ChaosController()
    assert chaos_call(c, "x", lambda: "ok") == "ok"


def test_exception_fault_raises() -> None:
    c = ChaosController(seed=0)
    c.add(Fault(target="x", kind=FaultKind.EXCEPTION, exception=ValueError, message="bad"))
    with pytest.raises(ValueError):
        chaos_call(c, "x", lambda: "ok")


def test_empty_fault_returns_default() -> None:
    c = ChaosController(seed=0)
    c.add(Fault(target="x", kind=FaultKind.EMPTY))
    assert chaos_call(c, "x", lambda: "ok", empty_value="") == ""


def test_timeout_fault_raises_timeout() -> None:
    c = ChaosController(seed=0)
    c.add(Fault(target="x", kind=FaultKind.TIMEOUT))
    with pytest.raises(TimeoutError):
        chaos_call(c, "x", lambda: "ok")


def test_delay_fault_runs_func() -> None:
    c = ChaosController(seed=0)
    c.add(Fault(target="x", kind=FaultKind.DELAY, delay_s=0.01))
    assert chaos_call(c, "x", lambda: "ran") == "ran"


def test_probability_zero_never_fires() -> None:
    c = ChaosController(seed=0)
    c.add(Fault(target="x", kind=FaultKind.EXCEPTION, probability=0.0))
    for _ in range(10):
        assert chaos_call(c, "x", lambda: "ok") == "ok"


def test_remove_fault() -> None:
    c = ChaosController()
    c.add(Fault(target="x", kind=FaultKind.EMPTY))
    assert c.remove("x") is True
    assert c.remove("x") is False


def test_clear_faults() -> None:
    c = ChaosController()
    c.add(Fault(target="x", kind=FaultKind.EMPTY))
    c.add(Fault(target="y", kind=FaultKind.EMPTY))
    c.clear()
    assert chaos_call(c, "x", lambda: "ok") == "ok"


def test_scenario_apply_and_remove() -> None:
    c = ChaosController(seed=0)
    s = ChaosScenario(name="x", faults=[Fault(target="t1", kind=FaultKind.EXCEPTION)])
    s.apply(c)
    with pytest.raises(RuntimeError):
        chaos_call(c, "t1", lambda: "ok")
    s.remove(c)
    assert chaos_call(c, "t1", lambda: "ok") == "ok"


def test_common_scenarios_present() -> None:
    names = {s.name for s in common_scenarios()}
    assert "mic_dies" in names
    assert "llm_500" in names


def test_seeded_controller_is_deterministic() -> None:
    c1 = ChaosController(seed=42)
    c1.add(Fault(target="x", kind=FaultKind.EXCEPTION, probability=0.5))
    c2 = ChaosController(seed=42)
    c2.add(Fault(target="x", kind=FaultKind.EXCEPTION, probability=0.5))

    def raises_or_returns(c: ChaosController) -> bool:
        try:
            chaos_call(c, "x", lambda: "ok")
            return False
        except RuntimeError:
            return True

    seq1 = [raises_or_returns(c1) for _ in range(20)]
    seq2 = [raises_or_returns(c2) for _ in range(20)]
    assert seq1 == seq2
