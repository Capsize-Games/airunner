"""Process management helpers for RuntimeMixin."""

from __future__ import annotations

import time
import subprocess


class ProcessManagerMixin:
    """Provide process-killing helpers for port management."""

    def _kill_via_lsof(self, port: int) -> bool:
        """Try to kill a process using lsof."""
        try:
            result = subprocess.run(
                ["lsof", "-ti", f":{port}"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode != 0 or not result.stdout.strip():
                return False

            for pid in result.stdout.strip().split("\n"):
                try:
                    self.logger.info(
                        "Killing process %s using port %s",
                        pid,
                        port,
                    )
                    subprocess.run(
                        ["kill", "-9", pid],
                        timeout=5,
                        check=False,
                    )
                    time.sleep(0.5)
                except Exception as exc:
                    self.logger.warning(
                        "Failed to kill process %s: %s",
                        pid,
                        exc,
                    )
            return True
        except FileNotFoundError:
            return False
        except Exception as exc:
            self.logger.debug(
                "Could not kill process on port %s: %s",
                port,
                exc,
            )
            return False

    def _kill_via_netstat(self, port: int) -> None:
        """Try to kill a process using netstat."""
        try:
            result = subprocess.run(
                ["netstat", "-tlnp"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            for line in result.stdout.split("\n"):
                if f":{port}" not in line or "LISTEN" not in line:
                    continue
                parts = line.split()
                if len(parts) <= 6:
                    continue
                pid_program = parts[6]
                if "/" not in pid_program:
                    continue
                pid = pid_program.split("/")[0]
                try:
                    self.logger.info(
                        "Killing process %s using port %s",
                        pid,
                        port,
                    )
                    subprocess.run(
                        ["kill", "-9", pid],
                        timeout=5,
                        check=False,
                    )
                except Exception as exc:
                    self.logger.warning(
                        "Failed to kill process %s: %s",
                        pid,
                        exc,
                    )
        except Exception as exc:
            self.logger.debug(
                "Could not check for processes on port %s: %s",
                port,
                exc,
            )

    def _kill_process_on_port(self, port: int) -> None:
        """Kill any process using the specified port."""
        if not self._kill_via_lsof(port):
            self._kill_via_netstat(port)
