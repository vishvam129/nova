"""Email integration: IMAP/SMTP + Gmail OAuth + Outlook Graph contracts.

Three backends share the ``EmailClient`` Protocol so the brain doesn't
know or care which is in use:
    - GenericImapSmtp  — username/password over IMAPS + SMTPS
    - GmailOAuth       — refresh-token-based send via the Gmail REST API
    - OutlookGraph     — refresh-token-based send via Microsoft Graph

This module ships the Generic backend (stdlib-only) and stub HTTP-based
classes for Gmail/Outlook so the auth + request shapes are testable.
"""

from __future__ import annotations

import imaplib
import smtplib
import ssl
from collections.abc import Iterable
from dataclasses import dataclass, field
from email.message import EmailMessage
from typing import Protocol


@dataclass(frozen=True, slots=True)
class EmailHeader:
    uid: str
    sender: str
    subject: str
    date: str
    flagged: bool = False


@dataclass(frozen=True, slots=True)
class EmailBody:
    uid: str
    subject: str
    sender: str
    body: str
    date: str = ""


class EmailClient(Protocol):
    def list_inbox(self, limit: int = 20) -> Iterable[EmailHeader]: ...
    def fetch(self, uid: str) -> EmailBody: ...
    def send(self, to: str, subject: str, body: str) -> bool: ...


# --------- Generic IMAP/SMTP ---------


@dataclass
class GenericImapSmtp:
    """Username/password IMAPS + SMTPS client."""

    host_imap: str
    host_smtp: str
    user: str
    password: str
    port_imap: int = 993
    port_smtp: int = 465

    def list_inbox(self, limit: int = 20) -> list[EmailHeader]:
        ctx = ssl.create_default_context()
        out: list[EmailHeader] = []
        with imaplib.IMAP4_SSL(self.host_imap, self.port_imap, ssl_context=ctx) as imap:
            imap.login(self.user, self.password)
            imap.select("INBOX")
            typ, data = imap.search(None, "ALL")
            if typ != "OK":
                return []
            ids = data[0].split()[-limit:]
            for uid in ids:
                typ, hdr = imap.fetch(uid, "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)])")
                if typ != "OK" or not hdr or not hdr[0]:
                    continue
                raw = hdr[0][1]
                if isinstance(raw, bytes):
                    text = raw.decode(errors="replace")
                    out.append(_parse_header(uid.decode(), text))
        return out

    def fetch(self, uid: str) -> EmailBody:
        ctx = ssl.create_default_context()
        with imaplib.IMAP4_SSL(self.host_imap, self.port_imap, ssl_context=ctx) as imap:
            imap.login(self.user, self.password)
            imap.select("INBOX")
            typ, data = imap.fetch(uid.encode(), "(RFC822)")
            if typ != "OK" or not data or not data[0]:
                return EmailBody(uid=uid, subject="", sender="", body="")
            raw = data[0][1]
        if not isinstance(raw, bytes):
            return EmailBody(uid=uid, subject="", sender="", body="")
        return _parse_body(uid, raw)

    def send(self, to: str, subject: str, body: str) -> bool:
        msg = EmailMessage()
        msg["From"] = self.user
        msg["To"] = to
        msg["Subject"] = subject
        msg.set_content(body)
        ctx = ssl.create_default_context()
        try:
            with smtplib.SMTP_SSL(self.host_smtp, self.port_smtp, context=ctx) as smtp:
                smtp.login(self.user, self.password)
                smtp.send_message(msg)
        except (smtplib.SMTPException, OSError):
            return False
        return True


def _parse_header(uid: str, text: str) -> EmailHeader:
    headers: dict[str, str] = {}
    for line in text.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            headers[k.strip().lower()] = v.strip()
    return EmailHeader(
        uid=uid,
        sender=headers.get("from", ""),
        subject=headers.get("subject", ""),
        date=headers.get("date", ""),
    )


def _parse_body(uid: str, raw: bytes) -> EmailBody:
    import email

    msg = email.message_from_bytes(raw)
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                payload = part.get_payload(decode=True)
                if isinstance(payload, bytes):
                    body = payload.decode(errors="replace")
                    break
    else:
        payload = msg.get_payload(decode=True)
        if isinstance(payload, bytes):
            body = payload.decode(errors="replace")
    return EmailBody(
        uid=uid,
        subject=msg.get("Subject", ""),
        sender=msg.get("From", ""),
        body=body,
        date=msg.get("Date", ""),
    )


# --------- Gmail / Outlook stubs ---------


@dataclass
class OAuthEmailBackend:
    """Common shape for Gmail / Outlook Graph senders.

    The full OAuth refresh dance is delegated to the caller (e.g. nova.tools.mcp);
    here we just track the access token + endpoint URL.
    """

    access_token: str
    sender: str
    endpoint: str = ""
    extra_headers: dict[str, str] = field(default_factory=dict)


@dataclass
class GmailOAuth(OAuthEmailBackend):
    endpoint: str = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"


@dataclass
class OutlookGraph(OAuthEmailBackend):
    endpoint: str = "https://graph.microsoft.com/v1.0/me/sendMail"


__all__ = [
    "EmailBody",
    "EmailClient",
    "EmailHeader",
    "GenericImapSmtp",
    "GmailOAuth",
    "OAuthEmailBackend",
    "OutlookGraph",
]
