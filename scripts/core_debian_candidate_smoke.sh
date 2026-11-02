#!/usr/bin/env bash
set -Eeuo pipefail

: "${CORE_SOURCE_SHA:?CORE_SOURCE_SHA must identify the tested candidate}"

artifact_dir=${1:?usage: core_debian_candidate_smoke.sh ARTIFACT_DIR}
deb_file=$(find "$artifact_dir" -maxdepth 1 -type f -name 'airunner_*_amd64.deb' -print -quit)
test -n "$deb_file" || { echo 'candidate .deb not found' >&2; exit 1; }
record="$artifact_dir/candidate-validation.json"
key_file=$(mktemp /run/airunner-candidate-key.XXXXXX)
dropin_dir=/etc/systemd/system/airunner-headless.service.d
dropin="$dropin_dir/90-core-candidate-smoke.conf"
policy=/usr/sbin/policy-rc.d
policy_backup=$(mktemp /run/airunner-policy-backup.XXXXXX)
had_policy=0
initial_pid=
status=failed

write_record() {
  STATUS="$status" SOURCE_SHA="${CORE_SOURCE_SHA:-unknown}" \
    DEB_SHA="$(sha256sum "$deb_file" | cut -d' ' -f1)" \
    python3 - "$record" <<'PY'
import json, os, sys
from pathlib import Path
Path(sys.argv[1]).write_text(json.dumps({
    "schema_version": 1,
    "profile": "linux-services-core",
    "source_sha": os.environ["SOURCE_SHA"],
    "debian_sha256": os.environ["DEB_SHA"],
    "clean_install_smoke": os.environ["STATUS"],
    "checks": [
        "fresh Ubuntu runner; local candidate package install",
        "systemd start, authenticated API probe, stop, start and restart",
    ] if os.environ["STATUS"] == "passed" else [],
    "exclusions": [
        "real model inference and model downloads",
        "offline network-denial behavior",
        "upgrade preservation from a prior package",
        "APT repository promotion or signing",
        "full-ML candidate build",
    ],
}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
}

cleanup() {
  rc=$?
  systemctl stop airunner-headless.service || true
  rm -f "$dropin" "$key_file"
  rmdir "$dropin_dir" 2>/dev/null || true
  if (( had_policy )); then
    cp -a "$policy_backup" "$policy"
  else
    rm -f "$policy"
  fi
  rm -f "$policy_backup"
  systemctl daemon-reload || true
  if (( rc != 0 )); then status=failed; fi
  write_record || true
  exit "$rc"
}
trap cleanup EXIT

if [[ -e "$policy" ]]; then
  had_policy=1
  cp -a "$policy" "$policy_backup"
fi
cat > "$policy" <<'EOF'
#!/bin/sh
exit 101
EOF
chmod 0755 "$policy"

apt-get update
apt-get install -y "$deb_file"

install -d -m 0755 "$dropin_dir"
api_key=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')
printf 'AIRUNNER_API_KEY=%s\nAIRUNNER_RUNTIME_BIND_HOST=127.0.0.1\nHF_HUB_OFFLINE=1\nHF_DATASETS_OFFLINE=1\nTRANSFORMERS_OFFLINE=1\n' "$api_key" > "$key_file"
chmod 0600 "$key_file"
cat > "$dropin" <<EOF
[Service]
EnvironmentFile=$key_file
EOF
chmod 0644 "$dropin"
systemctl daemon-reload

wait_for_health() {
  for attempt in $(seq 1 45); do
    if curl --silent --show-error --fail --connect-timeout 2 --max-time 3 \
      http://127.0.0.1:8080/health >/dev/null; then
      return 0
    fi
    sleep 2
  done
  journalctl -u airunner-headless.service --no-pager -n 100 >&2 || true
  return 1
}

assert_api_auth() {
  local code
  code=$(curl --silent --output /dev/null --write-out '%{http_code}' \
    --connect-timeout 2 --max-time 3 http://127.0.0.1:8080/health/daemon)
  [[ "$code" == 401 ]] || { echo "unauthenticated API returned $code, expected 401" >&2; return 1; }
  curl --silent --show-error --fail --connect-timeout 2 --max-time 3 \
    -H "Authorization: Bearer $api_key" \
    http://127.0.0.1:8080/health/daemon >/dev/null
}

assert_stopped() {
  local pid=$1
  for _ in $(seq 1 30); do
    if ! kill -0 "$pid" 2>/dev/null; then return 0; fi
    sleep 1
  done
  echo "daemon process $pid did not exit" >&2
  return 1
}

systemctl start airunner-headless.service
wait_for_health
assert_api_auth
initial_pid=$(systemctl show --property=MainPID --value airunner-headless.service)
[[ "$initial_pid" =~ ^[1-9][0-9]*$ ]]

systemctl stop airunner-headless.service
assert_stopped "$initial_pid"

systemctl start airunner-headless.service
wait_for_health
second_pid=$(systemctl show --property=MainPID --value airunner-headless.service)
[[ "$second_pid" =~ ^[1-9][0-9]*$ ]]
systemctl restart airunner-headless.service
wait_for_health
third_pid=$(systemctl show --property=MainPID --value airunner-headless.service)
[[ "$third_pid" =~ ^[1-9][0-9]*$ ]]
assert_stopped "$second_pid"
[[ "$third_pid" != "$second_pid" ]] || { echo 'restart retained daemon PID' >&2; exit 1; }
systemctl stop airunner-headless.service
assert_stopped "$third_pid"

status=passed
