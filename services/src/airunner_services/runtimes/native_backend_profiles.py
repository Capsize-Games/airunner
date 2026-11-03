"""Select and verify the native llama.cpp backend independently of GGUF tuning."""

from __future__ import annotations

import collections
import hashlib
import json
import os
import platform
import stat
import subprocess
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any

from airunner_services.runtimes.bundled_runtime_paths import (
    resolve_runtime_executable,
)

CUDA_PROFILE = "cuda-sm120a"
CPU_PROFILE = "cpu"
PROFILE_SCHEMA = "airunner-native-runtime-profile-v1"
PROFILE_ROOT_RELATIVE = Path("share/airunner/native-runtimes/cuda-sm120a")
_PROFILE_CACHE: collections.OrderedDict[tuple[Any, ...], dict[str, Any]] = (
    collections.OrderedDict()
)
_PROFILE_CACHE_LOCK = threading.Lock()
_DEVICE_PROBE_LOCK = threading.Lock()
_DEVICE_PROBE_SUCCEEDED_AT = 0.0
_DEVICE_PROBE_DEVICE: str | None = None


class NativeBackendUnavailable(RuntimeError):
    """A requested native backend is absent, unsupported, or unverified."""

    code = "native_backend_unavailable"


@dataclass(frozen=True)
class NativeBackendSelection:
    """Verified executable identity selected for one llama.cpp backend."""

    profile: str
    executable: str
    artifact_id: str
    manifest_sha256: str | None
    verified: bool
    device: str | None
    fit: str | None

    def metadata(self) -> dict[str, Any]:
        """Return selection metadata without claiming observed device use."""
        return {
            "backend_profile": self.profile,
            "backend_executable": self.executable,
            "backend_artifact_id": self.artifact_id,
            "backend_manifest_sha256": self.manifest_sha256,
            "backend_profile_verified": self.verified,
            "requested_device": self.device,
            "actual_device": None,
            "offloaded_layers": None,
        }


def select_native_backend(
    *,
    n_gpu_layers: int,
    bundle_root: str | os.PathLike[str] | None = None,
    requested: str | None = None,
    cpu_executable: str | None = None,
    cuda_profile_root: str | os.PathLike[str] | None = None,
    device_probe=None,
) -> NativeBackendSelection:
    """Choose CPU or verified CUDA backend based on explicit GPU intent."""
    choice = requested or os.environ.get("AIRUNNER_LLAMA_BACKEND", "auto")
    choice = str(choice).strip().lower() or "auto"
    if choice not in {"auto", CPU_PROFILE, CUDA_PROFILE}:
        raise NativeBackendUnavailable(
            "AIRUNNER_LLAMA_BACKEND must be auto, cpu, or cuda-sm120a"
        )
    if choice == CPU_PROFILE:
        return _cpu_selection(cpu_executable)

    gpu_requested = n_gpu_layers != 0
    if choice == "auto" and not gpu_requested:
        return _cpu_selection(cpu_executable)

    root = _cuda_root(bundle_root, cuda_profile_root)
    profile = _verify_cuda_profile(root)
    try:
        if device_probe is None:
            requested_device = _probe_sm120a_device_cached() or "CUDA0"
        else:
            requested_device = device_probe() or "CUDA0"
    except NativeBackendUnavailable:
        raise
    except Exception as error:
        raise NativeBackendUnavailable(
            "CUDA SM120a runtime is unavailable; install the supported NVIDIA "
            "driver and use a compute capability 12.0 GPU"
        ) from error
    return NativeBackendSelection(
        profile=CUDA_PROFILE,
        executable=str(root / profile["entrypoint"]),
        artifact_id=str(profile["artifact_id"]),
        manifest_sha256=profile["manifest_sha256"],
        verified=True,
        device=requested_device,
        fit="off",
    )


