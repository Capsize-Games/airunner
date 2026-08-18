# Shared

The `shared/` package is AIRunner's shared foundation surface. It owns the
canonical build metadata (`package_metadata.py`: version, requirement groups,
and console-script entry points single-sourced across the GUI, services,
native, and shared surfaces), plus the shared settings, contracts, and layout
modules imported by the other packages.

Importable shared code lives under `shared/airunner_common/`.

In a checkout, `airunner_common.package_metadata.README` resolves the
repo-root `README.md` for `long_description`; the published `airunner-common`
sdist carries its own `README.md` so a wheel built from the sdist resolves the
description without the repo root (issue #2061).
