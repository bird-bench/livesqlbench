from __future__ import annotations

import copy
import json
import re
import shutil
from pathlib import Path
from typing import Any

TEMPLATE_DIR = Path(__file__).parent / "template"


class LiveSQLBenchAdapter:
    """Adapter that converts LiveSQLBench records into Harbor task directories."""

    NAME = "livesqlbench"

    def __init__(
        self,
        task_dir: Path,
        data_jsonl: Path,
        data_root: Path,
        gt_jsonl: Path | None = None,
        template_dir: Path | None = None,
        eval_src_dir: Path | None = None,
        db_dump_root: Path | None = None,
        agent_image: str = "livesqlbench-main-openhands:latest",
    ) -> None:
        self.task_dir = Path(task_dir)
        self.data_root = Path(data_root)
        self.template_dir = Path(template_dir) if template_dir else TEMPLATE_DIR
        self.task_dir.mkdir(parents=True, exist_ok=True)
        self.agent_image = agent_image

        if not self.data_root.exists():
            raise FileNotFoundError(f"data_root not found: {self.data_root}")
        if not self.template_dir.exists():
            raise FileNotFoundError(f"template_dir not found: {self.template_dir}")

        self.eval_src_dir = (
            Path(eval_src_dir)
            if eval_src_dir is not None
            else self.data_root.parent.parent / "evaluation" / "src"
        )
        self.db_dump_root = (
            Path(db_dump_root)
            if db_dump_root is not None
            else self.data_root.parent.parent / "evaluation" / "postgre_table_dumps"
        )

        if not self.eval_src_dir.exists():
            raise FileNotFoundError(f"evaluator source directory not found: {self.eval_src_dir}")
        if not self.db_dump_root.exists():
            raise FileNotFoundError(f"db dump root directory not found: {self.db_dump_root}")

        data_records = self._load_jsonl_records(Path(data_jsonl))
        self.source_ids, self.source_index = self._build_source_index(data_records)
        self.patch_index = self._load_optional_patch_index(gt_jsonl)

    @staticmethod
    def _load_jsonl_records(path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            raise FileNotFoundError(f"jsonl file not found: {path}")

        records: list[dict[str, Any]] = []
        with path.open("r", encoding="utf-8") as file:
            for line_no, line in enumerate(file, start=1):
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    record = json.loads(stripped)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"Invalid JSON at {path}:{line_no}: {exc}") from exc
                if not isinstance(record, dict):
                    raise ValueError(f"Record at {path}:{line_no} must be a JSON object")
                records.append(record)

        return records

    @staticmethod
    def _build_source_index(
        data_records: list[dict[str, Any]],
    ) -> tuple[list[str], dict[str, dict[str, Any]]]:
        source_ids: list[str] = []
        source_index: dict[str, dict[str, Any]] = {}

        for idx, record in enumerate(data_records):
            raw_id = record.get("instance_id")
            if not raw_id:
                raw_id = f"record-{idx}"
            source_id = str(raw_id)
            if source_id in source_index:
                raise ValueError(f"Duplicate instance_id found: {source_id}")
            source_ids.append(source_id)
            source_index[source_id] = record

        return source_ids, source_index

    @staticmethod
    def _load_optional_patch_index(gt_jsonl: Path | None) -> dict[str, dict[str, Any]]:
        if gt_jsonl is None:
            return {}

        gt_path = Path(gt_jsonl)
        if not gt_path.exists():
            return {}

        patch_index: dict[str, dict[str, Any]] = {}
        with gt_path.open("r", encoding="utf-8") as file:
            for line_no, line in enumerate(file, start=1):
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    record = json.loads(stripped)
                except json.JSONDecodeError as exc:
                    raise ValueError(
                        f"Invalid JSON in optional patch file at {gt_path}:{line_no}: {exc}"
                    ) from exc
                source_id = record.get("instance_id")
                if not source_id:
                    continue
                patch_index[str(source_id)] = record

        return patch_index

    def get_all_source_ids(self) -> list[str]:
        return list(self.source_ids)

    @staticmethod
    def make_local_task_id(source_id: str) -> str:
        normalized = source_id.lower().replace("_", "-")
        normalized = re.sub(r"[^a-z0-9\-]", "-", normalized)
        normalized = re.sub(r"\-+", "-", normalized).strip("-")
        return f"livesqlbench-{normalized}"

    def generate_task_by_source_id(self, source_id: str) -> str:
        if source_id not in self.source_index:
            raise KeyError(f"Unknown source_id: {source_id}")

        record = self._resolve_task_record(source_id)
        local_task_id = self.make_local_task_id(source_id)
        self._prepare_task_directory(local_task_id, record)
        return local_task_id

    def generate_all_tasks(self, limit: int | None = None) -> list[str]:
        target_ids = self.get_all_source_ids()
        if limit is not None:
            target_ids = target_ids[: max(0, limit)]

        generated: list[str] = []
        for source_id in target_ids:
            generated.append(self.generate_task_by_source_id(source_id))
        return generated

    def _resolve_task_record(self, source_id: str) -> dict[str, Any]:
        base = copy.deepcopy(self.source_index[source_id])
        patch = self.patch_index.get(source_id)
        if patch:
            return self._merge_optional_patch(base, patch)
        return base

    @staticmethod
    def _merge_optional_patch(
        base_record: dict[str, Any], patch_record: dict[str, Any]
    ) -> dict[str, Any]:
        merged = copy.deepcopy(base_record)
        for key, value in patch_record.items():
            if key == "instance_id":
                continue
            if value is None:
                continue
            merged[key] = value
        return merged

    def _prepare_task_directory(self, local_task_id: str, record: dict[str, Any]) -> Path:
        output_dir = self.task_dir / local_task_id
        if output_dir.exists():
            shutil.rmtree(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        self._copy_template(output_dir)
        self._hide_unused_environment_files(output_dir)
        self._configure_docker_compose(output_dir, record)
        self._write_instruction(output_dir, record)
        self._write_task_toml(output_dir, record)
        self._write_solution(output_dir, record)
        self._write_task_payload(output_dir, record)
        self._copy_eval_src(output_dir)
        self._copy_db_assets(output_dir, record)
        self._copy_documents(output_dir, record)
        return output_dir

    def _copy_template(self, output_dir: Path) -> None:
        for item in self.template_dir.iterdir():
            # documents are rendered separately into environment/documents
            if item.name == "documents":
                continue

            destination = output_dir / item.name
            if item.is_dir():
                shutil.copytree(item, destination, dirs_exist_ok=True)
            else:
                shutil.copy2(item, destination)

    def _hide_unused_environment_files(self, output_dir: Path) -> None:
        """Keep host-only build assets out of generated instance directories."""
        dockerfile_db = output_dir / "environment" / "Dockerfile.db"
        if dockerfile_db.exists():
            dockerfile_db.unlink()

    def _configure_docker_compose(self, output_dir: Path, record: dict[str, Any]) -> None:
        """Configure docker-compose.yaml with the correct database image, main image name, and paths."""
        docker_compose_path = output_dir / "environment" / "docker-compose.yaml"
        if not docker_compose_path.exists():
            return

        selected_database = str(record.get("selected_database", ""))
        if not selected_database:
            raise ValueError("selected_database is missing from task record")

        # Read the template docker-compose.yaml
        content = docker_compose_path.read_text(encoding="utf-8")

        content = content.replace(
            "image: livesqlbench-main-openhands:latest",
            f"image: {self.agent_image}",
            1,
        )
        # Replace the default database image with the actual database-specific image
        # ${LSB_PG_IMAGE:-livesqlbench-postgresql:latest}
        # becomes: livesqlbench-db-<database>:latest
        db_image = f"livesqlbench-db-{selected_database}:latest"
        content = content.replace(
            "${LSB_PG_IMAGE:-livesqlbench-postgresql:latest}",
            db_image
        )

        # Keep db_assets mount as per-instance relative path:
        # ${LSB_DB_ASSETS_PATH:-.}/db_assets -> environment/db_assets
        # Actual files are prepared by _copy_db_assets() into each instance folder.

        # Write back the updated content
        docker_compose_path.write_text(content, encoding="utf-8")

    def _build_instruction(self, record: dict[str, Any]) -> str:
        source_id = str(record.get("instance_id", "unknown"))
        selected_database = str(record.get("selected_database", "unknown"))
        query = str(record.get("query", "")).strip()
        normal_query = str(record.get("normal_query", "")).strip()
        category = str(record.get("category", "Query"))
        conditions = record.get("conditions", {})
        external_knowledge = record.get("external_knowledge", [])

        db_dir = self.data_root / selected_database
        schema_path = db_dir / f"{selected_database}_schema.txt"
        kb_path = db_dir / f"{selected_database}_kb.jsonl"
        column_meaning_path = db_dir / f"{selected_database}_column_meaning_base.json"

        return (
            f"# LiveSQLBench Task: {source_id}\n\n"
            f"## User Query\n{query}\n\n"
            f"## Normalized Query\n{normal_query}\n\n"
            f"## Database\n- selected_database: {selected_database}\n\n"
            f"## Task Metadata\n"
            f"- category: {category}\n"
            f"- high_level: {record.get('high_level')}\n"
            f"- conditions: {json.dumps(conditions, ensure_ascii=False)}\n"
            f"- external_knowledge: {json.dumps(external_knowledge, ensure_ascii=False)}\n\n"
            f"## Reference Assets\n"
            f"- schema: {schema_path.name if schema_path.exists() else 'N/A'}\n"
            f"- kb: {kb_path.name if kb_path.exists() else 'N/A'}\n"
            f"- column_meaning: {column_meaning_path.name if column_meaning_path.exists() else 'N/A'}\n\n"
            "## Objective\n"
            "Write SQL that answers the user query in the given PostgreSQL setting.\n"
        )

    def _write_instruction(self, output_dir: Path, record: dict[str, Any]) -> None:
        """
        Render template/documents/README_TASK.md into instruction.md.

        This replaces the previous handwritten instruction builder.
        """
        template_readme = self.template_dir / "documents" / "README_TASK.md"
        if not template_readme.exists():
            raise FileNotFoundError(f"README task template not found: {template_readme}")

        rendered = self._render_document_template(
            template_readme.read_text(encoding="utf-8"),
            record,
        )
        instruction_path = output_dir / "instruction.md"
        instruction_path.write_text(rendered, encoding="utf-8")

    def _write_task_toml(self, output_dir: Path, record: dict[str, Any]) -> None:
        high_level = bool(record.get("high_level", False))
        category = str(record.get("category", "Query"))
        difficulty = "hard" if high_level else "medium"
        category_tag = "management" if category.lower() == "management" else "query"

        content = (
            'version = "1.0"\n\n'
            "[metadata]\n"
            'author_name = "LiveSQLBench Team"\n'
            'author_email = "bird.bench25@gmail.com"\n'
            f'difficulty = "{difficulty}"\n'
            'category = "text-to-sql"\n'
            f'tags = ["postgresql", "livesqlbench", "{category_tag}"]\n\n'
            "[verifier]\n"
            "timeout_sec = 1200.0\n\n"
            "[agent]\n"
            "timeout_sec = 1800.0\n\n"
            "[environment]\n"
            "build_timeout_sec = 1200.0\n"
            f'docker_image = "{self.agent_image}"\n'
            "cpus = 2\n"
            "memory_mb = 4096\n"
            "storage_mb = 20480\n"
        )
        (output_dir / "task.toml").write_text(content, encoding="utf-8")

    def _write_solution(self, output_dir: Path, record: dict[str, Any]) -> None:
        # Generate solve.sh that reads from task_payload.json and outputs pred.json
        solve_script = (
            "#!/bin/bash\n"
            "set -euo pipefail\n\n"
            "echo \"[solve.sh] Starting LiveSQLBench oracle solution...\"\n\n"
            "# Read the solution SQL from task payload and write to pred.json\n"
            "python3 - << 'PYTHON_SCRIPT'\n"
            "import json\n\n"
            "# Load task payload\n"
            "with open('/solution/task_payload.json', 'r') as f:\n"
            "    task_data = json.load(f)\n\n"
            "# Extract sol_sql (it's a list, take the first one)\n"
            "sol_sql_list = task_data.get(\"sol_sql\", [])\n"
            "if not sol_sql_list:\n"
            "    print(\"[solve.sh] ERROR: No solution SQL found in task payload\")\n"
            "    exit(1)\n\n"
            "instance_id = task_data.get(\"instance_id\", \"unknown\")\n\n"
            "# Write oracle SQL to /app/pred.json in the expected format\n"
            "with open('/app/pred.json', 'w') as f:\n"
            "    json.dump({\n"
            "        'instance_id': instance_id,\n"
            "        'predicted_sql': sol_sql_list\n"
            "    }, f)\n\n"
            "print(f\"[solve.sh] Oracle solution written to /app/pred.json\")\n"
            "sol_sql_preview = \"\\n\".join(sol_sql_list)\nprint(f\"[solve.sh] SQL: {sol_sql_preview}...\")\n"
            "PYTHON_SCRIPT\n\n"
            "echo \"[solve.sh] Oracle solution complete!\"\n"
            "echo \"Solution completed!\"\n"
        )

        solve_path = output_dir / "solution" / "solve.sh"
        solve_path.parent.mkdir(parents=True, exist_ok=True)
        solve_path.write_text(solve_script, encoding="utf-8")
        solve_path.chmod(0o755)

    def _write_task_payload(self, output_dir: Path, record: dict[str, Any]) -> None:
        payload_path = output_dir / "tests" / "task_payload.json"
        payload_path.parent.mkdir(parents=True, exist_ok=True)
        payload_path.write_text(
            json.dumps(record, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        payload_path = output_dir / "solution" / "task_payload.json"
        payload_path.parent.mkdir(parents=True, exist_ok=True)
        payload_path.write_text(
            json.dumps(record, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _copy_eval_src(self, output_dir: Path) -> None:
        destination = output_dir / "tests" / "evaluator_src"
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(self.eval_src_dir, destination)

    @staticmethod
    def _to_sql_blob(value: Any) -> str:
        if isinstance(value, list):
            return "\n\n".join(str(item) for item in value if str(item).strip())
        if value is None:
            return ""
        return str(value)

    def _copy_db_assets(self, output_dir: Path, record: dict[str, Any]) -> None:
        selected_database = str(record.get("selected_database", ""))
        if not selected_database:
            raise ValueError("selected_database is missing from task record")

        source = self.data_root / selected_database
        if not source.exists():
            raise FileNotFoundError(f"Database asset directory not found: {source}")

        dump_source = self.db_dump_root / f"{selected_database}_template"
        if not dump_source.exists():
            raise FileNotFoundError(f"Database dump directory not found: {dump_source}")

        destination = output_dir / "environment" / "db_assets"
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(source, destination)

        db_name_marker = destination / "db_name.txt"
        db_name_marker.write_text(f"{selected_database}\n", encoding="utf-8")

        preprocess_sql_blob = self._to_sql_blob(record.get("preprocess_sql", ""))
        preprocess_sql_path = destination / "preprocess.sql"
        preprocess_sql_path.write_text(preprocess_sql_blob + "\n", encoding="utf-8")

        dump_destination = destination / "db_dump"
        shutil.copytree(dump_source, dump_destination)

        order_source = self.db_dump_root / f"{selected_database}_table_orders.txt"
        order_destination = destination / "table_order.txt"
        if order_source.exists():
            shutil.copy2(order_source, order_destination)

    def _document_template_context(self, record: dict[str, Any]) -> dict[str, str]:
        instance_id = str(record.get("instance_id", ""))
        db_name = str(record.get("selected_database", ""))
        user_query = str(record.get("query", ""))

        return {
            "instance_id": instance_id,
            "db_name": db_name,
            "exact_db_name": db_name,
            "user_query": user_query,
        }

    def _render_document_template(self, template_text: str, record: dict[str, Any]) -> str:
        context = self._document_template_context(record)
        try:
            return template_text.format(**context)
        except KeyError as exc:
            missing_key = exc.args[0]
            raise ValueError(
                f"Missing placeholder value '{missing_key}' while rendering document template"
            ) from exc

    def _copy_documents(self, output_dir: Path, record: dict[str, Any]) -> None:
        template_documents_dir = self.template_dir / "documents"
        if not template_documents_dir.exists():
            raise FileNotFoundError(
                f"Template documents directory not found: {template_documents_dir}"
            )

        destination = output_dir / "environment" / "documents"
        if destination.exists():
            shutil.rmtree(destination)
        destination.mkdir(parents=True, exist_ok=True)

        for item in template_documents_dir.rglob("*"):
            relative = item.relative_to(template_documents_dir)
            target = destination / relative

            if item.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue

            target.parent.mkdir(parents=True, exist_ok=True)

            # Render all text-based template docs
            if item.suffix.lower() in {".md", ".txt", ".sh", ".sql", ".json", ".yaml", ".yml"}:
                content = item.read_text(encoding="utf-8")
                rendered = self._render_document_template(content, record)
                target.write_text(rendered, encoding="utf-8")

                # keep shell scripts executable
                if item.suffix.lower() == ".sh":
                    target.chmod(0o755)
            else:
                shutil.copy2(item, target)