#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

HARBOR_BIN="${REPO_ROOT}/LiveSQLBench-CLI/.venv-harbor/bin/harbor"
KEY_FILE="${LLM_KEY_FILE:-${REPO_ROOT}/key.txt}"
DEFAULT_DATASET="${REPO_ROOT}/LiveSQLBench-CLI/datasets/livesqlbench-large"

DATASET_PATH="${1:-${DEFAULT_DATASET}}"
if [[ $# -gt 0 ]]; then
  shift
fi

MODEL="${MODEL:-openai/gpt-5.5}"
REASONING_EFFORT="${REASONING_EFFORT:-low}"
N_CONCURRENT="${N_CONCURRENT:-6}"
MAX_ITERATIONS="${MAX_ITERATIONS:-50}"
AGENT_TIMEOUT_MULTIPLIER="${AGENT_TIMEOUT_MULTIPLIER:-0.333}"
JOB_NAME="${JOB_NAME:-livesqlbench-large-openhands-gpt55-low-n${N_CONCURRENT}-$(date +%Y%m%d-%H%M%S)}"
PROXY_URL="${PROXY_URL:-http://127.0.0.1:7897}"
# Set USE_PROXY=1 (and optionally PROXY_URL) only if you route traffic through a local proxy.
USE_PROXY="${USE_PROXY:-0}"

if [[ ! -x "${HARBOR_BIN}" ]]; then
  echo "Missing harbor binary: ${HARBOR_BIN}" >&2
  exit 1
fi

if [[ ! -f "${KEY_FILE}" ]]; then
  echo "Missing key file: ${KEY_FILE}" >&2
  exit 1
fi

if [[ ! -d "${DATASET_PATH}" ]]; then
  echo "Missing dataset path: ${DATASET_PATH}" >&2
  exit 1
fi

export PATH="${REPO_ROOT}/LiveSQLBench-CLI/.venv-harbor/bin:${PATH}"
export LLM_API_KEY="$(tr -d '\r\n ' < "${KEY_FILE}")"
export OPENAI_API_KEY="${LLM_API_KEY}"

if [[ "${USE_PROXY}" != "0" ]]; then
  export http_proxy="${PROXY_URL}"
  export https_proxy="${PROXY_URL}"
  export HTTP_PROXY="${PROXY_URL}"
  export HTTPS_PROXY="${PROXY_URL}"
fi

unset all_proxy
unset ALL_PROXY

echo "Dataset: ${DATASET_PATH}"
echo "Job name: ${JOB_NAME}"
echo "Model: ${MODEL}"
echo "Reasoning effort: ${REASONING_EFFORT}"
echo "Concurrency: ${N_CONCURRENT}"
echo "Max iterations: ${MAX_ITERATIONS}"
echo "Agent timeout multiplier: ${AGENT_TIMEOUT_MULTIPLIER}"
if [[ "${USE_PROXY}" != "0" ]]; then
  echo "HTTP(S) proxy: ${PROXY_URL}"
else
  echo "HTTP(S) proxy: disabled"
fi

exec "${HARBOR_BIN}" run \
  -p "${DATASET_PATH}" \
  -a openhands \
  -m "${MODEL}" \
  -n "${N_CONCURRENT}" \
  --job-name "${JOB_NAME}" \
  --ak "reasoning_effort=${REASONING_EFFORT}" \
  --ae "MAX_ITERATIONS=${MAX_ITERATIONS}" \
  --agent-timeout-multiplier "${AGENT_TIMEOUT_MULTIPLIER}" \
  "$@"
