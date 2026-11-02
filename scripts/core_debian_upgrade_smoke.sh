#!/usr/bin/env bash
set -Eeuo pipefail

: "${CORE_SOURCE_SHA:?CORE_SOURCE_SHA must identify the tested candidate}"
artifact_dir=$(realpath -e -- "${1:?usage: core_debian_upgrade_smoke.sh ARTIFACT_DIR}")
candidate_record="$artifact_dir/candidate.json"
fixture_dir="$artifact_dir/synthetic-upgrade-fixture"
fixture_record="$fixture_dir/fixture.json"
fixture_db="$fixture_dir/airunner.db"
validation="$artifact_dir/candidate-upgrade-validation.json"
baseline_deb="$artifact_dir/airunner_6.1.3-3_all.deb"
deb_file=$(find "$artifact_dir" -maxdepth 1 -type f -name 'airunner_*_amd64.deb' -print -quit)
test -n "$deb_file" && test -f "$candidate_record" && test -f "$fixture_record" && test -f "$fixture_db" && test -f "$baseline_deb"
test "$(id -u)" -eq 0 || { echo 'upgrade smoke must run as root' >&2; exit 1; }

# Refuse an already-installed package before allocating temp files or touching
# service, policy, or systemd state.
if dpkg-query -W -f='${db:Status-Status}' airunner 2>/dev/null | grep -qx installed; then
  echo 'airunner is already installed on the upgrade-smoke runner' >&2
  exit 1
fi

candidate_version=$(dpkg-deb --field "$deb_file" Version)
baseline_version=$(dpkg-deb --field "$baseline_deb" Version)
baseline_architecture=$(dpkg-deb --field "$baseline_deb" Architecture)
baseline_hash=$(sha256sum "$baseline_deb" | cut -d' ' -f1)
baseline_expected_hash=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["upgrade_baseline"]["sha256"])' "$candidate_record")
baseline_expected_version=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["upgrade_baseline"]["version"])' "$candidate_record")
baseline_expected_arch=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["upgrade_baseline"]["architecture"])' "$candidate_record")
candidate_source=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["source_sha"])' "$candidate_record")
fixture_source=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["source_sha"])' "$fixture_record")
candidate_hash=$(sha256sum "$deb_file" | cut -d' ' -f1)
record_hash=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["debian_sha256"])' "$candidate_record")
fixture_hash=$(sha256sum "$fixture_db" | cut -d' ' -f1)
fixture_record_hash=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["database_sha256"])' "$fixture_record")
[[ "$candidate_source" == "$CORE_SOURCE_SHA" && "$fixture_source" == "$CORE_SOURCE_SHA" ]]
[[ "$candidate_hash" == "$record_hash" && "$fixture_hash" == "$fixture_record_hash" ]]
[[ "$baseline_hash" == "$baseline_expected_hash" && "$baseline_version" == "$baseline_expected_version" ]]
[[ "$baseline_architecture" == "$baseline_expected_arch" && "$baseline_version" == "6.1.3-3" ]]
dpkg --compare-versions "$baseline_version" lt "$candidate_version"

# A service left active without an installed package is also outside this
# fresh-runner test contract. Do not take ownership of or stop it.
if systemctl is-active --quiet airunner-headless.service; then
  echo 'airunner-headless.service is already active on the upgrade-smoke runner' >&2
  exit 1
fi

dropin_dir=/etc/systemd/system/airunner-headless.service.d
dropin="$dropin_dir/90-core-upgrade-smoke.conf"
policy=/usr/sbin/policy-rc.d
key_file=
policy_backup=
had_policy=0
policy_changed=0
dropin_created=0
dropin_dir_created=0
unit_config_changed=0
service_start_attempted=0
status=failed
config_sha_before=
database_sha_before=
database_sha_after=
ownership_marker_sha_before=
ownership_marker_owner_before=
ownership_marker_sha_after=
ownership_marker_owner_after=
baseline_install_status=pending
candidate_upgrade_status=pending
database_migration_status=pending
remove_status=pending
purge_status=pending

