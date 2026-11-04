#!/bin/sh
# Install the host-local apt pull publisher and enable its systemd timer.
set -eu
umask 077

usage() {
    echo "usage: install-publisher.sh --config-source ROOT_ONLY_JSON" >&2
}

if [ "$(id -u)" -ne 0 ]; then
    echo "publisher installation requires root" >&2
    exit 1
fi
if [ "$#" -ne 2 ] || [ "$1" != "--config-source" ]; then
    usage
    exit 2
fi

config_source=$2
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
repo_root=$(CDPATH= cd -- "$script_dir/../.." && pwd)
publisher_source=$repo_root/packaging/apt/publisher.py
publish_source=$repo_root/packaging/apt/publish.sh
unit_source=$script_dir/airunner-apt-publisher.service
timer_source=$script_dir/airunner-apt-publisher.timer
config_target=/etc/airunner-apt-publisher.json
publisher_target=/usr/local/libexec/airunner-apt-publisher.py

if [ ! -f "$config_source" ] || [ -L "$config_source" ]; then
    echo "root-only publisher configuration source is unavailable" >&2
    exit 1
fi
for source in "$publisher_source" "$publish_source" "$unit_source" "$timer_source"; do
    if [ ! -f "$source" ] || [ -L "$source" ]; then
        echo "publisher installation source is unavailable" >&2
        exit 1
    fi
done
if [ -e "$config_target" ] || [ -L "$config_target" ]; then
    echo "publisher configuration already exists; refusing to replace it" >&2
    exit 1
fi

staged_config=$(mktemp /etc/.airunner-apt-publisher.XXXXXX)
cleanup() {
    rm -f "$staged_config"
}
trap cleanup EXIT HUP INT TERM
install -m 0600 "$config_source" "$staged_config"
python3 -I "$publisher_source" --config "$staged_config" --validate-config
publish_target=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["publish_script"])' "$staged_config")
case "$publish_target" in
    /*) ;;
    *) echo "publisher target must be absolute" >&2; exit 1 ;;
esac
case "$publish_target" in
    *[!A-Za-z0-9_./+-]*) echo "publisher target path is invalid" >&2; exit 1 ;;
    */../*|*/..|*/./*) echo "publisher target path is invalid" >&2; exit 1 ;;
esac

if [ -L "$publish_target" ] || { [ -e "$publish_target" ] && [ ! -f "$publish_target" ]; }; then
    echo "existing publisher target is not a regular file" >&2
    exit 1
fi
if [ -f "$publish_target" ] && [ ! -e "$publish_target.codex-backup" ]; then
    cp -p "$publish_target" "$publish_target.codex-backup"
fi
install -D -m 0600 "$staged_config" "$config_target"
install -D -m 0755 "$publisher_source" "$publisher_target"
install -D -m 0755 "$publish_source" "$publish_target"
install -D -m 0644 "$unit_source" /etc/systemd/system/airunner-apt-publisher.service
install -D -m 0644 "$timer_source" /etc/systemd/system/airunner-apt-publisher.timer
systemctl daemon-reload
systemctl enable --now airunner-apt-publisher.timer
