#!/usr/bin/env python3
"""Prepare locked eSpeak/CMake inputs and run the offline Ubuntu build."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import shutil
import signal
import subprocess
import sys
import tarfile
import tempfile
from datetime import datetime, timezone
from typing import Any, Callable
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
LOCK_RELATIVE = "packaging/espeak/source-lock.json"
SNAPSHOT_FILES = (
    "scripts/build_espeak_native_payload.py",
    "scripts/intake_espeak_source.py",
    LOCK_RELATIVE,
    "packaging/espeak/0001-offline-no-playback.patch",
    "packaging/espeak/BUILD.md",
)
CMAKE_URL = "https://github.com/Kitware/CMake/releases/download/v3.31.6/cmake-3.31.6-linux-x86_64.tar.gz"
CMAKE_ARCHIVE_SHA256 = "5a1133ff103c71eb5120e2cc3de922733e7d8a26a98ae716397e8676adb367bf"
CMAKE_BINARY_SHA256 = "c4b3b237dc7a013590db9e90f70fca2dfdedde09521e920d3339569ea364230a"
CMAKE_ROOT = "cmake-3.31.6-linux-x86_64"
BUILD_IMAGE = (
    "nvidia/cuda:12.9.2-devel-ubuntu24.04@sha256:"
    "16656a1ef115bca9e1f820c6349876f1486d2b3c9a0e615773799fe402960dc5"
)
CANONICAL_GIT_URL = "https://github.com/espeak-ng/espeak-ng.git"
RECEIPT_NAME = "launch-receipt.json"
RECIPE_NAME = "prepare-and-build-recipe.md"
MAX_DOWNLOAD_BYTES = 100 * 1024 * 1024
GIT_TIMEOUT_SECONDS = 180
PREPARE_TIMEOUT_SECONDS = 600
DEFAULT_BUILD_TIMEOUT_SECONDS = 600
MAX_LOG_TAIL = 4000


class PreparationError(RuntimeError):
    """A locked build input or isolated build step failed validation."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _bounded_tail(path: Path, limit: int = MAX_LOG_TAIL) -> str:
    if not path.exists():
        return ""
    with path.open("rb") as stream:
        stream.seek(0, os.SEEK_END)
        stream.seek(max(0, stream.tell() - limit))
        return stream.read().decode("utf-8", errors="replace")


def _write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    encoded = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _new_private_work_dir(path: Path) -> Path:
    path = path.expanduser()
    if path.exists() or path.is_symlink():
        raise PreparationError("work directory must not already exist")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.mkdir(mode=0o700)
    os.chmod(path, 0o700)
    return path.resolve(strict=True)


def _regular_file(path: Path, label: str) -> Path:
    if path.is_symlink() or not path.is_file():
        raise PreparationError(f"{label} must be an existing regular file")
    return path.resolve(strict=True)


def _private_git_dir(path: Path) -> Path:
    if path.is_symlink() or not path.is_dir():
        raise PreparationError("supplied Git mirror must be an existing real directory")
    resolved = path.resolve(strict=True)
    result = subprocess.run(
        ["git", f"--git-dir={resolved}", "rev-parse", "--is-bare-repository"],
        capture_output=True,
        text=True,
        timeout=GIT_TIMEOUT_SECONDS,
        check=False,
        env=_git_env(),
    )
    if result.returncode or result.stdout.strip() != "true":
        raise PreparationError("supplied Git mirror is not a bare repository")
    return resolved


def _git_output(git_dir: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", f"--git-dir={git_dir}", *args],
            capture_output=True,
            text=True,
            timeout=GIT_TIMEOUT_SECONDS,
            check=False,
            env=_git_env(),
        )
    except subprocess.TimeoutExpired as exc:
        raise PreparationError("Git source verification timed out") from exc
    if result.returncode:
        raise PreparationError("Git source verification failed")
    return result.stdout.strip()


def _git_env() -> dict[str, str]:
    env = dict(os.environ)
    for key in tuple(env):
        if key.startswith("GIT_CONFIG") or key in {"GIT_DIR", "GIT_WORK_TREE", "GIT_OBJECT_DIRECTORY"}:
            env.pop(key, None)
    env.update({
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_COUNT": "1",
        "GIT_CONFIG_KEY_0": "core.hooksPath",
        "GIT_CONFIG_VALUE_0": os.devnull,
        "GIT_TERMINAL_PROMPT": "0",
    })
    return env


