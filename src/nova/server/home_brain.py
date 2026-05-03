"""Always-on home-brain mode: keep the laptop listening with lid closed.

On Linux this means inhibiting systemd-logind's lid-switch handler; on
macOS it's pmset; on Windows it's powercfg.  ``HomeBrainMode`` exposes
``enable()`` / ``disable()`` and tracks the current state so the tray
toggle can reflect it.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from dataclasses import dataclass, field


@dataclass
class HomeBrainStatus:
    enabled: bool
    backend: str
    detail: str = ""


@dataclass
class HomeBrainMode:
    """Toggles 'don't sleep when lid closes' for the current OS."""

    _status: HomeBrainStatus = field(
        default_factory=lambda: HomeBrainStatus(enabled=False, backend="unknown")
    )
    _inhibitor: subprocess.Popen[bytes] | None = None

    @property
    def status(self) -> HomeBrainStatus:
        return self._status

    def enable(self) -> bool:
        if self._status.enabled:
            return True
        if sys.platform.startswith("linux"):
            return self._enable_linux()
        if sys.platform == "darwin":
            return self._enable_macos()
        if sys.platform == "win32":
            return self._enable_windows()
        self._status = HomeBrainStatus(False, "unsupported")
        return False

    def disable(self) -> bool:
        if not self._status.enabled:
            return True
        if self._inhibitor is not None:
            with _suppress(OSError):
                self._inhibitor.terminate()
                self._inhibitor.wait(timeout=2)
            self._inhibitor = None
        if sys.platform == "darwin":
            _run(["pmset", "-a", "lidwake", "1"])
        if sys.platform == "win32":
            _run(
                [
                    "powercfg",
                    "/setacvalueindex",
                    "SCHEME_CURRENT",
                    "SUB_BUTTONS",
                    "LIDACTION",
                    "1",
                ]
            )
        self._status = HomeBrainStatus(False, self._status.backend, "user disabled")
        return True

    # ----- Linux -----

    def _enable_linux(self) -> bool:
        if not shutil.which("systemd-inhibit"):
            self._status = HomeBrainStatus(False, "linux", "systemd-inhibit missing")
            return False
        try:
            self._inhibitor = subprocess.Popen(
                [
                    "systemd-inhibit",
                    "--what=handle-lid-switch:sleep:idle",
                    "--who=nova",
                    "--why=home-brain mode",
                    "sleep",
                    "infinity",
                ]
            )
        except OSError as exc:
            self._status = HomeBrainStatus(False, "linux", str(exc))
            return False
        self._status = HomeBrainStatus(True, "linux", f"pid={self._inhibitor.pid}")
        return True

    # ----- macOS -----

    def _enable_macos(self) -> bool:
        ok = _run(["pmset", "-a", "lidwake", "0"])
        self._status = HomeBrainStatus(ok, "macos", "pmset lidwake=0" if ok else "pmset failed")
        return ok

    # ----- Windows -----

    def _enable_windows(self) -> bool:
        ok = _run(
            [
                "powercfg",
                "/setacvalueindex",
                "SCHEME_CURRENT",
                "SUB_BUTTONS",
                "LIDACTION",
                "0",
            ]
        )
        self._status = HomeBrainStatus(ok, "windows", "powercfg LIDACTION=0")
        return ok


def _run(cmd: list[str]) -> bool:
    if not shutil.which(cmd[0]):
        return False
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return False
    return r.returncode == 0


class _suppress:
    """tiny context manager replacement to avoid contextlib import."""

    def __init__(self, *exc_types: type[BaseException]) -> None:
        self.exc_types = exc_types

    def __enter__(self) -> None:
        return None

    def __exit__(self, exc_type, exc, tb) -> bool:  # type: ignore[no-untyped-def]
        return exc_type is not None and issubclass(exc_type, self.exc_types)


__all__ = ["HomeBrainMode", "HomeBrainStatus"]
