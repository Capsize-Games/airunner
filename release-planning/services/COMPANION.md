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
| Local capability routing | Inventory and extract the generic capability definitions before removing companion routing modules. Keep runtime selection and offline enforcement behavior. |
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

The private repository source scan records 15 import entries across
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
It requires an explicit existing SQLite file, opens it with `mode=ro` and
`query_only`, rejects a symbolic-link file path, and enforces a finite query
deadline. It does not load service models, inspect table contents, return
identities or payloads, migrate, export, or delete data. An absent expected
table is reported with a `null` count; an existing empty table has a count of
zero. The command has no default database path:

```sh
python scripts/inventory_companion_store.py --database /path/to/existing.sqlite
```

No operational database was inspected for this change. Actual occupancy,
retention requirements, external consumers, and data ownership remain
unresolved until an explicitly authorized inventory and owner review.

## Retirement phases

1. **Separate generic runtime contracts.** Keep compatibility aliases and prove
   narrow imports do not initialize companion code. The embedding extraction
   and lazy route initialization are implemented; capability routing remains.
2. **Inventory callers and data.** Distinguish production registrations from
   test-only factories, document stored schemas and identify pending jobs.
   Existing data occupancy has not been inspected. A single-user store cannot
   be copied directly into a consumer's tenant or encryption model.
3. **Preserve compatibility and recovery.** Specify export, retention and
   rollback behavior before changing persistence. Existing tools require an
   explicit replacement or deprecation contract. No destructive downgrade is
   part of this phase.
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
implemented background handlers. Legacy mood tools and memory registrations
still exist and must be included in retirement analysis.

The earlier evaluation document and `services/tests/eval/` are absent from this
checkout. Model revisions, latency and factuality thresholds, hardware trials,
and operator acceptance remain pending. The retained characterization issues
must not be closed as real-model acceptance on the strength of deterministic
fixtures.
