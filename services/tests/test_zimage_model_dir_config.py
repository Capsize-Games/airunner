"""Regression tests for issue #2066: config-derived Z-Image model dir.

``resolve_zimage_txt2img_dir`` must derive the Z-Image txt2img directory
from the configured service base path — never from hardcoded developer or
container home directories. The previous implementation fell back to
``/home/airunner/.local/share/...`` and ``/home/joe/.local/share/...``,
which made model version resolution correct only on those machines.

Acceptance criteria pinned here:
- ``services/src/airunner_services/api/routes/art_model_versions.py``
  contains no ``/home/airunner`` or ``/home/joe`` literal.
- The route resolves the directory as
  ``Path(service_base_path()) / "art" / "models" / "Z-Image Turbo" / "txt2img"``.
- A non-existent config-derived path returns an empty string (no wrong
  fallback path on machines where the models are not installed).
"""

from __future__ import annotations

import re
from pathlib import Path

from airunner_services.api.routes import art_model_versions

_ROUTE_FILE = Path(art_model_versions.__file__).resolve()


def _source_text() -> str:
    return _ROUTE_FILE.read_text(encoding="utf-8")


def test_no_hardcoded_home_fallbacks_in_route() -> None:
    """No developer/container home paths survive in the route source."""
    matches = re.findall(r"home/(?:airunner|joe)", _source_text())
    assert not matches, (
        "resolve_zimage_txt2img_dir must not contain hardcoded "
        f"home fallbacks; found: {matches}"
    )


def test_zimage_dir_derived_from_service_base_path(monkeypatch, tmp_path) -> None:
    """The txt2img dir follows the configured service base path."""
    txt2img = tmp_path / "art" / "models" / "Z-Image Turbo" / "txt2img"
    txt2img.mkdir(parents=True)

    # The route resolves paths relative to service_base_path(); a real
    # database round-trip is out of scope for this regression test, so pin
    # the base path directly.
    monkeypatch.setattr(
        art_model_versions,
        "service_base_path",
        lambda: tmp_path,
    )

    assert art_model_versions.resolve_zimage_txt2img_dir() == str(txt2img)


def test_zimage_dir_returns_empty_when_missing(monkeypatch, tmp_path) -> None:
    """A missing config-derived dir yields an empty string, not a fallback."""
    monkeypatch.setattr(
        art_model_versions,
        "service_base_path",
        lambda: tmp_path,
    )

    assert art_model_versions.resolve_zimage_txt2img_dir() == ""


def test_route_resolves_through_service_base_path_only() -> None:
    """The derivation must be a single config-derived expression.

    The function must build its candidate from ``service_base_path()`` and
    must not keep a list of alternate home-directory fallbacks (the pre-#2066
    implementation iterated ``candidates``).
    """
    function_source = _source_text().split("def resolve_zimage_txt2img_dir")[1]
    assert "service_base_path()" in function_source
    assert "candidates" not in function_source
    assert "Z-Image Turbo" in function_source
    assert "/home" not in function_source
