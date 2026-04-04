#!/usr/bin/env python3
"""
Harbor-compatible single-instance evaluator for LiveSQLBench.

This wrapper reuses original LiveSQLBench evaluation helpers while evaluating
exactly one instance and emitting a binary reward.
"""

from __future__ import annotations

import json
import os
import sys

import psycopg2
from psycopg2 import sql

sys.path.insert(0, "/tests/evaluator_src")

from logger import NullLogger
from db_config import set_global_db_config, get_db_config
from db_utils import (
    execute_queries,
    close_postgresql_connection,
    get_connection_for_phase,
    reset_and_restore_database,
    close_postgresql_pool,
)
from evaluation import run_preprocessing, run_evaluation_phase
from utils import split_field
from test_utils import TEST_CASE_DEFAULT
from json_repair import repair_json


class SimpleLogger(NullLogger):
    def info(self, msg):
        print(f"[evaluator] {msg}", flush=True)

    def warning(self, msg):
        print(f"[evaluator][warn] {msg}", flush=True)

    def error(self, msg):
        print(f"[evaluator][error] {msg}", flush=True)


def _admin_connect():
    cfg = get_db_config()
    return psycopg2.connect(
        host=cfg["host"],
        port=cfg["port"],
        user=cfg["user"],
        password=cfg["password"],
        dbname="postgres",
        connect_timeout=10,
    )


def _database_exists(conn, db_name: str) -> bool:
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
        return cur.fetchone() is not None


def _terminate_connections(conn, db_name: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT pg_terminate_backend(pid)
            FROM pg_stat_activity
            WHERE datname = %s AND pid <> pg_backend_pid()
            """,
            (db_name,),
        )


def _ensure_template_db(base_db: str, logger: SimpleLogger) -> str:
    template_db = f"{base_db}_template"
    admin_conn = _admin_connect()
    admin_conn.autocommit = True
    try:
        if _database_exists(admin_conn, template_db):
            return template_db

        if not _database_exists(admin_conn, base_db):
            raise RuntimeError(f"Base database not found: {base_db}")

        logger.info(f"Creating template database {template_db} from {base_db}")
        _terminate_connections(admin_conn, base_db)
        with admin_conn.cursor() as cur:
            cur.execute(
                sql.SQL("CREATE DATABASE {} WITH TEMPLATE {}").format(
                    sql.Identifier(template_db),
                    sql.Identifier(base_db),
                )
            )
        return template_db
    finally:
        admin_conn.close()


def _recreate_process_db(process_db: str, template_db: str, logger: SimpleLogger) -> None:
    admin_conn = _admin_connect()
    admin_conn.autocommit = True
    try:
        _terminate_connections(admin_conn, process_db)
        with admin_conn.cursor() as cur:
            cur.execute(sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(process_db)))
            cur.execute(
                sql.SQL("CREATE DATABASE {} WITH TEMPLATE {}").format(
                    sql.Identifier(process_db),
                    sql.Identifier(template_db),
                )
            )
        logger.info(f"Prepared process database {process_db} from {template_db}")
    finally:
        admin_conn.close()


def _drop_process_db(process_db: str) -> None:
    admin_conn = _admin_connect()
    admin_conn.autocommit = True
    try:
        _terminate_connections(admin_conn, process_db)
        with admin_conn.cursor() as cur:
            cur.execute(sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(process_db)))
    finally:
        admin_conn.close()


def evaluate_single_instance() -> int:
    with open("/tests/task_payload.json", "r", encoding="utf-8") as f:
        data_item = json.load(f)
    with open("/app/pred.json", "r", encoding="utf-8", errors="replace") as f:
        pred_text = f.read()

    pred_data = repair_json(pred_text)
    pred_data = json.loads(pred_data)

    required_fields = ["selected_database", "preprocess_sql", "sol_sql"]
    missing_fields = [field for field in required_fields if field not in data_item]
    if missing_fields:
        print(f"[evaluator] FAIL: Missing fields: {', '.join(missing_fields)}")
        return 0

    pred_instance_id = pred_data.get("instance_id")
    predicted_sql_list = pred_data.get("predicted_sql")
    if not isinstance(predicted_sql_list, list) or len(predicted_sql_list) == 0:
        print("[evaluator] FAIL: /app/pred.json missing non-empty 'predicted_sql' list")
        return 0

    logger = SimpleLogger()

    instance_id = data_item.get("instance_id", "unknown")
    base_db = data_item["selected_database"]
    process_db = f"{base_db}_process_1"
    pg_password = os.environ.get("PGPASSWORD", "123123")

    if pred_instance_id and pred_instance_id != instance_id:
        logger.warning(
            f"pred.json instance_id ({pred_instance_id}) != task instance_id ({instance_id})"
        )

    preprocess_sql = split_field(data_item, "preprocess_sql")
    sol_sqls = split_field(data_item, "sol_sql")
    pred_sqls = predicted_sql_list

    test_cases = data_item.get("test_cases", [])
    conditions = data_item.get("conditions", {})
    category = data_item.get("category", "Query")
    efficiency = data_item.get("efficiency", False)

    kwargs = {}
    if category == "Query":
        test_cases = [TEST_CASE_DEFAULT]
        kwargs = {"conditions": conditions}

    logger.info(f"Instance: {instance_id}")
    logger.info(f"Base DB: {base_db}")
    logger.info(f"Process DB: {process_db}")

    template_db = _ensure_template_db(base_db, logger)
    _recreate_process_db(process_db, template_db, logger)

    # Explicit reset before evaluation to match original reset semantics.
    reset_and_restore_database(process_db, pg_password, logger)

    evaluation_conn = None
    evaluation_phase_execution_error = False
    evaluation_phase_timeout_error = False
    evaluation_phase_assertion_error = False
    try:
        try:
            evaluation_conn = get_connection_for_phase(process_db, logger)
            run_preprocessing(preprocess_sql, process_db, logger, evaluation_conn)

            (
                evaluation_phase_execution_error,
                evaluation_phase_timeout_error,
                evaluation_phase_assertion_error,
                _passed_count,
                _failed_tests,
            ) = run_evaluation_phase(
                pred_sqls,
                sol_sqls,
                process_db,
                test_cases,
                logger,
                evaluation_conn,
                efficiency,
                kwargs,
            )
        except Exception as exc:
            logger.error(f"Unexpected evaluation exception: {exc}")

        reward = 1 if not (
            evaluation_phase_execution_error
            or evaluation_phase_timeout_error
            or evaluation_phase_assertion_error
        ) else 0
        return reward
    finally:
        try:
            if evaluation_conn is not None:
                close_postgresql_connection(process_db, evaluation_conn)
        except Exception:
            pass
        try:
            close_postgresql_pool(process_db)
        except Exception:
            pass
        try:
            _drop_process_db(process_db)
        except Exception:
            pass


def main() -> int:
    set_global_db_config(
        host=os.environ.get("PGHOST", "postgresql"),
        port=int(os.environ.get("PGPORT", 5432)),
        user=os.environ.get("PGUSER", "root"),
        password=os.environ.get("PGPASSWORD", "123123"),
    )

    reward = evaluate_single_instance()

    os.makedirs("/logs/verifier", exist_ok=True)
    with open("/logs/verifier/reward.txt", "w", encoding="utf-8") as f:
        f.write(str(reward))
    print(f"[evaluator] Reward written: {reward}")
    return 0 if reward == 1 else 1


if __name__ == "__main__":
    sys.exit(main())