def _cpu_selection(executable: str | None) -> NativeBackendSelection:
    """Return the existing CPU binary or an explicit diagnostic override."""
    if executable is None:
        executable = resolve_runtime_executable(
            "AIRUNNER_LLAMA_SERVER_BIN", "llama-server"
        )
    path = str(Path(executable).expanduser())
    return NativeBackendSelection(
        profile=CPU_PROFILE,
        executable=path,
        artifact_id=(
            "explicit-cpu-executable"
            if os.environ.get("AIRUNNER_LLAMA_SERVER_BIN")
            else "legacy-cpu-binary"
        ),
        manifest_sha256=None,
        verified=False,
        device=None,
        fit=None,
    )


def _cuda_root(
    bundle_root: str | os.PathLike[str] | None,
    cuda_profile_root: str | os.PathLike[str] | None,
) -> Path:
    """Resolve the isolated CUDA profile tree without following symlinks."""
    configured = cuda_profile_root
    if configured:
        root = Path(configured).expanduser()
    else:
        bundle = bundle_root or os.environ.get("AIRUNNER_BUNDLE_ROOT")
        if not bundle:
            raise NativeBackendUnavailable(
                "CUDA SM120a runtime is unavailable: no bundle profile is configured; "
                "install a verified profile or set AIRUNNER_LLAMA_BACKEND=cpu"
            )
        root = Path(bundle).expanduser() / PROFILE_ROOT_RELATIVE
    root = Path(os.path.abspath(root))
    try:
        _reject_symlink_components(root)
    except (OSError, ValueError) as error:
        raise NativeBackendUnavailable(
            "CUDA SM120a runtime profile path contains a symlink or is inaccessible"
        ) from error
    return root


def _reject_symlink_components(path: Path) -> None:
    """Reject symlinks in every existing component of an absolute path."""
    absolute = Path(os.path.abspath(path))
    current = Path(absolute.anchor)
    for component in absolute.parts[1:]:
        current = current / component
        try:
            info = current.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode):
            raise ValueError("path contains a symlink component")


def _read_profile_manifest(root: Path) -> tuple[dict[str, Any], bytes]:
    """Read one bounded, regular, mode-safe profile manifest."""
    _reject_symlink_components(root)
    if not root.is_dir():
        raise ValueError("profile root is not a directory")
    manifest_path = root / "profile-manifest.json"
    info = manifest_path.lstat()
    if not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o644:
        raise ValueError("profile manifest must be a regular 0644 file")
    with manifest_path.open("rb") as stream:
        data = stream.read(1024 * 1024 + 1)
    if len(data) > 1024 * 1024:
        raise ValueError("profile manifest is oversized")
    manifest = json.loads(data)
    if not isinstance(manifest, dict):
        raise ValueError("profile manifest root must be an object")
    return manifest, data


def _validate_profile_manifest(
    manifest: dict[str, Any],
) -> tuple[dict[str, tuple[str, int]], str]:
    """Validate profile identity, provenance, inventory rows, and entrypoint."""
    _validate_profile_target(manifest)
    _validate_artifact_identity(manifest)
    _validate_source_identity(manifest.get("source"))
    _validate_producer_identity(manifest.get("producer"))
    listed = _validate_profile_files(manifest.get("files"))
    entrypoint = _validate_profile_entrypoint(manifest.get("entrypoint"), listed)
    return listed, entrypoint


def _validate_profile_target(manifest: dict[str, Any]) -> None:
    """Require a verified Linux x86_64 Ubuntu 24.04 SM120a release profile."""
    if manifest.get("schema") != PROFILE_SCHEMA:
        raise ValueError("unsupported profile manifest schema")
    if manifest.get("status") != "verified" or manifest.get("profile") != CUDA_PROFILE:
        raise ValueError("profile is not verified for cuda-sm120a")
    target = (
        manifest.get("platform"),
        manifest.get("abi"),
        manifest.get("compute_capability"),
    )
    if target != ("linux-x86_64", "ubuntu-24.04", "12.0"):
        raise ValueError("profile platform, ABI, or compute capability is unsupported")


