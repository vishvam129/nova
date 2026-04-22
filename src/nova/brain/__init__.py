"""LLM brain: model adapters, routing, agent loops."""

from nova.brain import llm as _llm
from nova.brain import models as _models

ChatMessage = _llm.ChatMessage
ChatResponse = _llm.ChatResponse
LlmBackend = _llm.LlmBackend
ToolCall = _llm.ToolCall
available_llms = _llm.available_llms
create_llm = _llm.create_llm
register_llm = _llm.register_llm

DEFAULT_MODELS = _models.DEFAULT_MODELS
ModelSpec = _models.ModelSpec
detect_ram_gb = _models.detect_ram_gb
pick_model = _models.pick_model
recommended_for_host = _models.recommended_for_host

__all__ = [
    "DEFAULT_MODELS",
    "ChatMessage",
    "ChatResponse",
    "LlmBackend",
    "ModelSpec",
    "ToolCall",
    "available_llms",
    "create_llm",
    "detect_ram_gb",
    "pick_model",
    "recommended_for_host",
    "register_llm",
]
