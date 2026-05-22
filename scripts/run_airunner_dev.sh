#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="${ROOT_DIR}/build/airunner-launcher"
LAUNCHER_BIN="${BUILD_DIR}/airunner"
STAMP_FILE="${BUILD_DIR}/.airunner-launcher-build-stamp"
REPO_PYTHON="${ROOT_DIR}/venv/bin/python"
REPO_DAEMON_BIN="${ROOT_DIR}/venv/bin/airunner-daemon"

export AIRUNNER_LOG_LEVEL="${AIRUNNER_LOG_LEVEL:-INFO}"

AIRUNNER_DEBUG_MODE="normal"
declare -a AIRUNNER_DEV_ARGS=()
declare -a AIRUNNER_DEV_COMMAND=()

print_debug_help() {
  cat <<'EOF'
Usage: ./scripts/run_airunner_dev.sh [--gdb|--coredump] [launcher-args]

Debug helpers:
  --gdb
      Launch AIRunner under gdb. The session follows the Python child
      process and defines an `airunner_dump` gdb command that writes full
      thread backtraces plus a local core file under build/debug/core/.

  --coredump, --core-dump
      Enable kernel core dumps before launching AIRunner. On systems using
      systemd-coredump, inspect the crash with coredumpctl after exit 139.

  --debug-help
      Print this debug-specific help and exit.

Examples:
  ./scripts/run_airunner_dev.sh --gdb
  ./scripts/run_airunner_dev.sh --coredump
  ./scripts/run_airunner_dev.sh --coredump --dry-run --print-plan
EOF
}

set_debug_mode() {
  local requested_mode="$1"

  if [[ "${AIRUNNER_DEBUG_MODE}" != "normal" \
    && "${AIRUNNER_DEBUG_MODE}" != "${requested_mode}" ]]; then
    echo "Choose only one debug mode: --gdb or --coredump" >&2
    exit 1
  fi

  AIRUNNER_DEBUG_MODE="${requested_mode}"
}

parse_debug_runner_args() {
  while (($#)); do
    case "$1" in
      --gdb)
        set_debug_mode "gdb"
        shift
        ;;
      --coredump|--core-dump)
        set_debug_mode "coredump"
        shift
        ;;
      --debug-help)
        print_debug_help
        exit 0
        ;;
      --)
        shift
        if (($#)); then
          AIRUNNER_DEV_ARGS+=("$@")
        fi
        return
        ;;
      *)
        AIRUNNER_DEV_ARGS+=("$1")
        shift
        ;;
    esac
  done
}

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

build_dev_command() {
  AIRUNNER_DEV_COMMAND=(
    "${LAUNCHER_BIN}"
    --mode dev
    --repo-root "${ROOT_DIR}"
  )

  if ((${#AIRUNNER_DEV_ARGS[@]} > 0)); then
    AIRUNNER_DEV_COMMAND+=("${AIRUNNER_DEV_ARGS[@]}")
  fi
}

require_command() {
  local command_name="$1"

  if command -v "${command_name}" >/dev/null 2>&1; then
    return
  fi

  echo "Required command not found: ${command_name}" >&2
  exit 1
}

current_core_pattern() {
  if [[ -r /proc/sys/kernel/core_pattern ]]; then
    tr -d '\n' < /proc/sys/kernel/core_pattern
  fi
}

core_dumps_disabled() {
  local core_pattern="$1"

  [[ "${core_pattern}" == "|/bin/false" ]]
}

core_dumps_use_systemd() {
  local core_pattern="$1"

  [[ "${core_pattern}" == *systemd-coredump* ]]
}

launch_under_gdb() {
  require_command gdb

  local gdb_dir core_dir timestamp gdb_commands log_file core_file
  gdb_dir="${ROOT_DIR}/build/debug/gdb"
  core_dir="${ROOT_DIR}/build/debug/core"
  mkdir -p "${gdb_dir}" "${core_dir}"

  timestamp="$(date +%Y%m%d-%H%M%S)"
  gdb_commands="${gdb_dir}/airunner-${timestamp}.gdb"
  log_file="${gdb_dir}/airunner-${timestamp}.gdb.log"
  core_file="${core_dir}/airunner-${timestamp}.core"

  cat >"${gdb_commands}" <<EOF
set pagination off
set confirm off
set print thread-events off
set follow-fork-mode parent
set detach-on-fork on
handle SIGPIPE nostop noprint pass
handle SIG32 nostop noprint pass
handle SIG33 nostop noprint pass
set logging file ${log_file}
set logging overwrite on
set logging on
define airunner_dump
  echo \n=== AIRunner thread backtraces ===\n
  thread apply all bt full
  echo \n=== Writing core file to ${core_file} ===\n
  generate-core-file ${core_file}
  echo \n=== AIRunner dump complete ===\n
end
document airunner_dump
Capture full thread backtraces and write a local core file.
end
EOF

  echo "Starting AIRunner under gdb" >&2
  echo "gdb log: ${log_file}" >&2
  echo "core file target: ${core_file}" >&2
  echo "When the crash stops in gdb, run: airunner_dump" >&2

  exec gdb -x "${gdb_commands}" -ex run --args \
    "${AIRUNNER_DEV_COMMAND[@]}" --no-fork
}

launch_with_coredump() {
  local core_pattern

  mkdir -p "${ROOT_DIR}/build/debug/core"
  ulimit -c unlimited
  core_pattern="$(current_core_pattern)"

  echo "Starting AIRunner with core dumps enabled" >&2
  if [[ -n "${core_pattern}" ]]; then
    echo "kernel.core_pattern=${core_pattern}" >&2
  fi

  if core_dumps_disabled "${core_pattern}"; then
    echo "Kernel core dumps are disabled on this host." >&2
    echo "Use ./scripts/run_airunner_dev.sh --gdb for a local crash" >&2
    echo "dump, or reconfigure kernel.core_pattern as root and retry" >&2
    echo "--coredump." >&2
    exit 1
  fi

  if core_dumps_use_systemd "${core_pattern}"; then
    echo "This system pipes crashes to a core collector." >&2
    echo "After exit 139, inspect the dump with:" >&2
    echo "  coredumpctl list airunner" >&2
    echo "  coredumpctl info airunner" >&2
  elif [[ "${core_pattern}" == \|* ]]; then
    echo "This system uses a custom core collector." >&2
    echo "Inspect crash artifacts with that collector or use --gdb" >&2
    echo "for a local core file." >&2
  else
    echo "File-based core dumps are enabled for this shell." >&2
    echo "If a crash occurs, look for a core file in the launch directory." >&2
  fi

  exec "${AIRUNNER_DEV_COMMAND[@]}"
}

launch_dev_runner() {
  case "${AIRUNNER_DEBUG_MODE}" in
    gdb)
      launch_under_gdb
      ;;
    coredump)
      launch_with_coredump
      ;;
    *)
      exec "${AIRUNNER_DEV_COMMAND[@]}"
      ;;
  esac
}

parse_debug_runner_args "$@"

ensure_current_launcher

stop_repo_daemons

build_dev_command

launch_dev_runner