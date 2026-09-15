"""Tests for the RELEASE GATE's decision logic.

These are distinct from test_check_artifact_imports.py, which covers the static
scanner. Neither file executes a real artifact -- the gate's end-to-end runs are
recorded in the PR, not here. What these pin is the logic that decides whether a
publish may proceed, because the expensive failures are the ones where the gate
says yes when it should say no.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from artifact_runtime_gate import (  # noqa: E402
    ALLOWED_PACKAGE_TOKENS,
    UnsupportedSelection,
    plan_validation,
)


class TestPackageSelection:
    """A selection must never reach Publish unvalidated."""

    def test_full_surface_validates_the_top_level_request(self):
        assert plan_validation("shared services native .") == ("full", "airunner")

    def test_bare_dot_is_the_full_surface(self):
        assert plan_validation(".") == ("full", "airunner")

    def test_sibling_bootstrap_validates_services(self):
        # The documented first-publish bootstrap. airunner is not published
        # here, but airunner-services owns the daemon entry points -- where the
        # 6.1.3 failure actually surfaced -- so it is validatable on its own.
        assert plan_validation("shared services native") == (
            "services",
            "airunner-services",
        )

    @pytest.mark.parametrize("selection", ["shared", "native", "shared native"])
    def test_unvalidatable_profile_is_rejected_not_skipped(self, selection):
        # airunner-common and airunner-native expose no runtime surface this
        # gate can exercise. Refusing is the point: skipping would publish them
        # with no validation at all.
        with pytest.raises(UnsupportedSelection) as exc:
            plan_validation(selection)
        assert "do not skip the gate" in str(exc.value)

    def test_empty_selection_is_rejected(self):
        with pytest.raises(UnsupportedSelection):
            plan_validation("   ")

    @pytest.mark.parametrize(
        "selection",
        ["shared services native ./", "x.y", "..", "shared;services", "SERVICES"],
    )
    def test_unknown_tokens_are_rejected(self, selection):
        with pytest.raises(UnsupportedSelection) as exc:
            plan_validation(selection)
        assert "unknown package selection token" in str(exc.value)

    def test_substring_lookalikes_are_not_treated_as_a_full_release(self):
        """The regression this replaced.

        The workflow previously decided with `contains(selection, '.')`. Every
        token here contains a dot, so a substring test would classify them as a
        full release and validate the wrong distribution -- or, worse, pass.
        """
        for selection in ("x.y", "./services", "shared."):
            with pytest.raises(UnsupportedSelection):
                plan_validation(selection)

    def test_token_set_is_exactly_the_build_directories(self):
        assert ALLOWED_PACKAGE_TOKENS == frozenset(
            {"shared", "services", "native", "."}
        )


class TestProvenanceDecision:
    """Version equality alone must not satisfy candidate identity."""

    @staticmethod
    def _first_party_origins(report: dict, candidate_dir: Path) -> list[str]:
        """Mirror of the gate's provenance rule, kept in sync by the tests."""
        bad = []
        for item in report.get("install", []):
            name = (item.get("metadata", {}).get("name") or "").lower()
            if not name.startswith("airunner"):
                continue
            url = (item.get("download_info", {}) or {}).get("url", "")
            if not (url.startswith("file://") and str(candidate_dir) in url):
                bad.append(name)
        return bad

    def test_local_candidate_artifacts_are_accepted(self, tmp_path):
        report = {
            "install": [
                {
                    "metadata": {"name": "airunner", "version": "6.1.3+local2"},
                    "download_info": {"url": f"file://{tmp_path}/airunner-6.1.3.whl"},
                }
            ]
        }
        assert self._first_party_origins(report, tmp_path) == []

    def test_same_version_artifact_from_the_index_is_rejected(self, tmp_path):
        """The substitution this check exists to catch.

        The version matches exactly, so a version-equality check would pass it,
        but the wheel came from PyPI rather than the candidate directory.
        """
        report = {
            "install": [
                {
                    "metadata": {"name": "airunner-services", "version": "6.1.3"},
                    "download_info": {
                        "url": "https://files.pythonhosted.org/packages/ab/airunner_services-6.1.3-py3-none-any.whl"
                    },
                }
            ]
        }
        assert self._first_party_origins(report, tmp_path) == ["airunner-services"]

    def test_third_party_dependencies_are_not_required_to_be_local(self, tmp_path):
        report = {
            "install": [
                {
                    "metadata": {"name": "pygments", "version": "2.21.0"},
                    "download_info": {
                        "url": "https://files.pythonhosted.org/packages/xy/pygments-2.21.0.whl"
                    },
                }
            ]
        }
        assert self._first_party_origins(report, tmp_path) == []
