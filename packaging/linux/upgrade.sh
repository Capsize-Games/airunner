#!/usr/bin/env bash
# Transactional upgrade for the Linux v1 services bundle (release P07).
#
# Stages a bundle into <prefix>/versions/.staging-<version>-<pid>,
# verifies the staged tree, then atomically activates it: the staged
# directory is renamed into place and the `current` symlink is swapped
# with a rename-based update. The previous version is retained,
# older versions are pruned to --keep-previous, and every outcome is
# recorded in <prefix>/upgrade-state.json. User data is never touched:
# the daemon snapshots the database before migrating, and `rollback`
# only re-points `current`, never downgrading a migrated database.
# No Python, Docker, or root needed; only bash + coreutils. The P06
# menu entry keeps working: its launcher path is stable across
# versions, so only the launcher itself is re-rendered here.
set -euo pipefail

SCRIPT_NAME="upgrade"
INSTALLER_DIR=$(dirname -- "$0")
# shellcheck source=release-lib.sh
[ -f "$INSTALLER_DIR/release-lib.sh" ] || {
    echo "upgrade: error: missing release-lib.sh next to $0" >&2; exit 1; }
. "$INSTALLER_DIR/release-lib.sh"

STATE_NAME="upgrade-state.json"

BUNDLE=""
PREFIX=""
VERSION_ARG=""
VERSION_GIVEN=0
DATA_DIR_ARG=""
EXECUTABLE="$DEFAULT_EXECUTABLE"
KEEP_PREVIOUS=1
ALLOW_SYSTEM=0
ROLLBACK=0
ROLLBACK_TO=""

usage() {
    cat <<'EOF'
Usage: upgrade.sh --bundle DIR --prefix DIR [options]
       upgrade.sh --rollback --prefix DIR [--rollback-to VER]

Options:
  --bundle DIR       bundle directory to activate (upgrade mode)
  --prefix DIR       install prefix holding versions/ (required)
  --version VER      version label (default: bundle VERSION file)
  --data-dir DIR     user data dir (default: <prefix>/data)
  --executable NAME  daemon file inside the bundle
  --keep-previous N  old versions to retain besides current (default: 1)
  --rollback         re-activate the previous version instead
  --rollback-to VER  rollback target (default: recorded previous)
  --allow-system-prefix  permit prefixes under system directories
  -h, --help         show this help
EOF
}

parse_args() {
    while [ "$#" -gt 0 ]; do
        case "$1" in
            --bundle) BUNDLE=$2; shift 2;;
            --prefix) PREFIX=$2; shift 2;;
            --version) VERSION_ARG=$2; VERSION_GIVEN=1; shift 2;;
            --data-dir) DATA_DIR_ARG=$2; shift 2;;
            --executable) EXECUTABLE=$2; shift 2;;
            --keep-previous) KEEP_PREVIOUS=$2; shift 2;;
            --rollback) ROLLBACK=1; shift;;
            --rollback-to) ROLLBACK_TO=$2; shift 2;;
            --allow-system-prefix) ALLOW_SYSTEM=1; shift;;
            -h|--help) usage; exit 0;;
            *) fail "unknown argument: $1 (see --help)";;
        esac
    done
    [ -n "$PREFIX" ] || fail "missing required --prefix DIR"
    case "$KEEP_PREVIOUS" in
        "" | *[!0-9]*) fail "invalid --keep-previous: $KEEP_PREVIOUS";;
    esac
    if [ "$ROLLBACK" -eq 1 ]; then
        [ -z "$BUNDLE" ] || fail "--bundle and --rollback are exclusive"
    else
        [ -n "$BUNDLE" ] || fail "missing required --bundle DIR"
    fi
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

current_version() { # $1=versions dir; prints "" when nothing installed
    if [ -L "$1/current" ]; then
        basename -- "$(readlink -- "$1/current")"
    fi
}

write_state() { # $1=prefix $2=status $3=previous $4=current
    local tmp=$1/.$STATE_NAME.$$
    {
        printf '{"status": "%s", "previous": "%s", ' "$2" "$3"
        printf '"current": "%s", "updated": "%s"}\n' "$4" "$(date -u +%FT%TZ)"
    } >"$tmp"
    mv -f -- "$tmp" "$1/$STATE_NAME"
}

state_field() { # $1=prefix $2=field; best-effort JSON string lookup
    sed -n "s/.*\"$2\": \"\([^\"]*\)\".*/\1/p" "$1/$STATE_NAME" 2>/dev/null
}

clean_stale_staging() { # $1=versions dir
    local entry
    for entry in "$1"/.staging-* "$1"/.retired-* "$1"/.current.*; do
        [ -e "$entry" ] || [ -L "$entry" ] || continue
        warn "removing residue from an interrupted run: $entry"
        rm -rf -- "$entry"
    done
}

stage_bundle() { # $1=bundle $2=staging dir $3=versions dir
    mkdir -p -- "$3"
    local resolved versions_resolved
    resolved=$(abs_path "$2")
    versions_resolved=$(abs_path "$3")
    path_inside "$resolved" "$versions_resolved" || fail "refusing to write outside: $2"
    rm -rf -- "$resolved"
    mkdir -p -- "$resolved"
    cp -a -- "$1/." "$resolved/"
    [ "${AIRUNNER_UPGRADE_FAIL_AT:-}" != "stage" ] || fail "injected failure at stage"
}

