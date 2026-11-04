#!/bin/sh
# Add one verified .deb to a staged reprepro tree. The caller supplies the
# live signing-key directory at runtime; this source file contains no key path.
set -eu
umask 027

if [ "$#" -ne 4 ]; then
    echo "usage: publish.sh STAGING_ROOT GNUPGHOME SUITE DEB" >&2
    exit 2
fi

repository_root=$1
gnupg_home=$2
suite=$3
deb=$4

case "$repository_root" in /*) ;; *) echo "repository root must be absolute" >&2; exit 2 ;; esac
case "$gnupg_home" in /*) ;; *) echo "GNUPGHOME must be absolute" >&2; exit 2 ;; esac
case "$suite" in *[!a-z0-9-]*|"") echo "suite is invalid" >&2; exit 2 ;; esac
if [ ! -d "$repository_root" ] || [ ! -d "$gnupg_home" ]; then
    echo "repository or signing-key directory is unavailable" >&2
    exit 1
fi
config=${AIRUNNER_APT_PUBLISHER_CONFIG:-/etc/airunner-apt-publisher.json}
if [ ! -f "$config" ] || [ -L "$config" ]; then
    echo "publisher configuration is unavailable" >&2
    exit 1
fi
live_root=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["repo_root"])' "$config")
configured_gnupg=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["gnupg_home"])' "$config")
configured_suite=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["suite"])' "$config")
if [ "$(CDPATH= cd -- "$(dirname -- "$repository_root")" && pwd)" != \
     "$(CDPATH= cd -- "$(dirname -- "$live_root")" && pwd)" ] ||
   [ "$(CDPATH= cd -- "$repository_root" && pwd)" = \
     "$(CDPATH= cd -- "$live_root" && pwd)" ] ||
   [ "$gnupg_home" != "$configured_gnupg" ] ||
   [ "$suite" != "$configured_suite" ]; then
    echo "publisher accepts only a sibling staging tree for its configured target" >&2
    exit 1
fi
if [ ! -f "$deb" ] || [ -L "$deb" ]; then
    echo "Debian package must be a regular non-symlink file" >&2
    exit 1
fi

export GNUPGHOME="$gnupg_home"
reprepro -b "$repository_root" includedeb "$suite" "$deb"
reprepro -b "$repository_root" list "$suite" airunner
