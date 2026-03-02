#!/bin/bash

set -euo pipefail

# Resolve directories
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
EVAL_BASE_DIR="$REPO_ROOT/evaluation/large_outputs"
INTER_OUTPUT_DIR="$EVAL_BASE_DIR/inter_output"
FINAL_OUTPUT_DIR="$EVAL_BASE_DIR/final_output"
RESULTS_DIR="$EVAL_BASE_DIR/eval_results"
DATASET_NAME="livesqlbench-large-v1"

# DB settings
DB_HOST="livesqlbench_postgresql_large_v1"
DB_PORT=5432
# DB_HOST="localhost"
# DB_PORT=5434

# Evaluation settings
LOGGING="true"

# Models to evaluate (use display names as they appear in filenames).
# Leave empty (MODELS=()) to process all files in INTER_OUTPUT_DIR.
MODELS=(
    # "claude-4-6"
    "gpt-5.3-codex"
)

# Python entrypoints
POST_PROCESS_PY="$REPO_ROOT/baseline/src/post_process.py"
EVALUATION_PY="$REPO_ROOT/evaluation/src/evaluation.py"

# Create output directories if they don't exist
mkdir -p "$FINAL_OUTPUT_DIR"
mkdir -p "$RESULTS_DIR"

echo "Processing and evaluating JSONL files from: $INTER_OUTPUT_DIR"

# Build file list
shopt -s nullglob
jsonl_files=()

if [ ${#MODELS[@]} -gt 0 ]; then
    echo "Models specified in script: ${MODELS[*]}"
    for model_display in "${MODELS[@]}"; do
        collo_file="$INTER_OUTPUT_DIR/${DATASET_NAME}-input_colloquial_query_${model_display}_prediction.jsonl"
        normal_file="$INTER_OUTPUT_DIR/${DATASET_NAME}-input_normal_query_${model_display}_prediction.jsonl"

        if [ -f "$collo_file" ]; then
            jsonl_files+=("$collo_file")
        else
            echo "Warning: Missing colloquial file for model ${model_display}: $(basename "$collo_file")"
        fi

        if [ -f "$normal_file" ]; then
            jsonl_files+=("$normal_file")
        else
            echo "Warning: Missing normal file for model ${model_display}: $(basename "$normal_file")"
        fi
    done
else
    jsonl_files=("$INTER_OUTPUT_DIR"/*.jsonl)
fi
shopt -u nullglob

if [ ${#jsonl_files[@]} -eq 0 ]; then
    echo "No JSONL files found in $INTER_OUTPUT_DIR"
    exit 0
fi

for input_file in "${jsonl_files[@]}"; do
    base_name="$(basename "$input_file" .jsonl)"

    echo "----------------------------------------"
    echo "Post-processing: $base_name"

    output_processed="$FINAL_OUTPUT_DIR/${base_name}_final_output.jsonl"

    python3 "$POST_PROCESS_PY" \
        --input_path "$input_file" \
        --output_path "$output_processed"

    echo "Evaluating: $base_name"
    log_file="$RESULTS_DIR/${base_name}_eval_results.log"
    python3 "$EVALUATION_PY" --jsonl_file "$output_processed" --db_host "$DB_HOST" --db_port "$DB_PORT" --output_dir "$RESULTS_DIR" --logging "$LOGGING" 2>&1 | tee "$log_file"

    echo "Completed: $base_name"
done

echo "----------------------------------------"
echo "All files processed and evaluated. Results in:"
echo "  Final outputs: $FINAL_OUTPUT_DIR"
echo "  Eval logs:     $RESULTS_DIR"
