# Coding Agent Workspace Operator Guide

This guide covers the operator-facing workflow for AIRunner coding projects.
It is intended for maintainers working on the `.airunner` coding workspace,
project trust modes, agent recovery, and future validation work.

## Project Model

AIRunner coding workspaces use a `.airunner/` metadata root inside the
project path. The contract is documented in
`docs/architecture/airunner_coding_project_contract.md`.

Key directories:

- `.airunner/workspace.json`: multi-root workspace registry and primary root
- `.airunner/settings.json`: trust mode, autonomy mode, and bootstrap metadata
- `.airunner/plans/`: human or agent markdown plans
- `.airunner/memory/`: markdown working memory
- `.airunner/agents/`: sessions, tasks, and handoffs
- `.airunner/audit/`: runs, tool calls, generated writes, and related review data
- `.airunner/indexes/`: machine-owned retrieval indexes such as
  `project_context_index.json`

## Project Setup

For new Python-first projects, AIRunner can scaffold a coding workspace with:

- `pyproject.toml`
- `README.md`
- `.gitignore`
- `src/<package>/__init__.py`
- `src/<package>/__main__.py`
- `tests/test_<package>.py`

The selected Python environment is persisted in `.airunner/settings.json` as
project metadata. Python quality workflows resolve commands from that metadata
so the same project can be reopened and validated consistently.

## Trust Modes

AIRunner currently uses two core trust concepts in coding workspaces:

- `review-first`: command execution and file-writing tools require explicit
  approval or review flags at the public tool boundary
- `full-autonomy`: trusted projects may run commands and machine-owned project
  operations without those extra approvals

Operators should treat `review-first` as the safe default for new or untrusted
projects. Move a workspace to `full-autonomy` only when the repository and its
agent behaviors are understood.

## Recovery Flows

Core recovery state lives under `.airunner/agents/` and `.airunner/audit/`.

- Sessions are resumable while they remain in `pending`, `running`, or `paused`
  states.
- Runs persist channel messages and tool calls under `.airunner/audit/runs/`.
- Long-running runs can now be compacted. Compaction preserves recent messages,
  summarizes older history into `run.summary`, and records compaction metadata.
- Generated writes remain reviewable and revertible from the audit trail.

When recovering a workspace after interruption:

1. Check `.airunner/settings.json` for trust and environment metadata.
2. Check `.airunner/agents/sessions/` and `.airunner/tasks/` for active task
   ownership.
3. Check `.airunner/audit/runs/` for the most recent run transcripts.
4. Rebuild `.airunner/indexes/project_context_index.json` if indexed retrieval
   looks stale.

## Validation Guidance

Use the focused coding-workspace validation alias for this feature area:

```bash
/home/joe/Projects/airunner/venv/bin/python src/airunner/bin/run_tests.py --component coding_workspace
```

That alias runs the targeted project, agent, and tool tests that cover the
coding-agent foundation rather than the full repository.

Useful component-level commands:

```bash
/home/joe/Projects/airunner/venv/bin/python src/airunner/bin/run_tests.py --component agents
/home/joe/Projects/airunner/venv/bin/python src/airunner/bin/run_tests.py --component document_editor
/home/joe/Projects/airunner/venv/bin/python src/airunner/bin/run_tests.py --component llm/tools
```

Suggested validation order for future coding-workspace changes:

1. Run `--component coding_workspace`.
2. Run any narrower component suite touched by the change.
3. If project command or terminal behavior changed, inspect persisted
   `.airunner/audit/` artifacts in a temporary test workspace.
4. If project metadata or retrieval changed, rebuild and query the project
   context index in tests rather than launching the full app.

## Operator Notes

- JSON under `.airunner/` is machine-owned unless a file is explicitly intended
  for human editing.
- Markdown under `.airunner/plans/` and `.airunner/memory/` is the preferred
  place for operator-readable working state.
- The AIRunner app itself should not be launched as part of normal validation
  for this feature area; use tests, diagnostics, and read-only inspection.