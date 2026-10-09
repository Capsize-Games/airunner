#!/usr/bin/env python3
"""Out-of-band generator for the content-safety policy data file.

The maintainer keeps the plaintext policy term list OUTSIDE the repository
(for example under the gitignored ``tmp/`` directory) and runs this script
locally to (re)generate the hashed data file that ships with the package.
The repository never contains the plaintext terms; this script contains no
terms and makes no network calls. It prints counts only, never a term or a
hash.

Usage:
    venv/bin/python scripts/build_policy_terms.py \
        --input tmp/policy_terms_source.txt --output <data-file>

``--input`` defaults to ``tmp/policy_terms_source.txt`` (inside the
gitignored ``tmp/`` directory). ``--output`` defaults to the packaged data
file. Both may point anywhere.

The output is a versioned ``airunner-policy-data/1`` artifact: sorted
lowercase hex SHA-256 digests plus ``#``-comment integrity metadata
(format, normalization, count, SHA-256 of the canonical digest block).
The output is deterministic: the same input always yields byte-identical
output (sorted hashes, fixed header, no timestamps).

Bounds: the source file must fit in ``MAX_SOURCE_BYTES`` with at most
``MAX_SOURCE_ENTRIES`` entries of at most ``MAX_ENTRY_CHARS`` characters
each; over-limit input aborts with exit code 2 and writes nothing. An
input that yields no digests is rejected the same way: an empty release
artifact is a build error, never shipped silently.

Release staging (``--stage-release``, issue S06) does the opposite job:
it takes an ALREADY-COMPILED private artifact plus its detached Ed25519
sidecar (``<artifact>.sig``), verifies the expected SHA-256 digest and
the signature against an owner-provisioned public-key trust store, and
stages the exact verified bytes to ``--output``. It never compiles from
a term list, never signs, and never handles a private key. Absent,
invalid, empty, or synthetic-only data (unsigned, or signed by a key
outside the release trust store) fails with exit code 2 and writes
nothing. Output and errors report counts and key IDs only; terms,
hashes, digests, and key material never appear.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SERVICES_SRC = _REPO_ROOT / "services" / "src"
if str(_SERVICES_SRC) not in sys.path:
    sys.path.insert(0, str(_SERVICES_SRC))

from airunner_services.content_safety.matcher import (  # noqa: E402
    NORMALIZATION_VERSION,
    candidate_hashes,
)
from airunner_services.content_safety.policy_data import (  # noqa: E402
    ARTIFACT_FORMAT_ID,
    MAX_ARTIFACT_BYTES,
    MAX_DIGESTS,
    PolicyDataError,
    canonical_digest_block,
    digest_block_sha256,
    parse_policy_artifact,
)
from airunner_services.content_safety.policy_signature import (  # noqa: E402
    ED25519_PUBLIC_KEY_BYTES,
    MAX_SIGNATURE_BYTES,
    PolicySignatureError,
    signature_path_for,
    verify_policy_artifact,
)

DEFAULT_INPUT = _REPO_ROOT / "tmp" / "policy_terms_source.txt"
DEFAULT_OUTPUT = (
    _SERVICES_SRC
    / "airunner_services"
    / "content_safety"
    / "data"
    / "policy_terms.dat"
)

MAX_SOURCE_BYTES = 64 * 1024 * 1024
MAX_SOURCE_ENTRIES = 1_000_000
MAX_ENTRY_CHARS = 1024

_HEADER = (
    "# Content safety policy data.\n"
    "#\n"
    "# Versioned artifact (airunner-policy-data/1): sorted lowercase hex\n"
    "# SHA-256 digests (UTF-8), one per line, with '#' integrity metadata\n"
    "# (format, normalization, count, sha256 of the digest block). Blank\n"
    "# lines and other '#' lines are ignored.\n"
    "# Generated out of band by scripts/build_policy_terms.py; never "
    "commit terms.\n"
)


class PolicyBuildError(ValueError):
    """The policy source or digest set failed compiler validation."""


def _read_source_entries(path: Path) -> list[str]:
    """Return non-blank, non-comment source lines (stripped), bounded."""
    if path.stat().st_size > MAX_SOURCE_BYTES:
        raise PolicyBuildError("source exceeds size bound")
    entries: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if len(stripped) > MAX_ENTRY_CHARS:
            raise PolicyBuildError("source entry exceeds length bound")
        entries.append(stripped)
        if len(entries) > MAX_SOURCE_ENTRIES:
            raise PolicyBuildError("source exceeds entry bound")
    return entries


def build_hashes(input_path: Path) -> tuple[int, set[str]]:
    """Return ``(entry_count, hashes)`` for the plaintext input file."""
    entries = _read_source_entries(input_path)
    hashes: set[str] = set()
    for entry in entries:
        hashes.update(candidate_hashes(entry))
    if len(hashes) > MAX_DIGESTS:
        raise PolicyBuildError("digest count exceeds bound")
    return len(entries), hashes


def render_artifact(hashes: set[str]) -> str:
    """Render the versioned artifact text for ``hashes`` (non-empty)."""
    if not hashes:
        raise PolicyBuildError("refusing to emit an empty release artifact")
    block = canonical_digest_block(hashes)
    meta = (
        f"# format: {ARTIFACT_FORMAT_ID}\n"
        f"# normalization: {NORMALIZATION_VERSION}\n"
        f"# count: {len(hashes)}\n"
        f"# sha256: {digest_block_sha256(hashes)}\n"
    )
    return _HEADER + meta + block


def write_data_file(output_path: Path, hashes: set[str]) -> None:
    """Write the versioned artifact for ``hashes``, one hash per line."""
    text = render_artifact(hashes)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text, encoding="utf-8")


MAX_TRUST_STORE_BYTES = 64 * 1024

_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")


def load_release_trust_store(path: Path) -> dict[str, bytes]:
    """Load a release trust store: key ID -> 32-byte public key.

    The file is strict JSON: a non-empty object mapping a key ID to a
    64-character lowercase hex Ed25519 public key. Errors are
    content-free; key material never appears in them.
    """
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise PolicyBuildError("trust store could not be read") from exc
    if len(raw) > MAX_TRUST_STORE_BYTES:
        raise PolicyBuildError("trust store exceeds size bound")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise PolicyBuildError("trust store is not UTF-8") from exc
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise PolicyBuildError("trust store is not valid JSON") from exc
    if not isinstance(payload, dict) or not payload:
        raise PolicyBuildError("trust store must be a non-empty object")
    store: dict[str, bytes] = {}
    for key_id, hex_key in payload.items():
        if not isinstance(key_id, str) or not key_id or len(key_id) > 64:
            raise PolicyBuildError("trust store holds a malformed key id")
        if not isinstance(hex_key, str):
            raise PolicyBuildError("trust store holds a malformed key")
        if not _HEX64_RE.match(hex_key.lower()):
            raise PolicyBuildError("trust store holds a malformed key")
        public_key = bytes.fromhex(hex_key.lower())
        if len(public_key) != ED25519_PUBLIC_KEY_BYTES:
            raise PolicyBuildError("trust store holds a malformed key")
        store[key_id] = public_key
    return store


def _read_release_bytes(artifact: Path) -> bytes:
    """Return the exact artifact bytes, bounded and present."""
    try:
        data = artifact.read_bytes()
    except OSError as exc:
        raise PolicyBuildError("release artifact is absent") from exc
    if not data or len(data) > MAX_ARTIFACT_BYTES:
        raise PolicyBuildError("release artifact exceeds size bound")
    return data


def _read_release_sidecar(artifact: Path) -> bytes:
    """Return the detached sidecar bytes; missing means synthetic-only."""
    try:
        signature = signature_path_for(artifact).read_bytes()
    except OSError as exc:
        raise PolicyBuildError(
            "release artifact is unsigned or synthetic-only"
        ) from exc
    if not signature or len(signature) > MAX_SIGNATURE_BYTES:
        raise PolicyBuildError("release signature exceeds size bound")
    return signature


def stage_release_artifact(
    *,
    artifact: Path,
    trust_store: dict[str, bytes],
    expected_sha256: str,
) -> tuple[bytes, str, int]:
    """Verify a compiled artifact; return ``(bytes, key_id, count)``.

    The expected digest must match the exact artifact bytes, the
    artifact must strictly parse to a non-empty digest set, and the
    detached sidecar must verify against ``trust_store``. Anything
    else -- absent, invalid, empty, unsigned, or signed outside the
    release trust store -- raises :class:`PolicyBuildError` with a
    content-free message.
    """
    data = _read_release_bytes(artifact)
    if not _HEX64_RE.match(expected_sha256.lower()):
        raise PolicyBuildError("expected digest is malformed")
    if hashlib.sha256(data).hexdigest() != expected_sha256.lower():
        raise PolicyBuildError("release artifact digest mismatch")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise PolicyBuildError("release artifact is not UTF-8") from exc
    try:
        hashes = parse_policy_artifact(text)
    except PolicyDataError as exc:
        raise PolicyBuildError(
            f"release artifact is invalid: {exc}"
        ) from exc
    if not hashes:
        raise PolicyBuildError("refusing to stage an empty policy artifact")
    try:
        key_id = verify_policy_artifact(
            data, _read_release_sidecar(artifact), trusted_keys=trust_store
        )
    except PolicySignatureError as exc:
        raise PolicyBuildError(
            f"release artifact is unsigned or synthetic-only: {exc}"
        ) from exc
    return data, key_id, len(hashes)


def write_staged_release(output_path: Path, data: bytes) -> None:
    """Write the exact verified release bytes to ``output_path``."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(data)


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    """Parse the compiler command line."""
    parser = argparse.ArgumentParser(
        description=(
            "Generate the hashed content-safety policy data file from a "
            "plaintext term list kept outside the repository. Prints counts "
            "only; never echoes a term or hash."
        )
    )
    parser.add_argument(
        "--input",
        default=str(DEFAULT_INPUT),
        help=(
            "Plaintext term list, one entry per line (default: "
            f"{DEFAULT_INPUT}); skipped: blanks and '#' comments."
        ),
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help=(
            "Destination hash data file (default: the packaged "
            "content_safety/data/policy_terms.dat)."
        ),
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress the counts summary.",
    )
    parser.add_argument(
        "--stage-release",
        action="store_true",
        help=(
            "Verify an already-compiled artifact plus its detached "
            ".sig sidecar against --trust-store and --expected-sha256, "
            "then stage the exact bytes to --output. Never compiles, "
            "signs, or handles a private key."
        ),
    )
    parser.add_argument(
        "--artifact",
        default=None,
        help="Compiled policy artifact to verify (release mode).",
    )
    parser.add_argument(
        "--trust-store",
        default=None,
        help=(
            "JSON trust store: object mapping key ID to 64-char hex "
            "Ed25519 public key (release mode)."
        ),
    )
    parser.add_argument(
        "--expected-sha256",
        default=None,
        help="Expected hex SHA-256 of the exact artifact bytes.",
    )
    return parser.parse_args(argv)


