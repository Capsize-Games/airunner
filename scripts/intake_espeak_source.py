#!/usr/bin/env python3
"""Create the locked eSpeak NG source archive from the private Git mirror."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "packaging/espeak/source-lock.json"
GIT_TIMEOUT_SECONDS = 120
ARCHIVE_TIMEOUT_SECONDS = 180
MAX_ERROR_CHARS = 4000


def stop_process(process: subprocess.Popen[bytes]) -> None:
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        process.wait(timeout=5)
        return
    except subprocess.TimeoutExpired:
        pass
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("process group did not exit after SIGKILL") from exc


def tail(stream) -> str:
    stream.seek(0, os.SEEK_END)
    stream.seek(max(0, stream.tell() - MAX_ERROR_CHARS))
    return stream.read().decode("utf-8", errors="replace")


def git(mirror: Path, *args: str) -> str:
    try:
        return subprocess.check_output(
            ["git", f"--git-dir={mirror}", *args], text=True,
            stderr=subprocess.PIPE, timeout=GIT_TIMEOUT_SECONDS,
        ).strip()
    except subprocess.TimeoutExpired as exc:
        stderr = str(exc.stderr or "")[-MAX_ERROR_CHARS:]
        raise RuntimeError(f"git command timed out after {GIT_TIMEOUT_SECONDS}s: {stderr}") from exc
    except subprocess.CalledProcessError as exc:
        stderr = str(exc.stderr or "")[-MAX_ERROR_CHARS:]
        raise RuntimeError(f"git command failed ({exc.returncode}): {stderr}") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--git-dir", type=Path, required=True, help="reviewed private bare Git mirror")
    parser.add_argument("--output-dir", type=Path, required=True, help="ignored/private directory for source input")
    args = parser.parse_args()
    mirror = args.git_dir.expanduser().resolve(strict=True)
    output_dir = args.output_dir.expanduser().resolve()
    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    pin = lock["upstream"]
    archive = lock["source_archive"]
    commit, tree = pin["commit"], pin["tree"]

    if git(mirror, "cat-file", "-t", commit) != "commit":
        raise SystemExit("locked commit is absent from the supplied mirror")
    if git(mirror, "rev-parse", f"{commit}^{{tree}}") != tree:
        raise SystemExit("locked commit resolves to an unexpected tree")

    output_dir.mkdir(parents=True, exist_ok=True)
    destination = output_dir / archive["filename"]
    fd, temporary_name = tempfile.mkstemp(prefix=".espeak-source-", dir=output_dir)
    os.close(fd)
    temporary = Path(temporary_name)
    try:
        with tempfile.TemporaryFile() as error_file, temporary.open("wb") as raw:
            git_proc = subprocess.Popen(
                ["git", f"--git-dir={mirror}", "archive", "--format=tar", "--prefix=espeak-ng/", commit],
                stdout=subprocess.PIPE,
                stderr=error_file,
                start_new_session=True,
            )
            assert git_proc.stdout is not None
            try:
                gzip_proc = subprocess.Popen(
                    ["gzip", "-n", "-9"], stdin=git_proc.stdout, stdout=raw,
                    stderr=error_file, start_new_session=True,
                )
            except OSError:
                stop_process(git_proc)
                raise
            git_proc.stdout.close()
            try:
                gzip_status = gzip_proc.wait(timeout=ARCHIVE_TIMEOUT_SECONDS)
            except subprocess.TimeoutExpired:
                stop_process(gzip_proc)
                stop_process(git_proc)
                raise RuntimeError(f"gzip archive compression exceeded {ARCHIVE_TIMEOUT_SECONDS}s")
            try:
                returncode = git_proc.wait(timeout=GIT_TIMEOUT_SECONDS)
            except subprocess.TimeoutExpired:
                stop_process(git_proc)
                raise RuntimeError(f"git archive exceeded {GIT_TIMEOUT_SECONDS}s")
            if returncode or gzip_status:
                raise RuntimeError(
                    f"git archive/gzip failed (git={returncode}, gzip={gzip_status}): {tail(error_file)}"
                )

        digest_state = hashlib.sha256()
        with temporary.open("rb") as archive_stream:
            for block in iter(lambda: archive_stream.read(1024 * 1024), b""):
                digest_state.update(block)
        digest = digest_state.hexdigest()
        size = temporary.stat().st_size
        if digest != archive["sha256"] or size != archive["size_bytes"]:
            raise SystemExit(f"archive identity mismatch: sha256={digest} size={size}")
        os.replace(temporary, destination)
        print(f"verified source archive: {destination} ({size} bytes, sha256 {digest})")
    finally:
        temporary.unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
