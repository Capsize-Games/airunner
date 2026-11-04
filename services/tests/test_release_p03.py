"""Regression tests for release issue P03.

P03 unifies the pinned native runtime manifests and release artifacts.
The in-repo build (``scripts/build_runtime_sidecars.sh``,
``native/runtime_sidecars/``,
``.github/workflows/native-runtime-sidecars.yml``) was extracted to
``Capsize-Games/airunner-native`` (issue #2196), so the unification
contract in this repository is now:

- one authoritative pin, ``.github/native-sidecar-version``, consumed
  by the CPU sidecar installer/release workflow, plus an independent
  verified CUDA profile pin when CUDA payload delivery is requested;
- the published bundle layout (``bin/llama-server``,
  ``bin/whisper-server``, full notices/provenance, and the isolated CUDA
  profile) matching runtime discovery without replacing the CPU binary;
- no developer absolute paths and no undocumented system binaries in
  the installer sidecar path;
- documentation describing the pinned-bundle flow, not the removed
  in-repo build.

No GUI launch, real model, network, or database side effects. The
bundle layout is exercised against a synthetic ``tmp_path`` tree and
``resolve_runtime_executable``; the installer and workflow are read as
text and never executed.
"""

from __future__ import annotations

from pathlib import Path
import json

import pytest

