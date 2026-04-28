"""Tests for nova.packaging."""

from __future__ import annotations

from pathlib import Path

import pytest

from nova.packaging import Backend, BuildSpec, build_argv, nuitka_argv, pyinstaller_argv


def test_pyinstaller_basic() -> None:
    spec = BuildSpec(entry=Path("main.py"), name="nova")
    argv = pyinstaller_argv(spec)
    assert argv[0] == "pyinstaller"
    assert "main.py" in argv
    assert "--onefile" in argv
    assert "--name" in argv


def test_pyinstaller_no_onefile() -> None:
    spec = BuildSpec(entry=Path("m.py"), one_file=False)
    argv = pyinstaller_argv(spec)
    assert "--onefile" not in argv


def test_pyinstaller_icon() -> None:
    spec = BuildSpec(entry=Path("m.py"), icon=Path("icon.ico"))
    argv = pyinstaller_argv(spec)
    assert "--icon" in argv
    assert any("icon.ico" in a for a in argv)


def test_pyinstaller_add_data() -> None:
    spec = BuildSpec(entry=Path("m.py"), add_data=[(Path("models"), "models")])
    argv = pyinstaller_argv(spec)
    assert "--add-data" in argv
    assert any("models" in a for a in argv)


def test_pyinstaller_hidden_imports() -> None:
    spec = BuildSpec(entry=Path("m.py"), hidden_imports=["nova.brain"])
    argv = pyinstaller_argv(spec)
    assert "--hidden-import" in argv
    assert "nova.brain" in argv


def test_nuitka_basic() -> None:
    spec = BuildSpec(entry=Path("m.py"), backend=Backend.NUITKA)
    argv = nuitka_argv(spec)
    assert "-m" in argv
    assert "nuitka" in argv
    assert "--standalone" in argv
    assert "--onefile" in argv


def test_nuitka_no_onefile() -> None:
    spec = BuildSpec(entry=Path("m.py"), backend=Backend.NUITKA, one_file=False)
    assert "--onefile" not in nuitka_argv(spec)


def test_build_argv_dispatch() -> None:
    spec_a = BuildSpec(entry=Path("m.py"), backend=Backend.PYINSTALLER)
    spec_b = BuildSpec(entry=Path("m.py"), backend=Backend.NUITKA)
    assert build_argv(spec_a)[0] == "pyinstaller"
    assert "nuitka" in build_argv(spec_b)


def test_extra_args_passthrough() -> None:
    spec = BuildSpec(entry=Path("m.py"), extra_args=["--debug"])
    argv = pyinstaller_argv(spec)
    assert "--debug" in argv


def test_output_name_platform() -> None:
    spec = BuildSpec(entry=Path("m.py"), name="nova")
    name = spec.output_name()
    assert name in {"nova", "nova.exe"}


def test_unknown_backend_raises() -> None:
    spec = BuildSpec(entry=Path("m.py"))
    object.__setattr__(spec, "backend", "bogus")  # bypass enum validation
    with pytest.raises(ValueError):
        build_argv(spec)
