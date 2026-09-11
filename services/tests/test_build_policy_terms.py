"""Tests for ``scripts/build_policy_terms.py`` (content-safety plan subtask S-2).

The generator turns a plaintext term list kept OUTSIDE the repository into the
hash-only content-safety data file. Every token used here is synthetic and
neutral: no real policy term appears in this file, and no assertion inspects a
log or stream beyond checking that it does not contain the synthetic input.
"""

from __future__ import annotations

import contextlib
import importlib.resources
import io
import re
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
    build_hashes,
    main,
    write_data_file,
)

from airunner_services.content_safety import (  # noqa: E402
    check_text,
    is_available,
    policy_data,
)

_HASH_RE = re.compile(r"^[0-9a-f]{64}$")

# Synthetic, neutral multi-token source entries only.
_TERMS = ["zorrb", "alpha widget zorb", "synthetic"]


@pytest.fixture
def work_dir() -> Iterator[Path]:
    """Create a scratch dir under the (gitignored) repo-local tmp/ tree."""
    base = _PROJECT_ROOT / "tmp" / "content_safety_tests"
    base.mkdir(parents=True, exist_ok=True)
    created = Path(tempfile.mkdtemp(prefix="gen_", dir=base))
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


def test_output_is_deterministic(work_dir: Path) -> None:
    """The same input always yields byte-identical output."""
    source = _write_terms(work_dir / "terms.txt", _TERMS)
    _, first = build_hashes(source)
    _, second = build_hashes(source)

    out_a = work_dir / "a.dat"
    out_b = work_dir / "b.dat"
    write_data_file(out_a, first)
    write_data_file(out_b, second)

    assert out_a.read_bytes() == out_b.read_bytes()


def test_output_is_hash_only_and_leaks_no_term(work_dir: Path) -> None:
    """Every non-comment line is a hash; no input token appears in the file."""
    source = _write_terms(work_dir / "terms.txt", _TERMS)
    _, hashes = build_hashes(source)

    out = work_dir / "policy.dat"
    write_data_file(out, hashes)
    text = out.read_text(encoding="utf-8")

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        assert _HASH_RE.match(stripped), "output must contain only hex hashes"

    for term in _TERMS:
        assert term not in text
        for token in term.split():
            assert token not in text


def test_comment_and_blank_lines_are_skipped(work_dir: Path) -> None:
    """Only real entries are counted and hashed."""
    source = work_dir / "terms.txt"
    source.write_text(
        "# a comment\n\nzorrb\n   \n#alpha\nsynthetic\n",
        encoding="utf-8",
    )

    count, hashes = build_hashes(source)

    assert count == 2
    assert hashes


def test_generated_data_is_loadable_round_trip(
    work_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Data produced by the generator is consumable by the matcher."""
    source = _write_terms(work_dir / "terms.txt", ["zorrb"])
    _, hashes = build_hashes(source)

    out = work_dir / "policy.dat"
    write_data_file(out, hashes)

    monkeypatch.setenv(policy_data.POLICY_DATA_ENV_VAR, str(out))
    policy_data.reset_cache()

    assert is_available() is True
    assert check_text("zorrb") is False
    assert check_text("a totally unrelated neutral phrase") is True


def test_missing_input_returns_error_code(work_dir: Path) -> None:
    """A missing source file fails with exit code 2 and writes nothing."""
    out = work_dir / "out.dat"
    rc = main(
        [
            "--input",
            str(work_dir / "does_not_exist.txt"),
            "--output",
            str(out),
            "--quiet",
        ]
    )

    assert rc == 2
    assert not out.exists()


def test_main_prints_counts_and_never_echoes_a_term(work_dir: Path) -> None:
    """The summary reports counts only; no source term reaches stdout."""
    source = _write_terms(work_dir / "terms.txt", _TERMS)
    out = work_dir / "policy.dat"

    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        rc = main(["--input", str(source), "--output", str(out)])

    printed = buffer.getvalue()
    assert rc == 0
    assert "entries read" in printed
    assert "hashes written" in printed
    for term in _TERMS:
        assert term not in printed
    assert out.is_file()


def test_committed_policy_data_ships_empty() -> None:
    """The public repo default is an empty, hash-only policy set."""
    resource = (
        importlib.resources.files("airunner_services.content_safety")
        .joinpath("data")
        .joinpath("policy_terms.dat")
    )
    hashes = [
        line.strip()
        for line in resource.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]

    assert hashes == [], "the public repository must ship an empty policy set"
