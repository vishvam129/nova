"""Android packaging: signed APK + Play-ready AAB.

Produces gradle CLI argv for ``./gradlew :app:assembleRelease`` /
``:app:bundleRelease`` plus the apksigner / bundletool invocations to
sign and verify the artefacts.

Signing keys come from a ``KeystoreConfig``; the values flow into gradle
via env vars (NOVA_KEYSTORE_PATH etc.) rather than CLI flags so they
don't show up in ``ps``.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class ArtefactKind(StrEnum):
    APK = "apk"
    AAB = "aab"


@dataclass(frozen=True, slots=True)
class KeystoreConfig:
    keystore_path: Path
    key_alias: str
    keystore_password: str
    key_password: str

    def env(self) -> dict[str, str]:
        return {
            "NOVA_KEYSTORE_PATH": str(self.keystore_path),
            "NOVA_KEY_ALIAS": self.key_alias,
            "NOVA_KEYSTORE_PASSWORD": self.keystore_password,
            "NOVA_KEY_PASSWORD": self.key_password,
        }


def gradle_argv(kind: ArtefactKind, *, gradle: str = "./gradlew") -> list[str]:
    """Return the argv for the gradle build invocation."""
    if kind is ArtefactKind.APK:
        return [gradle, ":app:assembleRelease", "--no-daemon"]
    if kind is ArtefactKind.AAB:
        return [gradle, ":app:bundleRelease", "--no-daemon"]
    raise ValueError(f"unknown artefact: {kind!r}")


def apksigner_sign_argv(
    apk: Path, *, ks: KeystoreConfig, apksigner: str = "apksigner"
) -> list[str]:
    return [
        apksigner,
        "sign",
        "--ks",
        str(ks.keystore_path),
        "--ks-key-alias",
        ks.key_alias,
        "--ks-pass",
        f"pass:{ks.keystore_password}",
        "--key-pass",
        f"pass:{ks.key_password}",
        str(apk),
    ]


def apksigner_verify_argv(apk: Path, *, apksigner: str = "apksigner") -> list[str]:
    return [apksigner, "verify", "--verbose", str(apk)]


def bundletool_validate_argv(aab: Path, *, bundletool: str = "bundletool") -> list[str]:
    return [bundletool, "validate", "--bundle", str(aab)]


def expected_artefact_path(
    project_root: Path, kind: ArtefactKind, *, flavor: str = "release"
) -> Path:
    """Path where gradle drops the artefact (with the conventional layout)."""
    if kind is ArtefactKind.APK:
        return project_root / "app" / "build" / "outputs" / "apk" / flavor / f"app-{flavor}.apk"
    if kind is ArtefactKind.AAB:
        return project_root / "app" / "build" / "outputs" / "bundle" / flavor / f"app-{flavor}.aab"
    raise ValueError(f"unknown artefact: {kind!r}")


def merged_env(extra: dict[str, str] | None = None) -> dict[str, str]:
    env = dict(os.environ)
    if extra:
        env.update(extra)
    return env


__all__ = [
    "ArtefactKind",
    "KeystoreConfig",
    "apksigner_sign_argv",
    "apksigner_verify_argv",
    "bundletool_validate_argv",
    "expected_artefact_path",
    "gradle_argv",
    "merged_env",
]
