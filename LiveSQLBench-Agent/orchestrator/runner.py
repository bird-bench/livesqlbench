"""Parallel evaluation runner for single-turn text-to-SQL."""

import asyncio
import argparse
import json
import logging
import time
import traceback
from pathlib import Path
from typing import Any, Callable, Awaitable, Dict, List

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


async def run_parallel_evaluation(
    tasks: List[dict],
    run_single_task: Callable[[dict], Awaitable[Dict[str, Any]]],
    output_path: str,
    concurrency: int = 5,
):
    semaphore = asyncio.Semaphore(concurrency)
    results: List[Dict[str, Any]] = []
    results_lock = asyncio.Lock()
    total_reward = 0.0
    p1_count = 0
    completed = 0
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    async def _save():
        n = len(results)
        if n == 0:
            return
        output = {
            "mode": "single-turn",
            "metrics": {
                "total_tasks": n,
                "total_reward": total_reward,
                "average_reward": total_reward / n,
                "phase1_rate": p1_count / n,
                "phase1_count": p1_count,
            },
            "results": results,
        }
        with open(output_path, "w") as f:
            json.dump(output, f, indent=2, default=str)

    async def _run_one(i: int, td: dict):
        nonlocal total_reward, p1_count, completed
        instance_id = td["instance_id"]
        async with semaphore:
            logger.info("=== Task %d/%d: %s ===", i + 1, len(tasks), instance_id)
            try:
                r = await run_single_task(td)
            except Exception as e:
                logger.error("Error: %s: %s", instance_id, e)
                traceback.print_exc()
                r = {"task_id": instance_id, "error": str(e), "total_reward": 0}

        async with results_lock:
            results.append(r)
            total_reward += r.get("total_reward", 0)
            if r.get("phase1_passed"):
                p1_count += 1
            completed += 1
            if completed % 5 == 0 or completed == len(tasks):
                await _save()

    await asyncio.gather(*[_run_one(i, td) for i, td in enumerate(tasks)])
    await _save()

    n = len(tasks)
    if n:
        logger.info(
            "\nDone! Tasks: %d, Avg Reward: %.4f, Pass: %d/%d (%.1f%%)",
            n, total_reward / n, p1_count, n, p1_count / n * 100,
        )


def load_tasks(data_path: str, limit: int = None) -> List[dict]:
    tasks = []
    with open(data_path) as f:
        for line in f:
            if line.strip():
                tasks.append(json.loads(line))
    if limit:
        tasks = tasks[:limit]
    return tasks


def main():
    parser = argparse.ArgumentParser(description="Single-turn text-to-SQL evaluation")
    parser.add_argument("--data", default=settings.data_path)
    parser.add_argument("--output", default="results/eval_single_turn.json")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--concurrency", type=int, default=5)
    args = parser.parse_args()

    from orchestrator.single_turn import run_single_task

    tasks = load_tasks(args.data, args.limit)
    logger.info("Single-turn: Evaluating %d tasks with concurrency=%d", len(tasks), args.concurrency)

    asyncio.run(run_parallel_evaluation(
        tasks=tasks,
        run_single_task=run_single_task,
        output_path=args.output,
        concurrency=args.concurrency,
    ))


if __name__ == "__main__":
    main()
