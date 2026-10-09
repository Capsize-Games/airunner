#!/usr/bin/env bash
# Stage pinned native sidecars into a Linux v1 candidate bundle (C01).
#
# Usage:
#   stage-sidecars.sh --tarball FILE --bundle DIR [--manifest NAME] \
#       -- NAME...
#
# Extracts the pinned sidecar tarball, installs each named binary
# into the bundle's bin/ dir, and extends the bundle manifest with
# the staged files so the single manifest still covers every bundle
# byte. Runs AFTER the freeze: PyInstaller removes its output dir
# (--noconfirm), so pre-seeding bin/ would be wiped; and the
# inspector fails unmanifested files, so staging without extending
# the manifest would fail verification.
#
# Fails closed: a missing tarball/bundle/manifest, a named binary
# absent from the tarball, an already-recorded manifest path, or a
# manifest that is not valid JSON all exit non-zero. The manifest
# is rewritten atomically (temp file plus rename).
#
# Needs bash, coreutils, and python3 (JSON manifest surgery).
# shellcheck shell=bash
set -euo pipefail

SCRIPT_NAME="stage-sidecars"
HERE=$(cd -- "$(dirname -- "$0")" && pwd)
# shellcheck source=release-lib.sh
. "$HERE/release-lib.sh"

TARBALL=""
BUNDLE=""
MANIFEST="bundle-manifest.json"
NAMES=""

usage() {
    sed -n '2,/^# shellcheck/p' -- "$0" | sed 's/^# \{0,1\}//'
}

valid_name() { # $1=candidate; rejects empty/hidden/odd sidecar names
    case "$1" in
        "" | .*) return 1;;
    esac
    case "$1" in
        *[!A-Za-z0-9._+-]*) return 1;;
    esac
    return 0
}

stage_one() { # $1=name; installs it and records the manifest relpath
    binary=$(find "$WORK" -name "$1" -type f | head -n 1)
    [ -n "$binary" ] || fail "sidecar $1 absent from $TARBALL"
    install -m 755 "$binary" "$BUNDLE/bin/$1"
    STAGED="$STAGED bin/$1"
}

while [ $# -gt 0 ]; do
    case "$1" in
        --tarball)
            [ $# -ge 2 ] || fail "missing value for --tarball"
            TARBALL=$2; shift 2;;
        --tarball=*) TARBALL=${1#--tarball=}; shift;;
        --bundle)
            [ $# -ge 2 ] || fail "missing value for --bundle"
            BUNDLE=$2; shift 2;;
        --bundle=*) BUNDLE=${1#--bundle=}; shift;;
        --manifest)
            [ $# -ge 2 ] || fail "missing value for --manifest"
            MANIFEST=$2; shift 2;;
        --manifest=*) MANIFEST=${1#--manifest=}; shift;;
        --)
            shift
            while [ $# -gt 0 ]; do
                valid_name "$1" || fail "bad sidecar name: $1"
                NAMES="$NAMES$1
"
                shift
            done
            break;;
        -h | --help) usage; exit 0;;
        *) fail "unknown argument: $1";;
    esac
done

[ -n "$TARBALL" ] || fail "no --tarball given"
[ -f "$TARBALL" ] || fail "tarball is not a file: $TARBALL"
[ -n "$BUNDLE" ] || fail "no --bundle given"
[ -d "$BUNDLE" ] || fail "bundle is not a directory: $BUNDLE"
valid_name "$MANIFEST" || fail "bad --manifest name: $MANIFEST"
MANIFEST_PATH="$BUNDLE/$MANIFEST"
[ -f "$MANIFEST_PATH" ] || fail "bundle has no manifest: $MANIFEST"
[ -n "$NAMES" ] || fail "no sidecar names given after --"

WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
tar -xzf "$TARBALL" -C "$WORK"
mkdir -p "$BUNDLE/bin"
STAGED=""
while IFS= read -r name; do
    [ -n "$name" ] || continue
    stage_one "$name"
done <<STAGE_NAMES
$NAMES
STAGE_NAMES

export MANIFEST_PATH BUNDLE STAGED
python3 - <<'PYEOF'
import hashlib
import json
import os

manifest_path = os.environ["MANIFEST_PATH"]
bundle = os.environ["BUNDLE"]
with open(manifest_path, encoding="utf-8") as handle:
    manifest = json.load(handle)
recorded = {entry["path"] for entry in manifest["files"]}
for rel in os.environ["STAGED"].split():
    if rel in recorded:
        raise SystemExit(f"manifest already records {rel}")
    digest = hashlib.sha256()
    with open(os.path.join(bundle, rel), "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    manifest["files"].append({"path": rel, "sha256": digest.hexdigest()})
manifest["files"].sort(key=lambda entry: entry["path"])
tmp_path = manifest_path + ".tmp"
with open(tmp_path, "w", encoding="utf-8") as handle:
    json.dump(manifest, indent=2, fp=handle)
    handle.write("\n")
os.replace(tmp_path, manifest_path)
PYEOF
printf '%s: staged%s\n' "$SCRIPT_NAME" "$STAGED"
