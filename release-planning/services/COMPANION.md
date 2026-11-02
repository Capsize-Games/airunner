# Companion ownership and retirement plan

AI Runner provides model execution, workers and service APIs. Cognitive policy
belongs to consuming applications: mood changes, curiosity, proactive messages,
persona composition and application-specific memory extraction should have one
implementation in the application layer.

The current companion package contains a substantial earlier implementation.
It is not wired into daemon startup as an end-to-end cognition service. Adding
a new companion endpoint and scheduler pump would create another policy owner.
The service release will preserve compatibility while separating dependencies
needed for ordinary model execution.

## Existing dependencies

| Dependency | Disposition |
|---|---|
| Embedding model identity and structured errors | Canonical definitions now live in `runtimes/embedding_contracts.py`. Companion names re-export the same types for compatibility. The local embedding runtime and Ollama helper use the neutral definitions. |
| API package initialization | Route modules now load on demand. Importing an embedding helper no longer imports the entire route set and companion modules. |
| Local capability routing | Generic pipeline definitions now live in `runtimes/local_pipeline.py`; companion routing retains compatibility aliases. Capability reporting uses the neutral module and preserves runtime selection and offline enforcement behavior. |
| Registered fact and turn tools | Retain the existing compatibility adapters until callers have a supported replacement or an explicit unsupported result. Do not silently unregister tools. |
| ORM models and historical Alembic revisions | Preserve schema history and data. Deleting an unused Python handler does not authorize dropping tables or rewriting migrations. |
| Durable jobs and inference adapters | Retain existing contracts during caller analysis. Model execution, cancellation, resource arbitration and truthful terminal results remain service responsibilities. |
| Mood, curiosity, prompt composition and memory policy | Retire the duplicate service implementation in bounded slices after caller and data checks. Do not add new production cognition integration here. |

## Stored data inventory

The schema includes `companion_sessions`, `companion_turns`,
`companion_facts`, `companion_narratives`, `companion_jobs`, and
`companion_migration_ledger`. ORM definitions are in
`services/src/airunner_services/database/models/companion_*.py`; the ledger
table definition is in
`services/src/airunner_services/llm/companion/migration_ledger.py`. Historical
Alembic revisions `910441db1456`, `eb1b28d1b87f`, and `3beaa16d79c8` create the
first five tables. Revision `d951d2fd378d` imports
`MIGRATION_LEDGER_TABLE` and `MIGRATION_METADATA` from the ledger module, so
that module remains part of migration replay until the historical import is
decoupled without changing the revision's behavior.

A repository source scan records 15 import entries across
`services/src/airunner_services/llm/tools/companion_memory_compat.py`,
`services/src/airunner_services/llm/tools/companion_memory_tools.py`, and the
historical ledger migration. The two tool modules contain current in-repository
memory-tool and compatibility-adapter callers. This scan does not observe
external applications or databases; it does not establish that external
consumers are absent or that stored data is unused.

[`scripts/inventory_companion_store.py`](../../scripts/inventory_companion_store.py)
can report expected-table row counts, aggregate known job and migration-ledger
statuses (with an `unknown` bucket), and one validated Alembic revision. It
uses the stored job statuses `queued`, `leased`, `succeeded`, `failed`, and
`cancelled`, and ledger statuses `migrated`, `failed`, `needs_resolution`, and
`resolved`; other or null values contribute only to `unknown`.
It requires an explicit existing standalone SQLite backup or snapshot; never
point it at an active database. It opens with `mode=ro&immutable=1` and
`query_only`, rejects a symbolic-link file path and existing `-wal`, `-shm`, or
`-journal` sidecars, and enforces a finite query deadline. The immutable mode
bypasses SQLite locking and change detection, so the caller must provide a
stable snapshot. The tool does not make a copy or validate snapshot stability.
It does not load service models, return conversation text, identities or
payloads, migrate, export, or delete data. An absent expected
table is reported with a `null` count; an existing empty table has a count of
zero. The command has no default database path:

```sh
python scripts/inventory_companion_store.py --database /path/to/backup.sqlite
```

No operational database was inspected for this change. Actual occupancy,
retention requirements, external consumers, and data ownership remain
unresolved until a separate operational inventory and retention decision.

The companion package's public `__init__.py` exports B01 request/result,
inference, repository protocol, scheduler protocol and tool-dispatch contracts.
There is no production construction of the durable scheduler, but that does
not establish the absence of external package consumers. No companion
implementation module has been removed: repository and tool call edges remain,
and historical migration replay imports `migration_ledger.py`.

