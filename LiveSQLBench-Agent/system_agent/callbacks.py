"""ADK callbacks: step-based budget management and turn limiting."""

import json
import logging
from typing import Any

from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.adk.tools.tool_context import ToolContext
from google.genai import types as genai_types

logger = logging.getLogger(__name__)

MAX_MODEL_TURNS = 60


def _preview(value: Any, limit: int = 2000) -> Any:
    if isinstance(value, (dict, list)):
        text = json.dumps(value, ensure_ascii=False)
    else:
        text = str(value)
    return text[:limit] + "...<truncated>" if len(text) > limit else text


async def before_model_callback(
    callback_context: CallbackContext, llm_request: LlmRequest
) -> LlmResponse | None:
    """Cap LLM invocations and enforce step/task limits."""
    turns = callback_context.state.get("model_turns", 0) + 1
    callback_context.state["model_turns"] = turns
    if turns > MAX_MODEL_TURNS:
        logger.warning("Max model turns (%d) reached, forcing stop.", MAX_MODEL_TURNS)
        return LlmResponse(
            content=genai_types.Content(
                role="model",
                parts=[genai_types.Part.from_text(
                    text="Maximum interaction turns reached. Task ended."
                )],
            ),
        )

    if callback_context.state.get("task_done", False):
        return LlmResponse(
            content=genai_types.Content(
                role="model",
                parts=[genai_types.Part.from_text(text="Task completed.")],
            ),
        )

    steps = callback_context.state.get("steps_remaining", 0)
    if steps <= 0:
        return LlmResponse(
            content=genai_types.Content(
                role="model",
                parts=[genai_types.Part.from_text(text="No steps remaining. Task ended.")],
            ),
        )

    return None


async def before_tool_callback(
    tool, args: dict, tool_context: ToolContext
) -> dict | None:
    """Deduct 1 step per tool call. Block if no steps remain."""
    steps = tool_context.state.get("steps_remaining", 0)
    tool_context.state["_steps_before"] = steps

    if steps <= 0:
        return {"error": "No steps remaining. You must stop."}

    tool_context.state["steps_remaining"] = steps - 1
    return None


async def after_tool_callback(
    tool, args: dict, tool_context: ToolContext, tool_response
) -> dict | None:
    """Record tool event in trajectory and append step count to response."""
    tool_name = tool.name if hasattr(tool, "name") else str(tool)
    steps_before = tool_context.state.get("_steps_before", 0)
    steps_after = tool_context.state.get("steps_remaining", 0)
    max_steps = tool_context.state.get("max_steps", 30)

    trajectory = tool_context.state.get("tool_trajectory", [])
    trajectory.append({
        "type": "tool",
        "tool": tool_name,
        "args": args,
        "result": _preview(tool_response),
        "steps_before": steps_before,
        "steps_after": steps_after,
    })
    tool_context.state["tool_trajectory"] = trajectory

    if steps_after > 0:
        note = f"\n\n[SYSTEM NOTE: Steps remaining: {steps_after}/{max_steps}]"
        return str(tool_response) + note
    return None
