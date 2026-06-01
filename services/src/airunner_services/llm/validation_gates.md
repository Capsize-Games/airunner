# LLM Refactor Validation Gates

Use this baseline for each refactor slice under
`services/src/airunner_services/llm`.

## No-behavior-change baseline

1. Keep the validation scope aligned with the touched slice.
2. Run a focused compile gate first.
3. Reuse the repository quality workflow on the touched path.
4. Run `mypy` on the touched service module or directory.
5. Record verification notes in the active GitHub issue as the slice
   lands. Do not defer validation notes to the umbrella issue.
6. Keep runtime validation manual and user-driven unless the user
   explicitly asks to launch the application.

## Commands

Prefer these commands from the repository root:

```bash
python -m compileall -q <touched-file-or-directory>
python scripts/code_quality_report.py --path <touched-file-or-directory>
python scripts/mypy_shortcut.py <touched-file-or-directory>
```

The installed entry points in `setup.py` map to the same tools:

- `airunner-quality-report`
- `airunner-mypy`

When the touched slice is broader than one file, scale from the file to
the owning directory, then to `services/src/airunner_services/llm` only
when the narrower checks are already green.

## Optional analysis tools

`radon` and `xenon` now power the broader services discovery workflow via:

```bash
python scripts/services_complexity_report.py
airunner-services-complexity-report
```

Use that workflow for directory-wide hotspot discovery and issue drafting.
Do not replace slice-scoped compile, quality-report, or `mypy` gates with it.

## Verification note template

Every refactor issue should capture:

- compile command(s) run
- quality-report command(s) run
- `mypy` command(s) run
- manual runtime validation status, marked as user-driven when pending