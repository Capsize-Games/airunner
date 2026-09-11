#!/usr/bin/env python3
"""Out-of-band generator for the content-safety policy data file.

The maintainer keeps the plaintext policy term list OUTSIDE the repository
(for example under the gitignored ``tmp/`` directory) and runs this script
locally to (re)generate the hashed data file that ships with the package.
The repository never contains the plaintext terms; this script contains no
terms and makes no network calls. It prints counts only, never a term or a
hash.

Usage:
    venv/bin/python scripts/build_policy_terms.py \\
        --input tmp/policy_terms_source.txt \\
        --output services/src/airunner_services/content_safety/data/policy_terms.dat

``--input`` defaults to ``tmp/policy_terms_source.txt`` (inside the
gitignored ``tmp/`` directory). ``--output`` defaults to the packaged data
file. Both may point anywhere; only hashes are written, one per line.

The output is deterministic: the same input always yields byte-identical
output (sorted hashes, fixed header, no timestamps).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SERVICES_SRC = _REPO_ROOT / "services" / "src"
if str(_SERVICES_SRC) not in sys.path:
    sys.path.insert(0, str(_SERVICES_SRC))

from airunner_services.content_safety.matcher import (  # noqa: E402
    candidate_hashes,
)

DEFAULT_INPUT = _REPO_ROOT / "tmp" / "policy_terms_source.txt"
DEFAULT_OUTPUT = (
    _SERVICES_SRC
    / "airunner_services"
    / "content_safety"
    / "data"
    / "policy_terms.dat"
)

_HEADER = (
    "# Content safety policy data.\n"
    "#\n"
    "# Format: one lowercase hex SHA-256 digest per line (UTF-8). Blank "
    "lines and\n"
    "# lines starting with '#' are ignored; malformed lines are skipped.\n"
    "# Generated out of band by scripts/build_policy_terms.py; never "
    "commit terms.\n"
)


def _read_source_entries(path: Path) -> list[str]:
    """Return non-blank, non-comment source lines (stripped)."""
    entries: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        entries.append(stripped)
    return entries


def build_hashes(input_path: Path) -> tuple[int, set[str]]:
    """Return ``(entry_count, hashes)`` for the plaintext input file."""
    entries = _read_source_entries(input_path)
    hashes: set[str] = set()
    for entry in entries:
        hashes.update(candidate_hashes(entry))
    return len(entries), hashes


def write_data_file(output_path: Path, hashes: set[str]) -> None:
    """Write the sorted hash set, one hash per line, UTF-8."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    body = _HEADER + "".join(f"{digest}\n" for digest in sorted(hashes))
    output_path.write_text(body, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
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
    args = parser.parse_args(argv)

    input_path = Path(args.input)
    if not input_path.is_file():
        print(
            f"error: input file not found: {input_path}",
            file=sys.stderr,
        )
        return 2

    entry_count, hashes = build_hashes(input_path)
    output_path = Path(args.output)
    write_data_file(output_path, hashes)

    if not args.quiet:
        print(f"entries read: {entry_count}")
        print(f"hashes written: {len(hashes)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
