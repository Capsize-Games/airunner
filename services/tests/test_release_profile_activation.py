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
    assert "profile_match 'stt-native|tts-python-core|linux-release" in dockerfile
    assert "grep -Eq ',(llm-native|linux-release" in dockerfile
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
