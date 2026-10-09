#!/usr/bin/env bash
# Safe uninstaller for the Linux v1 services bundle (release P08).
# Removes owned app/launcher/menu artifacts; user data is preserved
# by default. Managed-data deletion needs --delete-data --yes, lists
# its allowlisted files first, and never recursively deletes the data
# dir or any custom model/media directory. See UNINSTALL.md.
set -euo pipefail

DESKTOP_NAME="airunner-services.desktop"
ICON_NAME="airunner-services.png"
LAUNCHER_NAME="airunner-services"
MANIFEST_NAME="bundle-manifest.json"

# Allowlisted managed files under the data dir. Everything else
# (models/, media/, backups/, custom paths) is never deleted.
MANAGED_FILES="airunner.db airunner.db-journal airunner.db-shm
airunner.db-wal settings.json service.log"

PREFIX=""
DATA_DIR_ARG=""
DELETE_DATA=0
CONFIRM=0
ALLOW_SYSTEM=0

fail() { printf 'uninstall: error: %s\n' "$*" >&2; exit 1; }
warn() { printf 'uninstall: warning: %s\n' "$*" >&2; }
info() { printf 'uninstall: %s\n' "$*"; }

usage() {
    cat <<'EOF'
Usage: uninstall.sh [options]
Removes the app, launcher, and menu entry. Data is preserved
unless --delete-data --yes is passed (the plan lists first).
  --prefix DIR / --data-dir DIR / --delete-data / --yes
  --allow-system-prefix / -h, --help (details: UNINSTALL.md)
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
            --prefix) PREFIX=$2; shift 2;;
            --data-dir) DATA_DIR_ARG=$2; shift 2;;
            --delete-data) DELETE_DATA=1; shift;;
            --yes) CONFIRM=1; shift;;
            --allow-system-prefix) ALLOW_SYSTEM=1; shift;;
            -h|--help) usage; exit 0;;
            *) fail "unknown argument: $1 (see --help)";;
        esac
    done
}