write_record() {
  STATUS="$status" SOURCE_SHA="$CORE_SOURCE_SHA" DEB="$deb_file" BASELINE_DEB="$baseline_deb" \
    CANDIDATE_VERSION="$candidate_version" BASELINE_VERSION="$baseline_version" \
    CONFIG_SHA="$config_sha_before" DB_BEFORE="$database_sha_before" DB_AFTER="$database_sha_after" \
    BASELINE_INSTALL="$baseline_install_status" CANDIDATE_UPGRADE="$candidate_upgrade_status" \
    DB_MIGRATION="$database_migration_status" REMOVE_STATUS="$remove_status" PURGE_STATUS="$purge_status" \
    OWNER_HASH_BEFORE="$ownership_marker_sha_before" OWNER_UIDGID_BEFORE="$ownership_marker_owner_before" \
    OWNER_HASH_AFTER="$ownership_marker_sha_after" OWNER_UIDGID_AFTER="$ownership_marker_owner_after" \
    python3 - "$validation" "$candidate_record" "$fixture_record" <<'PY'
import hashlib
import json
import os
import sys
from pathlib import Path

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

target, candidate_path, fixture_path = map(Path, sys.argv[1:])
candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
payload = {
    "schema_version": 1,
    "profile": "linux-services-core",
    "source_sha": os.environ["SOURCE_SHA"],
    "debian_sha256": sha(os.environ["DEB"]),
    "debian_version": os.environ["CANDIDATE_VERSION"],
    "upgrade_smoke": os.environ["STATUS"],
    "checks": {
        "published_baseline_install": os.environ["BASELINE_INSTALL"],
        "candidate_package_upgrade": os.environ["CANDIDATE_UPGRADE"],
        "database_migration_and_marker": os.environ["DB_MIGRATION"],
        "package_remove_preserves_data": os.environ["REMOVE_STATUS"],
        "package_purge_preserves_data": os.environ["PURGE_STATUS"],
    },
    "candidate_lock_sha256": candidate["lock_sha256"],
    "fixture_kind": fixture["fixture_kind"],
    "fixture_source_sha": fixture["source_sha"],
    "fixture_database_sha256": fixture["database_sha256"],
    "alembic_revision_before": fixture["alembic_revision_before_upgrade"],
    "expected_alembic_heads_after": fixture["expected_alembic_heads_after_upgrade"],
    "config_sha256_before_upgrade": os.environ["CONFIG_SHA"],
    "database_sha256_before_migration": os.environ["DB_BEFORE"],
    "database_sha256_after_migration": os.environ["DB_AFTER"],
    "published_prior_release_upgrade": {
        "status": "passed" if os.environ["BASELINE_INSTALL"] == "passed" and os.environ["CANDIDATE_UPGRADE"] == "passed" else "incomplete",
        "source": "apt.airunner.art stable",
        "version": os.environ["BASELINE_VERSION"],
        "filename": Path(os.environ["BASELINE_DEB"]).name,
        "sha256": sha(os.environ["BASELINE_DEB"]),
        "source_revision": candidate["upgrade_baseline"]["source_revision"],
        "source_identity_note": candidate["upgrade_baseline"]["source_identity_note"],
    },
    "data_ownership_marker": {
        "sha256_before_upgrade": os.environ["OWNER_HASH_BEFORE"],
        "uid_gid_before_upgrade": os.environ["OWNER_UIDGID_BEFORE"],
        "sha256_after_upgrade": os.environ["OWNER_HASH_AFTER"],
        "uid_gid_after_upgrade": os.environ["OWNER_UIDGID_AFTER"],
    },
    "limitations": [
        "Uses a published prior services-only Debian package; no source commit is bound in its package metadata.",
        "Database fixture is synthetic and uses this candidate source's migrations at an intermediate revision, not a database or schema from the prior release.",
        "No production database, model, or model download was used.",
    ],
}
target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
}

cleanup() {
  rc=$?
  if (( service_start_attempted )); then
    systemctl stop airunner-headless.service 2>/dev/null || true
  fi
  if (( dropin_created )); then rm -f "$dropin"; fi
  if [[ -n "$key_file" ]]; then rm -f "$key_file"; fi
  if (( dropin_dir_created )); then rmdir "$dropin_dir" 2>/dev/null || true; fi
  if (( had_policy )); then
    cp -a "$policy_backup" "$policy"
  elif (( policy_changed )); then
    rm -f "$policy"
  fi
  if [[ -n "$policy_backup" ]]; then rm -f "$policy_backup"; fi
  if (( unit_config_changed )); then systemctl daemon-reload 2>/dev/null || true; fi
  if (( rc != 0 )); then status=failed; fi
  write_record || true
  exit "$rc"
}
trap cleanup EXIT

key_file=$(mktemp /run/airunner-upgrade-key.XXXXXX)
policy_backup=$(mktemp /run/airunner-policy-backup.XXXXXX)

if [[ -e "$policy" || -L "$policy" ]]; then
  [[ -f "$policy" && ! -L "$policy" ]] || {
    echo "refusing unsafe existing policy-rc.d path: $policy" >&2
    exit 1
  }
  cp -a "$policy" "$policy_backup"
  had_policy=1
fi
policy_changed=1
cat > "$policy" <<'EOF'
#!/bin/sh
exit 101
EOF
chmod 0755 "$policy"

apt-get update
apt-get install -y "$baseline_deb"
[[ "$(dpkg-query -W -f='${Version}' airunner)" == "$baseline_version" ]]
baseline_install_status=passed

config_file=/etc/airunner/daemon.yaml
database_file=/var/lib/airunner/data/airunner.db
test -f "$config_file"
printf '\n# synthetic Debian upgrade preservation marker\n' >> "$config_file"
config_sha_before=$(sha256sum "$config_file" | cut -d' ' -f1)
install -d -m 0700 -o airunner -g airunner /var/lib/airunner/data
install -m 0600 -o airunner -g airunner "$fixture_db" "$database_file"
database_sha_before=$(sha256sum "$database_file" | cut -d' ' -f1)
ownership_marker=/var/lib/airunner/data/.upgrade-ownership-marker
printf 'synthetic-data-ownership-preservation-marker-v1\n' > "$ownership_marker"
chown root:root "$ownership_marker"
chmod 0640 "$ownership_marker"
ownership_marker_sha_before=$(sha256sum "$ownership_marker" | cut -d' ' -f1)
ownership_marker_owner_before=$(stat -c '%u:%g:%a' "$ownership_marker")

