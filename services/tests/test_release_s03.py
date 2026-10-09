"""Release regression tests for S03 (versioned policy-data artifact).

Every token used here is synthetic and neutral. No real policy term
appears in this file, and no assertion inspects log content beyond
checking that it does not contain the synthetic input text.
"""

from __future__ import annotations

import contextlib
import importlib.resources
import io
import shutil
import sys
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from scripts.build_policy_terms import (  # noqa: E402
    PolicyBuildError,
    build_hashes,
    main,
    render_artifact,
)

from airunner_services.content_safety import (  # noqa: E402
    check_text,
    hash_token,
    is_available,
    policy_data,
)
from airunner_services.content_safety.matcher import (  # noqa: E402
    NORMALIZATION_VERSION as MATCHER_NORMALIZATION,
)
from airunner_services.content_safety.policy_data import (  # noqa: E402
    ARTIFACT_FORMAT_ID,
    ARTIFACT_VERSION,
    PolicyDataError,
    parse_policy_artifact,
)

_TERMS = ["zorrb", "quixnor widget", "blarf"]


@pytest.fixture
def work_dir() -> Iterator[Path]:
    """Create a scratch dir under the (gitignored) repo-local tmp/ tree."""
    base = _PROJECT_ROOT / "tmp" / "content_safety_tests"
    base.mkdir(parents=True, exist_ok=True)
    created = Path(tempfile.mkdtemp(prefix="s03_", dir=base))
    yield created
    shutil.rmtree(created, ignore_errors=True)


