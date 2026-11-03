"""Build wheel and sdist outputs with the reviewed setuptools backend."""

from __future__ import annotations

import argparse
import os
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("package", choices=("services", "native"))
    parser.add_argument("--outdir", type=Path, required=True)
    args = parser.parse_args()

    source = Path(args.package).resolve()
    output = args.outdir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    if not (source / "pyproject.toml").is_file():
        parser.error(f"missing build configuration: {source / 'pyproject.toml'}")

    # The project declares setuptools.build_meta with setuptools==84.2.1 and
    # wheel. Both are installed from the reviewed builder lock before this
    # script runs; disabling an additional frontend avoids a second resolver.
    os.chdir(source)
    from setuptools import build_meta

    print(f"Building {args.package} from {source}")
    print(f"wheel: {build_meta.build_wheel(str(output))}")
    print(f"sdist: {build_meta.build_sdist(str(output))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
