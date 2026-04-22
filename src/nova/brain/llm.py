"""LLM backend abstraction.

Uniform ``chat(messages, tools) -> ChatResponse`` API across providers.
Concrete adapters (Ollama, llama.cpp, vLLM, Claude, OpenAI, Gemini)
import their native SDKs lazily so you only pay for what you select.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol, runtime_checkable

Role = Literal["system", "user", "assistant", "tool"]


@dataclass(frozen=True, slots=True)
class ChatMessage:
    role: Role
    content: str
    name: str | None = None
    tool_call_id: str | None = None


@dataclass(frozen=True, slots=True)
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True, slots=True)
class ChatResponse:
    message: ChatMessage
    tool_calls: tuple[ToolCall, ...] = field(default_factory=tuple)
    finish_reason: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None


@runtime_checkable
class LlmBackend(Protocol):
    name: str
    model: str

    def chat(
        self,
        messages: Sequence[ChatMessage],
        tools: Sequence[dict[str, Any]] | None = None,
    ) -> ChatResponse: ...

    def stream(
        self,
        messages: Sequence[ChatMessage],
        tools: Sequence[dict[str, Any]] | None = None,
    ) -> Iterable[str]: ...


# --- Registry ---------------------------------------------------------------


class _LlmRegistry:
    def __init__(self) -> None:
        self._builders: dict[str, Callable[..., LlmBackend]] = {}

    def register(self, name: str, builder: Callable[..., LlmBackend]) -> None:
        self._builders[name] = builder

    def build(self, name: str, **kwargs: object) -> LlmBackend:
        if name not in self._builders:
            raise ValueError(f"unknown LLM backend: {name!r}")
        return self._builders[name](**kwargs)

    def names(self) -> Iterable[str]:
        return tuple(self._builders)


_registry = _LlmRegistry()


def register_llm(name: str, builder: Callable[..., LlmBackend]) -> None:
    _registry.register(name, builder)


def available_llms() -> tuple[str, ...]:
    return tuple(_registry.names())


def create_llm(backend: str = "ollama", **kwargs: object) -> LlmBackend:
    return _registry.build(backend, **kwargs)


# --- Built-in adapters (lazy) -----------------------------------------------


class _OllamaBackend:
    name = "ollama"

    def __init__(self, model: str = "gemma3:4b", host: str = "http://127.0.0.1:11434") -> None:
        self.model = model
        self.host = host
        self._client: Any | None = None

    def _ensure(self) -> Any:
        if self._client is None:
            import ollama

            self._client = ollama.Client(host=self.host)
        return self._client

    def _dump(self, messages: Sequence[ChatMessage]) -> list[dict[str, Any]]:
        return [{"role": m.role, "content": m.content} for m in messages]

    def chat(
        self,
        messages: Sequence[ChatMessage],
        tools: Sequence[dict[str, Any]] | None = None,
    ) -> ChatResponse:
        client = self._ensure()
        resp = client.chat(model=self.model, messages=self._dump(messages), tools=list(tools or []))
        msg = resp["message"]
        return ChatResponse(
            message=ChatMessage(role="assistant", content=msg.get("content", "")),
            finish_reason=resp.get("done_reason"),
        )

    def stream(
        self,
        messages: Sequence[ChatMessage],
        tools: Sequence[dict[str, Any]] | None = None,
    ) -> Iterable[str]:
        client = self._ensure()
        for part in client.chat(model=self.model, messages=self._dump(messages), stream=True):
            yield str(part["message"]["content"])


class _LlamaCppBackend:
    name = "llama.cpp"

    def __init__(self, model_path: str, n_ctx: int = 8192) -> None:
        self.model = model_path
        self.n_ctx = n_ctx
        self._llm: Any | None = None

    def _ensure(self) -> Any:
        if self._llm is None:
            from llama_cpp import Llama

            self._llm = Llama(model_path=self.model, n_ctx=self.n_ctx, verbose=False)
        return self._llm

    def _dump(self, messages: Sequence[ChatMessage]) -> list[dict[str, Any]]:
        return [{"role": m.role, "content": m.content} for m in messages]

    def chat(
        self,
        messages: Sequence[ChatMessage],
        tools: Sequence[dict[str, Any]] | None = None,
    ) -> ChatResponse:
        llm = self._ensure()
        resp = llm.create_chat_completion(messages=self._dump(messages))
        choice = resp["choices"][0]
        return ChatResponse(
            message=ChatMessage(role="assistant", content=choice["message"]["content"]),
            finish_reason=choice.get("finish_reason"),
        )

    def stream(
        self,
        messages: Sequence[ChatMessage],
        tools: Sequence[dict[str, Any]] | None = None,
    ) -> Iterable[str]:
        llm = self._ensure()
        for part in llm.create_chat_completion(messages=self._dump(messages), stream=True):
            delta = part["choices"][0]["delta"].get("content", "")
            if delta:
                yield str(delta)


class _VllmBackend:
    name = "vllm"

    def __init__(self, model: str, host: str = "http://127.0.0.1:8000") -> None:
        self.model = model
        self.host = host
        self._client: Any | None = None

    def _ensure(self) -> Any:
        if self._client is None:
            import openai

            self._client = openai.OpenAI(base_url=f"{self.host}/v1", api_key="vllm")
        return self._client

    def _dump(self, messages: Sequence[ChatMessage]) -> list[dict[str, Any]]:
        return [{"role": m.role, "content": m.content} for m in messages]

    def chat(
        self,
        messages: Sequence[ChatMessage],
        tools: Sequence[dict[str, Any]] | None = None,
    ) -> ChatResponse:
        client = self._ensure()
        resp = client.chat.completions.create(model=self.model, messages=self._dump(messages))
        choice = resp.choices[0]
        return ChatResponse(
            message=ChatMessage(role="assistant", content=choice.message.content or ""),
            finish_reason=choice.finish_reason,
        )

    def stream(
        self,
        messages: Sequence[ChatMessage],
        tools: Sequence[dict[str, Any]] | None = None,
    ) -> Iterable[str]:
        client = self._ensure()
        for chunk in client.chat.completions.create(
            model=self.model, messages=self._dump(messages), stream=True
        ):
            delta = chunk.choices[0].delta.content
            if delta:
                yield str(delta)


class _ClaudeBackend:
    name = "claude"

    def __init__(self, model: str = "claude-opus-4-7", api_key: str | None = None) -> None:
        self.model = model
        self.api_key = api_key
        self._client: Any | None = None

    def _ensure(self) -> Any:
        if self._client is None:
            import anthropic

            self._client = anthropic.Anthropic(api_key=self.api_key)
        return self._client

    def _split(self, messages: Sequence[ChatMessage]) -> tuple[str, list[dict[str, Any]]]:
        system = "\n".join(m.content for m in messages if m.role == "system")
        rest = [{"role": m.role, "content": m.content} for m in messages if m.role != "system"]
        return system, rest

    def chat(
        self,
        messages: Sequence[ChatMessage],
        tools: Sequence[dict[str, Any]] | None = None,
    ) -> ChatResponse:
        client = self._ensure()
        system, rest = self._split(messages)
        resp = client.messages.create(
            model=self.model,
            system=system,
            messages=rest,
            tools=list(tools or []),
            max_tokens=4096,
        )
        text = "".join(block.text for block in resp.content if block.type == "text")
        tool_calls = tuple(
            ToolCall(id=b.id, name=b.name, arguments=dict(b.input))
            for b in resp.content
            if b.type == "tool_use"
        )
        return ChatResponse(
            message=ChatMessage(role="assistant", content=text),
            tool_calls=tool_calls,
            finish_reason=resp.stop_reason,
            input_tokens=resp.usage.input_tokens,
            output_tokens=resp.usage.output_tokens,
        )

    def stream(
        self,
        messages: Sequence[ChatMessage],
        tools: Sequence[dict[str, Any]] | None = None,
    ) -> Iterable[str]:
        client = self._ensure()
        system, rest = self._split(messages)
        with client.messages.stream(
            model=self.model, system=system, messages=rest, max_tokens=4096
        ) as stream:
            for text in stream.text_stream:
                yield str(text)


class _OpenAiBackend:
    name = "openai"

    def __init__(self, model: str = "gpt-4o", api_key: str | None = None) -> None:
        self.model = model
        self.api_key = api_key
        self._client: Any | None = None

    def _ensure(self) -> Any:
        if self._client is None:
            import openai

            self._client = openai.OpenAI(api_key=self.api_key)
        return self._client

    def _dump(self, messages: Sequence[ChatMessage]) -> list[dict[str, Any]]:
        return [{"role": m.role, "content": m.content} for m in messages]

    def chat(
        self,
        messages: Sequence[ChatMessage],
        tools: Sequence[dict[str, Any]] | None = None,
    ) -> ChatResponse:
        client = self._ensure()
        resp = client.chat.completions.create(model=self.model, messages=self._dump(messages))
        choice = resp.choices[0]
        return ChatResponse(
            message=ChatMessage(role="assistant", content=choice.message.content or ""),
            finish_reason=choice.finish_reason,
        )

    def stream(
        self,
        messages: Sequence[ChatMessage],
        tools: Sequence[dict[str, Any]] | None = None,
    ) -> Iterable[str]:
        client = self._ensure()
        for chunk in client.chat.completions.create(
            model=self.model, messages=self._dump(messages), stream=True
        ):
            delta = chunk.choices[0].delta.content
            if delta:
                yield str(delta)


class _GeminiBackend:
    name = "gemini"

    def __init__(self, model: str = "gemini-2.5-flash", api_key: str | None = None) -> None:
        self.model = model
        self.api_key = api_key
        self._client: Any | None = None

    def _ensure(self) -> Any:
        if self._client is None:
            import google.generativeai as genai

            genai.configure(api_key=self.api_key)
            self._client = genai.GenerativeModel(self.model)
        return self._client

    def _flatten(self, messages: Sequence[ChatMessage]) -> str:
        return "\n".join(f"{m.role}: {m.content}" for m in messages)

    def chat(
        self,
        messages: Sequence[ChatMessage],
        tools: Sequence[dict[str, Any]] | None = None,
    ) -> ChatResponse:
        model = self._ensure()
        resp = model.generate_content(self._flatten(messages))
        return ChatResponse(message=ChatMessage(role="assistant", content=resp.text))

    def stream(
        self,
        messages: Sequence[ChatMessage],
        tools: Sequence[dict[str, Any]] | None = None,
    ) -> Iterable[str]:
        model = self._ensure()
        for chunk in model.generate_content(self._flatten(messages), stream=True):
            if chunk.text:
                yield str(chunk.text)


_registry.register("ollama", lambda **kw: _OllamaBackend(**kw))
_registry.register("llama.cpp", lambda **kw: _LlamaCppBackend(**kw))
_registry.register("vllm", lambda **kw: _VllmBackend(**kw))
_registry.register("claude", lambda **kw: _ClaudeBackend(**kw))
_registry.register("openai", lambda **kw: _OpenAiBackend(**kw))
_registry.register("gemini", lambda **kw: _GeminiBackend(**kw))