def _validate_artifact_identity(manifest: dict[str, Any]) -> None:
    """Require a nonempty stable artifact identity label."""
    artifact_id = manifest.get("artifact_id")
    if not isinstance(artifact_id, str) or not artifact_id.strip():
        raise ValueError("profile manifest is missing artifact_id")


def _validate_source_identity(source: Any) -> None:
    """Require repository, source commit, and source tree identities."""
    if (
        not isinstance(source, dict)
        or not source.get("repository")
        or not _is_hex(source.get("commit"), 40)
        or not _is_hex(source.get("tree"), 40)
    ):
        raise ValueError("profile source identity is malformed")


def _validate_producer_identity(producer: Any) -> None:
    """Require the producer commit and exact recipe digest."""
    if (
        not isinstance(producer, dict)
        or not _is_hex(producer.get("commit"), 40)
        or not _is_hex(producer.get("recipe_sha256"), 64)
    ):
        raise ValueError("profile producer identity is malformed")


def _validate_profile_files(files: Any) -> dict[str, tuple[str, int]]:
    """Validate and index a bounded, unique profile file inventory."""
    if not isinstance(files, list) or not files or len(files) > 10000:
        raise ValueError("profile manifest has an invalid file inventory")
    listed: dict[str, tuple[str, int]] = {}
    for entry in files:
        relative, digest, mode = _validate_profile_file_entry(entry)
        if relative in listed:
            raise ValueError("profile file path is duplicated")
        listed[relative] = (digest, mode)
    return listed


def _validate_profile_file_entry(entry: Any) -> tuple[str, str, int]:
    """Validate one relative file path, content hash, and file mode."""
    if not isinstance(entry, dict):
        raise ValueError("profile file entry is malformed")
    relative = entry.get("path")
    if not isinstance(relative, str) or not _is_safe_profile_path(relative):
        raise ValueError("profile file path escapes its tree")
    digest = entry.get("sha256")
    if not _is_hex(digest, 64):
        raise ValueError("profile file hash is malformed")
    mode = entry.get("mode")
    if mode not in (0o644, 0o755):
        raise ValueError("profile file mode is unsupported")
    return relative, digest, mode


def _is_safe_profile_path(relative: str) -> bool:
    """Return whether a manifest path is canonical and tree-relative."""
    path = PurePosixPath(relative)
    return not (
        path.is_absolute()
        or ".." in path.parts
        or "." in path.parts
        or "\\" in relative
        or path.as_posix() != relative
        or not path.parts
    )


def _validate_profile_entrypoint(
    entrypoint: Any, listed: dict[str, tuple[str, int]]
) -> str:
    """Require the confined CUDA wrapper as the profile entrypoint."""
    if entrypoint != "bin/llama-server-cuda" or entrypoint not in listed:
        raise ValueError("profile entrypoint is invalid")
    return entrypoint


