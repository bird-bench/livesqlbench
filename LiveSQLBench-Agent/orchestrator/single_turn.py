"""LiveSQLBench — Single-turn text-to-SQL agent pipeline.

The orchestrator:
1. Initializes the DB environment service
2. Initializes an agent session on the system-agent service
3. Sends the user query once
4. Reads the final session state for metrics
"""

import logging
import time
import traceback
from typing import Any, Dict

import httpx

from shared.config import settings

logger = logging.getLogger(__name__)

SYSTEM_AGENT_URL = f"http://localhost:{settings.system_agent_port}"
DB_ENV_URL = f"http://localhost:{settings.db_env_port}"

MAX_STEPS = 30


async def _post(url: str, payload: dict, timeout: float = 120.0) -> dict:
    async with httpx.AsyncClient(timeout=timeout, trust_env=False) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        return resp.json()


async def init_task_on_services(task_id: str, task_data: dict):
    payload = {
        "task_id": task_id,
        "task_data": {**task_data, "_interact_mode": "single-turn"},
    }
    await _post(f"{DB_ENV_URL}/init_task", payload)
    logger.info("  [%s] DB environment initialized", task_id)


async def init_agent_session(task_id: str, task_data: dict):
    state = {
        "task_id": task_id,
        "db_name": task_data["selected_database"],
        "user_query": task_data["query"],
        "steps_remaining": MAX_STEPS,
        "max_steps": MAX_STEPS,
        "total_reward": 0.0,
        "tool_trajectory": [],
        "adk_events": [],
        "phase1_completed": False,
        "task_done": False,
    }
    return await _post(
        f"{SYSTEM_AGENT_URL}/init_session",
        {"task_id": task_id, "state": state, "reset": True},
        timeout=30.0,
    )


async def run_agent_session(task_id: str, message: str):
    return await _post(
        f"{SYSTEM_AGENT_URL}/run_session",
        {"task_id": task_id, "message": message},
        timeout=1800.0,
    )


async def cleanup_task_service(task_id: str):
    try:
        await _post(f"{DB_ENV_URL}/cleanup_task", {"task_id": task_id}, timeout=30.0)
    except Exception as e:
        logger.warning("Cleanup failed for %s: %s", task_id, e)


async def run_single_task(task_data: dict) -> Dict[str, Any]:
    instance_id = task_data["instance_id"]
    db_name = task_data["selected_database"]
    logger.info("Starting task: %s (db: %s)", instance_id, db_name)
    start_time = time.time()

    await init_task_on_services(instance_id, task_data)

    try:
        await init_agent_session(instance_id, task_data)

        initial_message = (
            f"Database: {db_name}\n"
            f"Task ID: {instance_id}\n\n"
            f"User Query:\n{task_data['query']}\n\n"
            f"You have {MAX_STEPS} steps. Each tool call costs 1 step.\n"
            f"You have ONE submission attempt — make it count."
        )

        run_result = await run_agent_session(instance_id, initial_message)
        state = run_result.get("state", {})
        elapsed = time.time() - start_time

        steps_used = MAX_STEPS - max(0, state.get("steps_remaining", MAX_STEPS))
        result = {
            "task_id": instance_id,
            "instance_id": instance_id,
            "database": db_name,
            "phase1_passed": state.get("phase1_completed", False),
            "total_reward": state.get("total_reward", 0.0),
            "elapsed_seconds": elapsed,
            "steps_used": steps_used,
            "steps_remaining": max(0, state.get("steps_remaining", MAX_STEPS)),
            "tool_trajectory": state.get("tool_trajectory", []),
            "adk_events": state.get("adk_events", []),
            "final_response": run_result.get("response", ""),
        }
        logger.info(
            "Task %s done. Reward: %.2f, Steps used: %d, Time: %.1fs",
            instance_id,
            result["total_reward"],
            steps_used,
            elapsed,
        )
        return result
    finally:
        await cleanup_task_service(instance_id)
