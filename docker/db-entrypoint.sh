#!/usr/bin/env bash
set -euo pipefail

export PGDATA="${PGDATA:-/var/lib/postgresql/data}"
export PATH="${PATH}:/usr/pgsql-18/bin"

pg_ctl -D "$PGDATA" -w start

db_exists="$(psql -U postgres -d postgres -Atqc "SELECT 1 FROM pg_database WHERE datname='cot'" || true)"
if [[ "$db_exists" != "1" ]]; then
  cd /opt/tak/db-utils
  set +e
  ./takserver-setup-db.sh cot
  setup_status=$?
  set -e
  db_exists="$(psql -U postgres -d postgres -Atqc "SELECT 1 FROM pg_database WHERE datname='cot'" || true)"
  if [[ "$db_exists" != "1" ]]; then
    echo "TAK database initialization failed with status ${setup_status}." >&2
    exit "${setup_status:-1}"
  fi
else
  cp /opt/tak/db-utils/pg_hba.conf "$(psql -U postgres -d postgres -Atqc 'SHOW hba_file')"
  pg_ctl -D "$PGDATA" reload
  cd /opt/tak/db-utils
  java -jar SchemaManager.jar upgrade
fi

pg_ctl -D "$PGDATA" -m fast -w stop
exec postgres -D "$PGDATA"
