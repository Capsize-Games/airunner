# Complexity & Typing Tooling (issue #2052)

This page documents the project's current stance on static type checking and
code-complexity reporting. It exists so the tooling is consistent and its
non-gating role is explicit.

## mypy: configured, non-gating local aid

The mypy configuration lives in the project [`[tool.mypy]`](../pyproject.toml)
section (`python_version = "3.13"`, `ignore_missing_imports`,
`follow_imports = "skip"`, `check_untyped_defs`, `no_implicit_optional`, and
per-module `ignore_errors` overrides for `airunner.feather_rc` and
`airunner_services.vendor.*`). That section is the single source of truth for
mypy flags.

Two equivalent entry points both resolve that configuration:

```bash
# Shortcut entry point (installed as `airunner-mypy`):
airunner-mypy <file>

# Bare mypy, from the repo root:
mypy <path>
```

`scripts/mypy_shortcut.py` intentionally passes **no** flags on the command
line; mypy discovers `[tool.mypy]` from the current working directory upward,
so the shortcut and bare `mypy` always agree.

**Status: mypy is a non-gating local aid.** It is not enforced in CI, and the
whole tree is not expected to be type-clean. Run it per-file while editing;
do not block merges on it.

## Complexity reports: advisory artifacts

Both complexity report scripts are **advisory**: they surface hotspots for
human review and are not a CI gate. The `Thresholds` dataclass values and the
`--max-*` / `--min-mi` flags are guidance, not enforcement.

```bash
# GUI tree:
python scripts/gui_complexity_report.py

# Services tree:
python scripts/services_complexity_report.py
```

or, after installing the `[analysis]` extra (`pip install -e ".[analysis]"`):

```bash
airunner-gui-complexity-report
airunner-services-complexity-report
```

Outputs are written under `build/gui_complexity/` and
`build/services_complexity/` respectively (both gitignored).

The two scripts must keep their skip rules (`_is_generated`: `*_ui.py`,
`*_rc.py`) and default excludes (`build`, `dist`, `vendor`, `__pycache__`)
identical so the reports measure the same source surface. Parity is locked by
`services/tests/test_complexity_report_parity.py`.
