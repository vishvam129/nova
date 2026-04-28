"""Build one-file binaries via PyInstaller or Nuitka.

This module assembles the command-line arguments — actual build is the
caller's responsibility (CI / Makefile).  Centralising the spec here
keeps the per-platform flags consistent.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path


class Backend(StrEnum):
    PYINSTALLER = "pyinstaller"
    NUITKA = "nuitka"


@dataclass
class BuildSpec:
    """Inputs that drive the binary build."""

    entry: Path
    name: str = "nova"
    backend: Backend = Backend.PYINSTALLER
    one_file: bool = True
    icon: Path | None = None
    add_data: list[tuple[Path, str]] = field(default_factory=list)
    hidden_imports: list[str] = field(default_factory=list)
    extra_args: list[str] = field(default_factory=list)

    def output_name(self) -> str:
        if sys.platform == "win32":
            return f"{self.name}.exe"
        return self.name


def pyinstaller_argv(spec: BuildSpec) -> list[str]:
    args: list[str] = ["pyinstaller", str(spec.entry), "--name", spec.name]
    if spec.one_file:
        args.append("--onefile")
    args.extend(["--noconfirm", "--clean"])
    if spec.icon:
        args.extend(["--icon", str(spec.icon)])
    sep = ";" if sys.platform == "win32" else ":"
    for src, dest in spec.add_data:
        args.extend(["--add-data", f"{src}{sep}{dest}"])
    for mod in spec.hidden_imports:
        args.extend(["--hidden-import", mod])
    args.extend(spec.extra_args)
    return args


def nuitka_argv(spec: BuildSpec) -> list[str]:
    args: list[str] = [
        sys.executable,
        "-m",
        "nuitka",
        "--standalone",
        f"--output-filename={spec.output_name()}",
    ]
    if spec.one_file:
        args.append("--onefile")
    if spec.icon:
        if sys.platform == "win32":
            args.append(f"--windows-icon-from-ico={spec.icon}")
        else:
            args.append(f"--linux-icon={spec.icon}")
    for src, dest in spec.add_data:
        args.append(f"--include-data-files={src}={dest}")
    for mod in spec.hidden_imports:
        args.append(f"--include-module={mod}")
    args.extend(spec.extra_args)
    args.append(str(spec.entry))
    return args


def build_argv(spec: BuildSpec) -> list[str]:
    if spec.backend is Backend.PYINSTALLER:
        return pyinstaller_argv(spec)
    if spec.backend is Backend.NUITKA:
        return nuitka_argv(spec)
    raise ValueError(f"unknown backend: {spec.backend!r}")


__all__ = ["Backend", "BuildSpec", "build_argv", "nuitka_argv", "pyinstaller_argv"]