@pytest.fixture(autouse=True)
def _clean_policy_cache(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.delenv(policy_data.POLICY_DATA_ENV_VAR, raising=False)
    policy_data.reset_cache()
    yield
    policy_data.reset_cache()


def _write_terms(path: Path, terms: list[str]) -> Path:
    path.write_text("\n".join(terms) + "\n", encoding="utf-8")
    return path


def _valid_artifact() -> str:
    return render_artifact({hash_token("zorrb"), hash_token("quixnor")})


def _load_text(
    work_dir: Path, text: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = work_dir / "policy.dat"
    path.write_text(text, encoding="utf-8")
    monkeypatch.setenv(policy_data.POLICY_DATA_ENV_VAR, str(path))
    policy_data.reset_cache()


def test_identical_input_yields_identical_bytes(work_dir: Path) -> None:
    """The compiler is deterministic at the byte level."""
    source = _write_terms(work_dir / "terms.txt", _TERMS)
    out_a = work_dir / "a.dat"
    out_b = work_dir / "b.dat"
    assert main(["--input", str(source), "--output", str(out_a)]) == 0
    assert main(["--input", str(source), "--output", str(out_b)]) == 0
    assert out_a.read_bytes() == out_b.read_bytes()


def test_artifact_declares_compatibility_version() -> None:
    """The artifact carries format and normalization versions."""
    assert ARTIFACT_VERSION == 1
    text = _valid_artifact()
    assert f"# format: {ARTIFACT_FORMAT_ID}" in text
    assert f"# normalization: {MATCHER_NORMALIZATION}" in text
    assert policy_data.NORMALIZATION_VERSION == MATCHER_NORMALIZATION


def test_unknown_schema_version_is_rejected(
    work_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An artifact declaring a future format is rejected, not partial."""
    text = _valid_artifact().replace(
        f"# format: {ARTIFACT_FORMAT_ID}",
        "# format: airunner-policy-data/99",
    )
    with pytest.raises(PolicyDataError):
        parse_policy_artifact(text)
    _load_text(work_dir, text, monkeypatch)
    assert is_available() is False


def test_count_mismatch_is_rejected() -> None:
    """A declared count that does not match the digest lines is rejected."""
    text = _valid_artifact().replace("# count: 2", "# count: 3")
    with pytest.raises(PolicyDataError):
        parse_policy_artifact(text)
    bad_count = _valid_artifact().replace("# count: 2", "# count: many")
    with pytest.raises(PolicyDataError):
        parse_policy_artifact(bad_count)


def test_integrity_mismatch_is_rejected() -> None:
    """A digest block that does not match its sha256 is rejected."""
    lines = _valid_artifact().splitlines(keepends=True)
    for index, line in enumerate(lines):
        if line and not line.startswith("#") and line.strip():
            flipped = "0" if line[0] != "0" else "1"
            lines[index] = flipped + line[1:]
            break
    with pytest.raises(PolicyDataError):
        parse_policy_artifact("".join(lines))


def test_missing_or_duplicate_metadata_is_rejected() -> None:
    """Versioned artifacts require exactly one of each metadata line."""
    missing = "\n".join(
        line
        for line in _valid_artifact().splitlines()
        if not line.startswith("# sha256:")
    )
    with pytest.raises(PolicyDataError):
        parse_policy_artifact(missing)
    with pytest.raises(PolicyDataError):
        parse_policy_artifact(_valid_artifact() + "# count: 2\n")


def test_compiler_rejects_empty_release_artifact(work_dir: Path) -> None:
    """Empty input is a build error; nothing is written."""
    source = work_dir / "empty.txt"
    source.write_text("# only a comment\n\n", encoding="utf-8")
    out = work_dir / "out.dat"
    buffer = io.StringIO()
    with contextlib.redirect_stderr(buffer):
        assert main(["--input", str(source), "--output", str(out)]) == 2
    assert not out.exists()
    with pytest.raises(PolicyBuildError):
        render_artifact(set())


def test_compiler_never_echoes_source_lines(work_dir: Path) -> None:
    """Stdout and stderr carry counts only, never source text."""
    source = _write_terms(work_dir / "terms.txt", _TERMS)
    out = work_dir / "policy.dat"
    stdout = io.StringIO()
    stderr = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(
        stderr
    ):
        assert main(["--input", str(source), "--output", str(out)]) == 0
    printed = stdout.getvalue() + stderr.getvalue()
    assert "entries read" in printed
    for term in _TERMS:
        assert term not in printed
        for token in term.split():
            assert token not in printed


def test_oversized_artifact_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The parser is bounded by artifact size and digest count."""
    monkeypatch.setattr(policy_data, "MAX_ARTIFACT_BYTES", 64)
    with pytest.raises(PolicyDataError):
        parse_policy_artifact(_valid_artifact())
    monkeypatch.setattr(policy_data, "MAX_ARTIFACT_BYTES", 10**9)
    monkeypatch.setattr(policy_data, "MAX_DIGESTS", 1)
    with pytest.raises(PolicyDataError):
        parse_policy_artifact(_valid_artifact())


def test_overlong_line_in_versioned_file_is_rejected() -> None:
    """A versioned file with an over-long line is rejected wholesale."""
    text = _valid_artifact() + "x" * (policy_data.MAX_LINE_LENGTH + 1) + "\n"
    with pytest.raises(PolicyDataError):
        parse_policy_artifact(text)


def test_legacy_bare_hash_file_still_loads(
    work_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Unversioned digest files keep their lenient legacy semantics."""
    text = f"{hash_token('zorrb')}\nnot-a-hash\n# comment\n"
    assert parse_policy_artifact(text) == frozenset({hash_token("zorrb")})
    _load_text(work_dir, text, monkeypatch)
    assert is_available() is True
    assert check_text("zorrb") is False


def test_generated_artifact_round_trip_blocks_token(
    work_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Compiler output loads and matches through the public gate."""
    source = _write_terms(work_dir / "terms.txt", ["zorrb"])
    _, hashes = build_hashes(source)
    out = work_dir / "policy.dat"
    out.write_text(render_artifact(hashes), encoding="utf-8")
    monkeypatch.setenv(policy_data.POLICY_DATA_ENV_VAR, str(out))
    policy_data.reset_cache()
    assert is_available() is True
    assert check_text("zorrb") is False
    assert check_text("a totally unrelated neutral phrase") is True


def test_packaged_empty_artifact_is_versioned() -> None:
    """The public repo ships an empty but version-declared artifact."""
    resource = (
        importlib.resources.files("airunner_services.content_safety")
        .joinpath("data")
        .joinpath("policy_terms.dat")
    )
    text = resource.read_text(encoding="utf-8")
    assert f"# format: {ARTIFACT_FORMAT_ID}" in text
    assert "# count: 0" in text
    assert parse_policy_artifact(text) == frozenset()
    assert is_available() is False
