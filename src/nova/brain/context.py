"""Sliding-context manager with LLM-based summarization.

Keeps the system prompt plus the most recent ``keep_recent`` turns
verbatim. When the estimated token count crosses ``budget_tokens``, the
older tail is summarized (via an LLM) into a single synthetic system
message so the conversation can continue without losing the thread.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from nova.brain.llm import ChatMessage, LlmBackend


def estimate_tokens(text: str) -> int:
    """Cheap token estimator (~4 chars per token; accurate to ±20%)."""
    return max(1, len(text) // 4)


def estimate_history_tokens(history: list[ChatMessage]) -> int:
    return sum(estimate_tokens(m.content) for m in history)


SUMMARIZE_PROMPT = (
    "Summarize the following conversation between a user and an AI "
    "assistant. Keep: user preferences, open questions, facts about the "
    "user, and any commitments made. Drop pleasantries. Under 200 words."
)


@dataclass
class ContextWindow:
    budget_tokens: int = 6000
    keep_recent: int = 8
    _history: list[ChatMessage] = field(default_factory=list)

    def append(self, message: ChatMessage) -> None:
        self._history.append(message)

    def extend(self, messages: list[ChatMessage]) -> None:
        self._history.extend(messages)

    def history(self) -> list[ChatMessage]:
        return list(self._history)

    def tokens(self) -> int:
        return estimate_history_tokens(self._history)

    def needs_compact(self) -> bool:
        return self.tokens() > self.budget_tokens

    def compact(self, llm: LlmBackend) -> ChatMessage | None:
        """Collapse everything before the tail of ``keep_recent`` turns.

        Returns the synthetic summary message that was inserted, or
        ``None`` if no compaction was performed.
        """
        if len(self._history) <= self.keep_recent + 1:
            return None
        # Preserve the leading system message if present.
        head_system: list[ChatMessage] = []
        body = list(self._history)
        if body and body[0].role == "system":
            head_system = [body.pop(0)]
        if len(body) <= self.keep_recent:
            return None
        tail = body[-self.keep_recent :]
        older = body[: -self.keep_recent]
        if not older:
            return None
        transcript = "\n".join(f"{m.role}: {m.content}" for m in older)
        summary_resp = llm.chat(
            [
                ChatMessage(role="system", content=SUMMARIZE_PROMPT),
                ChatMessage(role="user", content=transcript),
            ]
        )
        summary_msg = ChatMessage(
            role="system", content=f"[prior summary]\n{summary_resp.message.content.strip()}"
        )
        self._history = head_system + [summary_msg] + tail
        return summary_msg

    def maybe_compact(self, llm: LlmBackend) -> ChatMessage | None:
        if self.needs_compact():
            return self.compact(llm)
        return None


__all__ = [
    "ContextWindow",
    "estimate_history_tokens",
    "estimate_tokens",
]
