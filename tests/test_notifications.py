"""Tests for nova.mobile.notifications."""

from __future__ import annotations

from datetime import datetime

from nova.mobile.notifications import (
    Notification,
    NotificationContext,
    NotificationFilter,
    decode_notification_frame,
)


def _n(package: str = "com.foo", title: str = "T", body: str = "B", **kw: object) -> Notification:
    return Notification(
        package=package,
        title=title,
        body=body,
        posted_at=datetime.now(),
        **kw,  # type: ignore[arg-type]
    )


def test_filter_accepts_normal_notification() -> None:
    f = NotificationFilter()
    assert f.accept(_n()) is True


def test_filter_drops_system_packages() -> None:
    f = NotificationFilter()
    assert f.accept(_n(package="com.android.systemui")) is False
    assert f.accept(_n(package="android")) is False


def test_filter_drops_ongoing() -> None:
    f = NotificationFilter()
    assert f.accept(_n(is_ongoing=True)) is False


def test_filter_dedupes_within_window() -> None:
    f = NotificationFilter()
    n = _n(title="hi", body="x")
    assert f.accept(n) is True
    assert f.accept(_n(title="hi", body="x")) is False


def test_filter_reset_clears_dedupe() -> None:
    f = NotificationFilter()
    f.accept(_n(title="x"))
    f.reset()
    assert f.accept(_n(title="x")) is True


def test_context_capacity() -> None:
    ctx = NotificationContext(capacity=2)
    ctx.add(_n(title="1"))
    ctx.add(_n(title="2"))
    ctx.add(_n(title="3"))
    titles = [n.title for n in ctx.recent()]
    assert titles == ["2", "3"]


def test_context_by_package() -> None:
    ctx = NotificationContext()
    ctx.add(_n(package="com.foo", title="A"))
    ctx.add(_n(package="com.bar", title="B"))
    foo = ctx.by_package("com.foo")
    assert len(foo) == 1
    assert foo[0].title == "A"


def test_context_to_brain_summary_empty() -> None:
    ctx = NotificationContext()
    assert "No recent" in ctx.to_brain_summary()


def test_context_to_brain_summary_has_titles() -> None:
    ctx = NotificationContext()
    ctx.add(_n(package="com.spotify", title="Now playing", body="Jazz"))
    summary = ctx.to_brain_summary()
    assert "com.spotify" in summary
    assert "Now playing" in summary
    assert "Jazz" in summary


def test_decode_frame() -> None:
    n = _n(title="x")
    n2 = decode_notification_frame(
        '{"package": "com.foo", "title": "x", "body": "B", '
        f'"posted_at": "{n.posted_at.isoformat()}"}}'
    )
    assert n2.title == "x"
    assert n2.package == "com.foo"
