#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Container entrypoint shared by the dev (open-core) and prod (extensions)
# images. Waits for PostgreSQL to accept connections, applies migrations, then
# execs the given command (the API server by default).
# ---------------------------------------------------------------------------
set -euo pipefail

log() { echo "[entrypoint] $*"; }

# ---------------------------------------------------------------------------
# 1. Wait for the database.
#
# Uses psycopg (a core dependency) against the same DATABASE_URL the app
# resolves, so we honour AIRUNNER_DATABASE_URL / AIRUNNER_POSTGRES_* exactly.
# ---------------------------------------------------------------------------
if [[ "${AIRUNNER_SKIP_DB_WAIT:-0}" != "1" ]]; then
    log "Waiting for PostgreSQL..."
    python - <<'PY'
import os
import sys
import time

# Resolve the same URL the application will use.
sys.path.insert(0, "/app/server/src")
try:
    from airunner_services.conf import settings
    url = settings.DATABASE_URL
except Exception:
    url = (
        os.environ.get("AIRUNNER_DATABASE_URL")
        or os.environ.get("DATABASE_URL")
        or ""
    )

import psycopg

deadline = time.time() + int(os.environ.get("AIRUNNER_DB_WAIT_TIMEOUT", "60"))
last_err = None
while time.time() < deadline:
    try:
        with psycopg.connect(url, connect_timeout=3):
            print("[entrypoint] PostgreSQL is ready.")
            break
    except Exception as exc:  # noqa: BLE001
        last_err = exc
        time.sleep(1.5)
else:
    print(f"[entrypoint] Database not reachable: {last_err}", file=sys.stderr)
    sys.exit(1)
PY
fi

# ---------------------------------------------------------------------------
# 2. Apply migrations (core + extensions).
#
# setup_database() also runs on server boot, but doing it here makes failures
# explicit and lets `migrate` be run as a one-off task in CI / deploys.
# ---------------------------------------------------------------------------
if [[ "${AIRUNNER_SKIP_MIGRATE:-0}" != "1" ]]; then
    log "Applying database migrations..."
    python - <<'PY'
import sys
sys.path.insert(0, "/app/server/src")
from airunner_services.database.setup_database import setup_database
setup_database()
print("[entrypoint] Migrations applied.")
PY
fi

# ---------------------------------------------------------------------------
# 3. Hand off to the requested command.
# ---------------------------------------------------------------------------
log "Starting: $*"
exec "$@"
