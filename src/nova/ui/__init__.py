"""Desktop UI: tray app, overlay, settings."""

from nova.ui import tray as _tray

MenuItem = _tray.MenuItem
TrayController = _tray.TrayController
TrayStatus = _tray.TrayStatus

__all__ = ["MenuItem", "TrayController", "TrayStatus"]
