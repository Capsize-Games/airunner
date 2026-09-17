"""Remove sidecar runtime configs left behind by dead processes.

Each sidecar launch writes a throwaway daemon config into the runtime
config directory and deletes it again in ``_cleanup_config``. That
delete only runs on the paths that end in Python: a graceful ``stop``,
a spawn failure, or a sidecar that exits during startup.

It cannot run when the parent is killed, crashes, or the machine loses
power, and those are ordinary events. The result is that the configs
accumulate silently and forever: one machine had 440 of them, dating
back four months, from art, TTS and server sidecars alike.

No exit hook fixes that, because ``SIGKILL`` runs no hooks. So the
directory is swept when a new sidecar starts instead, which is the one
moment the process is certain to reach: any config no live process has
open is by definition finished with.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

PROC = Path("/proc")


def live_config_paths() -> Optional[set[str]]:
    """Return config paths named on a running process's command line.

    Returns:
        Every ``.yaml`` path appearing in any process's argv, or None
        when ``/proc`` cannot be read. None means "unknown", and a
        caller must sweep nothing rather than guess -- deleting the
        config of a running sidecar would take the sidecar down with
        it on its next restart.
    """
    if not PROC.is_dir():
        return None
    found: set[str] = set()
    try:
        entries = list(PROC.iterdir())
    except OSError:
        return None
    for entry in entries:
        if entry.name.isdigit():
            found.update(_yaml_arguments(entry))
    return found


def _yaml_arguments(proc_entry: Path) -> set[str]:
    """Return the ``.yaml`` arguments of one process, if it is readable.

    A process that exits mid-scan, or belongs to another user, is
    skipped rather than raising: it is one missed candidate for the
    sweep, not a failure.
    """
    try:
        raw = (proc_entry / "cmdline").read_bytes()
    except OSError:
        return set()
    arguments = raw.split(b"\0")
    return {
        argument.decode("utf-8", "replace")
        for argument in arguments
        if argument.endswith(b".yaml")
    }


def sweep(
    config_dir: Path, prefix: str, keep: Optional[Path] = None
) -> int:
    """Delete configs with this prefix that no live process is using.

    Args:
        config_dir: The runtime config directory to sweep.
        prefix: Filename prefix, e.g. ``airunner-art-runtime-``.
        keep: A config to spare whatever else is decided -- the one
            the calling launcher has just written, which nothing has
            opened yet and so cannot look live.

    Returns:
        How many files were removed. Zero when ``/proc`` is unreadable,
        because the sweep fails closed.
    """
    live = live_config_paths()
    if live is None:
        return 0
    spared = str(keep) if keep is not None else ""
    removed = 0
    for path in sorted(config_dir.glob(f"{prefix}*.yaml")):
        if str(path) == spared or str(path) in live:
            continue
        removed += _remove(path)
    return removed


def _remove(path: Path) -> int:
    """Delete one stale config, reporting whether it went."""
    try:
        path.unlink()
    except OSError:
        return 0
    return 1


def sweep_all(config_dir: Path, keep: Optional[Path] = None) -> int:
    """Sweep every sidecar prefix this runtime writes."""
    prefixes = (
        "airunner-art-runtime-",
        "airunner-tts-runtime-",
        "airunner-server-",
        "airunner-headless-",
    )
    return sum(sweep(config_dir, prefix, keep) for prefix in prefixes)
