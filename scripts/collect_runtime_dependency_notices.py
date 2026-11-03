"""Collect and verify lock-bound Python dependency notices for an image."""

from __future__ import annotations

import argparse
import sys
import tomllib
from pathlib import Path

from dependency_notices import (
    collect_dependency_notices,
    verify_dependency_notice_manifest,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--bundle-dir", type=Path, required=True)
    args = parser.parse_args()

    try:
        with args.spec.open("rb") as stream:
            spec = tomllib.load(stream)
        collect_dependency_notices(spec, args.repo_root, args.bundle_dir)
        problems = verify_dependency_notice_manifest(
            args.bundle_dir, spec, args.repo_root
        )
    except (OSError, ValueError, tomllib.TOMLDecodeError) as error:
        print(f"Dependency notice collection failed: {error}", file=sys.stderr)
        return 1
    if problems:
        print("Dependency notice verification failed:", file=sys.stderr)
        for problem in problems:
            print(f"- {problem}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
