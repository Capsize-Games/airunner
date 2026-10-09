#!/usr/bin/env bash
# User-level installer for the Linux v1 services bundle (release P06).
# Installs a P05 bundle into <prefix>/versions/<version>/ with a
# launcher (<prefix>/bin/airunner-services), a menu entry, and user
# data in <prefix>/data (never wiped by reinstall). No Python, Docker,
# or root needed; only bash + coreutils. Paths may contain spaces; the
# caller working directory is irrelevant. Writes stay inside the prefix
# and the XDG user data dir; system dirs are refused without
# --allow-system-prefix. Disk space is validated before any write.
set -euo pipefail

DEFAULT_EXECUTABLE="airunner-daemon"
BUNDLE_ICON="share/icons/airunner-services.png"
DESKTOP_NAME="airunner-services.desktop"
ICON_NAME="airunner-services.png"
DISK_MARGIN_KB=51200

BUNDLE=""
PREFIX=""
VERSION_ARG=""
VERSION_GIVEN=0
DATA_DIR_ARG=""
EXECUTABLE="$DEFAULT_EXECUTABLE"
NO_DESKTOP=0
ALLOW_SYSTEM=0

fail() { printf 'install: error: %s\n' "$*" >&2; exit 1; }
warn() { printf 'install: warning: %s\n' "$*" >&2; }

usage() {
    cat <<'EOF'
Usage: install.sh --bundle DIR [options]

Options:
  --bundle DIR       P05 bundle directory to install (required)
  --prefix DIR       install prefix (default: ~/.local/share/airunner)
  --version VER      version label (default: bundle VERSION file)
  --data-dir DIR     user data dir (default: <prefix>/data)
  --executable NAME  daemon file inside the bundle
  --no-desktop       skip the menu entry and icon
  --allow-system-prefix  permit prefixes under system directories
  -h, --help         show this help
EOF
}

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

parse_args() {
    while [ "$#" -gt 0 ]; do
        case "$1" in
            --bundle) BUNDLE=$2; shift 2;;
            --prefix) PREFIX=$2; shift 2;;
            --version) VERSION_ARG=$2; VERSION_GIVEN=1; shift 2;;
            --data-dir) DATA_DIR_ARG=$2; shift 2;;
            --executable) EXECUTABLE=$2; shift 2;;
            --no-desktop) NO_DESKTOP=1; shift;;
            --allow-system-prefix) ALLOW_SYSTEM=1; shift;;
            -h|--help) usage; exit 0;;
            *) fail "unknown argument: $1 (see --help)";;
        esac
    done
    [ -n "$BUNDLE" ] || fail "missing required --bundle DIR"
}

