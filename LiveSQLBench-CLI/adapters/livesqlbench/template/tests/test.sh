#!/bin/bash
set -euo pipefail

mkdir -p /logs/verifier

echo "[test.sh] Starting LiveSQLBench evaluation..." | tee /logs/verifier/test.log

echo "[test.sh] Waiting for PostgreSQL..." | tee -a /logs/verifier/test.log
max_retries=600
retry_count=0
while ! python3 - <<'PY' >/dev/null 2>&1
import os
import socket

host = os.environ.get("PGHOST", "postgresql")
port = int(os.environ.get("PGPORT", "5432"))

try:
    with socket.create_connection((host, port), timeout=2):
        pass
except Exception:
    raise SystemExit(1)
PY
do
  retry_count=$((retry_count + 1))
  if [ $retry_count -ge $max_retries ]; then
    echo "[test.sh] ERROR: PostgreSQL did not become ready in time" | tee -a /logs/verifier/test.log
    echo "0.0" > /logs/verifier/reward.txt
    exit 1
  fi
  echo "[test.sh] Waiting for PostgreSQL (attempt $retry_count/$max_retries)..." | tee -a /logs/verifier/test.log
  sleep 2
done
echo "[test.sh] PostgreSQL is ready!" | tee -a /logs/verifier/test.log

if [ ! -f /app/pred.json ]; then
  echo "[test.sh] ERROR: Agent output not found at /app/pred.json" | tee -a /logs/verifier/test.log
  echo "0.0" > /logs/verifier/reward.txt
  exit 1
fi

echo "[test.sh] Found agent output: /app/pred.json" | tee -a /logs/verifier/test.log

{
  echo "===== DEBUG INFO ====="
  echo "pwd=$(pwd)"
  echo "PGHOST=${PGHOST:-}"
  echo "PGPORT=${PGPORT:-}"
  echo "--- /app ---"
  ls -l /app || true
  echo "--- pred.json ---"
  cat /app/pred.json || true
} > /logs/verifier/debug.txt 2>&1

echo "[test.sh] Running evaluator..." | tee -a /logs/verifier/test.log
if ! python3 /tests/evaluator.py > /logs/verifier/evaluator_stdout.txt 2> /logs/verifier/evaluator_stderr.txt; then
  echo "[test.sh] ERROR: Evaluator crashed" | tee -a /logs/verifier/test.log
  echo "0.0" > /logs/verifier/reward.txt
  exit 1
fi

if [ -f /logs/verifier/reward.txt ]; then
  reward=$(cat /logs/verifier/reward.txt)
  if [ "$reward" = "1" ] || [ "$reward" = "1.0" ]; then
    echo "[test.sh] ✓ PASSED" | tee -a /logs/verifier/test.log
  else
    echo "[test.sh] ✗ FAILED (reward=$reward)" | tee -a /logs/verifier/test.log
  fi
else
  echo "[test.sh] ERROR: Evaluator did not produce reward.txt" | tee -a /logs/verifier/test.log
  echo "0.0" > /logs/verifier/reward.txt
  exit 1
fi

echo "[test.sh] Evaluation complete!" | tee -a /logs/verifier/test.log