#!/usr/bin/env bash
# Promotion gate for Linux v1 release candidates (C01).
#
# Usage:
#   candidate-gate.sh --event release|workflow_dispatch \
#       --check job=result [--check job=result ...]
#
# Exits 0 only when every check the event requires reports exactly
# `success`. A required check that failed, was skipped or cancelled,
# or was never reported (missing or empty result) blocks promotion:
# there is deliberately no `success || skipped` tolerance here.
#
# The required sets mirror pypi-dispatch.yml. On `release` the
# trusted provisioning and sidecar jobs must have run; on
# `workflow_dispatch` they skip by design (no secrets, no sidecar
# fetch), so only the secret-free wiring check and the assembled
# candidate itself are required. Non-required results are reported
# and ignored. Dependency-free (bash + coreutils); sources
# release-lib.sh for fail()/warn().
# shellcheck shell=bash
set -euo pipefail

SCRIPT_NAME="candidate-gate"
HERE=$(cd -- "$(dirname -- "$0")" && pwd)
# shellcheck source=release-lib.sh
. "$HERE/release-lib.sh"

EVENT=""
CHECKS=""

usage() {
    sed -n '2,/^# shellcheck/p' -- "$0" | sed 's/^# \{0,1\}//'
}

required_jobs() { # $1=event; prints one required job per line
    case "$1" in
        release)
            printf '%s\n' provision-policy \
                provision-policy-fixture fetch-sidecars \
                linux-candidate;;
        workflow_dispatch)
            printf '%s\n' provision-policy-fixture \
                linux-candidate;;
    esac
}

result_of() { # $1=job; prints its first reported result or nothing
    printf '%s' "$CHECKS" | sed -n "s/^$1=//p" | head -n 1
}

add_check() { # $1=job=result; records one reported result
    case "$1" in
        *=*) CHECKS="$CHECKS$1
";;
        *) fail "malformed --check (want job=result): $1";;
    esac
}

while [ $# -gt 0 ]; do
    case "$1" in
        --event)
            [ $# -ge 2 ] || fail "missing value for --event"
            EVENT=$2; shift 2;;
        --event=*) EVENT=${1#--event=}; shift;;
        --check)
            [ $# -ge 2 ] || fail "missing value for --check"
            add_check "$2"; shift 2;;
        --check=*) add_check "${1#--check=}"; shift;;
        -h | --help) usage; exit 0;;
        *) fail "unknown argument: $1";;
    esac
done

case "$EVENT" in
    release | workflow_dispatch) ;;
    *) fail "unknown --event: $EVENT (want release|workflow_dispatch)";;
esac
[ -n "$CHECKS" ] || fail "no --check results given"

REQUIRED=$(required_jobs "$EVENT")
FLAT=" $(printf '%s' "$REQUIRED" | tr '\n' ' ') "
blocked=0
while IFS= read -r job; do
    [ -n "$job" ] || continue
    result=$(result_of "$job")
    case "$result" in
        success) ;;
        "")
            warn "blocking: no result reported for $job"
            blocked=1;;
        *)
            warn "blocking: $job reported '$result'"
            blocked=1;;
    esac
done <<JOBS
$REQUIRED
JOBS
while IFS= read -r check; do
    [ -n "$check" ] || continue
    case "$FLAT" in
        *" ${check%%=*} "*) ;;
        *) printf '%s: ignoring non-required %s\n' \
            "$SCRIPT_NAME" "$check";;
    esac
done <<REPORTED
$CHECKS
REPORTED
[ "$blocked" -eq 0 ] || fail "candidate promotion blocked"
printf '%s: promotion allowed (event %s)\n' "$SCRIPT_NAME" "$EVENT"