check_paths() { # $1=prefix $2=bundle $3=install dir $4=data dir
    if is_system_prefix "$1" && [ "$ALLOW_SYSTEM" -ne 1 ]; then
        fail "refusing system prefix without --allow-system-prefix: $1"
    fi
    [ "$2" = "$3" ] && fail "bundle and install dir are the same: $2"
    path_inside "$3" "$2" && fail "install dir is inside the bundle: $3"
    path_inside "$2" "$3" && fail "bundle is inside the install dir: $2"
    [ "$4" = "$3" ] && fail "data dir must stay outside the app dir: $4"
    path_inside "$4" "$3" && fail "data dir is inside the app dir: $4"
    return 0
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

copy_bundle() { # $1=bundle $2=install dir $3=versions dir
    mkdir -p -- "$3"
    local resolved versions_resolved
    resolved=$(abs_path "$2")
    versions_resolved=$(abs_path "$3")
    [ "$resolved" != "$versions_resolved" ] || fail "refusing the versions dir itself"
    path_inside "$resolved" "$versions_resolved" || fail "refusing to write outside: $2"
    rm -rf -- "$resolved"
    mkdir -p -- "$resolved"
    cp -a -- "$1/." "$resolved/"
    ln -sfn -- "$(basename -- "$resolved")" "$versions_resolved/current"
}

sh_quote() {
    local value=${1//\'/\'\\\'\'}
    printf "'%s'" "$value"
}

desktop_escape() {
    local value=${1//\\/\\\\}
    value=${value//\"/\\\"}
    printf '%s' "$value"
}

render_launcher() { # $1=template $2=dest $3=data dir
    [ -f "$1" ] || fail "missing launcher template: $1"
    local content
    content=$(cat -- "$1")
    content=${content//@AIRUNNER_DAEMON@/$EXECUTABLE}
    content=${content//@AIRUNNER_DATA_DIR@/$(sh_quote "$3")}
    printf '%s\n' "$content" >"$2"
    chmod 755 -- "$2"
}

render_desktop() { # $1=template $2=dest $3=launcher path
    [ -f "$1" ] || fail "missing desktop template: $1"
    local content
    content=$(cat -- "$1")
    content=${content//@AIRUNNER_LAUNCHER@/$(desktop_escape "$3")}
    printf '%s\n' "$content" >"$2"
}

write_entry_points() { # $1=installer dir $2=prefix $3=version $4=data
    mkdir -p -- "$2/bin" "$4"
    render_launcher "$1/airunner-services-launcher.sh" "$2/bin/airunner-services" "$4"
    [ "$NO_DESKTOP" -eq 1 ] && return 0
    local xdg=${XDG_DATA_HOME:-$HOME/.local/share}
    mkdir -p -- "$xdg/applications" "$xdg/icons/hicolor/64x64/apps"
    render_desktop "$1/airunner-services.desktop" "$xdg/applications/$DESKTOP_NAME" "$2/bin/airunner-services"
    local icon_src=$2/versions/$3/$BUNDLE_ICON
    if [ -f "$icon_src" ]; then
        cp -- "$icon_src" "$xdg/icons/hicolor/64x64/apps/$ICON_NAME"
    else
        warn "bundle carries no $BUNDLE_ICON; menu entry uses a fallback icon"
    fi
    refresh_desktop_db
}

refresh_desktop_db() {
    local xdg=${XDG_DATA_HOME:-$HOME/.local/share}
    if command -v update-desktop-database >/dev/null 2>&1; then
        update-desktop-database -- "$xdg/applications" >/dev/null 2>&1 || true
    fi
    if command -v gtk-update-icon-cache >/dev/null 2>&1; then
        gtk-update-icon-cache -f -q -- "$xdg/icons/hicolor" >/dev/null 2>&1 || true
    fi
}

print_summary() { # $1=prefix $2=version $3=data dir
    printf 'installed airunner-services %s\n' "$2"
    printf '  application: %s\n' "$1/versions/$2"
    printf '  launcher:    %s\n' "$1/bin/airunner-services"
    printf '  data:        %s\n' "$3"
    if [ "$NO_DESKTOP" -ne 1 ]; then
        local apps=${XDG_DATA_HOME:-$HOME/.local/share}/applications
        printf '  menu entry:  %s\n' "$apps/$DESKTOP_NAME"
    fi
}

main() {
    parse_args "$@"
    [ "${EUID:-$(id -u)}" -ne 0 ] || warn "running as root; a user-level prefix is still used"
    local bundle prefix version data_dir installer_dir
    bundle=$(abs_path "$BUNDLE"); installer_dir=$(abs_path "$(dirname -- "$0")")
    check_bundle "$bundle" "$EXECUTABLE"
    prefix=$(abs_path "${PREFIX:-$HOME/.local/share/airunner}")
    version=$VERSION_ARG
    [ "$VERSION_GIVEN" -eq 1 ] || version=$(default_version "$bundle")
    valid_version "$version" || fail "invalid --version: $version"
    data_dir=$(abs_path "${DATA_DIR_ARG:-$prefix/data}")
    check_paths "$prefix" "$bundle" "$prefix/versions/$version" "$data_dir"
    check_disk_space "$bundle" "$prefix"
    copy_bundle "$bundle" "$prefix/versions/$version" "$prefix/versions"
    write_entry_points "$installer_dir" "$prefix" "$version" "$data_dir"
    print_summary "$prefix" "$version" "$data_dir"
}

main "$@"