apt-get install -y "$deb_file"
[[ "$(dpkg-query -W -f='${Version}' airunner)" == "$candidate_version" ]]
[[ "$(sha256sum "$config_file" | cut -d' ' -f1)" == "$config_sha_before" ]]
[[ "$(sha256sum "$database_file" | cut -d' ' -f1)" == "$database_sha_before" ]]
ownership_marker_sha_after=$(sha256sum "$ownership_marker" | cut -d' ' -f1)
ownership_marker_owner_after=$(stat -c '%u:%g:%a' "$ownership_marker")
[[ "$ownership_marker_sha_after" == "$ownership_marker_sha_before" ]]
[[ "$ownership_marker_owner_after" == "$ownership_marker_owner_before" ]]
candidate_upgrade_status=passed

[[ ! -e "$dropin" && ! -L "$dropin" ]] || { echo "refusing existing smoke drop-in: $dropin" >&2; exit 1; }
if [[ ! -d "$dropin_dir" ]]; then
  install -d -m 0755 "$dropin_dir"
  dropin_dir_created=1
elif [[ -L "$dropin_dir" ]]; then
  echo "refusing symlink smoke drop-in directory: $dropin_dir" >&2
  exit 1
fi
api_key=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')
printf 'AIRUNNER_API_KEY=%s\nAIRUNNER_RUNTIME_BIND_HOST=127.0.0.1\nHF_HUB_OFFLINE=1\nHF_DATASETS_OFFLINE=1\nTRANSFORMERS_OFFLINE=1\n' "$api_key" > "$key_file"
chmod 0600 "$key_file"
dropin_created=1
unit_config_changed=1
cat > "$dropin" <<EOF
[Service]
EnvironmentFile=$key_file
EOF
chmod 0644 "$dropin"
systemctl daemon-reload
service_start_attempted=1
systemctl start airunner-headless.service
for attempt in $(seq 1 60); do
  if curl --silent --show-error --fail --connect-timeout 2 --max-time 3 \
    http://127.0.0.1:8080/health >/dev/null; then break; fi
  if [[ "$attempt" == 60 ]]; then
    journalctl -u airunner-headless.service --no-pager -n 120 >&2 || true
    exit 1
  fi
  sleep 2
done
curl --silent --show-error --fail --connect-timeout 2 --max-time 3 \
  -H "Authorization: Bearer $api_key" \
  http://127.0.0.1:8080/api/v1/health/daemon >/dev/null
systemctl stop airunner-headless.service
service_start_attempted=0

DATABASE_FILE="$database_file" FIXTURE_RECORD="$fixture_record" python3 - <<'PY'
import json
import os
import sqlite3
from pathlib import Path
fixture = json.loads(Path(os.environ["FIXTURE_RECORD"]).read_text(encoding="utf-8"))
with sqlite3.connect(os.environ["DATABASE_FILE"]) as connection:
    heads = sorted(row[0] for row in connection.execute("SELECT version_num FROM alembic_version"))
    marker = connection.execute(
        "SELECT payload FROM core_upgrade_fixture WHERE marker = ?",
        ("synthetic-marker",),
    ).fetchone()
expected = sorted(fixture["expected_alembic_heads_after_upgrade"])
assert heads == expected, (heads, expected)
assert marker == (fixture["fixture_payload"],), marker
PY
database_sha_after=$(sha256sum "$database_file" | cut -d' ' -f1)
database_migration_status=passed

apt-get remove -y airunner
test -f "$config_file" -a -f "$database_file" -a -f "$ownership_marker"
remove_status=passed
apt-get purge -y airunner
test -f "$config_file" -a -f "$database_file" -a -f "$ownership_marker"
[[ "$(sha256sum "$config_file" | cut -d' ' -f1)" == "$config_sha_before" ]]
[[ "$(sha256sum "$ownership_marker" | cut -d' ' -f1)" == "$ownership_marker_sha_before" ]]
[[ "$(stat -c '%u:%g:%a' "$ownership_marker")" == "$ownership_marker_owner_before" ]]
DATABASE_FILE="$database_file" FIXTURE_PAYLOAD='synthetic-core-upgrade-data-preservation-fixture-v1' python3 - <<'PY'
import os
import sqlite3
with sqlite3.connect(os.environ["DATABASE_FILE"]) as connection:
    row = connection.execute(
        "SELECT payload FROM core_upgrade_fixture WHERE marker = ?",
        ("synthetic-marker",),
    ).fetchone()
assert row == (os.environ["FIXTURE_PAYLOAD"],), row
PY
purge_status=passed

status=passed
