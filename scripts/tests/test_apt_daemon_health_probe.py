"""Run the installed-package health probe without a system Python dependency."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "packaging/apt"))

import publisher  # noqa: E402


@pytest.mark.parametrize(
    ("statuses", "curl_exit", "expected_exit", "expected_attempts"),
    [
        ("503 200", 0, 0, 2),
        ("301", 0, 1, 45),
        ("200", 7, 1, 45),
    ],
)
def test_health_probe_requires_exact_success_and_bounds_retries(
    tmp_path: Path,
    statuses: str,
    curl_exit: int,
    expected_exit: int,
    expected_attempts: int,
) -> None:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    # PATH contains no Python; the probe uses the curl installed by its parent.
    (fake_bin / "sleep").write_text("#!/bin/bash\nexit 0\n")
    (fake_bin / "curl").write_text(
        "#!/bin/bash\n"
        'attempt=0; if [ -f "$COUNTER" ]; then read -r attempt < "$COUNTER"; fi\n'
        'attempt=$((attempt + 1)); echo "$attempt" > "$COUNTER"\n'
        'read -ra statuses <<< "$STATUSES"\n'
        'index=$((attempt - 1)); if ((index >= ${#statuses[@]})); then index=$((${#statuses[@]} - 1)); fi\n'
        'printf %s "${statuses[$index]}"\n'
        'exit "$CURL_EXIT"\n'
    )
    for script in fake_bin.iterdir():
        script.chmod(0o755)
    counter = tmp_path / "attempts"
    result = subprocess.run(
        ["/bin/bash", "--noprofile", "--norc", "-euc", publisher._DAEMON_HEALTH_PROBE],
        env={
            "PATH": str(fake_bin),
            "HOME": str(tmp_path),
            "COUNTER": str(counter),
            "STATUSES": statuses,
            "CURL_EXIT": str(curl_exit),
        },
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == expected_exit, result.stderr
    assert int(counter.read_text()) == expected_attempts
    assert ("did not become healthy" in result.stderr) == bool(expected_exit)
