# AIRunner Coding Project Contract

## Goal

Define the on-disk contract for AIRunner coding workspaces before terminal,
agent, and editor-shell features start persisting their own state.

The contract is intentionally split between JSON metadata and markdown working
documents:

- JSON stores structured machine-owned configuration.
- Markdown stores human-readable plans, memory, and run notes.

This keeps project diffs readable while still giving the agent runtime explicit
schemas for settings, roots, and migration handling.

## Versioning

The initial coding-project contract is schema version `1`.

The following files carry explicit version fields:

- `.airunner/workspace.json`
- `.airunner/settings.json`

Migration rule:

- Future schema changes must add a new integer `schema_version`.
- Older readers may reject unknown future versions.
- Migrations should be additive when possible and destructive rewrites should
  happen in dedicated migration code rather than inside UI widgets.

## Directory Layout

Every AIRunner coding project owns a `.airunner/` directory at the project
root.

Required layout in schema version `1`:

```text
.airunner/
├── agents/
├── audit/
├── indexes/
├── memory/
├── plans/
├── sessions/
├── tasks/
├── terminal/
├── settings.json
└── workspace.json
```

## Ownership Boundaries

JSON files are machine-owned and should remain deterministic.

- `.airunner/workspace.json` defines project identity, multi-root metadata,
  primary root selection, and timestamps.
- `.airunner/settings.json` defines trust and autonomy policy.

Markdown directories are shared human and agent working space.

- `.airunner/plans/` stores project plans and execution breakdowns.
- `.airunner/memory/` stores durable project memory and notes.
- `.airunner/sessions/` stores per-run summaries or resumable conversation
  context.

Structured runtime data stays out of markdown.

- `.airunner/tasks/` will hold machine-readable task ledgers.
- `.airunner/audit/` will hold generated-write and command audit trails.
- `.airunner/indexes/` will hold disposable search and symbol indexes.
- `.airunner/terminal/` will hold persisted terminal-session metadata.
- `.airunner/agents/` will hold machine-readable agent profiles and state.

## Workspace Metadata

`workspace.json` owns the stable workspace definition.

Required fields in schema version `1`:

- `schema_version`
- `project_id`
- `project_name`
- `primary_root`
- `roots`
- `created_at`
- `updated_at`

Each root entry includes:

- `name`: stable display and lookup name
- `path`: project-relative path when inside the project root, otherwise an
  absolute path for external roots

Rules:

- At least one root must exist.
- Root names must be unique.
- Root paths must be unique.
- `primary_root` must refer to a declared root.

## Trust And Autonomy Policy

`settings.json` owns the trust model for coding agents.

Required fields in schema version `1`:

- `schema_version`
- `trust_level`
- `autonomy_mode`

Allowed trust levels:

- `untrusted`
- `trusted`

Allowed autonomy modes:

- `review-first`
- `mixed`
- `full-autonomy`

Policy rule in schema version `1`:

- Untrusted projects must use `review-first` autonomy.

That rule keeps background command execution and write application behind an
explicit trust decision.

## Multi-Root Storage Rules

AIRunner supports multiple workspace roots from the beginning of the coding
workspace effort.

Storage rules:

- The primary project root owns `.airunner/`.
- Additional roots are declared in `workspace.json`.
- Paths inside the primary project root should be stored relative to keep the
  workspace portable.
- External roots may remain absolute because portability depends on user
  environment and mount layout.

## Implementation Notes

The first implementation layer for this contract lives in the document editor
project service:

- `AirunnerWorkspaceConfig` defines versioned multi-root metadata.
- `AirunnerProjectSettings` defines trust and autonomy policy.
- `AirunnerProjectService` creates the layout and resolves root-aware paths.

That service should remain the single place that editor, terminal, indexing,
and agent features use when they need project-aware file access.# AIRunner Coding Project Contract

## Goal

Define the first stable on-disk contract for AIRunner coding workspaces.
The project root owns the developer-visible code and a dedicated `.airunner`
directory owns coding-agent state.

## Layout

Version 1 of the contract reserves these paths under the project root:

```text
.airunner/
├── settings.json
├── workspace.json
├── agents/
├── audit/
├── indexes/
├── memory/
├── plans/
├── sessions/
├── tasks/
└── terminal/
```

`workspace.json` stores project identity, root metadata, and the selected
primary root. `settings.json` stores trust and autonomy metadata.

## Artifact Ownership

Markdown is the human-authored source of truth for collaborative project
artifacts:

- `.airunner/plans/` for project and run plans
- `.airunner/memory/` for durable project memory and notes

JSON is the machine-managed source of truth for operational metadata:

- `.airunner/workspace.json` for workspace roots and project identity
- `.airunner/settings.json` for trust and autonomy policy
- `.airunner/tasks/` and `.airunner/sessions/` for task and session state
- `.airunner/audit/` and `.airunner/terminal/` for structured execution logs

This split keeps plans and notes diffable while allowing the runtime to store
structured execution state without forcing humans to hand-edit operational
records.

## Trust And Autonomy Policy

Version 1 defines two trust levels and three autonomy modes:

- `untrusted`
- `trusted`
- `review-first`
- `mixed`
- `full-autonomy`

Untrusted projects must stay in `review-first`. Trusted projects may opt into
`mixed` or `full-autonomy`.

`review-first` means AIRunner must require approval for commands and review for
file writes. `mixed` allows automatic command execution but still expects file
review. `full-autonomy` allows both command execution and file writes without
interactive checkpoints.

## Multi-Root Rules

`workspace.json` must list every declared workspace root. The primary project
root is stored as `workspace` with a relative path of `.`. Additional roots may
be stored as relative paths when they live under the project root or absolute
paths when they live elsewhere on disk.

Tooling that reads or writes files must resolve paths through the declared root
list instead of assuming one base directory.

## Versioning And Migration

Both `workspace.json` and `settings.json` carry `schema_version` values.
Version 1 is the baseline contract introduced for the coding-agent feature.

Future schema changes should follow these rules:

1. Add a forward migration path before changing defaults or required fields.
2. Keep markdown artifacts stable unless a migration truly needs new layout.
3. Prefer additive JSON changes before destructive structural rewrites.
4. Fail explicitly when AIRunner encounters a newer schema it does not know.

This keeps the `.airunner` directory inspectable and recoverable while giving
the application room to evolve the runtime model over time.