def _main_stage_release(args: argparse.Namespace) -> int:
    """Run release staging; return the process exit code."""
    if not args.artifact or not args.trust_store or not args.expected_sha256:
        print(
            "error: --stage-release needs --artifact, --trust-store, "
            "and --expected-sha256",
            file=sys.stderr,
        )
        return 2
    try:
        trust_store = load_release_trust_store(Path(args.trust_store))
        data, key_id, count = stage_release_artifact(
            artifact=Path(args.artifact),
            trust_store=trust_store,
            expected_sha256=args.expected_sha256,
        )
    except PolicyBuildError as exc:
        print(
            f"error: cannot stage release policy data: {exc}",
            file=sys.stderr,
        )
        return 2
    output_path = Path(args.output)
    try:
        write_staged_release(output_path, data)
    except OSError as exc:
        print(
            f"error: cannot write staged policy data: {exc}",
            file=sys.stderr,
        )
        return 2
    if not args.quiet:
        print(f"artifact: {ARTIFACT_FORMAT_ID}")
        print(f"hashes staged: {count}")
        print(f"key id: {key_id}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if args.stage_release:
        return _main_stage_release(args)
    input_path = Path(args.input)
    if not input_path.is_file():
        print(
            f"error: input file not found: {input_path}",
            file=sys.stderr,
        )
        return 2

    try:
        entry_count, hashes = build_hashes(input_path)
    except (OSError, UnicodeDecodeError, PolicyBuildError) as exc:
        print(f"error: cannot build policy data: {exc}", file=sys.stderr)
        return 2
    if not hashes:
        print(
            "error: refusing to emit an empty release artifact",
            file=sys.stderr,
        )
        return 2
    output_path = Path(args.output)
    try:
        write_data_file(output_path, hashes)
    except (OSError, PolicyBuildError) as exc:
        print(f"error: cannot write policy data: {exc}", file=sys.stderr)
        return 2

    if not args.quiet:
        print(f"artifact: {ARTIFACT_FORMAT_ID}")
        print(f"entries read: {entry_count}")
        print(f"hashes written: {len(hashes)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