@dataclass
class _ProfileTreeScan:
    """Collect safe file and directory identities while walking a profile."""

    root_resolved: Path
    actual_files: set[str] = field(default_factory=set)
    actual_directories: set[str] = field(default_factory=set)
    file_signatures: list[tuple[Any, ...]] = field(default_factory=list)
    directory_signatures: list[tuple[Any, ...]] = field(default_factory=list)
    visited: int = 0

    def walk(self, directory: Path, prefix: str = "") -> None:
        """Visit entries without following links or accepting special files."""
        with os.scandir(directory) as entries:
            for entry in entries:
                self.visited += 1
                if self.visited > 20000:
                    raise ValueError("profile tree has too many entries")
                name = f"{prefix}/{entry.name}" if prefix else entry.name
                info = entry.stat(follow_symlinks=False)
                self._record_entry(entry, name, info)

    def _record_entry(self, entry, name, info) -> None:
        """Validate one filesystem entry and recurse into safe directories."""
        if stat.S_ISLNK(info.st_mode):
            raise ValueError("profile tree contains a symlink")
        if stat.S_ISDIR(info.st_mode):
            self._record_directory(entry, name, info)
            self.walk(Path(entry.path), name)
            return
        if not stat.S_ISREG(info.st_mode):
            raise ValueError("profile tree contains a special file")
        self._record_regular_file(entry, name, info)

    def _record_directory(self, entry, name, info) -> None:
        """Capture a safe directory identity."""
        mode = stat.S_IMODE(info.st_mode)
        if mode & (stat.S_ISUID | stat.S_ISGID):
            raise ValueError("profile directory has unsafe mode bits")
        self.actual_directories.add(name)
        self.directory_signatures.append(
            (name, info.st_dev, info.st_ino, info.st_mtime_ns, info.st_ctime_ns, mode)
        )

    def _record_regular_file(self, entry, name, info) -> None:
        """Capture an inventory file or validate the excluded manifest."""
        mode = stat.S_IMODE(info.st_mode)
        if name == "profile-manifest.json":
            if mode != 0o644:
                raise ValueError("profile manifest mode is unsafe")
            return
        self.actual_files.add(name)
        resolved = Path(entry.path).resolve(strict=True)
        if not resolved.is_relative_to(self.root_resolved):
            raise ValueError("profile file escapes its tree")
        self.file_signatures.append(
            (name, info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns,
             info.st_ctime_ns, mode)
        )


def _profile_tree_inventory(
    root: Path,
    listed: dict[str, tuple[str, int]],
) -> tuple[list[tuple[Any, ...]], list[tuple[Any, ...]]]:
    """Reject tree extras and return cache-safe file and directory stats."""
    expected_directories = {
        parent.as_posix()
        for name in listed
        for parent in PurePosixPath(name).parents
        if parent.as_posix() != "."
    }
    scan = _ProfileTreeScan(root.resolve(strict=True))
    scan.walk(root)
    if scan.actual_files != set(listed):
        raise ValueError("profile file inventory does not match tree")
    if scan.actual_directories != expected_directories:
        raise ValueError("profile directory inventory does not match tree")
    _validate_profile_file_modes(scan.file_signatures, listed)
    return scan.file_signatures, scan.directory_signatures


def _validate_profile_file_modes(
    signatures: list[tuple[Any, ...]], listed: dict[str, tuple[str, int]]
) -> None:
    """Require every regular file mode to match its inventory entry."""
    for signature in signatures:
        relative, *_identity, mode = signature
        if mode != listed[relative][1]:
            raise ValueError("profile file mode does not match manifest")


def _verify_profile_hashes(
    root: Path,
    listed: dict[str, tuple[str, int]],
    entrypoint: str,
) -> None:
    """Hash every listed file and verify the launcher wrapper contract."""
    for relative, (expected_hash, _expected_mode) in listed.items():
        path = root.joinpath(*PurePosixPath(relative).parts)
        if _sha256_file(path) != expected_hash:
            raise ValueError("profile file hash does not match manifest")
    wrapper_path = root / entrypoint
    if wrapper_path.stat().st_size > 64 * 1024:
        raise ValueError("CUDA wrapper is oversized")
    wrapper = wrapper_path.read_text(encoding="utf-8")
    if not all(
        fragment in wrapper
        for fragment in (
            "server_dir=",
            "$server_dir/../lib",
            "export LD_LIBRARY_PATH",
            "cd /",
            'exec "$server_dir/llama-server" "$@"',
        )
    ):
        raise ValueError("CUDA wrapper lacks library and working-directory confinement")


