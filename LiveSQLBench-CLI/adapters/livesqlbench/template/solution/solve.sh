#!/bin/bash
set -euo pipefail

echo "[solve.sh] Starting LiveSQLBench oracle solution..."

# Read the solution SQL from task payload and write to pred.json
python3 - << 'PYTHON_SCRIPT'
import json

# Load task payload
with open('/solution/task_payload.json', 'r') as f:
    task_data = json.load(f)

# Extract sol_sql (it's a list, take the first one)
sol_sql_list = task_data.get("sol_sql", [])
if not sol_sql_list:
    print("[solve.sh] ERROR: No solution SQL found in task payload")
    exit(1)

# sol_sql = sol_sql_list[0]
instance_id = task_data.get("instance_id", "unknown")

# Write oracle SQL to /app/pred.json in the expected format
with open('/app/pred.json', 'w') as f:
    json.dump({
        'instance_id': instance_id,
        'predicted_sql': sol_sql_list
    }, f)

print(f"[solve.sh] Oracle solution written to /app/pred.json")
sol_sql_preview = "\n".join(sol_sql_list)
print(f"[solve.sh] SQL: {sol_sql_preview}...")
PYTHON_SCRIPT

echo "[solve.sh] Oracle solution complete!"
echo "Solution completed!"