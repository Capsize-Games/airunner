"""Simple dev-time auto-reloader for AIRunner.

AIRunner headless mode relies on a Qt event loop in the main thread.
Uvicorn's built-in --reload is a poor fit for that architecture, so this
script provides a lightweight polling-based auto-restart wrapper.

It watches Python source files under one or more directories and restarts
a child command when changes are detected.

Usage:
    python -m airunner.dev.autorestart -- airunner-headless --host 0.0.0.0 --port 8080

Environment:
    AIRUNNER_DEV_WATCH_DIRS: colon-separated list of directories to watch (default: /app/src)
    AIRUNNER_DEV_POLL_INTERVAL: seconds between scans (default: 1.0)
"""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time
import urllib.request
import urllib.error
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class WatchConfig:
    watch_dirs: list[Path]
    poll_interval_seconds: float


@dataclass(frozen=True)
class HealthConfig:
    url: str
    interval_seconds: float
    timeout_seconds: float
    max_consecutive_failures: int


def _is_healthy(url: str, timeout_seconds: float) -> bool:
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
            status = int(getattr(resp, "status", 0) or 0)
            return 200 <= status < 300
    except Exception:
        return False


def _iter_py_files(watch_dirs: Iterable[Path]) -> Iterable[Path]:
    for watch_dir in watch_dirs:
        if not watch_dir.exists():
            continue
        for path in watch_dir.rglob("*.py"):
            # Avoid scanning common junk folders if a wider directory is mounted.
            parts = set(path.parts)
            if any(p in parts for p in {"__pycache__", ".git", ".mypy_cache"}):
                continue
            yield path


def _snapshot_mtimes(watch_dirs: list[Path]) -> dict[Path, float]:
    snapshot: dict[Path, float] = {}
    for path in _iter_py_files(watch_dirs):
        try:
            snapshot[path] = path.stat().st_mtime
        except FileNotFoundError:
            # File could disappear between rglob and stat.
            continue
    return snapshot


def _changed(prev: dict[Path, float], curr: dict[Path, float]) -> bool:
    if prev.keys() != curr.keys():
        return True
    for path, mtime in curr.items():
        if prev.get(path) != mtime:
            return True
    return False


def _terminate_process(proc: subprocess.Popen[bytes], timeout_seconds: float = 10.0) -> None:
    if proc.poll() is not None:
        return

    try:
        proc.send_signal(signal.SIGINT)
        proc.wait(timeout=timeout_seconds)
        return
    except Exception:
        pass

    try:
        proc.terminate()
        proc.wait(timeout=timeout_seconds)
        return
    except Exception:
        pass

    try:
        proc.kill()
    except Exception:
        pass


def _parse_args(argv: list[str]) -> tuple[WatchConfig, list[str]]:
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument(
        "--watch",
        action="append",
        default=[],
        help="Directory to watch (repeatable). Default comes from AIRUNNER_DEV_WATCH_DIRS or /app/src.",
    )
    parser.add_argument(
        "--poll",
        type=float,
        default=None,
        help="Polling interval in seconds (default from AIRUNNER_DEV_POLL_INTERVAL or 1.0).",
    )
    parser.add_argument("--", dest="cmd_sep", action="store_true")

    if "--" in argv:
        idx = argv.index("--")
        known = argv[:idx]
        child_cmd = argv[idx + 1 :]
    else:
        known = argv
        child_cmd = []

    ns = parser.parse_args(known)

    poll = ns.poll
    if poll is None:
        poll = float(os.environ.get("AIRUNNER_DEV_POLL_INTERVAL", "1.0"))

    watch_dirs: list[Path] = []
    if ns.watch:
        watch_dirs = [Path(p).resolve() for p in ns.watch]
    else:
        env_dirs = os.environ.get("AIRUNNER_DEV_WATCH_DIRS", "/app/src")
        watch_dirs = [Path(p).resolve() for p in env_dirs.split(":" ) if p.strip()]

    return WatchConfig(watch_dirs=watch_dirs, poll_interval_seconds=poll), child_cmd


def _load_health_config() -> HealthConfig:
    url = os.environ.get("AIRUNNER_DEV_HEALTHCHECK_URL", "http://127.0.0.1:8080/health").strip()
    try:
        interval = float(os.environ.get("AIRUNNER_DEV_HEALTHCHECK_INTERVAL", "5"))
    except Exception:
        interval = 5.0
    try:
        timeout = float(os.environ.get("AIRUNNER_DEV_HEALTHCHECK_TIMEOUT", "2"))
    except Exception:
        timeout = 2.0
    try:
        max_failures = int(os.environ.get("AIRUNNER_DEV_HEALTHCHECK_MAX_FAILURES", "3"))
    except Exception:
        max_failures = 3

    if interval <= 0:
        interval = 5.0
    if timeout <= 0:
        timeout = 2.0
    if max_failures <= 0:
        max_failures = 3

    return HealthConfig(
        url=url,
        interval_seconds=interval,
        timeout_seconds=timeout,
        max_consecutive_failures=max_failures,
    )


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    config, child_cmd = _parse_args(argv)

    if not child_cmd:
        raise SystemExit(
            "No child command provided. Usage: python -m airunner.dev.autorestart -- <cmd> [args...]"
        )

    print(
        f"[autorestart] watching: {', '.join(str(p) for p in config.watch_dirs)}; poll={config.poll_interval_seconds}s",
        flush=True,
    )
    print(f"[autorestart] starting: {' '.join(child_cmd)}", flush=True)

    health = _load_health_config()
    print(
        f"[autorestart] health watchdog: url={health.url} interval={health.interval_seconds}s timeout={health.timeout_seconds}s max_failures={health.max_consecutive_failures}",
        flush=True,
    )

    should_exit = False

    def _handle_signal(_signum: int, _frame):
        nonlocal should_exit
        should_exit = True

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    last_snapshot = _snapshot_mtimes(config.watch_dirs)
    proc = subprocess.Popen(child_cmd)

    last_health_check = 0.0
    consecutive_health_failures = 0

    try:
        while True:
            if should_exit:
                _terminate_process(proc)
                return 0

            rc = proc.poll()
            if rc is not None:
                # If the child exits, mirror its exit code.
                return int(rc)

            now = time.monotonic()
            if (now - last_health_check) >= health.interval_seconds:
                last_health_check = now
                if _is_healthy(health.url, health.timeout_seconds):
                    consecutive_health_failures = 0
                else:
                    consecutive_health_failures += 1
                    print(
                        f"[autorestart] healthcheck failed ({consecutive_health_failures}/{health.max_consecutive_failures}); url={health.url}",
                        flush=True,
                    )

                    if consecutive_health_failures >= health.max_consecutive_failures:
                        print("[autorestart] child appears wedged; restarting...", flush=True)
                        _terminate_process(proc)
                        consecutive_health_failures = 0
                        proc = subprocess.Popen(child_cmd)
                        # Give the new process a moment before the next probe.
                        last_health_check = time.monotonic()

            time.sleep(config.poll_interval_seconds)

            curr_snapshot = _snapshot_mtimes(config.watch_dirs)
            if _changed(last_snapshot, curr_snapshot):
                print("[autorestart] change detected; restarting...", flush=True)
                _terminate_process(proc)
                last_snapshot = curr_snapshot
                proc = subprocess.Popen(child_cmd)

    finally:
        _terminate_process(proc)


if __name__ == "__main__":
    raise SystemExit(main())