def _verify_cuda_profile(root: Path) -> dict[str, Any]:
    """Verify a profile manifest and tree before a CUDA wrapper is selected."""
    try:
        manifest, data = _read_profile_manifest(root)
        listed, entrypoint = _validate_profile_manifest(manifest)
        file_signatures, directory_signatures = _profile_tree_inventory(
            root, listed
        )
        manifest_sha256 = hashlib.sha256(data).hexdigest()
        cache_key = (
            str(root),
            manifest_sha256,
            tuple(file_signatures),
            tuple(directory_signatures),
        )
        with _PROFILE_CACHE_LOCK:
            cached = _PROFILE_CACHE.get(cache_key)
            if cached is not None:
                _PROFILE_CACHE.move_to_end(cache_key)
                return dict(cached)
        _verify_profile_hashes(root, listed, entrypoint)
        verified = {
            "artifact_id": manifest["artifact_id"],
            "entrypoint": entrypoint,
            "manifest_sha256": manifest_sha256,
        }
        with _PROFILE_CACHE_LOCK:
            _PROFILE_CACHE[cache_key] = verified
            _PROFILE_CACHE.move_to_end(cache_key)
            while len(_PROFILE_CACHE) > 8:
                _PROFILE_CACHE.popitem(last=False)
        return dict(verified)
    except (OSError, ValueError, KeyError, TypeError, RecursionError) as error:
        raise NativeBackendUnavailable(
            "CUDA SM120a runtime profile is missing, malformed, or unverified; "
            "install a verified profile or set AIRUNNER_LLAMA_BACKEND=cpu"
        ) from error

def _is_hex(value: Any, size: int) -> bool:
    """Return whether a value is a lowercase hexadecimal digest of size."""
    return (
        isinstance(value, str)
        and len(value) == size
        and all(character in "0123456789abcdef" for character in value)
    )


def _sha256_file(path: Path) -> str:
    """Hash a potentially large sidecar file without loading it in memory."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _probe_sm120a_device_cached() -> str:
    """Reuse a recent successful PCI-ordered driver query across requests."""
    global _DEVICE_PROBE_SUCCEEDED_AT, _DEVICE_PROBE_DEVICE
    with _DEVICE_PROBE_LOCK:
        if "CUDA_VISIBLE_DEVICES" in os.environ:
            raise NativeBackendUnavailable(
                "CUDA SM120a runtime does not support CUDA_VISIBLE_DEVICES remapping; "
                "unset it and retry"
            )
        now = time.monotonic()
        if now - _DEVICE_PROBE_SUCCEEDED_AT < 5.0 and _DEVICE_PROBE_DEVICE:
            return _DEVICE_PROBE_DEVICE
        selected = _probe_sm120a_device()
        _DEVICE_PROBE_DEVICE = selected
        _DEVICE_PROBE_SUCCEEDED_AT = time.monotonic()
        return selected


def _probe_sm120a_device() -> str:
    """Map an SM120 GPU to llama.cpp's PCI-ordered CUDA device index."""
    if platform.system() != "Linux" or platform.machine().lower() not in {
        "x86_64",
        "amd64",
    }:
        raise NativeBackendUnavailable(
            "CUDA SM120a runtime is supported only on Linux x86_64"
        )
    if "CUDA_VISIBLE_DEVICES" in os.environ:
        raise NativeBackendUnavailable(
            "CUDA SM120a runtime does not support CUDA_VISIBLE_DEVICES remapping; "
            "unset it and retry"
        )
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=pci.bus_id,compute_cap",
                "--format=csv,noheader,nounits",
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=3,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise NativeBackendUnavailable(
            "CUDA SM120a runtime is unavailable: NVIDIA driver query failed"
        ) from error
    rows = []
    for line in result.stdout.splitlines():
        fields = [field.strip() for field in line.split(",")]
        if len(fields) != 2 or not fields[0] or not fields[1]:
            raise NativeBackendUnavailable(
                "CUDA SM120a runtime could not map NVIDIA PCI devices"
            )
        rows.append((fields[0], fields[1]))
    rows.sort(key=lambda row: row[0].lower())
    for index, (_bus_id, capability) in enumerate(rows):
        if capability == "12.0":
            return f"CUDA{index}"
    raise NativeBackendUnavailable(
        "CUDA SM120a runtime requires a visible compute capability 12.0 GPU"
    )


__all__ = [
    "CUDA_PROFILE",
    "CPU_PROFILE",
    "NativeBackendSelection",
    "NativeBackendUnavailable",
    "PROFILE_SCHEMA",
    "select_native_backend",
]
