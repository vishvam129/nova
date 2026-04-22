"""Tests for per-tool approval."""

from __future__ import annotations

from pathlib import Path

from nova.tools.approval import ApprovalManager, ConfirmRequest, Policy, in_memory_confirmer


def _nap(_t: float) -> None:
    return None


def test_default_is_quiet_confirm() -> None:
    m = ApprovalManager()
    assert m.get("anything") is Policy.QUIET_CONFIRM


def test_auto_never_prompts() -> None:
    m = ApprovalManager()
    m.set("read_file", Policy.AUTO)

    def boom(_r: ConfirmRequest) -> bool:
        raise AssertionError("should not be called")

    assert m.authorize("read_file", {}, boom, sleep=_nap) is True


def test_denied_always_false() -> None:
    m = ApprovalManager()
    m.set("rm", Policy.DENIED)
    calls: list[ConfirmRequest] = []
    assert m.authorize("rm", {}, lambda r: calls.append(r) or True, sleep=_nap) is False
    assert calls == []


def test_quiet_confirm_runs_unless_cancelled() -> None:
    m = ApprovalManager(quiet_timeout_ms=1)
    m.set("send_email", Policy.QUIET_CONFIRM)
    # Cancel means confirmer returns True => action skipped.
    cancel_cf = in_memory_confirmer({"send_email": True})
    assert m.authorize("send_email", {}, cancel_cf, sleep=_nap) is False
    # No cancel (confirmer returns False) => action runs.
    keep_cf = in_memory_confirmer({"send_email": False})
    assert m.authorize("send_email", {}, keep_cf, sleep=_nap) is True


def test_require_confirm_blocks_without_approval() -> None:
    m = ApprovalManager()
    m.set("transfer_money", Policy.REQUIRE_CONFIRM)
    assert m.authorize("transfer_money", {}, lambda _r: False, sleep=_nap) is False
    assert m.authorize("transfer_money", {}, lambda _r: True, sleep=_nap) is True


def test_save_and_load_roundtrip(tmp_path: Path) -> None:
    m = ApprovalManager(default=Policy.REQUIRE_CONFIRM, quiet_timeout_ms=500)
    m.set("read_file", Policy.AUTO)
    m.set("rm", Policy.DENIED)
    path = tmp_path / "approvals.json"
    m.save(path)
    fresh = ApprovalManager()
    fresh.load(path)
    assert fresh.default is Policy.REQUIRE_CONFIRM
    assert fresh.quiet_timeout_ms == 500
    assert fresh.get("read_file") is Policy.AUTO
    assert fresh.get("rm") is Policy.DENIED


def test_confirm_request_carries_arguments() -> None:
    m = ApprovalManager()
    m.set("run_shell", Policy.REQUIRE_CONFIRM)
    captured: list[ConfirmRequest] = []

    def cf(req: ConfirmRequest) -> bool:
        captured.append(req)
        return True

    m.authorize("run_shell", {"cmd": "ls"}, cf, sleep=_nap)
    assert captured[0].arguments == {"cmd": "ls"}
    assert captured[0].policy is Policy.REQUIRE_CONFIRM
