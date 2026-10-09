# AIRunner Services: safe uninstall (release P08)

Owner-run scenario for removing the Linux v1 services bundle
installed by `packaging/linux/install.sh`. No system uninstall is
performed by automation; run these steps on the target machine.

## 1. Default uninstall: app removed, user data preserved

From any working directory (it need not be the release directory,
and paths containing spaces are supported):

```sh
./uninstall.sh --prefix ~/.local/share/airunner
```

This removes only installer-owned artifacts:

- every `versions/<version>/` directory that carries a
  `bundle-manifest.json` install marker, plus the `current` link;
- the launcher `<prefix>/bin/airunner-services`;
- the menu entry and icon, but only when the installed
  `airunner-services.desktop` entry points at this prefix's
  launcher (an entry owned by another install is kept).

Unmanaged files are kept with a warning: version directories
without an install marker, a non-launcher file that replaced
`<prefix>/bin/airunner-services`, and a foreign menu entry.

User data is always preserved by default: models, media, the
SQLite database, settings, logs, and backups are untouched, and
the data directory path is printed for confirmation. Re-running
the same command is safe (idempotent); missing parts are skipped.

## 2. Explicit managed-data deletion

Managed data is deleted only when both flags are passed:

```sh
./uninstall.sh --prefix ~/.local/share/airunner --delete-data --yes
```

With `--delete-data` alone the script prints the deletion plan
and exits without deleting anything; `--yes` confirms it. Each
listed file is re-validated immediately before deletion, and the
data directory itself is removed only when left completely empty
(plain `rmdir`, which refuses non-empty directories).

Deletion scope is an allowlist of owned files directly under the
data directory:

- `airunner.db` plus its SQLite sidecars (`airunner.db-journal`,
  `airunner.db-shm`, `airunner.db-wal`);
- `settings.json`;
- `service.log`.

Every candidate must be a regular file (never a symlink or a
directory), owned by the current user, and resolved inside the
data directory; anything else is skipped with a warning. The
filesystem root and the home directory are refused as data
directories outright.

## 3. Backup and custom-path exclusions

Back up the data directory before any deletion:

```sh
cp -a ~/.local/share/airunner/data ~/airunner-data-backup
```

The following are never deleted by either uninstall mode:

- `models/` and `media/` libraries, including large downloads;
- `backups/` archives and any other directory under the data dir;
- custom model/media paths configured inside the application:
  deletion never follows a path outward, so an application
  setting that points at another location (or a symlink left in
  the data dir) is out of scope by construction;
- the data directory recorded by `--data-dir` at install time is
  honored (read back from the installed launcher), but passing a
  different `--data-dir` at uninstall time only re-targets the
  allowlisted files above, never a recursive directory removal.

There is no recursive deletion of any user-selected directory in
this tool. If a custom library must go, delete it yourself after
verifying its contents.

## 4. Privacy wording alignment

Later privacy documents (release issues L01/L02) build on these
promises: uninstalling the application does not erase personal
data; erasure is a separate explicit action with a visible file
list; backups and user libraries outside the allowlist stay
untouched. Do not weaken these statements without owner review.

## 5. Troubleshooting

- `re-run with --yes`: `--delete-data` without `--yes` only
  shows the plan; nothing was deleted.
- `refusing system prefix`: pick the user-level `--prefix` used
  at install time, or pass `--allow-system-prefix` deliberately.
- `keeping unmanaged entry`: a directory under `versions/` has
  no install marker, so it was left alone; inspect it by hand.
- `keeping menu entry owned by another install`: the menu entry
  points at a different prefix; uninstall that prefix instead.
- `no managed data files found`: the allowlisted files are
  already gone; remaining user files are intentionally kept.
