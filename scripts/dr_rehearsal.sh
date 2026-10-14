#!/usr/bin/env bash
# Disaster-recovery rehearsal on a throw-away local PostgreSQL: empty database -> migrations 0001..000N -> restore a JSON backup
# -> compare per-table row counts with the backup. Usage: scripts/dr_rehearsal.sh private/backups/<file>.json
# It stubs only what Supabase provides (roles, auth.users, auth.uid()). Nothing here touches the real project.
set -euo pipefail
BACKUP="$(readlink -f "${1:?backup json required}")"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PGBIN="$(ls -d /usr/lib/postgresql/*/bin | tail -1)"
DIR="$(mktemp -d)"; PORT=54329
trap 'su postgres -s /bin/bash -c "$PGBIN/pg_ctl -D $DIR/data stop -m immediate" >/dev/null 2>&1 || true; rm -rf "$DIR"' EXIT
chown -R postgres "$DIR" 2>/dev/null || true
run_pg() { su postgres -s /bin/bash -c "$*"; }
run_pg "$PGBIN/initdb -D $DIR/data -A trust >/dev/null"
run_pg "$PGBIN/pg_ctl -D $DIR/data -o '-p $PORT -k $DIR' -l $DIR/log -w start >/dev/null"
PSQL="psql -h $DIR -p $PORT -U postgres -v ON_ERROR_STOP=1 -q"
$PSQL -d postgres -c "create database nm" 
$PSQL -d nm <<'SQL'
create role anon nologin; create role authenticated nologin; create role service_role nologin bypassrls;
create schema auth; create table auth.users(id uuid primary key, email text, raw_user_meta_data jsonb);
create function auth.uid() returns uuid language sql stable as $$ select null::uuid $$;
create function auth.jwt() returns jsonb language sql stable as $$ select '{}'::jsonb $$;
SQL
for f in "$ROOT"/database/migrations/*.sql; do echo "migration $(basename "$f")"; $PSQL -d nm -f "$f" >/dev/null; done
python3 - "$BACKUP" "$DIR" <<'PY'
import json, sys, pathlib
data = json.load(open(sys.argv[1]))["tables"]
d = pathlib.Path(sys.argv[2])
for t, rows in data.items():
    (d / f"{t}.json").write_text(json.dumps(rows))
(d / "tables.txt").write_text("\n".join(data))
PY
chown -R postgres "$DIR" 2>/dev/null || true
$PSQL -d nm -c "set session_replication_role = replica; insert into auth.users(id) select (j->>'id')::uuid from json_array_elements(pg_read_file('$DIR/profiles.json')::json) j"
{
  echo "set session_replication_role = replica;"
  while read -r t; do echo "insert into public.$t select * from json_populate_recordset(null::public.$t, pg_read_file('$DIR/$t.json')::json) on conflict do nothing;"; done < <(cat "$DIR/tables.txt"; echo)
} > "$DIR/restore.sql"
$PSQL -d nm -f "$DIR/restore.sql"
fail=0
while read -r t; do
  [ -n "$t" ] || continue
  want=$(python3 -c "import json;print(len(json.load(open('$DIR/$t.json'))))")
  got=$($PSQL -d nm -At -c "select count(*) from public.$t")
  [ "$want" = "$got" ] && echo "ok   $t $got" || { echo "FAIL $t backup=$want restored=$got"; fail=1; }
done < <(cat "$DIR/tables.txt"; echo)
exit $fail
