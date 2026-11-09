"""Contract tests for the art providers documentation."""

from __future__ import annotations

import re
from pathlib import Path

_REPO_ROOT: Path = Path(__file__).resolve().parents[2]
_DOCS: Path = _REPO_ROOT / "docs" / "art-providers.md"
_ENV_EXAMPLE: Path = _REPO_ROOT / ".env.example"
_SERVICES_README: Path = _REPO_ROOT / "services" / "README.md"


def _read(path: Path) -> str:
    """Return file text, or empty string when missing."""
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def _docs() -> str:
    """Return the art providers guide text."""
    return _read(_DOCS)


def test_docs_exist_and_name_muse_provider() -> None:
    """Happy: guide exists and documents provider muse."""
    text: str = _docs()
    assert text, "docs/art-providers.md is missing or empty"
    assert 'provider="muse"' in text
    assert "provider=muse" in text.replace('"', "")


def test_docs_name_model_api_key_only_source() -> None:
    """Happy: guide names MODEL_API_KEY as the key source."""
    text: str = _docs()
    assert "MODEL_API_KEY" in text
    assert "only from" in text.lower()
    assert "MODEL_API_KEY" in _read(_ENV_EXAMPLE)


def test_docs_state_local_is_default() -> None:
    """Happy: guide states local is the default provider."""
    text: str = _docs().lower()
    assert "local" in text
    assert "default" in text
    assert 'provider="local"' in _docs()
    assert 'defaults to `"local"`' in _docs()


def test_docs_state_no_silent_fallback() -> None:
    """Happy: guide states there is no fallback."""
    text: str = _docs().lower()
    assert "no silent fallback" in text
    assert "never retried" in text


def test_docs_cover_env_overrides_and_meta_call() -> None:
    """Happy: env overrides and Meta endpoint documented."""
    text: str = _docs()
    for name in (
        "AIRUNNER_MUSE_BASE_URL",
        "AIRUNNER_MUSE_MODEL",
        "AIRUNNER_MUSE_TIMEOUT_S",
        "AIRUNNER_MUSE_MAX_IMAGE_BYTES",
    ):
        assert name in text
        assert name in _read(_ENV_EXAMPLE)
    assert "POST {base}/images/generations" in text
    assert "https://api.meta.ai/v1" in text
    assert "muse-image-1.0" in text


def test_docs_cover_envelope_privacy_and_https() -> None:
    """Happy: envelope, privacy, and HTTPS rules covered."""
    text: str = _docs()
    assert "ResponseEnvelope" in text
    assert "image_count" in text
    assert "https" in text.lower()
    low: str = text.lower()
    assert "never written to envelope" in low


def test_env_example_has_empty_muse_entries() -> None:
    """Happy: .env.example ships empty Muse entries."""
    text: str = _read(_ENV_EXAMPLE)
    assert re.search(r"^MODEL_API_KEY=$", text, re.M)
    for name in (
        "AIRUNNER_MUSE_BASE_URL",
        "AIRUNNER_MUSE_MODEL",
        "AIRUNNER_MUSE_TIMEOUT_S",
        "AIRUNNER_MUSE_MAX_IMAGE_BYTES",
    ):
        assert re.search(rf"^{name}=$", text, re.M)


def test_services_readme_links_guide() -> None:
    """Happy: services README links the guide."""
    text: str = _read(_SERVICES_README)
    assert "docs/art-providers.md" in text
    assert "Art providers" in text


def test_docs_have_curl_for_both_providers() -> None:
    """Happy: curl examples cover local and muse."""
    text: str = _docs()
    assert text.count("curl ") >= 2
    assert '"provider": "local"' in text
    assert '"provider": "muse"' in text


def test_docs_defers_pricing_to_meta_dashboard() -> None:
    """Sad: no invented pricing; dashboard is authority."""
    text: str = _docs()
    assert "Meta dashboard" in text
    assert "does not state Muse pricing" in text
    assert not re.search(r"\$\d", text)


def test_docs_contain_no_real_key() -> None:
    """Bad: guide and example hold no real credential."""
    combined: str = _docs() + _read(_ENV_EXAMPLE)
    assert not re.search(r"^MODEL_API_KEY=\S+", _read(_ENV_EXAMPLE), re.M)
    assert not re.search(r"sk-[A-Za-z0-9]{8,}", combined)


def test_missing_file_reads_as_empty() -> None:
    """Sad: missing file yields empty, not an exception."""
    missing: Path = _REPO_ROOT / "docs" / "no-such-file.md"
    assert _read(missing) == ""
    assert 'provider="muse"' not in _read(missing)
