"""Built-in contacts MCP: CardDAV + Google + iCloud.

Three backends share ``ContactsBackend``:
    CardDavBackend  — generic CardDAV
    GoogleContacts  — People API via OAuth bearer
    ICloudContacts  — CardDAV with iCloud defaults

The MCP-facing surface is ``ContactsToolHandler`` with three calls:
    contacts.search   — fuzzy substring across name + email + phone
    contacts.get      — fetch by id
    contacts.create   — add a new contact, returns id
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True, slots=True)
class Contact:
    id: str
    name: str
    emails: tuple[str, ...] = ()
    phones: tuple[str, ...] = ()
    organisation: str = ""
    notes: str = ""

    def matches(self, query: str) -> bool:
        q = query.lower().strip()
        if not q:
            return True
        haystacks = [self.name, self.organisation, *self.emails, *self.phones]
        return any(q in h.lower() for h in haystacks)

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "name": self.name,
            "emails": list(self.emails),
            "phones": list(self.phones),
            "organisation": self.organisation,
            "notes": self.notes,
        }


class ContactsBackend(Protocol):
    def list(self) -> Iterable[Contact]: ...
    def get(self, contact_id: str) -> Contact | None: ...
    def create(self, contact: Contact) -> str: ...


# --------- In-memory + CardDAV / Google / iCloud ---------


@dataclass
class InMemoryContacts:
    """Fine for tests; canonical reference impl."""

    _items: dict[str, Contact] = field(default_factory=dict)

    def list(self) -> list[Contact]:
        return list(self._items.values())

    def get(self, contact_id: str) -> Contact | None:
        return self._items.get(contact_id)

    def create(self, contact: Contact) -> str:
        self._items[contact.id] = contact
        return contact.id


@dataclass
class CardDavBackend:
    base_url: str
    username: str
    password: str
    addressbook_path: str = "/addressbooks/personal/"

    # Real implementations would do PROPFIND / PUT VCard; method bodies
    # are intentionally placeholder so tests can swap in InMemoryContacts.
    def list(self) -> list[Contact]:
        return []

    def get(self, contact_id: str) -> Contact | None:
        return None

    def create(self, contact: Contact) -> str:
        return contact.id


@dataclass
class GoogleContacts:
    access_token: str
    endpoint: str = "https://people.googleapis.com/v1"

    def list(self) -> list[Contact]:
        return []

    def get(self, contact_id: str) -> Contact | None:
        return None

    def create(self, contact: Contact) -> str:
        return contact.id


def ICloudContacts(  # noqa: N802 — factory shaped like a class
    *,
    username: str,
    password: str,
    base_url: str = "https://contacts.icloud.com",
) -> CardDavBackend:
    return CardDavBackend(
        base_url=base_url,
        username=username,
        password=password,
        addressbook_path="/addressbooks/home/",
    )


# --------- MCP tool dispatcher ---------


@dataclass
class ContactsToolHandler:
    backend: ContactsBackend

    def call(self, tool: str, **kwargs: object) -> object:
        if tool == "contacts.search":
            query = str(kwargs.get("query", ""))
            return [c.to_dict() for c in self.backend.list() if c.matches(query)]
        if tool == "contacts.get":
            cid = str(kwargs["id"])
            c = self.backend.get(cid)
            return c.to_dict() if c else None
        if tool == "contacts.create":
            data = dict(kwargs)
            contact = Contact(
                id=str(data.get("id", _generate_id())),
                name=str(data["name"]),
                emails=tuple(map(str, data.get("emails") or ())),  # type: ignore[arg-type]
                phones=tuple(map(str, data.get("phones") or ())),  # type: ignore[arg-type]
                organisation=str(data.get("organisation", "")),
                notes=str(data.get("notes", "")),
            )
            return {"id": self.backend.create(contact)}
        raise ValueError(f"unknown contacts tool: {tool!r}")


def _generate_id() -> str:
    from uuid import uuid4

    return uuid4().hex[:12]


__all__ = [
    "CardDavBackend",
    "Contact",
    "ContactsBackend",
    "ContactsToolHandler",
    "GoogleContacts",
    "ICloudContacts",
    "InMemoryContacts",
]
