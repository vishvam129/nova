"""Android Assistant gesture binding (long-press home).

Captures the Assistant gesture intent so the user can replace Google
Assistant with Nova system-wide.  This module describes the manifest
changes and intent-filter contract that the Kotlin app applies; the
Python side just carries config and the launch event over WebSocket.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# AndroidManifest.xml fragment that registers Nova as the system Assistant.
ASSISTANT_INTENT_FILTER = """\
<activity
    android:name=".ui.AssistantActivity"
    android:exported="true"
    android:noHistory="true"
    android:theme="@android:style/Theme.Translucent.NoTitleBar">
    <intent-filter>
        <action android:name="android.intent.action.ASSIST" />
        <action android:name="android.intent.action.VOICE_COMMAND" />
        <category android:name="android.intent.category.DEFAULT" />
    </intent-filter>
</activity>
"""

# role declaration for Android 11+ (RoleManager.ROLE_ASSISTANT)
ASSISTANT_ROLE_REQUEST_CODE = 4242


@dataclass
class AssistantBindingConfig:
    """User-facing settings for the assistant gesture."""

    enabled: bool = True
    open_overlay: bool = True
    immediate_listen: bool = True

    def to_dict(self) -> dict[str, object]:
        return {
            "enabled": self.enabled,
            "open_overlay": self.open_overlay,
            "immediate_listen": self.immediate_listen,
        }

    @classmethod
    def from_dict(cls, d: dict[str, object]) -> AssistantBindingConfig:
        return cls(
            enabled=bool(d.get("enabled", True)),
            open_overlay=bool(d.get("open_overlay", True)),
            immediate_listen=bool(d.get("immediate_listen", True)),
        )


@dataclass
class AssistantLaunchEvent:
    """Sent over the WebSocket each time the Assistant gesture fires."""

    source: str = "long_press_home"
    package_in_focus: str = ""
    extras: dict[str, str] = field(default_factory=dict)

    MESSAGE_TYPE: str = field(default="assistant_launch", init=False, repr=False)

    def to_dict(self) -> dict[str, object]:
        return {
            "type": self.MESSAGE_TYPE,
            "source": self.source,
            "package_in_focus": self.package_in_focus,
            "extras": dict(self.extras),
        }

    @classmethod
    def from_dict(cls, d: dict[str, object]) -> AssistantLaunchEvent:
        return cls(
            source=str(d.get("source", "long_press_home")),
            package_in_focus=str(d.get("package_in_focus", "")),
            extras=dict(d.get("extras") or {}),  # type: ignore[arg-type]
        )


def is_supported_source(source: str) -> bool:
    """Whether *source* is a recognised assistant-launch trigger."""
    return source in {
        "long_press_home",
        "power_button",
        "swipe_corners",
        "voice_match",
        "manual",
    }


__all__ = [
    "ASSISTANT_INTENT_FILTER",
    "ASSISTANT_ROLE_REQUEST_CODE",
    "AssistantBindingConfig",
    "AssistantLaunchEvent",
    "is_supported_source",
]
