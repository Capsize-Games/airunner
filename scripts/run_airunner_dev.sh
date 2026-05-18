#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="${ROOT_DIR}/build/airunner-launcher"
LAUNCHER_BIN="${BUILD_DIR}/airunner"
STAMP_FILE="${BUILD_DIR}/.airunner-launcher-build-stamp"
REPO_PYTHON="${ROOT_DIR}/venv/bin/python"
REPO_DAEMON_BIN="${ROOT_DIR}/venv/bin/airunner-daemon"

export AIRUNNER_LOG_LEVEL="${AIRUNNER_LOG_LEVEL:-INFO}"

runtime_port_listeners() {
  if ! command -v lsof >/dev/null 2>&1; then
    return
  fi

  local port
  for port in 8188 8190; do
    lsof -tiTCP:"${port}" -sTCP:LISTEN 2>/dev/null || true
  done | sort -u
}

runtime_port_status() {
  if ! command -v ss >/dev/null 2>&1; then
    return
  fi

  ss -ltnH '( sport = :8188 or sport = :8190 )' || true
}

runtime_ports_cleared() {
  local listeners
  listeners="$(runtime_port_status)"
  [[ -z "${listeners}" ]]
}

wait_for_runtime_ports_to_clear() {
  local timeout_seconds="$1"
  local deadline=$((SECONDS + timeout_seconds))

  while ! runtime_ports_cleared; do
    if (( SECONDS >= deadline )); then
      return 1
    fi
    sleep 0.2
  done

  return 0
}

stop_matching_processes() {
  local pattern="$1"
  local pids
  pids="$(pgrep -f "${pattern}" || true)"
  if [[ -z "${pids}" ]]; then
    return
  fi

  echo "Stopping existing AIRunner dev daemon processes: ${pids}" >&2
  pkill -TERM -f "${pattern}" || true

  local deadline=$((SECONDS + 5))
  while pgrep -f "${pattern}" >/dev/null 2>&1; do
    if (( SECONDS >= deadline )); then
      echo "Daemon processes still running, sending SIGKILL" >&2
      pkill -KILL -f "${pattern}" || true
      break
    fi
    sleep 0.2
  done

  local remaining
  remaining="$(pgrep -f "${pattern}" || true)"
  if [[ -n "${remaining}" ]]; then
    echo "Failed to stop AIRunner dev daemons: ${remaining}" >&2
    exit 1
  fi
}

require_clear_runtime_ports() {
  if ! command -v ss >/dev/null 2>&1; then
    return
  fi

  local listeners
  listeners="$(runtime_port_status)"
  if [[ -z "${listeners}" ]]; then
    return
  fi

  echo "AIRunner runtime ports are still occupied after cleanup:" >&2
  echo "${listeners}" >&2
  echo "Refusing to launch dev GUI against a stale daemon." >&2
  exit 1
}

current_git_head() {
  if ! command -v git >/dev/null 2>&1; then
    return
  fi

  git -C "${ROOT_DIR}" rev-parse HEAD 2>/dev/null || true
}

read_build_stamp_value() {
  local key="$1"

  if [[ ! -f "${STAMP_FILE}" ]]; then
    return
  fi

  awk -F= -v key="${key}" '$1 == key { print $2 }' "${STAMP_FILE}"
}

launcher_build_is_stale() {
  if [[ ! -x "${LAUNCHER_BIN}" ]]; then
    return 0
  fi

  if [[ ! -f "${STAMP_FILE}" ]]; then
    return 0
  fi

  local current_head stamp_head
  current_head="$(current_git_head)"
  stamp_head="$(read_build_stamp_value GIT_HEAD)"

  if [[ -n "${current_head}" && -n "${stamp_head}" \
    && "${current_head}" != "${stamp_head}" ]]; then
    return 0
  fi

  local rebuild_inputs=(
    "${ROOT_DIR}/native/airunner_launcher/src/main.cpp"
    "${ROOT_DIR}/native/airunner_launcher/CMakeLists.txt"
    "${ROOT_DIR}/scripts/build_airunner_launcher.sh"
    "${ROOT_DIR}/scripts/run_airunner_dev.sh"
  )
  local input
  for input in "${rebuild_inputs[@]}"; do
    if [[ "${input}" -nt "${LAUNCHER_BIN}" ]]; then
      return 0
    fi
  done

  return 1
}

ensure_current_launcher() {
  if ! launcher_build_is_stale; then
    return
  fi

  echo "Rebuilding AIRunner launcher for current repository state" >&2
  "${ROOT_DIR}/scripts/build_airunner_launcher.sh" --clean
}

stop_runtime_port_owners() {
  local pids
  pids="$(runtime_port_listeners)"
  if [[ -z "${pids}" ]]; then
    wait_for_runtime_ports_to_clear 5 || true
    return
  fi

  echo "Stopping AIRunner runtime port owners: ${pids}" >&2
  xargs -r kill -TERM <<<"${pids}" || true

  if wait_for_runtime_ports_to_clear 5; then
    return
  fi

  echo "Runtime port owners still running, sending SIGKILL" >&2
  runtime_port_listeners | xargs -r kill -KILL || true
  wait_for_runtime_ports_to_clear 5 || true
}

stop_repo_daemons() {
  if ! command -v pgrep >/dev/null 2>&1; then
    return
  fi

  local patterns=(
    "${REPO_PYTHON} -m airunner.services.daemon"
    "${REPO_DAEMON_BIN}"
  )
  local pattern
  for pattern in "${patterns[@]}"; do
    stop_matching_processes "${pattern}"
  done

  stop_runtime_port_owners
  require_clear_runtime_ports
}

ensure_current_launcher

stop_repo_daemons

exec "${LAUNCHER_BIN}" --mode dev --repo-root "${ROOT_DIR}" "$@"