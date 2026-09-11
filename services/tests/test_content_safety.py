"""Tests for the generic content-safety input matcher.

Every token used here is synthetic and neutral. No real policy term appears
in this file, and no assertion inspects the contents of a log record beyond
checking that it does not contain the synthetic input text.
"""

from __future__ import annotations

import importlib.resources
import re
import shutil
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest

from airunner_services.content_safety import (
    ContentSafetyResult,
    check_prompt_fields,
    check_text,
    hash_token,
    is_available,
    normalize_tokens,
)
from airunner_services.content_safety import policy_data

_HASH_RE = re.compile(r"^[0-9a-f]{64}$")
_REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def policy_dir() -> Iterator[Path]:
    """Create a scratch dir under the (gitignored) repo-local tmp/ tree."""
    base = _REPO_ROOT / "tmp" / "content_safety_tests"
    base.mkdir(parents=True, exist_ok=True)
    created = Path(tempfile.mkdtemp(prefix="run_", dir=base))
    yield created
    shutil.rmtree(created, ignore_errors=True)


@pytest.fixture(autouse=True)
def _clean_policy_cache(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.delenv(policy_data.POLICY_DATA_ENV_VAR, raising=False)
    policy_data.reset_cache()
    yield
    policy_data.reset_cache()


def _load(path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(policy_data.POLICY_DATA_ENV_VAR, str(path))
    policy_data.reset_cache()


def _write_hash_lines(path: Path, values: list[str]) -> Path:
    """Write one hash_token(digest-line) per value."""
    path.write_text(
        "".join(f"{hash_token(value)}\n" for value in values),
        encoding="utf-8",
    )
    return path


# --------------------------------------------------------------------------
# Primitives
# --------------------------------------------------------------------------


def test_hash_token_is_lowercase_sha256_hex() -> None:
    digest = hash_token("synthetic_example_token_1")
    assert _HASH_RE.match(digest)
    assert digest == digest.lower()
    assert len(digest) == 64


def test_normalize_tokens_is_deterministic() -> None:
    once = normalize_tokens("Synthetic-Example_Token.1")
    twice = normalize_tokens("Synthetic-Example_Token.1")
    assert once == twice
    assert once == ["synthetic", "example", "token", "1"]


def test_normalize_tokens_strips_diacritics_and_case() -> None:
    assert normalize_tokens("S\u00fdnth\u00e9tic") == ["synthetic"]


def test_normalize_tokens_collapses_long_runs_to_two() -> None:
    assert normalize_tokens("zorrrrb") == ["zorrb"]
    # A normal double letter is preserved.
    assert normalize_tokens("zorrb") == ["zorrb"]


def test_normalize_tokens_replaces_separators() -> None:
    assert normalize_tokens("alpha-widget/zorb") == ["alpha", "widget", "zorb"]


def test_normalize_tokens_handles_empty_and_non_string() -> None:
    assert normalize_tokens("") == []
    assert normalize_tokens(None) == []  # type: ignore[arg-type]


# --------------------------------------------------------------------------
# Matching
# --------------------------------------------------------------------------


def test_match_is_false_for_loaded_term(
    policy_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = _write_hash_lines(policy_dir / "policy_terms.dat", ["synthetic"])
    _load(path, monkeypatch)
    assert is_available() is True
    assert check_text("synthetic") is False
    assert check_text("totally unrelated neutral text") is True


def test_match_is_obfuscation_resistant(
    policy_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = _write_hash_lines(policy_dir / "policy_terms.dat", ["zorrb", "alpha"])
    _load(path, monkeypatch)
    # Repeated-character elongation collapses back to the stored double.
    assert check_text("zorrrrb") is False
    # Digit substitution folds back to the letter form.
    assert check_text("4lph4") is False
    # Case plus punctuation separators do not hide the token.
    assert check_text("ZORRB!") is False


def test_ngram_match_when_tokens_split_by_punctuation(
    policy_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = _write_hash_lines(
        policy_dir / "policy_terms.dat", ["alpha widget zorb"]
    )
    _load(path, monkeypatch)
    assert check_text("alpha;widget,zorb") is False
    # Only a prefix of the stored 3-gram: no match.
    assert check_text("alpha widget") is True


def test_check_text_allows_when_unavailable(
    policy_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _load(policy_dir / "missing.dat", monkeypatch)
    assert check_text("synthetic") is True


# --------------------------------------------------------------------------
# check_prompt_fields
# --------------------------------------------------------------------------


def test_check_prompt_fields_skips_none_and_empty(
    policy_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = _write_hash_lines(policy_dir / "policy_terms.dat", ["synthetic"])
    _load(path, monkeypatch)
    result = check_prompt_fields(
        prompt=None,
        negative_prompt="",
        second_prompt="a harmless neutral description",
        second_negative_prompt="synthetic",
    )
    assert isinstance(result, ContentSafetyResult)
    assert result.allowed is False
    assert result.field == "second_negative_prompt"
    # The reason is generic and never echoes the input.
    assert "synthetic" not in result.reason
    assert "harmless neutral description" not in result.reason


def test_check_prompt_fields_reports_first_blocking_field(
    policy_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = _write_hash_lines(policy_dir / "policy_terms.dat", ["synthetic"])
    _load(path, monkeypatch)
    result = check_prompt_fields(
        prompt="synthetic",
        negative_prompt="synthetic",
    )
    assert result.allowed is False
    assert result.field == "prompt"


def test_check_prompt_fields_allowed_when_clean(
    policy_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = _write_hash_lines(policy_dir / "policy_terms.dat", ["synthetic"])
    _load(path, monkeypatch)
    result = check_prompt_fields(prompt="a clean neutral prompt")
    assert result.allowed is True
    assert result.reason == "ok"
    assert result.field is None


def test_result_helper_constructors() -> None:
    allowed = ContentSafetyResult.allowed_result()
    assert allowed.allowed is True
    assert allowed.field is None
    blocked = ContentSafetyResult.blocked_result("prompt", "prohibited_content")
    assert blocked.allowed is False
    assert blocked.field == "prompt"


# --------------------------------------------------------------------------
# Availability / fail behavior
# --------------------------------------------------------------------------


def test_missing_data_file_is_unavailable_and_allows(
    policy_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    _load(policy_dir / "does_not_exist.dat", monkeypatch)
    with caplog.at_level("WARNING"):
        assert is_available() is False
        assert check_text("synthetic") is True
        result = check_prompt_fields(prompt="synthetic")
    assert result.allowed is True
    assert all(
        "synthetic" not in record.getMessage() for record in caplog.records
    )


def test_empty_data_file_is_unavailable(
    policy_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = policy_dir / "empty.dat"
    path.write_text("", encoding="utf-8")
    _load(path, monkeypatch)
    assert is_available() is False
    assert check_text("anything at all") is True


def test_corrupt_lines_are_ignored(
    policy_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = policy_dir / "corrupt.dat"
    path.write_text(
        "\n".join(
            [
                "",
                "# a comment line",
                "not-a-valid-hash",
                "zzzz",
                hash_token("synthetic"),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    _load(path, monkeypatch)
    assert is_available() is True
    assert check_text("synthetic") is False
    assert check_text("unrelated neutral text") is True


def test_file_with_only_corrupt_lines_is_unavailable(
    policy_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = policy_dir / "only_corrupt.dat"
    path.write_text("garbage\n# comment\n\n", encoding="utf-8")
    _load(path, monkeypatch)
    assert is_available() is False
    assert check_text("anything at all") is True


def test_uppercase_hashes_are_accepted(
    policy_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = policy_dir / "upper.dat"
    path.write_text(hash_token("synthetic").upper() + "\n", encoding="utf-8")
    _load(path, monkeypatch)
    assert is_available() is True
    assert check_text("synthetic") is False


def test_no_content_is_logged_on_match(
    policy_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    path = _write_hash_lines(policy_dir / "policy_terms.dat", ["synthetic"])
    _load(path, monkeypatch)
    with caplog.at_level("DEBUG"):
        check_text("synthetic")
        check_prompt_fields(prompt="synthetic")
    assert all(
        "synthetic" not in record.getMessage() for record in caplog.records
    )


def test_packaged_data_file_is_hash_only() -> None:
    """The committed data file may contain hashes only, never plaintext."""
    resource = (
        importlib.resources.files("airunner_services.content_safety")
        .joinpath("data")
        .joinpath("policy_terms.dat")
    )
    text = resource.read_text(encoding="utf-8")
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        assert _HASH_RE.match(stripped.lower()), (
            "policy data file must contain only hex hashes"
        )
