"""LLM brain: model adapters, routing, agent loops."""

from nova.brain import agent as _agent
from nova.brain import cloud as _cloud
from nova.brain import llm as _llm
from nova.brain import models as _models
from nova.brain import planner as _planner
from nova.brain import prompt as _prompt
from nova.brain import router as _router

ChatMessage = _llm.ChatMessage
ChatResponse = _llm.ChatResponse
LlmBackend = _llm.LlmBackend
ToolCall = _llm.ToolCall
available_llms = _llm.available_llms
create_llm = _llm.create_llm
register_llm = _llm.register_llm

CLAUDE_OPUS_MODEL = _cloud.CLAUDE_OPUS_MODEL
CloudProvider = _cloud.CloudProvider
cloud_available = _cloud.cloud_available
create_claude_opus = _cloud.create_claude_opus
create_cloud_backend = _cloud.create_cloud_backend
first_available_provider = _cloud.first_available_provider

AgentResult = _agent.AgentResult
AgentStep = _agent.AgentStep
ReactAgent = _agent.ReactAgent
Tool = _agent.Tool
ToolHandler = _agent.ToolHandler

PlanExecuteAgent = _planner.PlanExecuteAgent
PlanResult = _planner.PlanResult
StepResult = _planner.StepResult
parse_plan = _planner.parse_plan

DeviceContext = _prompt.DeviceContext
PromptContext = _prompt.PromptContext
WindowContext = _prompt.WindowContext
render_system_prompt = _prompt.render_system_prompt

HybridRouter = _router.HybridRouter
Privacy = _router.Privacy
RouteDecision = _router.RouteDecision
RouteRequest = _router.RouteRequest

DEFAULT_MODELS = _models.DEFAULT_MODELS
ModelSpec = _models.ModelSpec
detect_ram_gb = _models.detect_ram_gb
pick_model = _models.pick_model
recommended_for_host = _models.recommended_for_host

__all__ = [
    "CLAUDE_OPUS_MODEL",
    "DEFAULT_MODELS",
    "AgentResult",
    "AgentStep",
    "ChatMessage",
    "ChatResponse",
    "CloudProvider",
    "HybridRouter",
    "LlmBackend",
    "ModelSpec",
    "Privacy",
    "RouteDecision",
    "RouteRequest",
    "ToolCall",
    "available_llms",
    "cloud_available",
    "create_claude_opus",
    "create_cloud_backend",
    "create_llm",
    "detect_ram_gb",
    "first_available_provider",
    "pick_model",
    "recommended_for_host",
    "register_llm",
]
