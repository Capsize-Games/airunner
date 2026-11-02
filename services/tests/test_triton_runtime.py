from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

from airunner_services.art import triton_runtime

POLICY_PATH = (
    Path(__file__).resolve().parents[1]
    / "src/airunner_services/art/data/triton_external_toolchain_runtime.json"
)


def _write_spec(
    path: Path, spec: dict, content: bytes, *, executable: bool = False
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    if executable:
        path.chmod(0o755)
    spec["sha256"] = hashlib.sha256(content).hexdigest()
    spec["size_bytes"] = len(content)


def _fixture(tmp_path: Path) -> tuple[dict, dict[str, str]]:
    policy = copy.deepcopy(json.loads(POLICY_PATH.read_text(encoding="utf-8")))
    env: dict[str, str] = {}
    for index, tool in enumerate(policy["tools"]):
        path = tmp_path / "bin" / f"tool-{index}"
        _write_spec(
            path,
            tool,
            f"reviewed executable {index}".encode(),
            executable=True,
        )
        env[tool["env"]] = str(path)
    header_root = tmp_path / "include"
    env[policy["headers"]["env_any_of"][0]] = str(header_root)
    header = policy["headers"]["required_files"][0]
    _write_spec(
        header_root / header["relative_path"],
        header,
        b"/* reviewed cuda.h */\n",
    )
    cupti_root = tmp_path / "cupti"
    for index, item in enumerate(policy["cupti"]["required_files"]):
        filename = Path(item["path"]).name
        _write_spec(
            cupti_root / filename, item, f"reviewed CUPTI {index}".encode()
        )
    env[policy["cupti"]["env"]] = str(cupti_root)
    return policy, env


def _package_root(policy: dict, tmp_path: Path) -> Path:
    package_root = tmp_path / "site-packages" / "triton"
    member = policy["libdevice"]["retained_wheel_member"]
    retained_path = package_root / member["path"].removeprefix("triton/")
    _write_spec(
        retained_path,
        member,
        b"reviewed retained libdevice\n",
    )
    return package_root


def test_packaged_policy_is_available_without_repository_scripts() -> None:
    policy = triton_runtime.load_policy()
    assert policy["candidate"]["version"] == "3.7.1+capsize.2"
    assert len(policy["tools"]) == 4
    assert len(policy["cupti"]["required_files"]) == 9


def test_hash_check_does_not_execute_external_tool(tmp_path: Path) -> None:
    marker = tmp_path / "executed"
    spec = {"size_bytes": 0, "sha256": ""}
    payload = f"#!/bin/sh\ntouch {marker}\nexit 99\n".encode()
    path = tmp_path / "tool"
    _write_spec(path, spec, payload, executable=True)
    errors: list[str] = []
    assert triton_runtime._check(path, spec, "tool", errors, executable=True)
    assert errors == []
    assert not marker.exists()


def test_frozen_triton_root_uses_distribution_metadata_when_pathfinder_misses(
    tmp_path: Path, monkeypatch
) -> None:
    package_root = tmp_path / "_internal" / "triton"
    package_root.mkdir(parents=True)
    distribution = type(
        "Distribution",
        (),
        {"locate_file": lambda _self, path: package_root.parent / path},
    )()
    monkeypatch.setattr(
        triton_runtime.metadata, "distribution", lambda _name: distribution
    )
    monkeypatch.setattr(
        triton_runtime.importlib.machinery.PathFinder,
        "find_spec",
        lambda *_args: None,
    )

    assert triton_runtime._installed_triton_root() == package_root


def test_missing_frozen_and_importable_triton_roots_fail_closed(monkeypatch) -> None:
    monkeypatch.setattr(
        triton_runtime.metadata,
        "distribution",
        lambda _name: (_ for _ in ()).throw(
            triton_runtime.metadata.PackageNotFoundError
        ),
    )
    monkeypatch.setattr(
        triton_runtime.importlib.machinery.PathFinder,
        "find_spec",
        lambda *_args: None,
    )

    assert triton_runtime._installed_triton_root() is None


def test_valid_paths_hashes_are_accepted_and_errors_redact_paths(
    tmp_path: Path, monkeypatch
) -> None:
    policy, env = _fixture(tmp_path)
    monkeypatch.setattr(triton_runtime, "load_policy", lambda: policy)
    monkeypatch.setattr(triton_runtime.sys, "platform", "linux")
    monkeypatch.setattr(triton_runtime.platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(triton_runtime.sys, "version_info", (3, 13, 5))
    monkeypatch.setattr(
        triton_runtime.metadata, "version", lambda _name: "3.7.1+capsize.2"
    )
    package_root = _package_root(policy, tmp_path)
    monkeypatch.setattr(
        triton_runtime, "_installed_triton_root", lambda: package_root
    )
    assert triton_runtime.validate_toolchain(env) == []

    del env[policy["tools"][0]["env"]]
    errors = triton_runtime.validate_toolchain(env)
    assert f"{policy['tools'][0]['env']} is required" in errors
    assert str(tmp_path) not in " ".join(errors)


def test_installed_excluded_payload_rejected(
    tmp_path: Path, monkeypatch
) -> None:
    policy, env = _fixture(tmp_path)
    monkeypatch.setattr(triton_runtime, "load_policy", lambda: policy)
    monkeypatch.setattr(triton_runtime.sys, "platform", "linux")
    monkeypatch.setattr(triton_runtime.platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(triton_runtime.sys, "version_info", (3, 13, 5))
    monkeypatch.setattr(
        triton_runtime.metadata, "version", lambda _name: "3.7.1+capsize.2"
    )
    package_root = _package_root(policy, tmp_path)
    excluded = package_root / "backends/nvidia/bin/ptxas"
    excluded.parent.mkdir(parents=True)
    excluded.touch()
    monkeypatch.setattr(
        triton_runtime, "_installed_triton_root", lambda: package_root
    )
    assert (
        "installed Triton candidate contains excluded NVIDIA payload"
        in triton_runtime.validate_toolchain(env)
    )


def test_missing_retained_libdevice_is_rejected_without_override(
    tmp_path: Path, monkeypatch
) -> None:
    policy, env = _fixture(tmp_path)
    monkeypatch.setattr(triton_runtime, "load_policy", lambda: policy)
    monkeypatch.setattr(triton_runtime.sys, "platform", "linux")
    monkeypatch.setattr(triton_runtime.platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(triton_runtime.sys, "version_info", (3, 13, 5))
    monkeypatch.setattr(
        triton_runtime.metadata, "version", lambda _name: "3.7.1+capsize.2"
    )
    package_root = tmp_path / "site-packages" / "triton"
    package_root.mkdir(parents=True)
    monkeypatch.setattr(
        triton_runtime, "_installed_triton_root", lambda: package_root
    )

    errors = triton_runtime.validate_toolchain(env)

    assert "retained Triton libdevice must be a regular file" in errors
    assert policy["libdevice"]["env"] not in env
    assert str(tmp_path) not in " ".join(errors)


def test_wrong_target_fails_before_tool_paths_are_checked(
    tmp_path: Path, monkeypatch
) -> None:
    policy, _ = _fixture(tmp_path)
    monkeypatch.setattr(triton_runtime, "load_policy", lambda: policy)
    monkeypatch.setattr(triton_runtime.sys, "platform", "darwin")
    assert triton_runtime.validate_toolchain({}) == [
        "Triton external toolchain is supported only on Linux x86_64"
    ]
