"""Smoke test: package imports."""

from __future__ import annotations


def test_import() -> None:
    import nova

    assert nova.__version__
