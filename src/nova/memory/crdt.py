"""CRDT-based memory sync across devices.

Thin abstraction over a Y.js-style conflict-free replicated document.
The default ``DictCrdt`` is a tiny LWW-map useful for tests and
small-footprint deployments. A lazy ``YPyDoc`` adapter wires in the
real thing (``y-py``) when installed.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class Crdt(Protocol):
    def set(self, key: str, value: Any, lamport: int | None = None) -> None: ...

    def get(self, key: str) -> Any: ...

    def delete(self, key: str, lamport: int | None = None) -> None: ...

    def keys(self) -> Iterable[str]: ...

    def encode(self) -> bytes: ...

    def apply(self, update: bytes) -> None: ...


@dataclass
class DictCrdt:
    """Last-writer-wins map with Lamport clock for deterministic merge."""

    _data: dict[str, tuple[int, Any]] = field(default_factory=dict)
    _clock: int = 0

    def _tick(self) -> int:
        self._clock += 1
        return self._clock

    def set(self, key: str, value: Any, lamport: int | None = None) -> None:
        ts = lamport if lamport is not None else self._tick()
        current = self._data.get(key)
        if current is None or current[0] <= ts:
            self._data[key] = (ts, value)
            if lamport is not None:
                self._clock = max(self._clock, lamport)

    def get(self, key: str) -> Any:
        entry = self._data.get(key)
        return None if entry is None else entry[1]

    def delete(self, key: str, lamport: int | None = None) -> None:
        ts = lamport if lamport is not None else self._tick()
        current = self._data.get(key)
        if current is None or current[0] <= ts:
            self._data[key] = (ts, None)

    def keys(self) -> Iterable[str]:
        return tuple(k for k, (_, v) in self._data.items() if v is not None)

    def encode(self) -> bytes:
        import json

        payload = {k: [ts, v] for k, (ts, v) in self._data.items()}
        return json.dumps({"clock": self._clock, "data": payload}).encode()

    def apply(self, update: bytes) -> None:
        import json

        doc = json.loads(update)
        for k, (ts, v) in doc["data"].items():
            current = self._data.get(k)
            if current is None or current[0] < ts:
                self._data[k] = (ts, v)
            elif current[0] == ts and v is None:
                self._data[k] = (ts, None)
        self._clock = max(self._clock, int(doc.get("clock", 0)))


class YPyDoc:
    """Lazy adapter backed by ``y-py``."""

    def __init__(self, name: str = "nova") -> None:
        self.name = name
        self._doc: Any = None

    def _ensure(self) -> Any:
        if self._doc is None:
            import y_py

            self._doc = y_py.YDoc()
        return self._doc

    def _map(self) -> Any:
        return self._ensure().get_map(self.name)

    def set(self, key: str, value: Any, lamport: int | None = None) -> None:
        doc = self._ensure()
        with doc.begin_transaction() as txn:
            self._map().set(txn, key, value)

    def get(self, key: str) -> Any:
        return self._map().get(key)

    def delete(self, key: str, lamport: int | None = None) -> None:
        doc = self._ensure()
        with doc.begin_transaction() as txn:
            self._map().delete(txn, key)

    def keys(self) -> Iterable[str]:
        return tuple(self._map().keys())

    def encode(self) -> bytes:
        import y_py

        return bytes(y_py.encode_state_as_update(self._ensure()))

    def apply(self, update: bytes) -> None:
        import y_py

        y_py.apply_update(self._ensure(), update)


def merge(local: Crdt, remote: Crdt) -> None:
    """Bidirectional merge of two replicas."""
    local_state = local.encode()
    remote_state = remote.encode()
    local.apply(remote_state)
    remote.apply(local_state)


__all__ = ["Crdt", "DictCrdt", "YPyDoc", "merge"]
