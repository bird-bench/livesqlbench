"""LiveSQLBench ADK System Agent — Single-turn text-to-SQL."""

import logging
from typing import Any

from shared.config import settings

try:
    from google.adk import Agent
    from google.adk.tools import FunctionTool
    from google.genai import types
    ADK_AVAILABLE = True
    ADK_IMPORT_ERROR = ""
except ImportError as exc:
    Agent = Any
    FunctionTool = None
    types = None
    ADK_AVAILABLE = False
    ADK_IMPORT_ERROR = str(exc)

logger = logging.getLogger(__name__)

from shared.llm import build_adk_model as _build_model

INSTRUCTION = """You are a PostgreSQL expert. Your task is to write a SQL query that answers the user's question about a database.

You have access to tools that let you explore the database and submit your answer. Each tool call costs 1 step. You will be told how many steps remain after each action.

Available tools:
- get_schema: get the database schema (CREATE TABLE statements). Cost: 1 step
- get_all_column_meanings: get descriptions of all columns. Cost: 1 step
- get_column_meaning: get the description of one specific column. Cost: 1 step
- get_all_external_knowledge_names: list available domain knowledge entries. Cost: 1 step
- get_knowledge_definition: get one knowledge entry's definition. Cost: 1 step
- get_all_knowledge_definitions: get all knowledge definitions. Cost: 1 step
- execute_sql: run a SQL query and see results. Cost: 1 step
- submit_sql: submit your final SQL answer. Cost: 1 step

IMPORTANT RULES:
- You have ONE submission attempt. Once you call submit_sql, the task ends — pass or fail.
- Be confident before submitting. Test your SQL with execute_sql first.
- Be efficient with steps. A good strategy:
  1. Get the schema to understand the tables.
  2. Check external knowledge if the question involves domain-specific terms.
  3. Write and test your SQL with execute_sql.
  4. Submit when confident.
"""


def build_agent() -> Agent:
    """Build the single-turn text-to-SQL agent."""
    if not ADK_AVAILABLE:
        raise RuntimeError(f"google-adk runtime unavailable: {ADK_IMPORT_ERROR}")

    from system_agent.tools import get_tools
    from system_agent.callbacks import (
        before_model_callback, before_tool_callback, after_tool_callback,
    )

    model = _build_model(settings.system_agent_model)
    return Agent(
        model=model,
        name="bird_interact_agent",
        description="Single-turn text-to-SQL agent.",
        instruction=INSTRUCTION,
        tools=get_tools(),
        before_model_callback=before_model_callback,
        before_tool_callback=before_tool_callback,
        after_tool_callback=after_tool_callback,
        generate_content_config=types.GenerateContentConfig(temperature=0.0),
    )
