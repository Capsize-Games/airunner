"""CORE frozen profile stays separate from the full P05 ML bundle."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
SERVICES_SRC = ROOT / "services/src"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
if str(SERVICES_SRC) not in sys.path:
    sys.path.insert(0, str(SERVICES_SRC))

import inspect_linux_bundle  # noqa: E402
import linux_bundle_assemble  # noqa: E402


def test_core_spec_inherits_resources_but_replaces_full_ml_profile() -> None:
    spec = inspect_linux_bundle.load_spec(
        ROOT / "packaging/linux/services-core-bundle-spec.toml"
    )

    assert spec["bundle"]["name"] == "airunner-services-core"
    assert spec["bundle"]["executable"] == "airunner-core"
    assert spec["bundle"]["constraints"] == "package/constraints-linux-core.txt"
    assert spec["profile"]["aggregates"] == []
    assert spec["code"]["collect_binaries"] == []
    assert spec["code"]["runtime_hooks"] == []
    assert spec["code"]["collect_submodules"] == []
    assert "torch" not in spec["code"]["collect_binaries"]
    excluded_modules = set(spec["code"]["exclude_modules"])
    assert {
        "torch",
        "torchvision",
        "torchaudio",
        "llama_cpp",
        "gguf",
        "airunner_tts_vendor",
        "facehuggershield",
        "transformers",
        "diffusers",
        "safetensors",
        "accelerate",
        "bitsandbytes",
    } <= excluded_modules
    assert set(spec["profile"]["excludes"]) >= {
        "torch",
        "llama-cpp-python",
        "airunner-tts-vendor",
        "facehuggershield",
    }
    assert {
        "*.gguf",
        "*.safetensors",
        "*.pt",
        "*.pth",
        "*.ckpt",
        "*.onnx",
    } <= set(spec["exclusions"]["patterns"])
    assert "services/src/airunner_services/database/alembic.ini" in {
        entry["source"] for entry in spec["data"]
    }
    assert spec["data"] == inspect_linux_bundle.load_spec()["data"]
    required_data = {
        entry["source"] for entry in spec["data"] if entry.get("required", True)
    }
    assert {
        "services/src/airunner_services/database/alembic.ini",
        "services/src/airunner_services/database/alembic/*.py",
        "services/src/airunner_services/database/alembic/*.mako",
        "services/src/airunner_services/database/alembic/versions/*.py",
        "services/src/airunner_services/assets/reference_speakers/*.wav",
        "services/src/airunner_services/bin/*.sh",
        "LICENSE",
        "NOTICE",
        "THIRD_PARTY_NOTICES.md",
        "packaging/licenses/libuv-LICENSE",
        "packaging/licenses/watchfiles-rust-crates/*",
        "packaging/licenses/pydantic-core-rust-crates/*",
    } <= required_data
    for entry in spec["data"]:
        if entry.get("required", True):
            assert linux_bundle_assemble.expand_data(entry, ROOT)
    assert all(
        not entry.get("content_policy")
        for entry in spec["data"]
        if entry.get("required", True)
    )
    assert not inspect_linux_bundle.spec_errors(spec)
    coverage = spec["r01_coverage"]
    assert coverage["VOICE-04"] == "deferred:openvoice"
    assert coverage["ART-01"] == "optional:art-runtime"
    assert coverage["CHAT-03"] == "optional:llm-runtime"
    bundled_extras = {
        "art-python",
        "llm-native",
        "stt-native",
        "tts-python",
        "search",
    }
    assert all(
        token not in bundled_extras
        for value in coverage.values()
        for token in str(value).split(",")
    )
    assert spec["runtimes"]["bin_dir"] == "bin"
    assert spec["runtimes"]["root_env"] == "AIRUNNER_BUNDLE_ROOT"
    assert {
        (runtime["name"], runtime["feature"])
        for runtime in spec["runtime"]
    } == {("llama-server", "CHAT-03"), ("whisper-server", "VOICE-02")}


def test_dispatcher_names_match_the_service_console_contract() -> None:
    import ast

    setup_tree = ast.parse((ROOT / "services/setup.py").read_text(encoding="utf-8"))
    contract = next(
        node.value
        for node in setup_tree.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name)
            and target.id == "SERVICE_CONSOLE_SCRIPTS"
            for target in node.targets
        )
    )
    expected = {}
    for item in contract.elts:
        name, target = ast.literal_eval(item).split("=", 1)
        expected[name] = target
    source = (
        ROOT / "services/src/airunner_services/bundle_console_dispatch.py"
    ).read_text(encoding="utf-8")
    dispatch_tree = ast.parse(source)
    mapping = next(
        node.value
        for node in dispatch_tree.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "_ENTRY_POINTS"
            for target in node.targets
        )
    )
    actual = {
        ast.literal_eval(key): ":".join(ast.literal_eval(value))
        for key, value in zip(mapping.keys, mapping.values)
    }
    assert {
        name: target
        for name, target in actual.items()
        if name != "airunner-core"
    } == expected
    assert actual["airunner-core"] == "airunner_services.daemon:main"

    spec = inspect_linux_bundle.load_spec(
        ROOT / "packaging/linux/services-core-bundle-spec.toml"
    )
    hidden_imports = set(spec["code"]["hidden_imports"])
    assert {target.split(":", 1)[0] for target in expected.values()} <= hidden_imports


def test_dispatcher_uses_the_symlink_name_and_keeps_process_arguments(
    monkeypatch,
    tmp_path,
) -> None:
    import importlib
    from types import SimpleNamespace

    from airunner_services import bundle_console_dispatch

    executable = tmp_path / "airunner-core"
    executable.write_text("fake executable", encoding="utf-8")
    invocations = []

    for alias, (module_name, _function_name) in (
        bundle_console_dispatch._ENTRY_POINTS.items()
    ):
        invoked_argv = [str(tmp_path / alias), "--daemon-config", "daemon.yaml"]
        if alias != "airunner-core":
            (tmp_path / alias).symlink_to(executable)

        def fake_main(module_name=module_name):
            invocations.append((module_name, list(bundle_console_dispatch.sys.argv)))
            return 17

        monkeypatch.setattr(
            importlib,
            "import_module",
            lambda _name: SimpleNamespace(main=fake_main),
        )
        monkeypatch.setattr(bundle_console_dispatch.sys, "argv", invoked_argv)

        assert bundle_console_dispatch.main() == 17
        assert invocations[-1] == (module_name, invoked_argv)


def test_generated_entry_propagates_exit_code_and_arguments(tmp_path) -> None:
    import os
    import subprocess

    (tmp_path / "fake_entry.py").write_text(
        "import sys\n"
        "def main():\n"
        "    return 23 if sys.argv[1:] == ['--probe', 'kept'] else 91\n",
        encoding="utf-8",
    )
    entry = linux_bundle_assemble.write_entry_script(
        tmp_path, "fake_entry", "main"
    )
    env = dict(os.environ)
    env["PYTHONPATH"] = str(tmp_path)

    result = subprocess.run(
        [sys.executable, str(entry), "--probe", "kept"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 23, result.stderr


def test_dispatcher_accepts_real_symlink_argv0_in_fake_process(tmp_path) -> None:
    import json
    import os
    import subprocess

    executable = tmp_path / "airunner-core"
    executable.write_text(
        f"#!{sys.executable}\n"
        "import sys\n"
        "import types\n"
        "import json\n"
        "target = types.ModuleType('airunner_services.bin.airunner_headless')\n"
        "def main():\n"
        "    print(json.dumps(sys.argv))\n"
        "    return 29\n"
        "target.main = main\n"
        "sys.modules[target.__name__] = target\n"
        "from airunner_services.bundle_console_dispatch import main as dispatch\n"
        "raise SystemExit(dispatch())\n",
        encoding="utf-8",
    )
    executable.chmod(0o755)
    alias = tmp_path / "airunner-headless"
    alias.symlink_to(executable)
    env = dict(os.environ)
    env["PYTHONPATH"] = str(SERVICES_SRC)

    result = subprocess.run(
        [str(alias), "--daemon-config", "daemon.yaml"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 29, result.stderr
    assert json.loads(result.stdout) == [
        str(alias),
        "--daemon-config",
        "daemon.yaml",
    ]


def test_core_build_command_keeps_vendor_path_and_omits_standard_policy_data(
    tmp_path,
) -> None:
    spec = inspect_linux_bundle.load_spec(
        ROOT / "packaging/linux/services-core-bundle-spec.toml"
    )
    entry = tmp_path / "entry.py"
    command = linux_bundle_assemble.build_command(
        spec,
        ROOT,
        entry,
        tmp_path / "dist",
        tmp_path / "work",
        "pyinstaller",
    )

    search_paths = [
        command[index + 1]
        for index, value in enumerate(command[:-1])
        if value == "--paths"
    ]
    assert search_paths == [
        str(ROOT / "services/src"),
        str(ROOT / "native/src"),
        str(ROOT / "debian/vendor"),
    ]
    assert not any(
        "content_safety/data" in value for value in command
    )
    excluded = {
        command[index + 1]
        for index, value in enumerate(command[:-1])
        if value == "--exclude-module"
    }
    assert {
        "torch",
        "torchvision",
        "torchaudio",
        "llama_cpp",
        "gguf",
        "airunner_tts_vendor",
        "facehuggershield",
        "transformers",
        "diffusers",
        "safetensors",
        "accelerate",
        "bitsandbytes",
    } <= excluded


def test_vendored_common_matches_the_reviewed_618_release_manifest() -> None:
    import ast
    import hashlib
    import json

    vendor = ROOT / "debian/vendor"
    manifest = json.loads(
        (vendor / "airunner-common.json").read_text(encoding="utf-8")
    )
    assert manifest["distribution"] == "airunner-common"
    assert manifest["version"] == "6.1.8"
    assert manifest["source_repository"] == (
        "https://github.com/Capsize-Games/airunner-common"
    )
    assert manifest["source_commit"] == "733b0f4c8fb38952866e9cf7be2cc69793a46e92"
    assert manifest["wheel_filename"] == "airunner_common-6.1.8-py3-none-any.whl"
    assert manifest["wheel_sha256"] == (
        "ac2110ecbcd965c9a773405494bcecb3d1c6c5f127d22fde81d37478b94088fd"
    )
    assert manifest["wheel_record_verified"] is True

    files = manifest["vendored_files_sha256"]
    actual_files = {
        path.relative_to(vendor).as_posix()
        for path in (vendor / "airunner_common").glob("*.py")
    }
    assert actual_files == set(files)
    for relative_path, expected in files.items():
        actual = hashlib.sha256((vendor / relative_path).read_bytes()).hexdigest()
        assert actual == expected, relative_path

    license_info = manifest["license"]
    license_bytes = (ROOT / license_info["path"]).read_bytes()
    assert hashlib.sha256(license_bytes).hexdigest() == license_info["sha256"]

    metadata = ast.parse(
        (vendor / "airunner_common/package_metadata.py").read_text(
            encoding="utf-8"
        )
    )
    version = next(
        ast.literal_eval(node.value)
        for node in metadata.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "VERSION"
            for target in node.targets
        )
    )
    assert version == manifest["version"]


def test_debian_binary_depends_on_frozen_closure_and_preserves_systemd_alias() -> None:
    control = (ROOT / "debian/control").read_text(encoding="utf-8")
    rules = (ROOT / "debian/rules").read_text(encoding="utf-8")
    unit = (ROOT / "debian/airunner.airunner-headless.service").read_text(
        encoding="utf-8"
    )

    assert "Architecture: amd64" in control
    assert "${shlibs:Depends}" in control
    assert "${python3:Depends}" not in control
    assert "services-core-bundle-spec.toml" in rules
    assert "AIRUNNER_CORE_PYTHON" in rules
    assert "ExecStart=/usr/bin/airunner-headless" in unit
