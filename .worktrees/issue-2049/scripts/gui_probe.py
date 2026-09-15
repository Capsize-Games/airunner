#!/usr/bin/env python3
"""Launch AIRunner with a live GUI probe and execute scripted actions."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
import signal
import subprocess
import sys
import time
import uuid
from pathlib import Path


def _probe_base_path() -> Path:
    raw_path = os.environ.get(
        "AIRUNNER_BASE_PATH",
        "~/.local/share/airunner",
    )
    return Path(raw_path).expanduser().resolve()


def _validate_session_dir(session_dir: Path) -> Path:
    base_path = _probe_base_path()
    try:
        session_dir.relative_to(base_path)
    except ValueError as exc:
        raise ValueError(
            "Probe session dir must stay inside AIRUNNER_BASE_PATH: "
            f"{base_path}"
        ) from exc
    return session_dir


def _build_session_dir(requested: str | None) -> Path:
    if requested:
        session_dir = Path(requested).expanduser().resolve()
    else:
        stamp = time.strftime("%Y%m%d-%H%M%S")
        session_dir = _probe_base_path() / "gui-probe" / stamp
    session_dir = _validate_session_dir(session_dir)
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir


def _launch_process(
    command: str,
    session_dir: Path,
    repo_root: Path,
) -> tuple[subprocess.Popen, Path]:
    probe_dir = session_dir / "probe"
    probe_dir.mkdir(parents=True, exist_ok=True)
    log_path = session_dir / "gui.log"
    env = os.environ.copy()
    env["AIRUNNER_GUI_PROBE_DIR"] = str(probe_dir)
    env.setdefault("AIRUNNER_LOG_LEVEL", "DEBUG")
    env.setdefault("AIRUNNER_SAVE_LOG_TO_FILE", "1")
    env.setdefault(
        "AIRUNNER_LOG_FILE",
        str(session_dir / "airunner.app.log"),
    )
    log_handle = log_path.open("w", encoding="utf-8")
    process = subprocess.Popen(
        shlex.split(command),
        cwd=repo_root,
        env=env,
        stdout=log_handle,
        stderr=subprocess.STDOUT,
    )
    return process, log_path


def _wait_for_ready(
    process: subprocess.Popen,
    probe_dir: Path,
    timeout_seconds: float,
) -> dict:
    ready_path = probe_dir / "ready.json"
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if ready_path.exists():
            return json.loads(ready_path.read_text(encoding="utf-8"))
        if process.poll() is not None:
            raise RuntimeError("GUI process exited before probe became ready")
        time.sleep(0.1)
    raise RuntimeError("Timed out waiting for the GUI probe to become ready")


def _command_payload(action_token: str) -> dict:
    action, _, value = action_token.partition(":")
    if action == "ping":
        return {"action": "ping"}
    if action == "wait":
        seconds = float(value or "0")
        if seconds < 0:
            raise ValueError("wait action requires a non-negative delay")
        return {"action": "wait", "seconds": seconds}
    if action == "click":
        return {"action": "click", "object_name": value}
    if action == "widget-state":
        return {"action": "widget_state", "object_name": value}
    if action == "dump-widget-tree":
        return {"action": "dump_widget_tree", "artifact": value or None}
    if action == "screenshot":
        return {"action": "screenshot", "artifact": value or None}
    raise ValueError(f"Unsupported action token: {action_token}")


def _send_command(probe_dir: Path, payload: dict) -> Path:
    command_id = str(uuid.uuid4())
    command_path = probe_dir / "commands" / f"{command_id}.json"
    command_path.write_text(
        json.dumps({**payload, "id": command_id}, indent=2),
        encoding="utf-8",
    )
    return probe_dir / "responses" / f"{command_id}.json"


def _wait_for_response(
    process: subprocess.Popen,
    response_path: Path,
    timeout_seconds: float,
) -> dict:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if response_path.exists():
            return json.loads(response_path.read_text(encoding="utf-8"))
        if process.poll() is not None:
            raise RuntimeError("GUI process exited while waiting for action")
        time.sleep(0.05)
    raise TimeoutError("Timed out waiting for GUI probe response")


def _collect_gdb_backtrace(pid: int, output_path: Path) -> str | None:
    if shutil.which("gdb") is None:
        return None
    command = [
        "gdb",
        "-p",
        str(pid),
        "-batch",
        "-ex",
        "set pagination off",
        "-ex",
        "thread apply all bt",
        "-ex",
        "py-bt",
        "-ex",
        "detach",
        "-ex",
        "quit",
    ]
    with output_path.open("w", encoding="utf-8") as handle:
        subprocess.run(
            command,
            stdout=handle,
            stderr=subprocess.STDOUT,
            timeout=20,
            check=False,
        )
    return str(output_path)


def _write_freeze_report(
    process: subprocess.Popen,
    session_dir: Path,
    payload: dict,
    log_path: Path,
) -> Path:
    os.kill(process.pid, signal.SIGUSR1)
    gdb_path = _collect_gdb_backtrace(
        process.pid,
        session_dir / "gdb-backtrace.txt",
    )
    report = {
        "pid": process.pid,
        "action": payload,
        "log_path": str(log_path),
        "gdb_backtrace_path": gdb_path,
        "reported_at": time.time(),
    }
    report_path = session_dir / "freeze-report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report_path


def _terminate_process(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def main() -> int:
    parser = argparse.ArgumentParser(description="AIRunner GUI probe")
    parser.add_argument(
        "--launch-command",
        default="./scripts/run.sh",
        help="Command used to start the application",
    )
    parser.add_argument(
        "--session-dir",
        help="Optional directory for logs, probe files, and artifacts",
    )
    parser.add_argument(
        "--ready-timeout",
        type=float,
        default=60.0,
        help="Seconds to wait for the probe to become ready",
    )
    parser.add_argument(
        "--action-timeout",
        type=float,
        default=10.0,
        help="Seconds to wait for each action response",
    )
    parser.add_argument(
        "--action",
        action="append",
        default=[],
        help=(
            "Action token to execute. Supported forms: ping, wait:seconds, "
            "click:object_name, widget-state:object_name, "
            "dump-widget-tree[:file.json], screenshot[:file.png]"
        ),
    )
    parser.add_argument(
        "--keep-running",
        action="store_true",
        help="Leave the GUI process running after actions complete",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    session_dir = _build_session_dir(args.session_dir)
    process, log_path = _launch_process(
        args.launch_command,
        session_dir,
        repo_root,
    )
    probe_dir = session_dir / "probe"

    try:
        ready = _wait_for_ready(process, probe_dir, args.ready_timeout)
        print(
            json.dumps(
                {"session_dir": str(session_dir), "ready": ready},
                indent=2,
            )
        )

        actions = args.action or ["ping", "dump-widget-tree", "screenshot"]
        for action_token in actions:
            payload = _command_payload(action_token)
            if payload.get("action") == "wait":
                time.sleep(float(payload.get("seconds", 0.0)))
                print(
                    json.dumps(
                        {
                            "action": "wait",
                            "ok": True,
                            "result": {
                                "seconds": payload.get("seconds", 0.0),
                            },
                        },
                        indent=2,
                    )
                )
                continue
            response_path = _send_command(probe_dir, payload)
            try:
                response = _wait_for_response(
                    process,
                    response_path,
                    args.action_timeout,
                )
            except TimeoutError:
                report_path = _write_freeze_report(
                    process,
                    session_dir,
                    payload,
                    log_path,
                )
                print(
                    json.dumps(
                        {
                            "ok": False,
                            "freeze_report": str(report_path),
                            "log_path": str(log_path),
                        },
                        indent=2,
                    )
                )
                return 1
            print(json.dumps(response, indent=2))
            if not response.get("ok", False):
                return 1
        return 0
    finally:
        if not args.keep_running:
            _terminate_process(process)


if __name__ == "__main__":
    sys.exit(main())