`llm/tools/__init__.py` imports and registers `companion_memory_tools`;
`companion_memory_compat.py` still adapts legacy memory operations; and
`ToolManager` registers `update_mood`. The streaming mixins also call the
existing mood update path. These registrations and paths remain intact.

The UwUchat checkout is a separate, locally dirty owner application. Its
`server/portable/exporter.py` exports that application's character, cumulative
memory and attributed conversations; its matching importer validates bundle
revisions and merges those records into the tenant. That bundle is not the
AIRunner companion SQLite schema and does not cover companion job or migration
ledger rows. UwUchat's source was inspected read-only; none of its files or
existing dirty changes were edited for this contract.

## Snapshot export and compatibility contract

[`scripts/export_companion_snapshot.py`](../../scripts/export_companion_snapshot.py)
creates an explicit, byte-for-byte copy of a standalone SQLite backup or
snapshot to a new local path. It hashes the copy and reports only byte count
and SHA-256. It does not query the database, transform rows, choose tables,
drop unknown columns, change job states, run migrations, or modify the source.
The destination must not already exist. The exporter rejects symlinks,
SQLite journal sidecars, and files without the SQLite header. It detects source
file metadata changes during copying and removes an incomplete destination on
failure. Because the file is an opaque full-database copy, it contains the
source database's private contents; choose a protected local destination and
do not upload it as a source artifact. The command requires an explicit
source and destination:

```sh
python scripts/export_companion_snapshot.py \
  --source /path/to/stable-backup.sqlite \
  --destination /path/to/new-protected-copy.sqlite
```

This is a recovery copy, not a cross-application import format. It does not
make an active database safe to copy; obtain a stable standalone snapshot
through the database owner's backup procedure first. No operational database
or backup was read or copied for this change. Tests use synthetic SQLite files
only.

Retirement remains gated by evidence, not a claim of data absence. Before
removing a production registration or persistence contract, the change must
show the replacement and its callers, preserve job state and the complete
database snapshot, retain the historical Alembic chain and ledger import, and
keep the compatibility surface available for external consumers that have not
yet been inventoried. No table, row, model, registered tool, migration, or
duplicate-policy module was deleted here. No new companion endpoint, worker,
or scheduler pump was added.

## Retirement phases

1. **Separate generic runtime contracts.** Keep compatibility aliases and prove
   narrow imports do not initialize companion code. The embedding extraction
   and lazy route initialization are implemented. Capability routing also uses
   neutral definitions, with compatibility aliases and focused route tests.
2. **Inventory callers and data.** Distinguish production registrations from
   test-only factories, document stored schemas and identify pending jobs.
   Existing data occupancy has not been inspected. A single-user store cannot
   be copied directly into a consumer's tenant or encryption model. UwUchat's
   separate portable bundle does not cover the AIRunner companion job or
   migration-ledger tables.
3. **Preserve compatibility and recovery.** Keep current registrations,
   exports and historical schema replay available. Use the opaque snapshot
   exporter only with an explicitly provided stable backup. External callers,
   retention requirements and actual occupancy remain unknown; no destructive
   downgrade or data transformation is part of this phase.
4. **Remove isolated duplicate policy.** Delete only modules with a proven
   absence of remaining callers, retain historical migration imports, and run
   focused compatibility and database checks. Keep each deletion reviewable.
5. **Verify the service boundary.** Test runtime routing, authenticated model
   APIs, streaming cancellation and memory-tool compatibility independently
   of application-level cognition. Evaluate consumer behavior in its owner
   application rather than claiming parity from the old port.

These phases are tracked in the service Kanban project. The implementation
and data-preservation work remains open after the initial extraction. No
companion schema, stored records or policy modules were deleted in that change.

## Characterization evidence

The B01-B14 deterministic suites cover contracts, temporary SQLite repositories,
fact correction and recall, embedding identity, durable jobs, prompt budgets,
tool cancellation, inference adapters and migration recovery. An isolated run
reported **174 passed, 852 warnings**. Providers were fakes; this establishes
neither real-model quality nor equivalence to a consuming application's current
behavior. Focused checks added for the contract extraction also verify the
companion-free import boundary and compatibility aliases.

There is no companion turn endpoint, production construction of
`DurableCompanionScheduler`, handler registration set or scheduler pump in the
daemon. Mood and curiosity enum entries route to providers but do not establish
implemented background handlers. This does not mean companion code is unused:
the memory tools are registered and existing mood update paths remain in use.

The earlier evaluation document and `services/tests/eval/` are absent from this
checkout. Model revisions, latency and factuality thresholds, hardware trials,
and operator acceptance remain pending. The retained characterization issues
must not be closed as real-model acceptance on the strength of deterministic
fixtures.
