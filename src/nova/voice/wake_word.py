"""Wake word detection abstraction.

Two real backends are supported: ``openwakeword`` (default, free) and
``porcupine`` (Picovoice). Backends are imported lazily so their native
dependencies are only required when actually selected.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class WakeEvent:
    """A single wake word activation."""

    phrase: str
    score: float
    timestamp: float


Listener = Callable[[WakeEvent], None]


@runtime_checkable
class WakeWordEngine(Protocol):
    """Backend interface. Implementations are cheap to construct and may
    load models lazily on first ``feed``."""

    sample_rate: int

    def feed(self, pcm16: bytes) -> WakeEvent | None:
        """Process a PCM-16 mono frame; return an event if triggered."""

    def close(self) -> None: ...


class _BackendRegistry:
    def __init__(self) -> None:
        self._builders: dict[str, Callable[..., WakeWordEngine]] = {}

    def register(self, name: str, builder: Callable[..., WakeWordEngine]) -> None:
        self._builders[name] = builder

    def build(self, name: str, **kwargs: object) -> WakeWordEngine:
        if name not in self._builders:
            raise ValueError(f"unknown wake-word backend: {name!r}")
        return self._builders[name](**kwargs)

    def names(self) -> Iterable[str]:
        return tuple(self._builders)


_registry = _BackendRegistry()


def register_backend(name: str, builder: Callable[..., WakeWordEngine]) -> None:
    """Register a wake-word backend under ``name``."""
    _registry.register(name, builder)


def available_backends() -> tuple[str, ...]:
    return tuple(_registry.names())


def create_engine(backend: str = "openwakeword", **kwargs: object) -> WakeWordEngine:
    """Instantiate a wake-word engine by backend name."""
    return _registry.build(backend, **kwargs)


# --- Built-in backends ------------------------------------------------------


def _build_openwakeword(
    phrase: str = "hey_nova",
    threshold: float = 0.5,
    sample_rate: int = 16000,
) -> WakeWordEngine:
    from nova.voice._backends import OpenWakeWordEngine

    return OpenWakeWordEngine(phrase=phrase, threshold=threshold, sample_rate=sample_rate)


def _build_porcupine(
    phrase: str = "jarvis",
    access_key: str | None = None,
    sample_rate: int = 16000,
) -> WakeWordEngine:
    from nova.voice._backends import PorcupineEngine

    return PorcupineEngine(phrase=phrase, access_key=access_key, sample_rate=sample_rate)


_registry.register("openwakeword", _build_openwakeword)
_registry.register("porcupine", _build_porcupine)
