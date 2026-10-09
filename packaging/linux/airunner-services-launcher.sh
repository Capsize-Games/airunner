#!/bin/sh
# AIRunner services launcher template (release P06).
#
# Installed by packaging/linux/install.sh to <prefix>/bin/airunner-services
# with the daemon name and data dir filled in at install time. Resolves
# the installed daemon, bundle resources, and user data dir, then execs
# the daemon. Pure POSIX sh: no Python required. Do not run this
# template directly; its placeholders are only valid after installation.
set -eu

DAEMON_NAME=@AIRUNNER_DAEMON@
DEFAULT_DATA_DIR=@AIRUNNER_DATA_DIR@

self_path() {
    if command -v readlink >/dev/null 2>&1; then
        readlink -f -- "$0"
    else
        printf '%s\n' "$0"
    fi
}

SELF=$(self_path)
BIN_DIR=$(CDPATH= cd -- "$(dirname -- "$SELF")" && pwd -P)
PREFIX=$(dirname -- "$BIN_DIR")
APP_ROOT="$PREFIX/versions/current"
if [ ! -d "$APP_ROOT" ]; then
    echo "airunner-services: no installed version at $APP_ROOT" >&2
    exit 1
fi
DAEMON="$APP_ROOT/$DAEMON_NAME"
if [ ! -x "$DAEMON" ]; then
    echo "airunner-services: daemon is not executable: $DAEMON" >&2
    exit 1
fi
: "${AIRUNNER_BUNDLE_ROOT:=$APP_ROOT}"
: "${AIRUNNER_DATA_DIR:=$DEFAULT_DATA_DIR}"
export AIRUNNER_BUNDLE_ROOT AIRUNNER_DATA_DIR
mkdir -p -- "$AIRUNNER_DATA_DIR"
exec "$DAEMON" "$@"
