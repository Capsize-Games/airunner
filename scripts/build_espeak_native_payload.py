#!/usr/bin/env python3
"""Build a locked eSpeak NG CLI and data payload without network access."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import signal
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = ROOT / "packaging/espeak/source-lock.json"
PATCH_PATH = ROOT / "packaging/espeak/0001-offline-no-playback.patch"
BUILD_DOC_PATH = ROOT / "packaging/espeak/BUILD.md"
INTAKE_SCRIPT_PATH = ROOT / "scripts/intake_espeak_source.py"
BUILD_SCRIPT_PATH = ROOT / "scripts/build_espeak_native_payload.py"
COMMAND_TIMEOUT_SECONDS = 300
BUILD_TIMEOUT_SECONDS = 3600
MAX_EVIDENCE_CHARS = 4000


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_blob_id(path: Path) -> str:
    content = path.read_bytes()
    header = f"blob {len(content)}\0".encode("ascii")
    return hashlib.sha1(header + content).hexdigest()


def run(
    command: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None,
    timeout: int = COMMAND_TIMEOUT_SECONDS,
) -> str:
    def tail(stream) -> str:
        stream.seek(0, os.SEEK_END)
        stream.seek(max(0, stream.tell() - MAX_EVIDENCE_CHARS))
        return stream.read().decode("utf-8", errors="replace")

    with tempfile.TemporaryFile() as stdout_file, tempfile.TemporaryFile() as stderr_file:
        process = subprocess.Popen(
            command, cwd=cwd, env=env, stdout=stdout_file, stderr=stderr_file,
            start_new_session=True,
        )
        try:
            returncode = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired as exc:
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
                except subprocess.TimeoutExpired as kill_error:
                    raise RuntimeError(
                        f"timed-out process group did not exit after SIGKILL: {' '.join(command)}"
                    ) from kill_error
            else:
                # The parent may exit on SIGTERM while a compiler child remains.
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            raise RuntimeError(
                f"command timed out after {timeout}s: {' '.join(command)}\n"
                f"bounded stdout tail:\n{tail(stdout_file)}\n"
                f"bounded stderr tail:\n{tail(stderr_file)}"
            ) from exc
        stdout = tail(stdout_file)
        stderr = tail(stderr_file)
        if returncode:
            raise RuntimeError(
                f"command failed ({returncode}): {' '.join(command)}\n"
                f"bounded stdout tail:\n{stdout}\nbounded stderr tail:\n{stderr}"
            )
        return (stdout + stderr).strip()


def safe_unpack(archive_path: Path, destination: Path) -> Path:
    with tarfile.open(archive_path, "r:gz") as archive:
        members = archive.getmembers()
        for member in members:
            name = PurePosixPath(member.name)
            if (
                name.is_absolute() or ".." in name.parts or not name.parts
                or name.parts[0] != "espeak-ng" or member.islnk()
            ):
                raise ValueError(f"unsafe source archive member: {member.name}")
            if member.issym():
                target = PurePosixPath(member.linkname)
                if target.is_absolute():
                    raise ValueError(f"unsafe absolute source symlink: {member.name}")
                resolved: list[str] = list(name.parent.parts)
                for part in target.parts:
                    if part == "..":
                        if len(resolved) <= 1:
                            raise ValueError(f"source symlink escapes source root: {member.name}")
                        resolved.pop()
                    elif part not in {"", "."}:
                        resolved.append(part)
        archive.extractall(destination, filter="data")
    root = destination / "espeak-ng"
    if not (root / "CMakeLists.txt").is_file():
        raise ValueError("source archive does not contain the expected eSpeak NG root")
    return root


def require_target_environment() -> None:
    if platform.machine() not in {"x86_64", "amd64"}:
        raise SystemExit("build must run in the locked Ubuntu 24.04 x86_64 target container")
    release = Path("/etc/os-release").read_text(encoding="utf-8")
    if 'ID=ubuntu' not in release or 'VERSION_ID="24.04"' not in release:
        raise SystemExit("build must run in Ubuntu 24.04; host builds are not supported")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-archive", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True, help="must be an empty directory")
    args = parser.parse_args()
    require_target_environment()
    lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    archive_info = lock["source_archive"]
    archive_path = args.source_archive.expanduser().resolve(strict=True)
    output_dir = args.output_dir.expanduser().resolve()
    if archive_path.name != archive_info["filename"]:
        raise SystemExit("source archive filename does not match the lock")
    if archive_path.stat().st_size != archive_info["size_bytes"] or sha256(archive_path) != archive_info["sha256"]:
        raise SystemExit("source archive hash or size does not match the lock")
    patch_info = lock["patches"][0]
    if sha256(PATCH_PATH) != patch_info["sha256"]:
        raise SystemExit("local patch hash does not match source lock")
    output_dir.mkdir(parents=True, exist_ok=True)
    if any(output_dir.iterdir()):
        raise SystemExit("output directory must be empty")

    with tempfile.TemporaryDirectory(prefix="espeak-build-") as temporary:
        work = Path(temporary)
        source = safe_unpack(archive_path, work / "source")
        patch_command = [
            "patch", "--batch", "--forward", "--fuzz=0", "-p1",
            "--input", str(PATCH_PATH.resolve()),
        ]
        run([*patch_command, "--dry-run"], cwd=source)
        run(patch_command, cwd=source)
        build_dir = work / "build"
        prefix = Path("/usr")
        run(
            [
                "cmake", "-S", str(source), "-B", str(build_dir),
                "-DCMAKE_BUILD_TYPE=Release",
                f"-DCMAKE_INSTALL_PREFIX={prefix}",
                "-DFETCHCONTENT_FULLY_DISCONNECTED=ON",
                "-DUSE_LIBSONIC=OFF",
                "-DUSE_MBROLA=OFF",
                "-DUSE_LIBPCAUDIO=OFF",
                "-DUSE_SPEECHPLAYER=OFF",
                "-DUSE_ASYNC=OFF",
                "-DUSE_KLATT=ON",
                "-DESPEAK_COMPAT=OFF",
                "-DESPEAK_BUILD_MANPAGES=OFF",
                "-DBUILD_SHARED_LIBS=OFF",
            ],
            cwd=source,
        )
        run(
            ["cmake", "--build", str(build_dir), "--target", "espeak-ng-bin", "data", "--parallel", "2"],
            timeout=BUILD_TIMEOUT_SECONDS,
        )
        stage = work / "stage"
        run(["cmake", "--install", str(build_dir), "--prefix", str(prefix)], env={**os.environ, "DESTDIR": str(stage)})

        payload = output_dir / "payload"
        (payload / "bin").mkdir(parents=True)
        (payload / "share").mkdir()
        installed = stage / "usr"
        executable = installed / "bin/espeak-ng"
        data = installed / "share/espeak-ng-data"
        if not executable.is_file() or not data.is_dir():
            raise RuntimeError("install tree lacks expected CLI or generated voice data")
        shutil.copy2(executable, payload / "bin/espeak-ng")
        shutil.copytree(data, payload / "share/espeak-ng-data", symlinks=False)

        notices = payload / "licenses/espeak-ng"
        notices.mkdir(parents=True)
        for filename, expected_blob_id in lock["license_git_blob_ids"].items():
            source_notice = source / filename
            actual_blob_id = git_blob_id(source_notice)
            if actual_blob_id != expected_blob_id:
                raise RuntimeError(f"locked Git blob ID mismatch for license notice {filename}")
            shutil.copy2(source_notice, notices / filename)
        provenance = payload / "source"
        provenance.mkdir()
        shutil.copy2(archive_path, provenance / archive_info["filename"])
        shutil.copy2(PATCH_PATH, provenance / PATCH_PATH.name)
        shutil.copy2(LOCK_PATH, provenance / LOCK_PATH.name)
        shutil.copy2(INTAKE_SCRIPT_PATH, provenance / INTAKE_SCRIPT_PATH.name)
        shutil.copy2(BUILD_SCRIPT_PATH, provenance / BUILD_SCRIPT_PATH.name)
        shutil.copy2(BUILD_DOC_PATH, provenance / BUILD_DOC_PATH.name)

        files: dict[str, str] = {}
        for path in sorted(item for item in payload.rglob("*") if item.is_file()):
            files[path.relative_to(payload).as_posix()] = sha256(path)
        receipt = {
            "source_commit": lock["upstream"]["commit"],
            "source_tree": lock["upstream"]["tree"],
            "source_archive_sha256": archive_info["sha256"],
            "patch_sha256": patch_info["sha256"],
            "target": lock["target"],
            "platform": platform.platform(),
            "cmake_version": run(["cmake", "--version"]).splitlines()[0],
            "compiler_version": run(["cc", "--version"]).splitlines()[0],
            "patch_version": run(["patch", "--version"]).splitlines()[0],
            "build_configuration": "Release; offline; explicit espeak-ng-bin and data targets",
            "files_sha256": files,
        }
        (payload / "build-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(f"staged eSpeak NG payload at {output_dir / 'payload'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
