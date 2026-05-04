#!/bin/bash
set -euo pipefail

export PGDATA="${PGDATA:-/var/lib/postgresql/livesqlbench-data}"
export SELECTED_DB_FILE="${SELECTED_DB_FILE:-/opt/livesqlbench/db_seed/db_name.txt}"
export DB_DUMP_DIR="${DB_DUMP_DIR:-/opt/livesqlbench/db_seed/db_dump}"
export PREPROCESS_SQL_FILE="${PREPROCESS_SQL_FILE:-/opt/livesqlbench/db_seed/preprocess.sql}"
export TABLE_ORDER_FILE="${TABLE_ORDER_FILE:-/opt/livesqlbench/db_seed/table_order.txt}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=livesqlbench-init-db.sh
source "${SCRIPT_DIR}/livesqlbench-init-db.sh"

selected_database="$(read_selected_database)"

mkdir -p "${PGDATA}"
chmod 700 "${PGDATA}"

initdb -D "${PGDATA}" --username=postgres --auth-local=trust --auth-host=scram-sha-256
{
    echo "listen_addresses = '*'"
    echo "port = 5432"
} >> "${PGDATA}/postgresql.conf"
echo "host all all all scram-sha-256" >> "${PGDATA}/pg_hba.conf"

pg_ctl -D "${PGDATA}" -o "-c listen_addresses=''" -w start
cleanup() {
    pg_ctl -D "${PGDATA}" -m fast -w stop >/dev/null 2>&1 || true
}
trap cleanup EXIT

psql -v ON_ERROR_STOP=1 --username postgres --dbname postgres <<EOSQL
DO \$\$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '${POSTGRES_USER}') THEN
        EXECUTE format('CREATE ROLE %I WITH LOGIN SUPERUSER PASSWORD %L', '${POSTGRES_USER}', '${POSTGRES_PASSWORD}');
    ELSE
        EXECUTE format('ALTER ROLE %I WITH LOGIN SUPERUSER PASSWORD %L', '${POSTGRES_USER}', '${POSTGRES_PASSWORD}');
    END IF;
END
\$\$;
EOSQL

create_template_database "${selected_database}"

trap - EXIT
cleanup

echo "[bootstrap-db-image.sh] Preloaded PostgreSQL template ready for ${selected_database}"
