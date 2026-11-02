"""Fail-closed runtime checks for the externally staged Triton toolchain.

This module uses only the standard library and is packaged with the services
wheel. It hashes files and inspects package metadata; it never imports Triton,
executes NVIDIA tools, or loads shared libraries.
"""

from __future__ import annotations

import hashlib
import importlib.machinery
import json
import os
import platform
import sys
from importlib import metadata, resources
from pathlib import Path
from typing import Any

POLICY_SHA256 = (
    "a0da9a8a3cae9eb5fd95f368294c3130feb4f3f7f7f8bb9f1d5284f60b0245fb"
)


def _digest(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def _resolve(raw: str | None, key: str, errors: list[str]) -> Path | None:
    if not raw:
        errors.append(f"{key} is required")
        return None
    path = Path(raw)
    if not path.is_absolute():
        errors.append(f"{key} must be an absolute path")
        return None
    try:
        return path.resolve(strict=True)
    except (OSError, RuntimeError):
        errors.append(f"{key} path does not exist")
        return None


def _check(
    path: Path,
    spec: dict[str, Any],
    label: str,
    errors: list[str],
    executable: bool = False,
) -> bool:
    try:
        if not path.is_file():
            errors.append(f"{label} must be a regular file")
            return False
        if executable and not os.access(path, os.X_OK):
            errors.append(f"{label} must be executable")
            return False
        digest, size = _digest(path)
    except OSError:
        errors.append(f"{label} cannot be read")
        return False
    if size != spec.get("size_bytes") or digest != spec.get("sha256"):
        errors.append(f"{label} does not match the reviewed toolchain")
        return False
    return True


def load_policy() -> dict[str, Any]:
    """Load the policy shipped in the installed services package."""
    resource = resources.files("airunner_services.art").joinpath(
        "data/triton_external_toolchain_runtime.json"
    )
    payload = resource.read_bytes()
    if hashlib.sha256(payload).hexdigest() != POLICY_SHA256:
        raise ValueError(
            "packaged Triton toolchain policy digest is not reviewed"
        )
    policy = json.loads(payload)
    if not isinstance(policy, dict) or policy.get("schema_version") != 1:
        raise ValueError("packaged Triton toolchain policy is unsupported")
    return policy


def _installed_triton_root() -> Path | None:
    """Locate Triton without importing its package code."""
    try:
        distribution = metadata.distribution("triton")
        candidate = Path(distribution.locate_file("triton"))
        if candidate.is_dir():
            return candidate.resolve(strict=True)
    except (metadata.PackageNotFoundError, OSError, RuntimeError):
        pass
    try:
        spec = importlib.machinery.PathFinder.find_spec("triton", sys.path)
        if spec is None or not spec.submodule_search_locations:
            return None
        return Path(next(iter(spec.submodule_search_locations))).resolve()
    except (ImportError, OSError, RuntimeError):
        return None


def validate_toolchain(environ: dict[str, str] | None = None) -> list[str]:
    """Return redacted errors when the exact candidate/toolchain contract fails."""
    env = os.environ if environ is None else environ
    try:
        policy = load_policy()
    except (OSError, ValueError, json.JSONDecodeError):
        return ["packaged Triton toolchain policy cannot be read"]
    candidate = policy["candidate"]
    errors: list[str] = []
    if sys.platform != "linux" or platform.machine().lower() not in {
        "x86_64",
        "amd64",
    }:
        return ["Triton external toolchain is supported only on Linux x86_64"]
    if sys.version_info[:2] != (3, 13):
        return ["Triton external toolchain is reviewed only for Python 3.13"]
    try:
        installed_version = metadata.version(candidate["distribution"])
    except metadata.PackageNotFoundError:
        return ["reviewed Triton candidate is not installed"]
    if installed_version != candidate["version"]:
        return [
            "installed Triton version does not match the reviewed external-toolchain candidate"
        ]

    root = _installed_triton_root()
    if root is None:
        return [
            "installed Triton package cannot be located without importing it"
        ]
    for prefix, expected_count in policy["excluded_counts"].items():
        directory = root / prefix.removeprefix("triton/")
        if directory.exists():
            count = sum(1 for item in directory.rglob("*") if item.is_file())
            if count != expected_count:
                errors.append(
                    "installed Triton candidate contains excluded NVIDIA payload"
                )
                break

    for tool in policy["tools"]:
        name = tool["env"]
        path = _resolve(env.get(name), name, errors)
        if path is not None:
            _check(path, tool, name, errors, executable=True)

    header_roots = []
    configured_header_paths = [
        (name, env[name])
        for name in policy["headers"]["env_any_of"]
        if env.get(name)
    ]
    if not configured_header_paths:
        errors.append(
            "one of the reviewed external CUDA include path variables is required"
        )
    for name, raw_path in configured_header_paths:
        path = _resolve(raw_path, name, errors)
        if path is not None and path.is_dir():
            header_roots.append(path)
        elif path is not None:
            errors.append(f"{name} must point to a directory")
    for header in policy["headers"]["required_files"]:
        candidates = [root / header["relative_path"] for root in header_roots]
        if not any(
            _check(path, header, "external CUDA header", [], False)
            for path in candidates
        ):
            errors.append(
                "external CUDA include roots lack the exact reviewed cuda.h"
            )

    cupti = policy["cupti"]
    cupti_root = _resolve(env.get(cupti["env"]), cupti["env"], errors)
    if cupti_root is not None and cupti_root.is_dir():
        for spec in cupti["required_files"]:
            _check(
                cupti_root / Path(spec["path"]).name,
                spec,
                cupti["env"],
                errors,
            )
    elif cupti_root is not None:
        errors.append(f"{cupti['env']} must point to a directory")

    libdevice = policy["libdevice"]
    retained_member = libdevice["retained_wheel_member"]
    retained_path = root / retained_member["path"].removeprefix("triton/")
    _check(
        retained_path,
        retained_member,
        "retained Triton libdevice",
        errors,
    )
    if env.get(libdevice["env"]):
        path = _resolve(env.get(libdevice["env"]), libdevice["env"], errors)
        if path is not None:
            _check(path, retained_member, libdevice["env"], errors)
    return errors


def ensure_available(
    environ: dict[str, str] | None = None,
) -> tuple[bool, str]:
    """Return availability and a safe user-facing reason for compile opt-in."""
    errors = validate_toolchain(environ)
    if errors:
        return False, "; ".join(errors)
    return True, "reviewed external Triton toolchain is available"
