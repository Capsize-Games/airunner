"""Exercise Debian postinst against temporary paths and fake identity tools."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
POSTINST = ROOT / "debian/airunner.postinst"


def _postinst_fixture(tmp_path: Path) -> tuple[Path, dict[str, str], Path]:
    """Return a path-rewritten postinst, fake-command environment, and log."""
    state = tmp_path / "var/lib/airunner"
    log_root = tmp_path / "var/log/airunner"
    config_root = tmp_path / "etc/airunner"
    seed_root = tmp_path / "usr/share/airunner"
    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir()
    getent = fake_bin / "getent"
    getent.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    getent.chmod(0o755)
    log = tmp_path / "chown-args.log"
    chown = fake_bin / "chown"
    chown.write_text(
        "#!/bin/sh\n"
        f"printf '%s\\n' \"$*\" >> '{log}'\n"
        "exec /usr/bin/chown \"$@\"\n",
        encoding="utf-8",
    )
    chown.chmod(0o755)

    source = POSTINST.read_text(encoding="utf-8")
    for original, replacement in (
        ("/var/lib/airunner", str(state)),
        ("/var/log/airunner", str(log_root)),
        ("/etc/airunner", str(config_root)),
        ("/usr/share/airunner", str(seed_root)),
        ("airunner:airunner", f"{os.getuid()}:{os.getgid()}"),
        ("root:airunner", f"{os.getuid()}:{os.getgid()}"),
    ):
        source = source.replace(original, replacement)
    script = tmp_path / "postinst-fixture"
    script.write_text(source, encoding="utf-8")
    script.chmod(0o755)
    env = dict(os.environ, PATH=f"{fake_bin}:/usr/bin:/bin")
    return script, env, log


def _run(script: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(script), "configure"],
        env=env,
        capture_output=True,
        check=False,
        text=True,
    )


def test_postinst_refuses_symlinked_runtime_parent_before_mutating_target(
    tmp_path: Path,
) -> None:
    script, env, _log = _postinst_fixture(tmp_path)
    state = tmp_path / "var/lib/airunner"
    outside = tmp_path / "outside-state"
    state.mkdir(parents=True)
    outside.mkdir()
    sentinel = outside / "keep.txt"
    sentinel.write_text("keep\n", encoding="utf-8")
    sentinel.chmod(0o644)
    (state / "runtime").symlink_to(outside, target_is_directory=True)

    result = _run(script, env)

    assert result.returncode != 0
    assert "refusing unsafe install path" in result.stderr
    assert not (outside / "configs").exists()
    assert sentinel.read_text(encoding="utf-8") == "keep\n"
    assert sentinel.stat().st_mode & 0o777 == 0o644


def test_postinst_refuses_symlinked_config_before_chown_or_chmod(
    tmp_path: Path,
) -> None:
    script, env, log = _postinst_fixture(tmp_path)
    config_root = tmp_path / "etc/airunner"
    outside = tmp_path / "outside-config"
    config_root.mkdir(parents=True)
    outside.write_text("fixture: true\n", encoding="utf-8")
    outside.chmod(0o600)
    (config_root / "daemon.yaml").symlink_to(outside)
    before = outside.stat()

    result = _run(script, env)

    after = outside.stat()
    assert result.returncode != 0
    assert "refusing unsafe install path" in result.stderr
    assert not log.exists()
    assert outside.stat().st_mode & 0o777 == 0o600
    assert (after.st_uid, after.st_gid, after.st_mtime_ns) == (
        before.st_uid,
        before.st_gid,
        before.st_mtime_ns,
    )


def test_postinst_upgrade_does_not_recursively_chown_user_files(
    tmp_path: Path,
) -> None:
    script, env, log = _postinst_fixture(tmp_path)
    state = tmp_path / "var/lib/airunner"
    runtime = state / "runtime"
    for path in (
        runtime / "configs",
        runtime / "sockets",
        state / "cache",
        state / "models",
        tmp_path / "var/log/airunner",
        tmp_path / "etc/airunner",
        tmp_path / "usr/share/airunner",
    ):
        path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "usr/share/airunner/daemon.yaml").write_text(
        "fixture: true\n", encoding="utf-8"
    )
    model = state / "models/user-model.bin"
    model.write_bytes(b"user model data\n")
    model.chmod(0o640)
    log_file = tmp_path / "var/log/airunner/user.log"
    log_file.write_text("user log data\n", encoding="utf-8")
    before = {
        path: (
            path.read_bytes(),
            path.stat().st_uid,
            path.stat().st_gid,
            path.stat().st_mode & 0o777,
            path.stat().st_mtime_ns,
            path.stat().st_ctime_ns,
        )
        for path in (model, log_file)
    }

    result = _run(script, env)

    assert result.returncode == 0, result.stderr
    for path, expected in before.items():
        current = path.stat()
        assert (
            path.read_bytes(),
            current.st_uid,
            current.st_gid,
            current.st_mode & 0o777,
            current.st_mtime_ns,
            current.st_ctime_ns,
        ) == expected
    calls = log.read_text(encoding="utf-8").splitlines()
    assert calls
    assert all("-R" not in call for call in calls)
    assert all(str(model) not in call and str(log_file) not in call for call in calls)
