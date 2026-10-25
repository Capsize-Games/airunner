# AIRunner Services: manual user-level install (release P06)

Owner-run scenario for installing the Linux v1 services bundle without
root, Python, or Docker. No system install is performed by automation;
run these steps on the target machine and keep the output as evidence.

## 1. Prerequisites

- x86_64 Linux with bash and coreutils (Ubuntu 24.04 LTS baseline).
- The release directory: a P05 bundle plus this installer side by side:
  `install.sh`, `airunner-services-launcher.sh`,
  `airunner-services.desktop`, and the bundle directory containing
  `airunner-daemon`, `bundle-manifest.json`, `bin/`, and `legal/`.
- Enough free disk space for the bundle plus 50 MB of headroom; the
  installer checks this itself and refuses to start when short.

## 2. Install

From any working directory (it need not be the release directory, and
paths containing spaces are supported):

```sh
./install.sh --bundle ./airunner-services-1.2.3 --version 1.2.3
```

Expected result (paths under `~/.local/share/airunner`):

```text
installed airunner-services 1.2.3
  application: /home/owner/.local/share/airunner/versions/1.2.3
  launcher:    /home/owner/.local/share/airunner/bin/airunner-services
  data:        /home/owner/.local/share/airunner/data
  menu entry:  /home/owner/.local/share/applications/airunner-services.desktop
```

Useful options: `--prefix DIR` for another user-level location,
`--data-dir DIR` to separate user data further, `--version VER` to
override the bundle `VERSION` file, `--no-desktop` to skip the menu
entry and icon. Run `./install.sh --help` for the full list.
`AIRUNNER_INSTALL_REQUIRED_KB` overrides the free-space requirement
when extra headroom must be reserved; `XDG_DATA_HOME` redirects the
menu entry and icon.

## 3. Launch and verify

- Start `AIRunner Services` from the desktop menu, or run
  `~/.local/share/airunner/bin/airunner-services` directly.
- The launcher resolves the installed daemon, exports
  `AIRUNNER_BUNDLE_ROOT` (the version directory) and
  `AIRUNNER_DATA_DIR` (the data directory), then execs the daemon;
  explicit environment values are respected as overrides.
- Confirm the menu entry shows the installed icon, then verify the
  headless API (default HTTP 127.0.0.1:8080):
  `curl http://127.0.0.1:8080/health` (also `/api/v1/health`).
- The bundle is headless and Qt-free: there is no terminal window.
  When the daemon runs under systemd instead, check
  `systemctl status airunner-headless` and
  `journalctl -u airunner-headless`; for the user-level install
  above, the daemon logs to the configured runtime log directory.

## 4. Guarantees and limits

- No root: never run with sudo; prefixes under system directories
  (`/usr`, `/opt`, `/etc`, `/var`, ...) are refused unless
  `--allow-system-prefix` is passed explicitly.
- Installation and user data are separate: reinstalling a version
  replaces only `versions/<version>/` and never touches the data dir.
- Repeatable: re-running the same install command reproduces the same
  tree; an unrelated working directory and spaces in paths are safe.
- Uninstall and upgrades are owned by release issues P07/P08 and are
  not implemented here; do not hand-delete version directories that a
  later upgrade transaction may need for recovery.

## 5. Troubleshooting

- `no --version given and no VERSION file`: pass `--version` or add a
  `VERSION` file to the bundle directory.
- `insufficient disk space`: free space, then re-run; nothing was
  written because the check runs before any copy.
- `refusing system prefix`: pick a user-level `--prefix` instead.
- Menu entry without icon: the bundle carried no
  `share/icons/airunner-services.png`; the entry still launches.
