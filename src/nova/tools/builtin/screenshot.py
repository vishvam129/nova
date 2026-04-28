"""Screenshot + OCR tool with optional region selection.

``capture()`` writes a PNG screenshot to the given path; ``ocr()`` runs
tesseract on it and returns the extracted text.  Both methods raise
``ScreenshotUnavailable`` if the required binary is not on PATH.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path


class ScreenshotUnavailable(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class Region:
    """Pixel-coordinate rectangle: top-left corner + size."""

    x: int
    y: int
    width: int
    height: int

    def as_geometry(self) -> str:
        # ImageMagick / scrot geometry string
        return f"{self.width}x{self.height}+{self.x}+{self.y}"


def capture(out_path: Path, region: Region | None = None) -> Path:
    """Take a screenshot to *out_path* (PNG). Returns the path."""
    cmd = _capture_cmd(out_path, region)
    if cmd is None:
        raise ScreenshotUnavailable(
            "no screenshot tool found (need scrot/grim/screencapture/snippingtool)"
        )
    result = subprocess.run(cmd, capture_output=True, timeout=10)
    if result.returncode != 0:
        raise ScreenshotUnavailable(result.stderr.decode(errors="replace"))
    return out_path


def _linux_cmd(out_path: Path, region: Region | None) -> list[str] | None:
    if shutil.which("grim"):
        cmd = ["grim"]
        if region:
            cmd += ["-g", region.as_geometry()]
        cmd.append(str(out_path))
        return cmd
    if shutil.which("scrot"):
        cmd = ["scrot"]
        if region:
            cmd += ["-a", region.as_geometry()]
        cmd.append(str(out_path))
        return cmd
    return None


def _macos_cmd(out_path: Path, region: Region | None) -> list[str] | None:
    if not shutil.which("screencapture"):
        return None
    cmd = ["screencapture", "-x"]
    if region:
        cmd += ["-R", f"{region.x},{region.y},{region.width},{region.height}"]
    cmd.append(str(out_path))
    return cmd


def _capture_cmd(out_path: Path, region: Region | None) -> list[str] | None:
    if sys.platform.startswith("linux"):
        return _linux_cmd(out_path, region)
    if sys.platform == "darwin":
        return _macos_cmd(out_path, region)
    if sys.platform == "win32" and shutil.which("powershell"):
        ps = (
            "Add-Type -AssemblyName System.Windows.Forms; "
            "$bmp=New-Object System.Drawing.Bitmap "
            "([System.Windows.Forms.Screen]::PrimaryScreen.Bounds.Width),"
            "([System.Windows.Forms.Screen]::PrimaryScreen.Bounds.Height); "
            "$g=[System.Drawing.Graphics]::FromImage($bmp); "
            "$g.CopyFromScreen(0,0,0,0,$bmp.Size); "
            f"$bmp.Save('{out_path}')"
        )
        return ["powershell", "-Command", ps]
    return None


def ocr(image_path: Path, lang: str = "eng") -> str:
    """Run tesseract on *image_path* and return the recognised text."""
    if not shutil.which("tesseract"):
        raise ScreenshotUnavailable("tesseract not on PATH")
    cmd = ["tesseract", str(image_path), "stdout", "-l", lang]
    result = subprocess.run(cmd, capture_output=True, timeout=30)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.decode(errors="replace"))
    return result.stdout.decode(errors="replace").strip()


def capture_and_ocr(region: Region | None = None, lang: str = "eng") -> str:
    """Convenience: screenshot to a temp file then OCR it."""
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        tmp = Path(f.name)
    try:
        capture(tmp, region)
        return ocr(tmp, lang)
    finally:
        tmp.unlink(missing_ok=True)


__all__ = ["Region", "ScreenshotUnavailable", "capture", "capture_and_ocr", "ocr"]