from airunner_services.runtimes.bundled_runtime_paths import (
    resolve_runtime_executable,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PIN_FILE = _REPO_ROOT / ".github" / "native-sidecar-version"
_CHECKSUM_FILE = _REPO_ROOT / ".github" / "native-sidecar-checksums.json"
_INSTALL_SH = _REPO_ROOT / "scripts" / "install.sh"
_WORKFLOW = _REPO_ROOT / ".github" / "workflows" / "pypi-dispatch.yml"
_DOCKERFILE = _REPO_ROOT / "Dockerfile"
_DOCKER_WORKFLOW = _REPO_ROOT / ".github" / "workflows" / "docker-release.yml"
_DEV_LAUNCHER = _REPO_ROOT / "scripts" / "dev" / "run_services.sh"
_NATIVE_REPO = "Capsize-Games/airunner-native"
_LINUX_BUNDLE = "runtime-sidecars-linux.tar.gz"
_SIDECAR_BINARIES = ("llama-server", "whisper-server")


def _read_text(path: Path) -> str:
    """Return the UTF-8 text of a repository file."""
    return path.read_text(encoding="utf-8")


def test_tag_and_digest_metadata_bind_one_native_sidecar_source() -> None:
    """The tag and checksum records bind to the reviewed source commit."""
    raw = _read_text(_PIN_FILE)
    lines = [line for line in raw.splitlines() if line.strip()]
    assert len(lines) == 1, raw
    tag = lines[0].strip()
    assert tag and "/" not in tag and " " not in tag, raw
    metadata = json.loads(_read_text(_CHECKSUM_FILE))
    assert metadata["tag"] == tag == "v0.3.0"
    assert metadata["source_commit"] == "3d1806423402f47d1f7612a8cd8fc70d48c5a3c2"
    assert metadata["source_review_status"] == "reviewed"
    review = "release-planning/services/input-reviews/airunner-native-0.3.0.md"
    assert review in metadata["source_review_note"]
    assert (_REPO_ROOT / review).is_file()
    assert metadata["provenance_status"] == "verified"
    assert metadata["archives"]["linux"]["sha256"] == (
        "59adcd438fed44c63ed65a4b17cfbf4afbdecaba164cfeec3d300b909dd5d9e0"
    )
    assert metadata["archives"]["windows"]["sha256"] == (
        "b7f671b693b1a78c6d100e5287306bd5a05420a5ef46c7d5d7fd4e72882c7aa1"
    )


def test_removed_in_repo_sidecar_build_stays_removed() -> None:
    """The extracted build must not drift back as a duplicate."""
    assert not (_REPO_ROOT / "scripts" / "build_runtime_sidecars.sh").exists()
    assert not (_REPO_ROOT / "native" / "runtime_sidecars").exists()
    assert not (
        _REPO_ROOT / ".github" / "workflows" / "native-runtime-sidecars.yml"
    ).exists()


def test_installer_consumes_pin_file_without_hardcoded_tag() -> None:
    """The staging helper resolves the CPU tag from the checked-in pin."""
    text = _read_text(_INSTALL_SH)
    stager = _read_text(_REPO_ROOT / "scripts" / "stage_native_runtime_payload.py")
    assert "stage_native_runtime_payload.py" in text
    assert 'CPU_TAG_FILE = ROOT / ".github/native-sidecar-version"' in stager
    assert 'CPU_ASSET = "runtime-sidecars-linux.tar.gz"' in stager


def test_release_workflow_consumes_same_pin_and_repo() -> None:
    """The release workflow mirrors the installer, not a second pin."""
    text = _read_text(_WORKFLOW)
    assert ".github/native-sidecar-version" in text
    assert _NATIVE_REPO in text
    assert "releases/download/${tag}/" in text
    assert "for platform in linux windows" in text
    assert "runtime-sidecars-${platform}.tar.gz" in text
    assert "--checksums .github/native-sidecar-checksums.json" in text
    assert "python scripts/sidecar_archive.py verify" in text
    fetch = text.split("  fetch-sidecars:", 1)[1].split(
        "  publish-release-assets:", 1
    )[0]
    assert fetch.index("sidecar_archive.py check-pin") < fetch.index("curl -fsSL")
    assert fetch.index("curl -fsSL") < fetch.index("sidecar_archive.py verify")


def test_bundle_bin_layout_matches_runtime_discovery(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Discovery resolves the same bin/ names the bundle ships."""
    bin_dir = tmp_path / "bundle" / "bin"
    bin_dir.mkdir(parents=True)
    for name in _SIDECAR_BINARIES:
        candidate = bin_dir / name
        candidate.write_text("#!/bin/sh\n")
        candidate.chmod(0o755)
    monkeypatch.setenv("AIRUNNER_BUNDLE_ROOT", str(tmp_path / "bundle"))
    monkeypatch.delenv("AIRUNNER_LLAMA_SERVER_BIN", raising=False)
    monkeypatch.delenv("AIRUNNER_WHISPER_SERVER_BIN", raising=False)

    assert resolve_runtime_executable(
        "AIRUNNER_LLAMA_SERVER_BIN", "llama-server"
    ) == str(bin_dir / "llama-server")
    assert resolve_runtime_executable(
        "AIRUNNER_WHISPER_SERVER_BIN", "whisper-server"
    ) == str(bin_dir / "whisper-server")


def test_explicit_override_wins_over_bundle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An explicit binary path still bypasses bundle discovery."""
    custom = tmp_path / "custom-llama-server"
    custom.write_text("#!/bin/sh\n")
    # resolve_runtime_executable requires the override to be executable
    # (PermissionError otherwise, enforced since the voice-slice
    # hardening): the fixture binary must carry the exec bit.
    custom.chmod(0o755)
    monkeypatch.setenv("AIRUNNER_BUNDLE_ROOT", str(tmp_path))
    monkeypatch.setenv("AIRUNNER_LLAMA_SERVER_BIN", str(custom))

    assert resolve_runtime_executable(
        "AIRUNNER_LLAMA_SERVER_BIN", "llama-server"
    ) == str(custom)


def test_unknown_binary_falls_back_to_plain_name(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A missing binary degrades to a PATH lookup, not a crash."""
    monkeypatch.setenv("AIRUNNER_BUNDLE_ROOT", str(tmp_path))
    monkeypatch.delenv("AIRUNNER_LLAMA_SERVER_BIN", raising=False)

    assert (
        resolve_runtime_executable(
            "AIRUNNER_LLAMA_SERVER_BIN", "not-a-sidecar-binary"
        )
        == "not-a-sidecar-binary"
    )


def test_installer_links_the_discovered_binary_names() -> None:
    """The installer link step uses the bundle/discovery names."""
    text = _read_text(_INSTALL_SH)
    assert "for binary_name in llama-server whisper-server" in text
    assert 'link_sidecar_binaries "$NATIVE_RUNTIME_DIR/bin"' in text


def test_installer_sidecar_paths_are_repo_relative() -> None:
    """No developer absolute paths in the sidecar download/link flow."""
    text = _read_text(_INSTALL_SH)
    for forbidden in ("/home/", "/root/", "/Users/", "/tmp/"):
        assert forbidden not in text, forbidden
    assert 'NATIVE_RUNTIME_DIR="$ROOT_DIR/build/runtime-sidecars/linux"' in text
    assert 'NATIVE_CUDA_PROFILE_PIN="${AIRUNNER_NATIVE_CUDA_PROFILE_PIN:-' in text


def test_installer_and_workflow_consume_expected_archive_digests() -> None:
    """Both download paths require the committed checksum authority."""
    installer = _read_text(_INSTALL_SH)
    workflow = _read_text(_WORKFLOW)
    assert "stage_native_runtime_payload.py" in installer
    assert ".github/native-sidecar-checksums.json" in workflow
    assert "sidecar_archive.py verify" in workflow


def test_installer_never_extracts_an_unverified_tarball() -> None:
    """Hash verification and file selection precede both installed links."""
    text = _read_text(_INSTALL_SH)
    assert "tar -xzf" not in text
    stage = text.index('stage_native_runtime_payload.py"')
    link = text.index('link_sidecar_binaries "$NATIVE_RUNTIME_DIR/bin"')
    assert stage < link
    assert "--require-cuda-profile" in text
    assert "--cuda-profile-pin \"$NATIVE_CUDA_PROFILE_PIN\"" in text


def test_cuda_selection_never_falls_back_to_a_source_build() -> None:
    """CUDA selection stages only the independently pinned release profile."""
    text = _read_text(_INSTALL_SH)
    assert "build_sidecars_from_source" not in text
    assert "build_runtime_sidecars.sh" not in text
    assert "git -c core.hooksPath=/dev/null clone" not in text
    assert "no reviewed CUDA profile pin" in _read_text(
        _REPO_ROOT / "scripts" / "stage_native_runtime_payload.py"
    )


def test_dev_launcher_uses_profile_override_without_changing_bundle_root() -> None:
    text = _read_text(_DEV_LAUNCHER)
    assert "AIRUNNER_LLAMA_CUDA_PROFILE_ROOT" in text
    assert "unset AIRUNNER_LLAMA_CUDA_PROFILE_ROOT" in text
    assert "AIRUNNER_BUNDLE_ROOT=" not in text


def test_runtime_settings_accept_separate_profile_root_override() -> None:
    text = _read_text(
        _REPO_ROOT
        / "services/src/airunner_services/runtimes/llama_cpp_runtime_settings.py"
    )
    assert 'cuda_profile_root=os.environ.get("AIRUNNER_LLAMA_CUDA_PROFILE_ROOT")' in text


def test_full_docker_image_requires_both_verified_profiles_and_preserves_runtime_paths() -> None:
    dockerfile = _read_text(_DOCKERFILE)
    workflow = _read_text(_DOCKER_WORKFLOW)
    assert "source=native-runtime" in dockerfile
    assert "sha256sum -c SHA256SUMS" in dockerfile
    assert "/native-runtimes/cuda-sm120a/profile-manifest.json" in dockerfile
    assert "COPY --from=reviewed-inputs /native-runtime/payload/ /opt/airunner/" in dockerfile
    assert "ENV AIRUNNER_BUNDLE_ROOT=/opt/airunner" in dockerfile
    assert "AIRUNNER_BUNDLE_ROOT=/opt/airunner" in dockerfile
    assert "AIRUNNER_PYTHON" not in dockerfile
    assert "install -m 0755 /opt/airunner-speech/bin/espeak-ng /opt/airunner/bin/espeak-ng" in dockerfile
    assert "cp -a /opt/airunner-speech/share/espeak-ng-data /opt/airunner/share/espeak-ng-data" in dockerfile
    assert "--require-cuda-profile" in workflow


def test_docs_do_not_reference_removed_build_paths() -> None:
    """Synced docs describe the pinned bundle, not the old build."""
    doc_paths = [
        _REPO_ROOT / "README.md",
        _REPO_ROOT / "native" / "README.md",
        _REPO_ROOT / "scripts" / "README.md",
        _REPO_ROOT / "docs" / "architecture" / "package_split_contract.md",
    ]
    for doc_path in doc_paths:
        text = _read_text(doc_path)
        assert "scripts/build_runtime_sidecars.sh" not in text
        assert "native/runtime_sidecars/" not in text
        assert "build/runtime-sidecars/linux" not in text
        for line in text.splitlines():
            if "native-runtime-sidecars" in line:
                assert "airunner-native" in line, line


def test_settings_modules_use_bundle_binary_names() -> None:
    """LLM/STT settings resolve the exact names the bundle ships."""
    runtimes = (
        _REPO_ROOT / "services" / "src" / "airunner_services" / "runtimes"
    )
    llama_text = _read_text(runtimes / "llama_cpp_runtime_settings.py")
    whisper_text = _read_text(runtimes / "whisper_cpp_runtime_settings.py")
    assert '"llama-server"' in llama_text
    assert '"whisper-server"' in whisper_text
