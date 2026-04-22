"""Tests for HybridRouter."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any

from nova.brain.llm import ChatMessage, ChatResponse
from nova.brain.router import (
    HybridRouter,
    Privacy,
    RouteRequest,
)


class StubLlm:
    def __init__(self, name: str) -> None:
        self.name = name
        self.model = name

    def chat(
        self,
        messages: Sequence[ChatMessage],
        tools: Sequence[dict[str, Any]] | None = None,
    ) -> ChatResponse:
        return ChatResponse(message=ChatMessage(role="assistant", content=self.name))

    def stream(
        self,
        messages: Sequence[ChatMessage],
        tools: Sequence[dict[str, Any]] | None = None,
    ) -> Iterable[str]:
        yield self.name


def _req(**kw: Any) -> RouteRequest:
    return RouteRequest(messages=[ChatMessage(role="user", content="hi")], **kw)


def test_no_cloud_forces_local() -> None:
    router = HybridRouter(local=StubLlm("local"))
    dec = router.decide(_req(difficulty="hard"))
    assert dec.target == "local"
    assert "no cloud" in dec.reason


def test_secret_privacy_forces_local_even_when_hard() -> None:
    router = HybridRouter(local=StubLlm("local"), cloud=StubLlm("cloud"))
    dec = router.decide(_req(privacy=Privacy.SECRET, difficulty="hard"))
    assert dec.target == "local"
    assert dec.reason == "privacy=secret"


def test_computer_use_forces_cloud() -> None:
    router = HybridRouter(local=StubLlm("local"), cloud=StubLlm("cloud"))
    dec = router.decide(_req(needs_computer_use=True))
    assert dec.target == "cloud"


def test_hard_difficulty_routes_to_cloud() -> None:
    router = HybridRouter(local=StubLlm("local"), cloud=StubLlm("cloud"))
    dec = router.decide(_req(difficulty="hard", privacy=Privacy.PUBLIC))
    assert dec.target == "cloud"


def test_easy_public_request_stays_local() -> None:
    router = HybridRouter(local=StubLlm("local"), cloud=StubLlm("cloud"))
    dec = router.decide(_req(difficulty="easy", privacy=Privacy.PUBLIC))
    assert dec.target == "local"


def test_cost_cap_forces_local_even_when_hard() -> None:
    router = HybridRouter(
        local=StubLlm("local"),
        cloud=StubLlm("cloud"),
        daily_cost_cap_usd=1.0,
        spend_today_usd=1.5,
    )
    dec = router.decide(_req(difficulty="hard", privacy=Privacy.PUBLIC))
    assert dec.target == "local"
    assert "cost cap" in dec.reason


def test_decisions_are_logged() -> None:
    router = HybridRouter(local=StubLlm("local"), cloud=StubLlm("cloud"))
    router.decide(_req())
    router.decide(_req(difficulty="hard", privacy=Privacy.PUBLIC))
    assert len(router.decisions) == 2


def test_pick_returns_correct_backend() -> None:
    local = StubLlm("local")
    cloud = StubLlm("cloud")
    router = HybridRouter(local=local, cloud=cloud)
    assert router.pick(_req(difficulty="easy", privacy=Privacy.PUBLIC)).name == "local"
    assert router.pick(_req(difficulty="hard", privacy=Privacy.PUBLIC)).name == "cloud"


def test_vision_request_routes_cloud() -> None:
    router = HybridRouter(local=StubLlm("local"), cloud=StubLlm("cloud"))
    dec = router.decide(_req(needs_vision=True, privacy=Privacy.PUBLIC))
    assert dec.target == "cloud"
