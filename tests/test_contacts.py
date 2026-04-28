"""Tests for nova.integrations.contacts."""

from __future__ import annotations

import pytest

from nova.integrations.contacts import (
    CardDavBackend,
    Contact,
    ContactsToolHandler,
    GoogleContacts,
    ICloudContacts,
    InMemoryContacts,
)


def _alice() -> Contact:
    return Contact(
        id="c1",
        name="Alice Bob",
        emails=("alice@example.com",),
        phones=("+15555550100",),
        organisation="Acme",
    )


def test_contact_matches_name() -> None:
    c = _alice()
    assert c.matches("alice") is True
    assert c.matches("BOB") is True


def test_contact_matches_email() -> None:
    assert _alice().matches("example.com") is True


def test_contact_matches_org() -> None:
    assert _alice().matches("acme") is True


def test_contact_no_match() -> None:
    assert _alice().matches("zzzzz") is False


def test_contact_empty_query_matches_everyone() -> None:
    assert _alice().matches("") is True


def test_in_memory_create_and_get() -> None:
    backend = InMemoryContacts()
    backend.create(_alice())
    out = backend.get("c1")
    assert out is not None
    assert out.name == "Alice Bob"


def test_in_memory_list() -> None:
    backend = InMemoryContacts()
    backend.create(_alice())
    backend.create(Contact(id="c2", name="Bob"))
    assert len(backend.list()) == 2


def test_handler_search_filters() -> None:
    backend = InMemoryContacts()
    backend.create(_alice())
    backend.create(Contact(id="c2", name="Carl"))
    h = ContactsToolHandler(backend=backend)
    out = h.call("contacts.search", query="alice")
    assert isinstance(out, list)
    assert len(out) == 1


def test_handler_get_existing() -> None:
    backend = InMemoryContacts()
    backend.create(_alice())
    h = ContactsToolHandler(backend=backend)
    assert h.call("contacts.get", id="c1") is not None


def test_handler_get_missing() -> None:
    h = ContactsToolHandler(backend=InMemoryContacts())
    assert h.call("contacts.get", id="ghost") is None


def test_handler_create_returns_id() -> None:
    backend = InMemoryContacts()
    h = ContactsToolHandler(backend=backend)
    out = h.call("contacts.create", id="cX", name="New Person", emails=["x@y.com"])
    assert out == {"id": "cX"}
    assert backend.get("cX") is not None


def test_handler_unknown_tool() -> None:
    h = ContactsToolHandler(backend=InMemoryContacts())
    with pytest.raises(ValueError):
        h.call("contacts.bogus")


def test_carddav_construct() -> None:
    b = CardDavBackend(base_url="https://x", username="u", password="p")
    assert b.addressbook_path.endswith("/")


def test_icloud_factory_uses_icloud_url() -> None:
    b = ICloudContacts(username="u", password="p")
    assert "icloud.com" in b.base_url


def test_google_contacts_default() -> None:
    g = GoogleContacts(access_token="t")
    assert "googleapis.com" in g.endpoint
