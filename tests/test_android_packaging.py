"""Tests for nova.android_packaging."""

from __future__ import annotations

from pathlib import Path

import pytest

from nova.android_packaging import (
    ArtefactKind,
    KeystoreConfig,
    apksigner_sign_argv,
    apksigner_verify_argv,
    bundletool_validate_argv,
    expected_artefact_path,
    gradle_argv,
    merged_env,
)


def _ks(tmp_path: Path) -> KeystoreConfig:
    return KeystoreConfig(
        keystore_path=tmp_path / "ks.jks",
        key_alias="nova",
        keystore_password="kspw",
        key_password="kpw",
    )


def test_gradle_argv_apk() -> None:
    argv = gradle_argv(ArtefactKind.APK)
    assert ":app:assembleRelease" in argv


def test_gradle_argv_aab() -> None:
    argv = gradle_argv(ArtefactKind.AAB)
    assert ":app:bundleRelease" in argv


def test_keystore_env(tmp_path: Path) -> None:
    env = _ks(tmp_path).env()
    assert "NOVA_KEYSTORE_PATH" in env
    assert env["NOVA_KEY_ALIAS"] == "nova"


def test_apksigner_sign_argv(tmp_path: Path) -> None:
    apk = tmp_path / "app.apk"
    argv = apksigner_sign_argv(apk, ks=_ks(tmp_path))
    assert argv[0] == "apksigner"
    assert "sign" in argv
    assert "--ks" in argv
    assert "pass:kspw" in argv


def test_apksigner_verify_argv(tmp_path: Path) -> None:
    argv = apksigner_verify_argv(tmp_path / "app.apk")
    assert "verify" in argv
    assert "--verbose" in argv


def test_bundletool_validate_argv(tmp_path: Path) -> None:
    argv = bundletool_validate_argv(tmp_path / "app.aab")
    assert "validate" in argv
    assert "--bundle" in argv


def test_expected_apk_path(tmp_path: Path) -> None:
    p = expected_artefact_path(tmp_path, ArtefactKind.APK)
    assert p.name == "app-release.apk"
    assert "outputs/apk" in str(p)


def test_expected_aab_path(tmp_path: Path) -> None:
    p = expected_artefact_path(tmp_path, ArtefactKind.AAB)
    assert p.name == "app-release.aab"
    assert "outputs/bundle" in str(p)


def test_merged_env_includes_extra() -> None:
    env = merged_env({"FOO": "bar"})
    assert env["FOO"] == "bar"
    assert "PATH" in env  # inherited


def test_unknown_artefact_raises() -> None:
    with pytest.raises(ValueError):
        gradle_argv("bogus")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        expected_artefact_path(Path("/"), "bogus")  # type: ignore[arg-type]