activate_staging() { # $1=staging dir $2=install dir $3=versions dir
    local target=$2
    local retired=$3/.retired-$$
    if [ -e "$target" ] || [ -L "$target" ]; then
        mv -T -- "$target" "$retired"
    fi
    if ! mv -T -- "$1" "$target"; then
        [ ! -e "$retired" ] || mv -T -- "$retired" "$target"
        fail "activation rename failed for $target"
    fi
    rm -rf -- "$retired"
    [ "${AIRUNNER_UPGRADE_FAIL_AT:-}" != "activate" ] || fail "injected failure at activate"
    point_current "$3" "$(basename -- "$target")"
}

point_current() { # $1=versions dir $2=version; atomic symlink swap
    local tmp=$1/.current.$$
    ln -sfn -- "$2" "$tmp"
    mv -T -- "$tmp" "$1/current"
}

prune_versions() { # $1=versions dir $2=current $3=keep count
    local kept=0 entry name
    for entry in "$1"/*; do
        [ -d "$entry" ] || continue
        name=$(basename -- "$entry")
        case "$name" in .*|current) continue;; esac
        [ "$name" != "$2" ] || continue
        kept=$((kept + 1))
        [ "$kept" -le "$3" ] || rm -rf -- "$entry"
    done
}

write_launcher() { # $1=prefix $2=data dir
    mkdir -p -- "$1/bin" "$2"
    render_launcher "$INSTALLER_DIR/airunner-services-launcher.sh" "$1/bin/airunner-services" "$EXECUTABLE" "$2"
}

do_upgrade() {
    [ "${EUID:-$(id -u)}" -ne 0 ] || warn "running as root; a user-level prefix is still used"
    local bundle prefix version data_dir
    bundle=$(abs_path "$BUNDLE")
    check_bundle "$bundle" "$EXECUTABLE"
    prefix=$(abs_path "$PREFIX")
    version=$VERSION_ARG
    [ "$VERSION_GIVEN" -eq 1 ] || version=$(default_version "$bundle")
    valid_version "$version" || fail "invalid --version: $version"
    data_dir=$(abs_path "${DATA_DIR_ARG:-$prefix/data}")
    check_paths "$prefix" "$bundle" "$prefix/versions/$version" "$data_dir"
    check_disk_space "$bundle" "$prefix"
    local versions=$prefix/versions
    local target=$versions/$version
    local staging=$versions/.staging-$version-$$
    local previous
    previous=$(current_version "$versions")
    clean_stale_staging "$versions"
    write_state "$prefix" "staging" "$previous" "$version"
    stage_bundle "$bundle" "$staging" "$versions"
    check_bundle "$staging" "$EXECUTABLE"
    [ "${AIRUNNER_UPGRADE_FAIL_AT:-}" != "verify" ] || fail "injected failure at verify"
    activate_staging "$staging" "$target" "$versions"
    prune_versions "$versions" "$version" "$KEEP_PREVIOUS"
    write_launcher "$prefix" "$data_dir"
    write_state "$prefix" "ok" "$previous" "$version"
    printf 'upgraded airunner-services %s -> %s\n' "${previous:-none}" "$version"
    printf '  application: %s\n' "$target"
    printf '  previous:    %s\n' "${previous:-none (fresh install state)}"
    printf '  data:        %s (untouched)\n' "$data_dir"
}

do_rollback() {
    local prefix
    prefix=$(abs_path "$PREFIX")
    if is_system_prefix "$prefix" && [ "$ALLOW_SYSTEM" -ne 1 ]; then
        fail "refusing system prefix without --allow-system-prefix: $prefix"
    fi
    local versions=$prefix/versions
    [ -d "$versions" ] || fail "no versions dir under prefix: $prefix"
    local target=$ROLLBACK_TO
    local active
    active=$(current_version "$versions")
    if [ -z "$target" ]; then
        target=$(state_field "$prefix" "previous")
        [ -n "$target" ] || fail "no previous version recorded; pass --rollback-to VER"
    fi
    valid_version "$target" || fail "invalid rollback target: $target"
    [ -d "$versions/$target" ] || fail "rollback target is not installed: $target"
    check_bundle "$versions/$target" "$EXECUTABLE"
    [ "$target" != "$active" ] || fail "already on version: $target"
    point_current "$versions" "$target"
    local data_dir
    data_dir=$(abs_path "${DATA_DIR_ARG:-$prefix/data}")
    write_launcher "$prefix" "$data_dir"
    write_state "$prefix" "rolled-back" "$active" "$target"
    printf 'rolled back airunner-services %s -> %s\n' "${active:-none}" "$target"
    printf '  application: %s\n' "$versions/$target"
    printf '  data:        %s (untouched; a migrated database is kept, never downgraded)\n' "$data_dir"
}

main() {
    parse_args "$@"
    if [ "$ROLLBACK" -eq 1 ]; then
        do_rollback
    else
        do_upgrade
    fi
}

main "$@"
