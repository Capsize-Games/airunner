# Services Complexity Workflow

Use this workflow to measure code complexity across
`services/src/airunner_services`, record the findings, and draft follow-up
cleanup issues.

## Setup

From the repository root, install the optional analysis tools:

```bash
pip install -e ".[analysis]"
```

If you do not want to install the extra set, install the tools directly:

```bash
pip install radon xenon
```

## Generate the Report

Run the dedicated report script from the repository root:

```bash
python scripts/services_complexity_report.py
```

Or use the console entry point after installation:

```bash
airunner-services-complexity-report
```

By default this writes two ignored outputs under
`build/services_complexity/`:

- `services_complexity_report.json`
- `services_complexity_report.md`

The report includes:

- Radon cyclomatic complexity, maintainability index, and Halstead volume
- file, class, and function size hotspots
- Xenon gate output for the selected thresholds
- draft issue candidates grouped by services subsystem

## Thresholds

The default thresholds match the current cleanup target:

- files: 200 SLOC or less
- classes: 200 lines or less
- functions and methods: 20 lines or less
- Radon block rank: `B` or better
- maintainability index: `65` or higher

Override them when needed:

```bash
python scripts/services_complexity_report.py \
  --max-file-lines 180 \
  --max-class-lines 180 \
  --max-function-lines 15 \
  --max-complexity-rank A
```

## Creating GitHub Issues

Use the `issue_candidates` array in the JSON report as the starting point for
new cleanup issues. Each candidate includes a ready-to-paste title and body.

Example:

```bash
gh issue create \
  --title "$(jq -r '.issue_candidates[0].title' build/services_complexity/services_complexity_report.json)" \
  --body "$(jq -r '.issue_candidates[0].body_markdown' build/services_complexity/services_complexity_report.json)"
```

When opening issues, keep them focused on one subsystem at a time so the
resulting refactor slices stay small enough to validate and land safely.