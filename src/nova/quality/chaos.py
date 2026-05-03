"""Chaos test harness: injects failures mid-request to verify graceful degradation.

Three primitives:
    Fault           — describes one injected failure
    ChaosController — toggles faults on/off
    chaos_call      — wraps a call so it raises / returns the configured fault

Designed for use in tests around the voice pipeline (mic, STT, LLM, TTS,
WS) so we can assert "the agent says 'something went wrong, try again'
instead of crashing".
"""

from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TypeVar


class FaultKind(StrEnum):
    EXCEPTION = "exception"
    EMPTY = "empty"  # returns "" / b"" / None / 0
    DELAY = "delay"  # returns a sentinel after sleeping
    TIMEOUT = "timeout"  # raises TimeoutError


@dataclass(frozen=True, slots=True)
class Fault:
    target: str  # e.g. 'mic.read', 'stt.transcribe', 'llm.generate'
    kind: FaultKind
    probability: float = 1.0
    exception: type[BaseException] = RuntimeError
    delay_s: float = 0.0
    message: str = "chaos"

    def fires(self, rng: random.Random) -> bool:
        return rng.random() < self.probability


@dataclass
class ChaosController:
    """Holds enabled faults; ``chaos_call`` consults this on every wrap."""

    faults: dict[str, Fault] = field(default_factory=dict)
    seed: int | None = None
    _rng: random.Random = field(init=False)

    def __post_init__(self) -> None:
        self._rng = random.Random(self.seed)

    def add(self, fault: Fault) -> None:
        self.faults[fault.target] = fault

    def remove(self, target: str) -> bool:
        return self.faults.pop(target, None) is not None

    def clear(self) -> None:
        self.faults.clear()

    def fault_for(self, target: str) -> Fault | None:
        fault = self.faults.get(target)
        if fault is None:
            return None
        if not fault.fires(self._rng):
            return None
        return fault


T = TypeVar("T")


def chaos_call(
    controller: ChaosController,
    target: str,
    func: Callable[[], T],
    *,
    empty_value: T | None = None,
) -> T:
    """Run *func* unless *controller* injects a fault for *target*."""
    fault = controller.fault_for(target)
    if fault is None:
        return func()
    if fault.kind is FaultKind.EXCEPTION:
        raise fault.exception(fault.message)
    if fault.kind is FaultKind.TIMEOUT:
        raise TimeoutError(fault.message)
    if fault.kind is FaultKind.DELAY:
        import time as _t

        _t.sleep(fault.delay_s)
        return func()
    # EMPTY
    return empty_value  # type: ignore[return-value]


@dataclass
class ChaosScenario:
    """Convenience: name + list of faults, applied/removed in batches."""

    name: str
    faults: list[Fault] = field(default_factory=list)

    def apply(self, controller: ChaosController) -> None:
        for f in self.faults:
            controller.add(f)

    def remove(self, controller: ChaosController) -> None:
        for f in self.faults:
            controller.remove(f.target)


def common_scenarios() -> list[ChaosScenario]:
    return [
        ChaosScenario(
            name="mic_dies",
            faults=[Fault(target="mic.read", kind=FaultKind.EMPTY)],
        ),
        ChaosScenario(
            name="stt_timeout",
            faults=[Fault(target="stt.transcribe", kind=FaultKind.TIMEOUT)],
        ),
        ChaosScenario(
            name="llm_500",
            faults=[
                Fault(
                    target="llm.generate",
                    kind=FaultKind.EXCEPTION,
                    exception=RuntimeError,
                    message="LLM 500",
                )
            ],
        ),
        ChaosScenario(
            name="flaky_network",
            faults=[
                Fault(target="ws.send", kind=FaultKind.EXCEPTION, probability=0.3),
                Fault(target="http.get", kind=FaultKind.TIMEOUT, probability=0.2),
            ],
        ),
    ]


__all__ = [
    "ChaosController",
    "ChaosScenario",
    "Fault",
    "FaultKind",
    "chaos_call",
    "common_scenarios",
]
