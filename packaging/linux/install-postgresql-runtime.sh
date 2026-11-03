#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"

if (( EUID != 0 )); then
    echo "PostgreSQL prerequisite installation requires root; rerun this script with sudo." >&2
    exit 2
fi
if [[ ! -r /etc/os-release ]]; then
    echo "Cannot identify the target operating system; PostgreSQL prerequisites require Ubuntu 24.04 amd64." >&2
    exit 2
fi
# /etc/os-release is a trusted operating-system file and defines the standard
# shell variables used by Ubuntu package tooling.
# shellcheck disable=SC1091
. /etc/os-release
if [[ "${ID:-}" != ubuntu || "${VERSION_ID:-}" != 24.04 ]] || \
    [[ "$(dpkg --print-architecture)" != amd64 ]]; then
    echo "PostgreSQL prerequisites require Ubuntu 24.04 amd64; no packages were changed." >&2
    exit 2
fi

cd "$script_dir"
if ! sha256sum -c SHA256SUMS >/dev/null; then
    echo "PostgreSQL prerequisite payload failed SHA-256 verification; no packages were changed." >&2
    exit 2
fi
if ! (cd build-supplement && sha256sum -c SHA256SUMS >/dev/null); then
    echo "Build compatibility payload failed SHA-256 verification; no packages were changed." >&2
    exit 2
fi
if ! grep -Fq '"root": "libpq5=16.15-0ubuntu0.24.04.1"' \
    postgresql-libpq-noble-runtime-lock.json; then
    echo "PostgreSQL package lock does not name the reviewed Noble libpq5 root; no packages were changed." >&2
    exit 2
fi

all_exact=true
supplement_needed=false
if dpkg-query -W -f='${db:Status-Status}' libc6-dev 2>/dev/null | grep -qx installed; then
    supplement_needed=true
fi
mapfile -t package_specs < install-packages.txt
if [[ "$supplement_needed" == true ]]; then
    mapfile -t supplement_specs < build-supplement/install-packages.txt
    package_specs+=("${supplement_specs[@]}")
fi
for package_spec in "${package_specs[@]}"; do
    [[ "$package_spec" == *=* ]] || {
        echo "Invalid package entry in install list; no packages were changed." >&2
        exit 2
    }
    package="${package_spec%%=*}"
    wanted="${package_spec#*=}"
    [[ -n "$package" && -n "$wanted" ]] || {
        echo "Invalid package entry in install-packages.txt; no packages were changed." >&2
        exit 2
    }
    installed="$(dpkg-query -W -f='${Version}' "$package" 2>/dev/null || true)"
    if [[ "$installed" == "$wanted" ]]; then
        continue
    fi
    all_exact=false
    if [[ -n "$installed" ]] && dpkg --compare-versions "$installed" gt "$wanted"; then
        echo "$package is already newer than the reviewed version; refusing a downgrade." >&2
        exit 2
    fi
done
if [[ "$all_exact" == true ]]; then
    echo "Reviewed PostgreSQL OS package versions are already installed."
    exit 0
fi

command -v dpkg-deb >/dev/null
command -v apt-get >/dev/null
repo="$(mktemp -d "${TMPDIR:-/tmp}/airunner-libpq.XXXXXXXX")"
trap 'rm -rf -- "$repo"' EXIT
mkdir -p "$repo/debs" "$repo/lists/partial" "$repo/archives/partial"
cp -- debs/*.deb build-supplement/debs/*.deb "$repo/debs/"
# apt's file transport may read the public local repository as `_apt`.
# mktemp creates a private root directory, so grant read/traverse only on the
# repository metadata and reviewed archives before apt update.
chmod 0755 "$repo" "$repo/debs"
chmod 0644 "$repo"/debs/*.deb
printf '' > "$repo/Packages"
for deb in "$repo"/debs/*.deb; do
    metadata="$(dpkg-deb -f "$deb")"
    filename="${deb##*/}"
    size="$(stat -c %s "$deb")"
    digest="$(sha256sum "$deb")"
    digest="${digest%% *}"
    printf '%s\nFilename: debs/%s\nSize: %s\nSHA256: %s\n\n' \
        "$metadata" "$filename" "$size" "$digest" >> "$repo/Packages"
done
gzip -c -n -9 "$repo/Packages" > "$repo/Packages.gz"
packages_sha="$(sha256sum "$repo/Packages")"
packages_sha="${packages_sha%% *}"
packages_size="$(stat -c %s "$repo/Packages")"
compressed_sha="$(sha256sum "$repo/Packages.gz")"
compressed_sha="${compressed_sha%% *}"
compressed_size="$(stat -c %s "$repo/Packages.gz")"
{
    printf 'Origin: AIRunner reviewed PostgreSQL runtime prerequisites\n'
    printf 'Label: AIRunner Ubuntu Noble libpq closure\n'
    printf 'Suite: noble-local\nCodename: noble-local\n'
    printf 'Architectures: amd64\nComponents: main\n'
    printf 'Description: Hash-verified local Ubuntu packages\nSHA256:\n'
    printf ' %s %s Packages\n %s %s Packages.gz\n' \
        "$packages_sha" "$packages_size" "$compressed_sha" "$compressed_size"
} > "$repo/Release"
source_list="$repo/sources.list"
printf 'deb [trusted=yes] file:%s ./\n' "$repo" > "$source_list"

apt_local() {
    apt-get \
        -o "Dir::Etc::sourcelist=$source_list" \
        -o Dir::Etc::sourceparts=- \
        -o "Dir::State::lists=$repo/lists" \
        -o "Dir::Cache::archives=$repo/archives" \
        -o APT::Get::List-Cleanup=0 \
        "$@"
}

apt_local update
cp -- "$repo"/debs/*.deb "$repo/archives/"
apt_local --no-download --no-remove --no-install-recommends -y install \
    "${package_specs[@]}"

for package_spec in "${package_specs[@]}"; do
    package="${package_spec%%=*}"
    wanted="${package_spec#*=}"
    installed="$(dpkg-query -W -f='${Version}' "$package")"
    if [[ "$installed" != "$wanted" ]]; then
        echo "Installed $package version differs from the reviewed lock." >&2
        exit 1
    fi
done
if [[ "$supplement_needed" == true ]]; then
    echo "Installed libpq closure and conditional glibc development compatibility supplement."
else
    echo "Installed the reviewed Ubuntu 24.04 libpq prerequisite closure."
fi
