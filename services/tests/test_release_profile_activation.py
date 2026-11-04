"""Prevent release defaults from selecting deferred vendor profiles."""

from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_HELPERS = ROOT / "scripts/install_helpers.sh"
_INSTALL = ROOT / "scripts/install.sh"
_DISTRIBUTED_INSTALL = ROOT / "deployment/install_distributed.sh"
_DOCKERFILE = ROOT / "Dockerfile"
_DOCKER_RELEASE = ROOT / ".github/workflows/docker-release.yml"
_DOCKER_COMPOSE_DEV = ROOT / "docker-compose.dev.yml"
_DOCKER_STAGER = ROOT / "scripts/stage_docker_release_inputs.py"


def _helper_profile_status(profile: str) -> int:
    """Run only the side-effect-free profile predicate in bash."""
    result = subprocess.run(
        [
            "bash", "-c",
            'source "$1"; service_profile_uses_deferred_tts_vendor "$2"',
            "release-profile-test", str(_HELPERS), profile,
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=5,
    )
    return result.returncode


def test_supported_profile_is_not_vendor_bearing() -> None:
    assert _helper_profile_status("linux-release") == 1
    assert _helper_profile_status("tts-python-core") == 1


def test_legacy_vendor_profiles_are_rejected_by_shared_predicate() -> None:
    for profile in (
        "tts-python", "headless", "desktop", "all", "all_dev",
        "all_native", "all_dev_native", "windows", "openvoice",
        "melotts", "openvoice_jp", "gruut_support",
    ):
        assert _helper_profile_status(profile) == 0, profile


def test_local_installers_default_to_release_and_reject_legacy_profiles() -> None:
    install = _INSTALL.read_text(encoding="utf-8")
    distributed = _DISTRIBUTED_INSTALL.read_text(encoding="utf-8")

    assert 'AIRUNNER_DEV_SERVICE_PROFILE:-linux-release' in install
    assert "SERVICE_PROFILE=\"${AIRUNNER_DEV_SERVICE_PROFILE:-desktop}\"" not in install
    assert "service_profile_uses_deferred_tts_vendor \"$SERVICE_PROFILE\"" in install
    assert "printf 'linux-release\\n'" in distributed
    assert "service_profile_uses_deferred_tts_vendor \"$service_profile\"" in distributed
    for source in (install, distributed):
        guard = source.index("service_profile_uses_deferred_tts_vendor")
        python_resolution = source.index('find_python "$PYTHON_CMD" 3.13')
        assert guard < python_resolution


def test_docker_default_uses_release_profile_and_blocks_vendor_profiles_early() -> None:
    dockerfile = _DOCKERFILE.read_text(encoding="utf-8")

    assert "ARG AIRUNNER_INSTALL_PROFILES=linux-release" in dockerfile
    guard = dockerfile.index("activates deferred airunner-tts-vendor")
    apt_install = dockerfile.index("apt-get update && apt-get install")
    assert guard < apt_install
    assert "reviewed Docker inputs cover only AIRUNNER_INSTALL_PROFILES=linux-release" in dockerfile
    assert "profile_match 'stt-native|tts-python-core|linux-release" in dockerfile
    assert "--no-index --find-links=/tmp/release-inputs/runtime" in dockerfile
    assert "pip-26.2.2-py3-none-any.whl" in dockerfile
    assert "https://bootstrap.pypa.io/get-pip.py" not in dockerfile
    assert "--no-index --find-links=/tmp/release-inputs/bootstrap" in dockerfile
    assert "pip-26.2.2.dist-info/licenses" in dockerfile
    assert "/usr/share/doc/airunner/legal/bootstrap-pip" in dockerfile
    assert "--require-hashes -r /tmp/release-inputs/runtime/requirements.txt" in dockerfile
    assert "--require-hashes -r /tmp/release-inputs/builder/requirements.txt" in dockerfile
    assert "--no-deps --no-build-isolation" in dockerfile
    assert "pip install --upgrade pip setuptools wheel" not in dockerfile
    assert "--extra-index-url" not in dockerfile
    assert "--no-binary=llama-cpp-python" not in dockerfile
    assert "from=reviewed-inputs,source=runtime" in dockerfile
    assert "from=reviewed-inputs,source=builder" in dockerfile
    assert "collect_runtime_dependency_notices.py" in dockerfile
    assert "desktop-equivalent release aggregate" not in dockerfile
    guard = dockerfile[dockerfile.index("RUN case "):dockerfile.index(
        "# Install system dependencies"
    )]
    for legacy_profile in (
        "tts-python", "headless", "desktop", "all", "all_dev",
        "all_native", "all_dev_native", "windows", "openvoice",
        "melotts", "openvoice_cn", "openvoice_jp", "openvoice_kr",
        "openvoice_tw", "gruut_support",
    ):
        assert f"*,{legacy_profile},*" in guard


def test_docker_release_job_selects_release_profile() -> None:
    workflow = _DOCKER_RELEASE.read_text(encoding="utf-8")
    assert "profiles: linux-release" in workflow
    assert "profiles: core,llm-native,stt-native,art-python,tts-python" not in workflow


def test_docker_release_stages_hashed_inputs_outside_the_image_context() -> None:
    workflow = _DOCKER_RELEASE.read_text(encoding="utf-8")
    stager = _DOCKER_STAGER.read_text(encoding="utf-8")
    stage = workflow.index("Stage reviewed Docker build inputs")
    build = workflow.index("Build ${{ matrix.name }} image")
    assert stage < build
    assert "scripts/stage_docker_release_inputs.py --output-dir \"$inputs\"" in workflow
    for name in (
        "package/linux-release-v4-artifact-sources.json",
        "package/constraints-linux-nvidia-cu129-linux-release.txt",
        "package/linux-builder-tools-artifact-sources.json",
        "package/constraints-linux-builder-tools.txt",
        "package/linux-docker-bootstrap-artifact-sources.json",
        "package/constraints-linux-docker-bootstrap.txt",
    ):
        assert name in stager
    assert "GH_TOKEN: ${{ github.token }}" in workflow
    assert "reviewed-inputs=${{ env.DOCKER_RELEASE_INPUTS }}" in workflow
    assert 'echo "DOCKER_RELEASE_INPUTS=$inputs" >> "$GITHUB_ENV"' in workflow


def test_development_compose_requires_prepared_reviewed_inputs() -> None:
    compose = _DOCKER_COMPOSE_DEV.read_text(encoding="utf-8")
    assert "additional_contexts:" in compose
    assert "reviewed-inputs: ${AIRUNNER_DOCKER_REVIEWED_INPUTS:?" in compose
    assert "docker-compose.dev.yml" in compose
    assert "Stage reviewed inputs first" in compose


def test_docker_input_stager_is_allowlisted_and_external_to_checkout() -> None:
    source = _DOCKER_STAGER.read_text(encoding="utf-8")
    assert '"release-source"' in source
    assert '".git"' not in source
    assert '".headlesscode"' not in source
    assert "must be outside the repository" in source
    assert "must not be a symlink" in source
