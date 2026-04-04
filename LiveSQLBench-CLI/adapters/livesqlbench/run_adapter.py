from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Iterable

SCRIPT_DIR = Path(__file__).resolve().parent
HARBOR_ROOT = SCRIPT_DIR.parent.parent
WORKSPACE_ROOT = HARBOR_ROOT.parent

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from adapter import LiveSQLBenchAdapter  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def _default_output_dir() -> Path:
    return HARBOR_ROOT / "datasets" / "livesqlbench"

def _default_data_root() -> Path:
    return WORKSPACE_ROOT / "data" / "livesqlbench-base-lite"

def _default_data_jsonl() -> Path:
    return _default_data_root() / "livesqlbench_data.jsonl"

def _default_eval_src() -> Path:
    return WORKSPACE_ROOT / "evaluation" / "src"

def _default_db_dump_root() -> Path:
    return WORKSPACE_ROOT / "evaluation" / "postgre_table_dumps"

def _read_ids_from_file(path: Path) -> list[str]:
    lines: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        lines.append(stripped)
    return lines


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate Harbor tasks for livesqlbench",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--data-root",
        type=Path,
        default=_default_data_root(),
        help="Path to livesqlbench data folder directory",
    )
    parser.add_argument(
        "--agent-image",
        type=str,
        default="livesqlbench-main-openhands:latest",
        help="Docker image used for the main agent container",
    )
    parser.add_argument(
        "--eval-src-dir",
        type=Path,
        default=_default_eval_src(),
        help="Path to original LiveSQLBench evaluation/src directory",
    )
    parser.add_argument(
        "--db-dump-root",
        type=Path,
        default=_default_db_dump_root(),
        help="Path to original LiveSQLBench table dumps directory",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=_default_output_dir(),
        help="Directory to write generated tasks (defaults to datasets/livesqlbench)",
    )
    parser.add_argument(
        "--ids",
        nargs="*",
        default=None,
        help="Explicit source ids to convert (space-separated)",
    )
    parser.add_argument(
        "--ids-file",
        type=Path,
        default=None,
        help="Path to a text file with one source id per line",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Generate only the first N tasks from the provided ids",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing task directories",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        dest="list_tasks",
        help="List source ids and exit",
    )
    return parser.parse_args()


def _collect_ids(ids_cli: Iterable[str] | None, ids_file: Path | None) -> list[str]:
    if ids_cli:
        return list(ids_cli)
    if ids_file and ids_file.exists():
        return _read_ids_from_file(ids_file)
    return []


def main() -> None:
    args = _parse_args()

    if args.data_root:
        default_gt = args.data_root / "livesqlbench_data.jsonl"
        data_jsonl = args.data_root / "livesqlbench_data.jsonl"
    else:
        default_gt = _default_data_jsonl()
    if default_gt.exists():
        gt_jsonl = default_gt

    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    adapter = LiveSQLBenchAdapter(
        task_dir=output_dir,
        data_jsonl=data_jsonl.resolve(),
        data_root=args.data_root.resolve(),
        gt_jsonl=gt_jsonl.resolve(),
        eval_src_dir=args.eval_src_dir.resolve(),
        db_dump_root=args.db_dump_root.resolve(),
        agent_image=args.agent_image,
    )

    all_source_ids = adapter.get_all_source_ids()

    if args.list_tasks:
        print(f"Available source ids ({len(all_source_ids)}):")
        for source_id in all_source_ids:
            print(source_id)
        return

    explicit_ids = _collect_ids(args.ids, args.ids_file)
    if explicit_ids:
        selected_ids = explicit_ids
    else:
        selected_ids = all_source_ids

    if args.limit is not None:
        selected_ids = selected_ids[: max(0, args.limit)]

    generated = 0
    skipped = 0
    errors = 0

    logger.info(f"Output directory: {output_dir}")
    logger.info(f"Preparing {len(selected_ids)} task(s)")

    for idx, source_id in enumerate(selected_ids, start=1):
        local_task_id = LiveSQLBenchAdapter.make_local_task_id(source_id)
        task_dir = output_dir / local_task_id

        if task_dir.exists() and not args.force:
            logger.info(
                f"[{idx}/{len(selected_ids)}] Skip {source_id} -> {local_task_id} (exists)"
            )
            skipped += 1
            continue

        try:
            adapter.generate_task_by_source_id(source_id)
            logger.info(f"[{idx}/{len(selected_ids)}] Generated {source_id} -> {local_task_id}")
            generated += 1
        except Exception as exc:
            logger.error(f"[{idx}/{len(selected_ids)}] Failed {source_id}: {exc}")
            errors += 1

    print("=" * 60)
    print("LiveSQLBench Adapter Summary")
    print(f"Generated: {generated}")
    print(f"Skipped:   {skipped}")
    print(f"Errors:    {errors}")
    print(f"Total:     {len(selected_ids)}")
    print(f"Output:    {output_dir}")
    print("=" * 60)

    if errors > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()