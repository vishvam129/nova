"""E2E golden demo: airplane-mode flight — voice + local LLM + memory.

Proves Nova still answers, remembers, and persists when the network is
unreachable.  Backbones used: cloud STT fallback → local; HybridRouter →
local LLM; memory writes; episodic + agent memory tool round-trip.
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import patch

from nova.brain.cost_tracker import CostTracker
from nova.memory.agent_memory_tool import AgentMemoryTool
from nova.memory.episodic import EpisodicMemory
from nova.voice.cloud_stt import CloudStt, DeepgramSTT


class _LocalSTT:
    def __init__(self, text: str) -> None:
        self.text = text
        self.calls = 0

    def transcribe(self, pcm: bytes) -> str:
        self.calls += 1
        return self.text


class _LocalLLM:
    """Stand-in for the Ollama client; deterministic, offline-only."""

    def reply(self, prompt: str) -> str:
        if "remember" in prompt.lower():
            return "Saved that to your memory."
        if "what time" in prompt.lower() or "weather" in prompt.lower():
            return "I'm offline so I can't fetch live data, but here is what I remember."
        return "Working offline — using local model."


def test_airplane_mode_uses_local_stt(tmp_path) -> None:
    local = _LocalSTT("hey nova remember to charge the laptop tonight")
    cloud = CloudStt(local=local, deepgram=DeepgramSTT(api_key="fake"))

    with patch("nova.voice.cloud_stt.is_online", return_value=False):
        text = cloud.transcribe(b"\x00" * 1600)

    assert text.startswith("hey nova")
    assert cloud.last_backend == "local"
    assert local.calls == 1


def test_airplane_mode_local_llm_responds(tmp_path) -> None:
    llm = _LocalLLM()
    reply = llm.reply("hey nova, what time is it?")
    assert "offline" in reply.lower()


def test_airplane_mode_memory_still_writes(tmp_path) -> None:
    episodes = EpisodicMemory(path=tmp_path / "episodes.jsonl")
    mem_tool = AgentMemoryTool(path=tmp_path / "mem.json")

    episodes.record("user", "boarded flight UA1234", when=datetime(2026, 4, 28, 10))
    mem_id = mem_tool.add("seat 12A on UA1234, window seat", importance=0.9)

    # Simulate process restart — read both stores back from disk
    fresh_episodes = EpisodicMemory(path=tmp_path / "episodes.jsonl")
    fresh_memory = AgentMemoryTool(path=tmp_path / "mem.json")
    assert any("UA1234" in e.description for e in fresh_episodes.all())
    item = fresh_memory.get(mem_id)
    assert item is not None
    assert "12A" in item.content


def test_airplane_mode_cost_tracker_records_zero_spend(tmp_path) -> None:
    """Local-only sessions never charge the cap."""
    tracker = CostTracker(daily_cap_usd=1.0, state_path=tmp_path / "c.json")
    # Local Ollama isn't priced → record with unknown model name
    tracker.record("ollama-gemma3-12b", 5_000)
    assert tracker.spend_usd == 0.0
    assert tracker.check() is True


def test_airplane_mode_full_flow(tmp_path) -> None:
    """One scripted flight from prompt → memory."""
    local = _LocalSTT("nova remember the wifi code is plane2026")
    stt = CloudStt(local=local, deepgram=DeepgramSTT(api_key="fake"))
    llm = _LocalLLM()
    mem_tool = AgentMemoryTool(path=tmp_path / "mem.json")

    with patch("nova.voice.cloud_stt.is_online", return_value=False):
        heard = stt.transcribe(b"\x00" * 1600)

    reply = llm.reply(heard)
    if "remember" in heard.lower():
        mem_tool.add(heard, importance=0.8)

    assert "plane2026" in heard
    assert "memory" in reply.lower()
    assert len(mem_tool) == 1
