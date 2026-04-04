#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HARBOR_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
LIVESQLBENCH_ROOT="$(cd "${HARBOR_ROOT}/.." && pwd)"

DEFAULT_DB_ASSETS_DIR="${LIVESQLBENCH_ROOT}/evaluation/postgre_table_dumps"
DB_ASSETS_DIR="${DEFAULT_DB_ASSETS_DIR}"

DOCKERFILE_PATH="${SCRIPT_DIR}/template/environment/Dockerfile.db"
BUILD_CONTEXT="${SCRIPT_DIR}/template"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

TARGET_NAME=""

usage() {
    cat <<EOF
Usage:
  $(basename "$0") [--db-dir <path>] [--name <db_name>] [--help]

Behavior:
  1) Lists all target database images before building.
  2) With --name, targets one database (exact or unique prefix).
  3) Without --name, builds only missing images.
  4) Existing images are skipped and listed in summary.
  5) If --db-dir is not provided, uses the default LiveSQLBench dump path:
     ${DEFAULT_DB_ASSETS_DIR}

Options:
  --db-dir <path>   Path to the database dump directory.
                    This directory should contain one subdirectory per database.
  --name <db_name>  Build only one database image by exact name or unique prefix.
  --help, -h        Show this help message.

Examples:
  $(basename "$0")
  $(basename "$0") --db-dir /path/to/postgre_table_dumps
  $(basename "$0") --name solar_panel_large
  $(basename "$0") --db-dir /path/to/postgre_table_dumps --name solar_panel
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --db-dir)
            if [[ $# -lt 2 ]]; then
                echo -e "${RED}ERROR: --db-dir requires a value${NC}"
                exit 1
            fi
            DB_ASSETS_DIR="$2"
            shift 2
            ;;
        --name|--db_name)
            if [[ $# -lt 2 ]]; then
                echo -e "${RED}ERROR: $1 requires a value${NC}"
                exit 1
            fi
            TARGET_NAME="$2"
            shift 2
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        *)
            echo -e "${RED}ERROR: Unknown argument: $1${NC}"
            usage
            exit 1
            ;;
    esac
done

if [[ ! -d "${DB_ASSETS_DIR}" ]]; then
    echo -e "${RED}ERROR: Database dump directory not found: ${DB_ASSETS_DIR}${NC}"
    echo -e "${YELLOW}Please provide the correct path with --db-dir, or place the dumps under:${NC}"
    echo "  ${DEFAULT_DB_ASSETS_DIR}"
    exit 1
fi

if [[ ! -f "${DOCKERFILE_PATH}" ]]; then
    echo -e "${RED}ERROR: Dockerfile not found: ${DOCKERFILE_PATH}${NC}"
    exit 1
fi

mapfile -t ALL_DBS < <(find "${DB_ASSETS_DIR}" -mindepth 1 -maxdepth 1 -type d -printf "%f\n" | sort)
if [[ ${#ALL_DBS[@]} -eq 0 ]]; then
    echo -e "${RED}ERROR: No databases found in ${DB_ASSETS_DIR}${NC}"
    exit 1
fi

SELECTED_DBS=()
if [[ -n "${TARGET_NAME}" ]]; then
    for db in "${ALL_DBS[@]}"; do
        if [[ "${db}" == "${TARGET_NAME}" ]]; then
            SELECTED_DBS=("${db}")
            break
        fi
    done

    if [[ ${#SELECTED_DBS[@]} -eq 0 ]]; then
        mapfile -t MATCHED_DBS < <(printf "%s\n" "${ALL_DBS[@]}" | grep -E "^${TARGET_NAME}" || true)
        if [[ ${#MATCHED_DBS[@]} -eq 1 ]]; then
            SELECTED_DBS=("${MATCHED_DBS[0]}")
        elif [[ ${#MATCHED_DBS[@]} -gt 1 ]]; then
            echo -e "${RED}ERROR: Ambiguous db name '${TARGET_NAME}'. Matches:${NC}"
            for db in "${MATCHED_DBS[@]}"; do
                echo "  - ${db}"
            done
            exit 1
        else
            echo -e "${RED}ERROR: Database not found: ${TARGET_NAME}${NC}"
            exit 1
        fi
    fi
else
    SELECTED_DBS=("${ALL_DBS[@]}")
fi

echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}LiveSQLBench Database Image Builder${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""
echo -e "${YELLOW}Database dump directory:${NC}"
echo "  ${DB_ASSETS_DIR}"
echo ""
echo -e "${YELLOW}Target image names:${NC}"
for db in "${SELECTED_DBS[@]}"; do
    db_clean="${db%_template}"
    echo "  - livesqlbench-db-${db_clean}:latest"
done
echo ""

BUILT=()
SKIPPED=()
FAILED=()

TOTAL=${#SELECTED_DBS[@]}
INDEX=0
for db in "${SELECTED_DBS[@]}"; do
    INDEX=$((INDEX + 1))
    db_clean="${db%_template}"
    image="livesqlbench-db-${db_clean}:latest"

    if docker image inspect "${image}" >/dev/null 2>&1; then
        echo -e "${YELLOW}[${INDEX}/${TOTAL}] Skip existing: ${image}${NC}"
        SKIPPED+=("${image}")
        continue
    fi

    echo -e "${YELLOW}[${INDEX}/${TOTAL}] Building: ${image}${NC}"
    if docker build \
        --build-arg DATABASE_NAME="${db}" \
        -t "${image}" \
        -f "${DOCKERFILE_PATH}" \
        "${BUILD_CONTEXT}"; then
        BUILT+=("${image}")
    else
        FAILED+=("${image}")
    fi
done

echo ""
echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}Build Summary${NC}"
echo -e "${GREEN}================================================${NC}"
echo "Built   : ${#BUILT[@]}"
echo "Skipped : ${#SKIPPED[@]}"
echo "Failed  : ${#FAILED[@]}"

if [[ ${#BUILT[@]} -gt 0 ]]; then
    echo ""
    echo -e "${GREEN}Built images:${NC}"
    for image in "${BUILT[@]}"; do
        echo "  - ${image}"
    done
fi

if [[ ${#SKIPPED[@]} -gt 0 ]]; then
    echo ""
    echo -e "${YELLOW}Skipped images (already exist):${NC}"
    for image in "${SKIPPED[@]}"; do
        echo "  - ${image}"
    done
fi

if [[ ${#FAILED[@]} -gt 0 ]]; then
    echo ""
    echo -e "${RED}Failed images:${NC}"
    for image in "${FAILED[@]}"; do
        echo "  - ${image}"
    done
    exit 1
fi

echo ""
echo -e "${GREEN}Done.${NC}"