"""Tests for PolicyEngine."""

from __future__ import annotations

from nova.safety.policy import PolicyEngine, Verdict


def test_default_is_unknown_when_no_rules() -> None:
    p = PolicyEngine()
    assert p.check("path", "/etc/passwd") is Verdict.UNKNOWN


def test_deny_beats_allow() -> None:
    p = PolicyEngine()
    p.allow("path", "/home/*")
    p.deny("path", "/home/me/.ssh/*")
    assert p.check("path", "/home/me/.ssh/id_rsa") is Verdict.DENY


def test_allow_wins_when_no_deny() -> None:
    p = PolicyEngine()
    p.allow("path", "/home/me/Documents/*")
    assert p.check("path", "/home/me/Documents/a.md") is Verdict.ALLOW
    assert p.check("path", "/etc/passwd") is Verdict.UNKNOWN


def test_domain_suffix_matching() -> None:
    p = PolicyEngine()
    p.allow("domain", "github.com")
    assert p.check("domain", "api.github.com") is Verdict.ALLOW
    assert p.check("domain", "https://api.github.com/repos") is Verdict.ALLOW
    assert p.check("domain", "evil.com") is Verdict.UNKNOWN


def test_command_head_matching() -> None:
    p = PolicyEngine()
    p.deny("command", "rm")
    p.allow("command", "ls")
    assert p.check("command", "rm -rf /") is Verdict.DENY
    assert p.check("command", "/usr/bin/rm foo") is Verdict.DENY
    assert p.check("command", "ls -la") is Verdict.ALLOW


def test_tool_exact_matching() -> None:
    p = PolicyEngine()
    p.deny("tool", "delete_account")
    p.allow("tool", "*")
    # deny beats wildcard allow
    assert p.check("tool", "delete_account") is Verdict.DENY
    assert p.check("tool", "send_email") is Verdict.ALLOW


def test_default_verdict_configurable() -> None:
    p = PolicyEngine(default=Verdict.DENY)
    assert p.check("path", "/") is Verdict.DENY
    p.allow("path", "/home/*")
    assert p.check("path", "/home/me") is Verdict.ALLOW


def test_path_glob_pattern() -> None:
    p = PolicyEngine()
    p.allow("path", "*.md")
    assert p.check("path", "notes.md") is Verdict.ALLOW
    assert p.check("path", "notes.txt") is Verdict.UNKNOWN
