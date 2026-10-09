# Shared helpers for the Linux v1 release scripts (P06/P07).
#
# Sourced by packaging/linux/upgrade.sh; install.sh keeps its own copy
# because it is a frozen P06 artifact. Expects `set -euo pipefail` in
# the caller. Must stay dependency-free (bash + coreutils only).
# shellcheck shell=bash

DEFAULT_EXECUTABLE="airunner-daemon"
DISK_MARGIN_KB=51200

fail() { printf '%s: error: %s\n' "$SCRIPT_NAME" "$*" >&2; exit 1; }
warn() { printf '%s: warning: %s\n' "$SCRIPT_NAME" "$*" >&2; }

abs_path() { realpath -m -- "$1"; }

path_inside() { # $1=path $2=possible parent (both absolute)
    case "$1" in
        "$2" | "$2"/*) return 0;;
        *) return 1;;
    esac
}

is_system_prefix() { # $1=absolute prefix
    case "$1" in
        /|/usr|/usr/*|/bin|/bin/*|/sbin|/sbin/*|/lib|/lib/*|/lib64|/lib64/*|/etc|/etc/*|/var|/var/*|/opt|/opt/*|/root|/root/*|/boot|/boot/*|/sys|/sys/*|/proc|/proc/*|/dev|/dev/*|/run|/run/*|/snap|/snap/*)
            return 0;;
        *) return 1;;
    esac
}

valid_version() {
    case "$1" in
        "" | current | . | ..) return 1;;
    esac
    case "$1" in
        *[!A-Za-z0-9._+-]*) return 1;;
    esac
    [ "${#1}" -le 64 ] || return 1
    case "$1" in
        [A-Za-z0-9]*) return 0;;
        *) return 1;;
    esac
}

default_version() { # $1=bundle; prints the bundle VERSION file
    local file=$1/VERSION
    [ -f "$file" ] || fail "no --version given and no VERSION file: $1"
    local version
    version=$(tr -d ' \t\r\n' <"$file")
    [ -n "$version" ] || fail "bundle VERSION file is empty: $file"
    printf '%s\n' "$version"
}

existing_parent() {
    local dir=$1
    while [ ! -e "$dir" ]; do
        dir=$(dirname -- "$dir")
    done
    printf '%s\n' "$dir"
}

check_disk_space() { # $1=bundle $2=prefix; must run before any write
    local size_kb avail_kb required_kb parent
    size_kb=$(du -sk -- "$1" | cut -f1)
    parent=$(existing_parent "$2")
    avail_kb=$(df -k --output=avail -- "$parent" | tail -n 1)
    avail_kb=$(printf '%s' "$avail_kb" | tr -d '[:space:]')
    required_kb=${AIRUNNER_INSTALL_REQUIRED_KB:-$((size_kb + DISK_MARGIN_KB))}
    case "$required_kb" in
        "" | *[!0-9]*) fail "required space is not numeric: $required_kb";;
    esac
    if [ "$avail_kb" -lt "$required_kb" ]; then
        fail "insufficient disk space under $2: need ${required_kb}K, have ${avail_kb}K"
    fi
}

check_bundle() { # $1=bundle $2=executable
    case "$2" in
        "" | *[!A-Za-z0-9._+-]*) fail "invalid --executable name: $2";;
    esac
    [ -d "$1" ] || fail "bundle is not a directory: $1"
    [ -x "$1/$2" ] || fail "bundle has no executable $2: $1"
    [ -f "$1/bundle-manifest.json" ] || fail "bundle has no manifest: $1"
    [ -d "$1/bin" ] || fail "bundle has no bin/ sidecar dir: $1"
    [ -d "$1/legal" ] || fail "bundle has no legal/ dir: $1"
}

sh_quote() {
    local value=${1//\'/\'\\\'\'}
    printf "'%s'" "$value"
}

render_launcher() { # $1=template $2=dest $3=daemon $4=data dir
    [ -f "$1" ] || fail "missing launcher template: $1"
    local content
    content=$(cat -- "$1")
    content=${content//@AIRUNNER_DAEMON@/$3}
    content=${content//@AIRUNNER_DATA_DIR@/$(sh_quote "$4")}
    printf '%s\n' "$content" >"$2"
    chmod 755 -- "$2"
}
