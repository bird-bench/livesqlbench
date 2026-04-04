"""System Agent Service (Port 6000).

Wraps the LLM agent behind a FastAPI endpoint so the orchestrator
communicates through HTTP:
  - System Agent:    port 6000 (this service)
  - DB Environment:  port 6002
"""

import logging
from typing import Any, Dict

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from shared.config import settings
from system_agent.adk_runtime import AdkRuntime

logger = logging.getLogger(__name__)
app = FastAPI(title="LiveSQLBench System Agent", version="1.0.0")
runtime = AdkRuntime()


class SessionInitRequest(BaseModel):
    task_id: str
    state: Dict[str, Any] = {}
    reset: bool = True


class SessionRunRequest(BaseModel):
    task_id: str
    message: str


@app.post("/init_session")
async def init_session(req: SessionInitRequest):
    if not runtime.available:
        raise HTTPException(status_code=503, detail=f"ADK runtime unavailable: {runtime.error}")
    return await runtime.init_session(
        task_id=req.task_id,
        state=req.state,
        reset=req.reset,
    )


@app.post("/run_session")
async def run_session(req: SessionRunRequest):
    if not runtime.available:
        raise HTTPException(status_code=503, detail=f"ADK runtime unavailable: {runtime.error}")
    return await runtime.run_turn(
        task_id=req.task_id,
        message=req.message,
    )


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "system_agent",
        "model": settings.system_agent_model,
        "adk_available": runtime.available,
        "adk_error": runtime.error,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.system_agent_port)