launcher_data_dir() { # $1=launcher path; prints embedded data dir
    local line rest
    line=$(grep -m1 '^DEFAULT_DATA_DIR=' "$1" 2>/dev/null || true)
    [ -n "$line" ] || return 1
    rest=${line#DEFAULT_DATA_DIR=}
    case "$rest" in \'*\') ;; *) return 1;; esac
    rest=${rest#\'}; rest=${rest%\'}
    printf '%s' "$rest" | sed "s/'\\\\''/'/g"
}

is_managed_version() { # $1=version dir; owned installs carry a manifest
    [ -d "$1" ] && [ ! -L "$1" ] && [ -f "$1/$MANIFEST_NAME" ]
}

remove_versions() { # $1=versions dir
    [ -e "$1" ] || { info "no versions dir; skipping: $1"; return 0; }
    [ -L "$1" ] && fail "refusing versions dir symlink: $1"
    [ -d "$1" ] || fail "versions path is not a directory: $1"
    local entry base
    for entry in "$1"/* "$1"/.*; do
        base=$(basename -- "$entry")
        case "$base" in . | .. | '*' | '.*') continue;; esac
        if [ -L "$entry" ]; then
            rm -f -- "$entry"; info "removed link: $entry"
        elif is_managed_version "$entry"; then
            rm -rf -- "$entry"; info "removed version: $entry"
        elif [ -e "$entry" ]; then
            warn "keeping unmanaged entry (no $MANIFEST_NAME): $entry"
        fi
    done
    rmdir -- "$1" 2>/dev/null || true
}

is_managed_launcher() { # $1=launcher path; owned launchers embed this
    [ -f "$1" ] && [ ! -L "$1" ] \
        && grep -q '^DAEMON_NAME=' "$1" 2>/dev/null
}

remove_launcher() { # $1=prefix
    local launcher=$1/bin/$LAUNCHER_NAME
    if [ -L "$launcher" ]; then
        rm -f -- "$launcher"; info "removed link: $launcher"
    elif [ -e "$launcher" ]; then
        if is_managed_launcher "$launcher"; then
            rm -f -- "$launcher"; info "removed launcher: $launcher"
        else
            warn "keeping unmanaged launcher file: $launcher"
        fi
    fi
    rmdir -- "$1/bin" 2>/dev/null || true
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

remove_menu_entry() { # $1=launcher path
    local xdg=${XDG_DATA_HOME:-$HOME/.local/share}
    local desktop=$xdg/applications/$DESKTOP_NAME
    local icon=$xdg/icons/hicolor/64x64/apps/$ICON_NAME
    [ -f "$desktop" ] || { info "no menu entry; skipping"; return 0; }
    if grep -Fq -- "$1" "$desktop" 2>/dev/null; then
        rm -f -- "$desktop"; info "removed menu entry: $desktop"
        if [ -f "$icon" ]; then
            rm -f -- "$icon"; info "removed icon: $icon"
        fi
        refresh_desktop_db
    else
        warn "keeping menu entry owned by another install: $desktop"
    fi
}

uninstall_app() { # $1=prefix $2=launcher $3=versions dir
    remove_versions "$3"
    remove_launcher "$1"
    remove_menu_entry "$2"
    rmdir -- "$1" 2>/dev/null || true # only if already empty
}

resolve_data_dir() { # $1=prefix; prints the data dir to report/clean
    [ -n "$DATA_DIR_ARG" ] && { abs_path "$DATA_DIR_ARG"; return 0; }
    local launcher=$1/bin/$LAUNCHER_NAME embedded
    if embedded=$(launcher_data_dir "$launcher" 2>/dev/null); then
        abs_path "$embedded"
    else
        abs_path "$1/data"
    fi
}

candidate_ok() { # $1=file $2=data dir; owned regular file in bounds
    [ -f "$1" ] && [ ! -L "$1" ] || return 1
    [ -O "$1" ] || return 1
    local resolved
    resolved=$(abs_path "$1")
    path_inside "$resolved" "$2" && [ "$resolved" != "$2" ]
}

plan_data_deletion() { # $1=data dir; prints deletable files, warns rest
    local name target
    # shellcheck disable=SC2086: intentional word splitting of the list
    for name in $MANAGED_FILES; do
        target=$1/$name
        if [ -L "$target" ]; then
            warn "skipping symlink (not an owned file): $target"
        elif [ -e "$target" ] && candidate_ok "$target" "$1"; then
            printf '%s\n' "$target"
        elif [ -e "$target" ]; then
            warn "skipping file that failed ownership checks: $target"
        fi
    done
}

show_plan() { # $1=data dir $2=plan text
    printf 'uninstall: managed-data deletion plan under %s:\n' "$1"
    while IFS= read -r listed; do
        printf 'uninstall:   %s\n' "$listed"
    done <<<"$2"
}

delete_managed_data() { # $1=data dir
    [ "$1" != / ] || fail "refusing to clean the filesystem root"
    [ "$1" != "$HOME" ] || fail "refusing to clean the home dir: $1"
    [ -e "$1" ] || { info "no data dir; nothing to delete: $1"; return 0; }
    [ -L "$1" ] && fail "refusing data dir that is a symlink: $1"
    [ -d "$1" ] || fail "data path is not a directory: $1"
    local plan file
    plan=$(plan_data_deletion "$1")
    [ -n "$plan" ] || { info "no managed data files: $1"; return 0; }
    show_plan "$1" "$plan"
    [ "$CONFIRM" -eq 1 ] || fail "re-run with --yes to delete the files listed above"
    while IFS= read -r file; do
        candidate_ok "$file" "$1" || fail "aborting: no longer an owned file: $file"
        rm -f -- "$file"
        info "deleted managed file: $file"
    done <<<"$plan"
    rmdir -- "$1" 2>/dev/null && info "removed now-empty data dir: $1" || true
}

check_prefix() { # prints the validated absolute prefix
    local prefix
    prefix=$(abs_path "${PREFIX:-$HOME/.local/share/airunner}")
    [ "$prefix" != / ] || fail "refusing the filesystem root as prefix"
    if is_system_prefix "$prefix" && [ "$ALLOW_SYSTEM" -ne 1 ]; then
        fail "refusing system prefix without --allow-system-prefix: $prefix"
    fi
    printf '%s\n' "$prefix"
}

main() {
    parse_args "$@"
    local prefix versions launcher data_dir
    prefix=$(check_prefix)
    versions=$prefix/versions launcher=$prefix/bin/$LAUNCHER_NAME
    if [ ! -e "$versions" ] && [ ! -e "$launcher" ]; then
        info "nothing installed under prefix: $prefix"
    fi
    local data_dir
    data_dir=$(resolve_data_dir "$prefix")
    uninstall_app "$prefix" "$launcher" "$versions"
    if [ "$DELETE_DATA" -eq 1 ]; then
        delete_managed_data "$data_dir"
    else
        info "preserved user data: $data_dir"
        info "to delete managed data, re-run with --delete-data --yes"
    fi
    info "uninstall complete for prefix: $prefix"
}

main "$@"
