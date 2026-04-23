"""Desktop UI: tray app, overlay, settings."""

from nova.ui import settings as _settings
from nova.ui import tray as _tray

MenuItem = _tray.MenuItem
TrayController = _tray.TrayController
TrayStatus = _tray.TrayStatus

SettingsSection = _settings.SettingsSection
SettingsService = _settings.SettingsService

__all__ = [
    "MenuItem",
    "SettingsSection",
    "SettingsService",
    "TrayController",
    "TrayStatus",
]
