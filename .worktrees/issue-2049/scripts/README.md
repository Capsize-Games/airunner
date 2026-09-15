# Scripts

The `scripts/` directory holds developer tooling. It is not a Python package
that ships in the runtime product; everything here is for contributors working
in a repo checkout.

## What This Directory Owns

- the unified test runner (`run_tests.py`) that drives the unit, runtime
  smoke, eval, and GUI functional suites
- UI and resource build helpers (`build_ui.py`, `process_qss.py`,
  `compile_translations.py`)
- developer install helpers (`install.sh`, `install_helpers.sh`,
  `build_runtime_sidecars.sh`)
- code-quality and reporting tooling (`code_quality_report.py`,
  `coverage_report.py`, the dead-code scanners and unused-import checkers,
  the complexity reports, `mypy_shortcut.py`, `security_audit.sh`)
- local dev orchestration under `scripts/dev/` (`run_services.sh`,
  `run_gui.sh`, `test_services.sh`, `stop_services.sh`)

The architecture audit and package map are tracked in
[docs/architecture/architecture-complexity-audit.md](../docs/architecture/architecture-complexity-audit.md)
and
[docs/architecture/layered_product_architecture.md](../docs/architecture/layered_product_architecture.md).

## Usage

Run the unit suite from a repo checkout:

```bash
./venv/bin/python scripts/run_tests.py --unit
```

Rebuild the UI assets after changing `.ui` or `.qrc` sources:

```bash
./venv/bin/python scripts/build_ui.py
```

See `scripts/run_tests.py --help` for the full set of test targets.
