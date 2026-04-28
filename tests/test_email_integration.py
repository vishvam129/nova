"""Tests for nova.integrations.email."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from nova.integrations.email import (
    EmailBody,
    EmailHeader,
    GenericImapSmtp,
    GmailOAuth,
    OutlookGraph,
    _parse_body,
    _parse_header,
)


def test_email_header_parsing() -> None:
    text = "From: alice@example.com\r\nSubject: Hi there\r\nDate: Mon, 28 Apr 2026 10:00:00\r\n"
    h = _parse_header("123", text)
    assert h.uid == "123"
    assert h.sender == "alice@example.com"
    assert h.subject == "Hi there"


def test_email_body_parsing_simple_text() -> None:
    raw = b"From: a@x.com\r\nSubject: T\r\n\r\nHello world body"
    body = _parse_body("uid", raw)
    assert "Hello world body" in body.body
    assert body.subject == "T"


def test_email_body_parsing_multipart() -> None:
    raw = (
        b"From: a@x.com\r\n"
        b"Subject: Multi\r\n"
        b'Content-Type: multipart/alternative; boundary="BOUNDARY"\r\n'
        b"\r\n"
        b"--BOUNDARY\r\n"
        b"Content-Type: text/plain\r\n"
        b"\r\n"
        b"plain part\r\n"
        b"--BOUNDARY--\r\n"
    )
    body = _parse_body("u", raw)
    assert "plain part" in body.body


def test_send_with_smtp_failure() -> None:
    client = GenericImapSmtp(host_imap="i", host_smtp="s", user="u@x.com", password="p")
    with patch("nova.integrations.email.smtplib.SMTP_SSL", side_effect=OSError):
        assert client.send("to@x.com", "hi", "body") is False


def test_send_with_smtp_success() -> None:
    client = GenericImapSmtp(host_imap="i", host_smtp="s", user="u@x.com", password="p")
    smtp = MagicMock()
    smtp.__enter__ = MagicMock(return_value=smtp)
    smtp.__exit__ = MagicMock(return_value=False)
    with patch("nova.integrations.email.smtplib.SMTP_SSL", return_value=smtp):
        assert client.send("to@x.com", "hi", "body") is True
    smtp.login.assert_called_once_with("u@x.com", "p")
    smtp.send_message.assert_called_once()


def test_email_header_dataclass() -> None:
    h = EmailHeader(uid="1", sender="a@x", subject="s", date="d")
    assert h.flagged is False


def test_email_body_dataclass() -> None:
    b = EmailBody(uid="1", subject="s", sender="a@x", body="hello")
    assert b.body == "hello"


def test_gmail_oauth_default_endpoint() -> None:
    g = GmailOAuth(access_token="t", sender="a@x.com")
    assert "gmail.googleapis.com" in g.endpoint


def test_outlook_default_endpoint() -> None:
    o = OutlookGraph(access_token="t", sender="a@x.com")
    assert "graph.microsoft.com" in o.endpoint
