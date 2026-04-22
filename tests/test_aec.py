"""Tests for AEC abstraction."""

from __future__ import annotations

import pytest

from nova.voice.aec import (
    EchoCanceller,
    NullEchoCanceller,
    apply_aec,
    available_aecs,
    create_aec,
)


def test_available_aecs() -> None:
    assert {"null", "webrtc"}.issubset(set(available_aecs()))


def test_unknown_backend_raises() -> None:
    with pytest.raises(ValueError):
        create_aec("nope")


def test_null_is_passthrough() -> None:
    aec = create_aec("null")
    assert isinstance(aec, EchoCanceller)
    assert aec.process(b"near", b"far") == b"near"


def test_apply_aec_pairs_streams() -> None:
    aec = NullEchoCanceller()
    out = list(apply_aec(aec, [b"a", b"b"], [b"x", b"y"]))
    assert out == [b"a", b"b"]


def test_apply_aec_pads_far_with_silence_when_short() -> None:
    aec = NullEchoCanceller()
    out = list(apply_aec(aec, [b"ab", b"cd"], [b"xy"]))
    assert out == [b"ab", b"cd"]


def test_null_close_is_idempotent() -> None:
    aec = NullEchoCanceller()
    aec.close()
    aec.close()