def _snapshot_committed_inputs(work: Path) -> tuple[Path, str, dict[str, str]]:
    try:
        revision = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, timeout=30
        ).strip()
    except (OSError, subprocess.SubprocessError) as exc:
        raise PreparationError("could not identify committed build inputs") from exc
    snapshot = work / "source-snapshot"
    hashes: dict[str, str] = {}
    for relative in SNAPSHOT_FILES:
        try:
            content = subprocess.check_output(
                ["git", "show", f"{revision}:{relative}"], cwd=ROOT, timeout=30
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise PreparationError(f"committed build input is unavailable: {relative}") from exc
        destination = snapshot / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
        hashes[relative] = hashlib.sha256(content).hexdigest()
    return snapshot, revision, hashes


def _fetch_pinned_source(mirror: Path, commit: str) -> None:
    mirror.mkdir(mode=0o700, parents=True, exist_ok=False)
    commands = (
        ["git", "init", "--bare", str(mirror)],
        ["git", f"--git-dir={mirror}", "fetch", "--no-tags", "--depth=1", CANONICAL_GIT_URL, commit],
    )
    for command in commands:
        try:
            completed = subprocess.run(
                command, capture_output=True, text=True,
                timeout=GIT_TIMEOUT_SECONDS, check=False, env=_git_env(),
            )
        except subprocess.TimeoutExpired as exc:
            raise PreparationError("explicit canonical source fetch timed out") from exc
        if completed.returncode:
            raise PreparationError("explicit canonical source fetch failed")


def _download_cmake(destination: Path, *, opener: Callable[..., Any] = urlopen) -> None:
    temporary = destination.with_name(f".{destination.name}.download")
    total = 0
    try:
        with opener(CMAKE_URL, timeout=60) as response, temporary.open("wb") as output:
            while True:
                block = response.read(1024 * 1024)
                if not block:
                    break
                total += len(block)
                if total > MAX_DOWNLOAD_BYTES:
                    raise PreparationError("CMake archive download exceeds the size limit")
                output.write(block)
        os.replace(temporary, destination)
    except PreparationError:
        raise
    except Exception as exc:
        raise PreparationError("official CMake archive download failed") from exc
    finally:
        temporary.unlink(missing_ok=True)


def _check_tar_members(archive: tarfile.TarFile) -> None:
    for member in archive.getmembers():
        path = PurePosixPath(member.name)
        if path.is_absolute() or ".." in path.parts or not path.parts or path.parts[0] != CMAKE_ROOT:
            raise PreparationError("CMake archive contains an unsafe path")
        if member.islnk():
            raise PreparationError("CMake archive contains an unsupported hard link")
        if member.mode & 0o6000:
            raise PreparationError("CMake archive contains a setuid or setgid member")
        if member.issym():
            link = PurePosixPath(member.linkname)
            if link.is_absolute():
                raise PreparationError("CMake archive contains an absolute symlink")
            resolved = list(path.parent.parts)
            for part in link.parts:
                if part in {"", "."}:
                    continue
                if part == "..":
                    if len(resolved) <= 1:
                        raise PreparationError("CMake archive symlink escapes its root")
                    resolved.pop()
                else:
                    resolved.append(part)


def verify_and_extract_cmake(
    archive_path: Path,
    destination: Path,
    *,
    expected_archive_sha256: str = CMAKE_ARCHIVE_SHA256,
    expected_binary_sha256: str = CMAKE_BINARY_SHA256,
) -> Path:
    archive_path = _regular_file(archive_path, "CMake archive")
    if sha256(archive_path) != expected_archive_sha256:
        raise PreparationError("CMake archive SHA-256 does not match the reviewed pin")
    try:
        with tarfile.open(archive_path, "r:gz") as archive:
            _check_tar_members(archive)
            try:
                binary_member = archive.getmember(f"{CMAKE_ROOT}/bin/cmake")
            except KeyError as exc:
                raise PreparationError("CMake archive is missing its cmake executable") from exc
            if not binary_member.isfile():
                raise PreparationError("CMake executable archive member is not a regular file")
            binary_stream = archive.extractfile(binary_member)
            if binary_stream is None:
                raise PreparationError("CMake executable archive member cannot be read")
            digest = hashlib.sha256()
            for block in iter(lambda: binary_stream.read(1024 * 1024), b""):
                digest.update(block)
            if digest.hexdigest() != expected_binary_sha256:
                raise PreparationError("CMake executable SHA-256 does not match the reviewed pin")
            destination.mkdir(parents=True, exist_ok=False)
            archive.extractall(destination, filter="data")
    except PreparationError:
        raise
    except (OSError, tarfile.TarError, EOFError) as exc:
        raise PreparationError("CMake archive is malformed or could not be extracted") from exc
    return destination / CMAKE_ROOT


def _python_base(prefix: Path) -> tuple[Path, Path]:
    if prefix.is_symlink() or not prefix.is_dir():
        raise PreparationError("Python base prefix must be an existing real directory")
    prefix = prefix.resolve(strict=True)
    executable = prefix / "bin/python3.13"
    if executable.is_symlink() or not executable.is_file() or not os.access(executable, os.X_OK):
        raise PreparationError("Python base prefix must contain executable bin/python3.13")
    return prefix, executable


def docker_command(
    *, image: str, source_snapshot: Path, cmake_prefix: Path, python_prefix: Path,
    source_archive: Path, output_dir: Path, cidfile: Path,
) -> list[str]:
    if platform.machine().lower() not in {"x86_64", "amd64"}:
        raise PreparationError("isolated build is pinned to linux/amd64")
    command = [
        "docker", "run", "--rm", "--pull=never", "--runtime=runc", "--platform=linux/amd64",
        "--network=none", "--read-only", "--cap-drop=ALL", "--security-opt=no-new-privileges",
        "--cpus=2", "--memory=4g", "--pids-limit=512", "--user", f"{os.getuid()}:{os.getgid()}",
        "--cidfile", str(cidfile), "--tmpfs", "/tmp:rw,noexec,nosuid,size=64m",
    ]
    for key, value in {
        "HOME": "/tmp", "TMPDIR": "/out/work-temp",
        "PATH": "/opt/cmake/bin:/opt/python/bin:/usr/bin:/bin",
        "PYTHONDONTWRITEBYTECODE": "1", "CUDA_VISIBLE_DEVICES": "", "HF_HUB_OFFLINE": "1",
    }.items():
        command.extend(("--env", f"{key}={value}"))
    mounts = (
        (source_snapshot / "scripts", "/src/scripts", True),
        (source_snapshot / "packaging/espeak", "/src/packaging/espeak", True),
        (cmake_prefix, "/opt/cmake", True),
        (python_prefix, "/opt/python", True),
        (source_archive, f"/inputs/{source_archive.name}", True),
        (output_dir, "/out", False),
    )
    for host_path, container_path, read_only in mounts:
        resolved = host_path.resolve(strict=True)
        if any(char in str(resolved) for char in ",\n\r"):
            raise PreparationError("mount path contains unsupported punctuation")
        mount = f"type=bind,src={resolved},dst={container_path}"
        if read_only:
            mount += ",readonly"
        command.extend(("--mount", mount))
    command.extend((
        "--entrypoint", "/opt/python/bin/python3.13", image,
        "/src/scripts/build_espeak_native_payload.py", "--source-archive",
        f"/inputs/{source_archive.name}", "--output-dir", "/out/candidate",
    ))
    return command


def _kill_group(process: subprocess.Popen[bytes]) -> None:
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired as exc:
            raise PreparationError("Docker controller did not exit after SIGKILL") from exc
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def _run_build(command: list[str], log_path: Path, timeout: int) -> int:
    with log_path.open("wb") as log:
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            return process.wait(timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            _kill_group(process)
            raise PreparationError(f"offline build exceeded its {timeout}s timeout") from exc


def _container_cleanup(cidfile: Path) -> tuple[str | None, bool]:
    if not cidfile.is_file():
        return None, False
    cid = cidfile.read_text(encoding="ascii", errors="strict").strip()
    if not re.fullmatch(r"[0-9a-f]{64}", cid):
        raise PreparationError("Docker wrote an invalid container ID file")
    inspect = subprocess.run(
        ["docker", "inspect", "--format", "{{.State.Running}}", cid],
        capture_output=True, text=True, timeout=15, check=False,
    )
    if inspect.returncode and "no such object" not in (inspect.stdout + inspect.stderr).lower():
        raise PreparationError("could not inspect the owned Docker container")
    if inspect.returncode == 0:
        subprocess.run(["docker", "rm", "--force", cid], capture_output=True, timeout=30, check=False)
    final_inspect = subprocess.run(
        ["docker", "inspect", cid], capture_output=True, timeout=15, check=False
    )
    absent = (
        final_inspect.returncode != 0
        and "no such object" in (final_inspect.stdout + final_inspect.stderr).decode("utf-8", errors="replace").lower()
    )
    if final_inspect.returncode != 0 and not absent:
        raise PreparationError("could not confirm absence of the owned Docker container")
    return cid, absent


def _run_intake(snapshot: Path, git_dir: Path, archive_dir: Path, archive_filename: str) -> Path:
    archive_dir.mkdir(mode=0o700, parents=True, exist_ok=False)
    script = snapshot / "scripts/intake_espeak_source.py"
    try:
        result = subprocess.run(
            [sys.executable, str(script), "--git-dir", str(git_dir), "--output-dir", str(archive_dir)],
            capture_output=True, text=True, timeout=PREPARE_TIMEOUT_SECONDS, check=False, env=_git_env(),
        )
    except subprocess.TimeoutExpired as exc:
        raise PreparationError("locked eSpeak source archive preparation timed out") from exc
    if result.returncode:
        raise PreparationError("locked eSpeak source archive preparation failed")
    return archive_dir / archive_filename


def _recipe_text() -> str:
    return """# eSpeak NG native payload preparation and build recipe

This receipt accompanies `out/candidate/payload/`. The source archive is
created from the exact commit and tree in the committed `source-lock.json`.
The reviewed CMake 3.31.6 archive and its `bin/cmake` member are SHA-256
checked before extraction. The build then runs the committed
`scripts/build_espeak_native_payload.py` inside the pinned CUDA Ubuntu 24.04
image with `runc`, no network, read-only root, two CPUs, 4 GiB memory, no GPU
devices, and a finite timeout. The reviewed host Python base prefix and CMake
tree are bind-mounted read-only; the fresh output directory and bounded `/tmp`
tmpfs are writable.

Network access is used only when the operator explicitly selects
`--fetch-canonical` and/or `--download-cmake`, before the isolated build.
Supplied private mirror and CMake archive inputs avoid those network steps.
The preparer never installs host packages, clears caches, removes existing
output, or executes the CMake binary on the host.
"""


def prepare(args: argparse.Namespace) -> Path:
    work = _new_private_work_dir(args.work_dir)
    inputs = work / "inputs"
    inputs.mkdir(mode=0o700)
    snapshot, source_revision, source_hashes = _snapshot_committed_inputs(work)
    lock = json.loads((snapshot / LOCK_RELATIVE).read_text(encoding="utf-8"))
    source_pin = lock["upstream"]
    archive_info = lock["source_archive"]
    if source_pin.get("canonical_project", "").removesuffix(".git") != CANONICAL_GIT_URL.removesuffix(".git"):
        raise PreparationError("canonical fetch URL does not match the committed source lock")

    if args.fetch_canonical:
        mirror = work / "private-source-mirror.git"
        _fetch_pinned_source(mirror, source_pin["commit"])
    else:
        mirror = _private_git_dir(args.git_dir)
    if (
        _git_output(mirror, "cat-file", "-t", source_pin["commit"]) != "commit"
        or _git_output(mirror, "rev-parse", f"{source_pin['commit']}^{{tree}}") != source_pin["tree"]
    ):
        raise PreparationError("source mirror does not contain the locked commit and tree")
    archive = _run_intake(snapshot, mirror, inputs / "source-archive", archive_info["filename"])
    if archive.name != archive_info["filename"] or archive.stat().st_size != archive_info["size_bytes"]:
        raise PreparationError("prepared source archive size or name differs from lock")
    if sha256(archive) != archive_info["sha256"]:
        raise PreparationError("prepared source archive SHA-256 differs from lock")

    if args.download_cmake:
        cmake_archive = inputs / "cmake-3.31.6-linux-x86_64.tar.gz"
        _download_cmake(cmake_archive)
    else:
        supplied = _regular_file(args.cmake_archive, "CMake archive")
        if supplied.name != "cmake-3.31.6-linux-x86_64.tar.gz":
            raise PreparationError("supplied CMake archive has an unexpected filename")
        cmake_archive = inputs / supplied.name
        shutil.copyfile(supplied, cmake_archive)
    cmake_root = verify_and_extract_cmake(cmake_archive, work / "toolchain/cmake")
    python_prefix, python_executable = _python_base(args.python_base_prefix)

    output = work / "out"
    output.mkdir(mode=0o700)
    (output / "work-temp").mkdir(mode=0o700)
    candidate = output / "candidate"
    candidate.mkdir(mode=0o700)
    cidfile = work / "container.cid"
    log = work / "build.log"
    receipt_path = work / RECEIPT_NAME
    receipt: dict[str, Any] = {
        "schema_version": 1,
        "status": "prepared",
        "source_revision": source_revision,
        "source_inputs_sha256": dict(sorted(source_hashes.items())),
        "source_commit": source_pin["commit"],
        "source_tree": source_pin["tree"],
        "source_archive_sha256": archive_info["sha256"],
        "source_archive_size_bytes": archive_info["size_bytes"],
        "cmake_url": CMAKE_URL,
        "cmake_archive_sha256": CMAKE_ARCHIVE_SHA256,
        "cmake_archive_size_bytes": cmake_archive.stat().st_size,
        "cmake_binary_sha256": CMAKE_BINARY_SHA256,
        "python_binary_sha256": sha256(python_executable),
        "image": BUILD_IMAGE,
        "network": "none during build",
        "runtime": "runc",
        "gpu_devices_requested": False,
        "cpu_limit": 2,
        "memory_limit_gib": 4,
        "timeout_seconds": args.timeout_seconds,
        "source_method": "canonical pinned fetch" if args.fetch_canonical else "supplied private bare mirror",
        "cmake_method": "explicit official download" if args.download_cmake else "supplied archive",
        "target": lock["target"],
        "candidate_path": "out/candidate/payload",
        "recipe_path": RECIPE_NAME,
        "preparer_sha256": sha256(Path(__file__).resolve()),
        "recipe_sha256": hashlib.sha256(_recipe_text().encode("utf-8")).hexdigest(),
    }
    identity_inputs = {
        key: receipt[key]
        for key in (
            "source_revision", "source_inputs_sha256", "source_commit", "source_tree",
            "source_archive_sha256", "cmake_archive_sha256", "cmake_binary_sha256",
            "python_binary_sha256", "image", "target", "preparer_sha256", "recipe_sha256",
        )
    }
    receipt["build_identity_sha256"] = hashlib.sha256(
        json.dumps(identity_inputs, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    _write_json_atomic(receipt_path, receipt)
    (work / RECIPE_NAME).write_text(_recipe_text(), encoding="utf-8")
    command = docker_command(
        image=BUILD_IMAGE,
        source_snapshot=snapshot,
        cmake_prefix=cmake_root,
        python_prefix=python_prefix,
        source_archive=archive,
        output_dir=output,
        cidfile=cidfile,
    )
    receipt["status"] = "running"
    receipt["started_at"] = datetime.now(timezone.utc).isoformat()
    _write_json_atomic(receipt_path, receipt)
    build_status: int | None = None
    try:
        build_status = _run_build(command, log, args.timeout_seconds)
        receipt["returncode"] = build_status
        receipt["status"] = "built" if build_status == 0 else "failed"
    except (PreparationError, OSError, subprocess.SubprocessError) as exc:
        receipt["status"] = "timed_out" if "timeout" in str(exc) else "failed"
        receipt["error"] = str(exc)
        receipt["log_tail"] = _bounded_tail(log)
    finally:
        try:
            cid, container_absent = _container_cleanup(cidfile)
        except (OSError, PreparationError, subprocess.SubprocessError) as exc:
            cid, container_absent = None, False
            receipt["cleanup_error"] = str(exc)
        receipt["container_id"] = cid
        receipt["container_absent_after_cleanup"] = container_absent
        receipt["finished_at"] = datetime.now(timezone.utc).isoformat()
        receipt["build_log_sha256"] = sha256(log) if log.exists() else None
        if not container_absent:
            if receipt["status"] == "built":
                receipt["status"] = "cleanup_failed"
            elif "cleanup_error" not in receipt:
                receipt["cleanup_error"] = "container absence could not be confirmed"
        _write_json_atomic(receipt_path, receipt)
    if receipt["status"] != "built" or build_status != 0:
        raise PreparationError(f"isolated build did not complete successfully; see {receipt_path}")
    payload = candidate / "payload"
    if not payload.is_dir():
        raise PreparationError("isolated build completed without the expected payload directory")
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work-dir", type=Path, required=True, help="new private work directory")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--git-dir", type=Path, help="existing reviewed private bare Git mirror")
    source.add_argument("--fetch-canonical", action="store_true", help="explicitly fetch the pinned commit from the canonical project")
    cmake = parser.add_mutually_exclusive_group(required=True)
    cmake.add_argument("--cmake-archive", type=Path, help="existing locally supplied CMake 3.31.6 archive")
    cmake.add_argument("--download-cmake", action="store_true", help="explicitly download the pinned official CMake archive")
    parser.add_argument("--python-base-prefix", type=Path, required=True, help="reviewed host Python 3.13 base prefix to mount read-only")
    parser.add_argument("--timeout-seconds", type=int, default=DEFAULT_BUILD_TIMEOUT_SECONDS)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not 1 <= args.timeout_seconds <= 3600:
        parser.error("--timeout-seconds must be between 1 and 3600")
    try:
        payload = prepare(args)
    except (OSError, ValueError, PreparationError, subprocess.SubprocessError) as exc:
        parser.exit(1, f"prepare-espeak-native: error: {exc}\n")
    print(f"prepared eSpeak NG payload: {payload}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
