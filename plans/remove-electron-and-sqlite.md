# Plan: Remove Electron & SQLite — Move to Web-Only Architecture

## Overview

This document catalogs **every file and code path** that supports Electron (desktop shell) and SQLite/IndexedDB (local persistence). The goal is a web-only app with server-side data storage (PostgreSQL) only — no local SQLite, no Electron, no browser-side IndexedDB cache.

---

## PART 1: ELECTRON REMOVAL

### 1.1 Entire directory to delete

| Path | Contents |
|------|----------|
| [`electron/`](electron/) | Main process, preload, package.json, lockfile, embedded Python resources |

**Contents:**
- [`electron/main.js`](electron/main.js) — Electron main process: spawns Python backend as child process, creates [`BrowserWindow`](electron/main.js:292), polls `/health`, loads frontend
- [`electron/preload.js`](electron/preload.js) — Preload script exposing `window.airunner` (platform, version) via [`contextBridge`](electron/preload.js:9)
- [`electron/package.json`](electron/package.json) — Electron dependencies (`electron ^39.8.5`, `electron-builder ^26.8.1`), build config for AppImage/deb/NSIS
- [`electron/package-lock.json`](electron/package-lock.json) — Full lockfile
- [`electron/resources/`](electron/resources/) — Embedded CPython runtime, compiled React frontend, Jupyter files (hundreds of files)

### 1.2 Build / packaging scripts to delete or heavily modify

| File | Electron references |
|------|---------------------|
| [`package/build_bundle.sh`](package/build_bundle.sh) | Lines [17-19](package/build_bundle.sh:17): Sets `ELECTRON_DIR`, uses it for resources. Lines [206-233](package/build_bundle.sh:206): Copies build artifacts into `electron/resources/`, runs [`electron-builder`](package/build_bundle.sh:225) |
| [`package/build_bundle.ps1`](package/build_bundle.ps1) | Lines [17-21](package/build_bundle.ps1:17): Sets `$ELECTRON_DIR`, copies to resources. Line ~175: Runs electron-builder for Windows |
| [`scripts/package_linux_appimage.sh`](scripts/package_linux_appimage.sh) | AppImage generation — references the bundle directory structure |
| [`packaging/windows/airunner.nsi`](packaging/windows/airunner.nsi) | NSIS Windows installer |
| [`packaging/linux/`](packaging/linux/) | Icons, [`airunner.desktop`](packaging/linux/airunner.desktop) desktop entry |

### 1.3 Server-side code referencing Electron-specific env vars

| File | What to change |
|------|----------------|
| [`server/src/airunner_services/api/server_helpers.py`](server/src/airunner_services/api/server_helpers.py:103-118) | `_mount_static_files()` reads [`AIRUNNER_STATIC_DIR`](server/src/airunner_services/api/server_helpers.py:106) env var set only by Electron's [`main.js`](electron/main.js:110). Remove or repurpose this function. |

### 1.4 Client-side Electron references

**None found.** The search for `window.airunner`, `airunner.platform`, `airunner.version` returned zero results in `.ts` and `.tsx` files. The client does not consume the Electron preload API.

### 1.5 Documentation

| File | What to change |
|------|----------------|
| [`README.md`](README.md:112-128) | Remove the "Electron app" architecture diagram and description |

### 1.6 Root `package.json`

| File | What to check |
|------|---------------|
| [`package.json`](package.json) | Check for any Electron-related scripts or devDependencies |

### 1.7 `.gitignore`

| File | What to check |
|------|---------------|
| [`.gitignore`](.gitignore) | No Electron-specific entries found; may need additions for new build artifacts |

---

## PART 2: SQLITE REMOVAL (Server-Side)

### 2.1 Engine & connection layer

| File | SQLite-specific code | Action |
|------|---------------------|--------|
| [`server/src/airunner_services/database/db/engine.py`](server/src/airunner_services/database/db/engine.py) | [`_is_sqlite_url()`](server/src/airunner_services/database/db/engine.py:17-19), [`_configure_sqlite_connection()`](server/src/airunner_services/database/db/engine.py:22-32) (WAL pragma, busy_timeout), [`create_configured_engine()`](server/src/airunner_services/database/db/engine.py:35-40) conditionally attaches SQLite event listener | **Rewrite** to PostgreSQL-only. Remove `_is_sqlite_url`, `_configure_sqlite_connection`, `SQLITE_BUSY_TIMEOUT_MS`. |

### 2.2 Configuration (settings/presets)

| File | SQLite-specific code | Action |
|------|---------------------|--------|
| [`server/src/airunner_services/conf/default_settings.py`](server/src/airunner_services/conf/default_settings.py:25-26) | [`DATABASE_BACKEND = "sqlite"`](server/src/airunner_services/conf/default_settings.py:25), [`SQLITE_DB_NAME`](server/src/airunner_services/conf/default_settings.py:26-28) | Remove SQLite defaults, make PostgreSQL the only backend |
| [`server/src/airunner_services/conf/__init__.py`](server/src/airunner_services/conf/__init__.py:118-139) | [`_build_db_url()`](server/src/airunner_services/conf/__init__.py:118-139) has SQLite branch (lines 133-139): constructs `sqlite:///` URL | **Remove SQLite branch** — make PostgreSQL the only path |
| [`server/src/airunner_services/conf/presets/development.py`](server/src/airunner_services/conf/presets/development.py) | [`DATABASE_BACKEND = "sqlite"`](server/src/airunner_services/conf/presets/development.py:5), [`SQLITE_DB_NAME = "airunner.dev.db"`](server/src/airunner_services/conf/presets/development.py:6) | Remove, replace with PostgreSQL defaults |

### 2.3 Session management

| File | SQLite-specific code | Action |
|------|---------------------|--------|
| [`server/src/airunner_services/database/session.py`](server/src/airunner_services/database/session.py) | [`_ensure_sqlite_parent_dir()`](server/src/airunner_services/database/session.py:90-96) — called in 3 places: [line 134](server/src/airunner_services/database/session.py:134), [line 211](server/src/airunner_services/database/session.py:211); also the entire multi-tenant schema logic is PostgreSQL-only and should remain | Remove `_ensure_sqlite_parent_dir()` and its call sites |

### 2.4 Database setup

| File | SQLite-specific code | Action |
|------|---------------------|--------|
| [`server/src/airunner_services/database/setup_database.py`](server/src/airunner_services/database/setup_database.py) | [`_ensure_sqlite_parent_dir()`](server/src/airunner_services/database/setup_database.py:53-60) — called on [line 356](server/src/airunner_services/database/setup_database.py:356); comment on [lines 322-325](server/src/airunner_services/database/setup_database.py:322-325): "Gated behind AIRUNNER_REQUIRE_POSTGRES so the open-core desktop app (which legitimately runs on SQLite) is never affected" | Remove `_ensure_sqlite_parent_dir()`, remove the `_enforce_db_policy` gate comment |

### 2.5 Migration helpers (SQLite dialect branching)

| File | SQLite-specific code | Action |
|------|---------------------|--------|
| [`server/src/airunner_services/database/db/column.py`](server/src/airunner_services/database/db/column.py) | `_dialect_name() == "sqlite"` checks on [line 243](server/src/airunner_services/database/db/column.py:243) and [line 275](server/src/airunner_services/database/db/column.py:275) with `recreate="always"`, SQLite limitation messages on [lines 264](server/src/airunner_services/database/db/column.py:264) and [303](server/src/airunner_services/database/db/column.py:303) | Remove all SQLite-specific `batch_alter_table` with `recreate="always"` branches, keep PostgreSQL path |
| [`server/src/airunner_services/database/db/foreign_key.py`](server/src/airunner_services/database/db/foreign_key.py) | `dialect_name == "sqlite"` check on [line 25](server/src/airunner_services/database/db/foreign_key.py:25) with `recreate="always"` | Remove SQLite branch |

### 2.6 Alembic migration files (SQLite conditionals in individual migrations)

Each of these files has SQLite-specific logic (dialect checks, `recreate="always"`, `sqlite.JSON()`, etc.):

| File | SQLite references |
|------|-------------------|
| [`server/src/airunner_services/database/alembic/versions/b1c4d5e6f7a8_remove_nodegraph_schema.py`](server/src/airunner_services/database/alembic/versions/b1c4d5e6f7a8_remove_nodegraph_schema.py:36) | `dialect.name == "sqlite"` check for batch_alter_table |
| [`server/src/airunner_services/database/alembic/versions/48b1c0d3e4f5_drop_retired_mode_routing_columns.py`](server/src/airunner_services/database/alembic/versions/48b1c0d3e4f5_drop_retired_mode_routing_columns.py:38) | `dialect.name == "sqlite"` check |
| [`server/src/airunner_services/database/alembic/versions/6b0f0f6c3e4a_move_client_local_application_settings_to_qsettings.py`](server/src/airunner_services/database/alembic/versions/6b0f0f6c3e4a_move_client_local_application_settings_to_qsettings.py:72-74) | SQLite comment in downgrade; [line 158](server/src/airunner_services/database/alembic/versions/6b0f0f6c3e4a_move_client_local_application_settings_to_qsettings.py:158) `dialect.name == "sqlite"` |
| [`server/src/airunner_services/database/alembic/versions/843e4b044d4d_add_model_id_column_to_llm_generator_.py`](server/src/airunner_services/database/alembic/versions/843e4b044d4d_add_model_id_column_to_llm_generator_.py:36-37) | "SQLite doesn't support DROP COLUMN" comment |
| [`server/src/airunner_services/database/alembic/versions/d2ab5f1c9a7e_move_client_local_language_and_audio_to_qsettings.py`](server/src/airunner_services/database/alembic/versions/d2ab5f1c9a7e_move_client_local_language_and_audio_to_qsettings.py:123) | `dialect.name == "sqlite"` |
| [`server/src/airunner_services/database/alembic/versions/7b88f4d9a4a1_add_reasoning_effort_to_llm_generator_.py`](server/src/airunner_services/database/alembic/versions/7b88f4d9a4a1_add_reasoning_effort_to_llm_generator_.py:44-45) | "SQLite downgrade is intentionally skipped" |
| [`server/src/airunner_services/database/alembic/versions/20c05328cd3b_restore_nsfw_filter_setting.py`](server/src/airunner_services/database/alembic/versions/20c05328cd3b_restore_nsfw_filter_setting.py:29) | "SQLite does not support DROP COLUMN directly" |
| [`server/src/airunner_services/database/alembic/versions/5a4d9d9e0b67_add_quantization_and_enabled_adapters_to_.py`](server/src/airunner_services/database/alembic/versions/5a4d9d9e0b67_add_quantization_and_enabled_adapters_to_.py:57-58) | "SQLite downgrade is intentionally skipped" |
| [`server/src/airunner_services/database/alembic/versions/f480bbc9acdb_drop_knowledge_facts_and_knowledge_.py`](server/src/airunner_services/database/alembic/versions/f480bbc9acdb_drop_knowledge_facts_and_knowledge_.py:23) | "SQLite compatibility" comment |
| [`server/src/airunner_services/database/alembic/versions/6b36790f3292_add_layer_id_to_settings_models.py`](server/src/airunner_services/database/alembic/versions/6b36790f3292_add_layer_id_to_settings_models.py:62) | "batch operation for SQLite compatibility" |
| [`server/src/airunner_services/database/alembic/versions/91e21ecaef23_add_video_projects_table.py`](server/src/airunner_services/database/alembic/versions/91e21ecaef23_add_video_projects_table.py:13) | [`from sqlalchemy.dialects import sqlite`](server/src/airunner_services/database/alembic/versions/91e21ecaef23_add_video_projects_table.py:13), uses [`sqlite.JSON()`](server/src/airunner_services/database/alembic/versions/91e21ecaef23_add_video_projects_table.py:59-61) |
| [`server/src/airunner_services/database/alembic/versions/d4184aabeff9_remove_allow_online_mode_column_.py`](server/src/airunner_services/database/alembic/versions/d4184aabeff9_remove_allow_online_mode_column_.py:22) | "SQLite dev DBs can drift" comment |
| [`server/src/airunner_services/database/alembic/versions/2a7206a1ff79_add_expression_parameters_to_openvoice_.py`](server/src/airunner_services/database/alembic/versions/2a7206a1ff79_add_expression_parameters_to_openvoice_.py:46) | "SQLite doesn't support DROP COLUMN" comment |
| [`server/src/airunner_services/database/alembic/versions/01b52e38f588_add_long_running_project_tables.py`](server/src/airunner_services/database/alembic/versions/01b52e38f588_add_long_running_project_tables.py:31) | "Use add_table helper for SQLite compatibility" comment |

### 2.7 Dependencies to remove

| File | Dependencies |
|------|-------------|
| [`server/package_metadata.py`](server/package_metadata.py:28-29) | [`aiosqlite==0.21.0`](server/package_metadata.py:28), keep `sqlalchemy==2.0.38` and `psycopg[binary]>=3.2.0` |
| [`server/setup.py`](server/setup.py) | Likely references aiosqlite as well |

### 2.8 Test files

| File | SQLite references |
|------|-------------------|
| [`server/src/airunner_services/tests/functional/test_art_service_runtime_smoke.py`](server/src/airunner_services/tests/functional/test_art_service_runtime_smoke.py:50) | [`db_url = f"sqlite:///{tmp_path / 'art-service-runtime.sqlite'}"`](server/src/airunner_services/tests/functional/test_art_service_runtime_smoke.py:50) |
| [`server/src/airunner_services/tests/functional/test_art_service_runtime_probe.py`](server/src/airunner_services/tests/functional/art_service_runtime_probe.py) | Uses `reset_engine` from session.py |
| [`server/src/airunner_services/tests/functional/test_art_service_runtime_conditioned.py`](server/src/airunner_services/tests/functional/test_art_service_runtime_conditioned.py:90) | [`db_url = f"sqlite:///{tmp_path / 'art-service-runtime-probe.sqlite'}"`](server/src/airunner_services/tests/functional/test_art_service_runtime_conditioned.py:90) |

### 2.9 Alembic configuration

| File | Action |
|------|--------|
| [`server/src/airunner_services/database/alembic.ini`](server/src/airunner_services/database/alembic.ini:64) | Commented-out [`sqlalchemy.url = sqlite:///`](server/src/airunner_services/database/alembic.ini:64) — remove |

---

## PART 3: CLIENT-SIDE IndexedDB / Dexie REMOVAL

> **Important:** This is browser-side storage (via Dexie over IndexedDB), not server-side SQLite. Currently used as a **read-through cache** — all hooks gracefully fall back to direct server fetches when `db === null` (e.g., private browsing). Removing Dexie means all hooks become server-only fetches.

### 3.1 Entire `db/` directory to delete

| File | Purpose |
|------|---------|
| [`client/src/db/db.ts`](client/src/db/db.ts) | [`AiRunnerDb`](client/src/db/db.ts:66) class extending Dexie, all table definitions (conversations, messages, loras, embeddings, kbDocuments, civitaiModels, civitaiThumbnails, canvasDocuments, imageDates, images), [`getDb()`](client/src/db/db.ts:99) singleton |
| [`client/src/db/DbContext.tsx`](client/src/db/DbContext.tsx) | [`DbProvider`](client/src/db/DbContext.tsx:11) React context, [`useDb()`](client/src/db/DbContext.tsx:26) hook |
| [`client/src/db/SyncManager.ts`](client/src/db/SyncManager.ts) | [`SyncManager`](client/src/db/SyncManager.ts:16) class — generic cache-sync-from-server pattern |
| [`client/src/db/evict.ts`](client/src/db/evict.ts) | [`withQuotaEviction()`](client/src/db/evict.ts:23), [`clearAllCache()`](client/src/db/evict.ts:56) |

### 3.2 Entry point to modify

| File | What to change |
|------|----------------|
| [`client/src/main.tsx`](client/src/main.tsx:7) | Remove [`import { DbProvider }`](client/src/main.tsx:7), unwrap [`<DbProvider>`](client/src/main.tsx:12-14) from render tree |

### 3.3 Hooks to rewrite (remove Dexie dependency, become pure server-fetch)

| Hook file | Dexie usage |
|-----------|-------------|
| [`client/src/hooks/useConversations.ts`](client/src/hooks/useConversations.ts) | Uses [`useDb()`](client/src/hooks/useConversations.ts:16), [`SyncManager`](client/src/hooks/useConversations.ts:40), [`db.conversations`](client/src/hooks/useConversations.ts:40). Already has fallback path for `db === null`. |
| [`client/src/hooks/useConversationMessages.ts`](client/src/hooks/useConversationMessages.ts) | Uses [`useDb()`](client/src/hooks/useConversationMessages.ts:38), `db.messages.where()` caching. CachedMessage type from `../db/db`. |
| [`client/src/hooks/useLoras.ts`](client/src/hooks/useLoras.ts) | Uses [`useDb()`](client/src/hooks/useLoras.ts:17), [`SyncManager`](client/src/hooks/useLoras.ts:38), `db.loras`. CachedLora type from `../db/db`. |
| [`client/src/hooks/useEmbeddings.ts`](client/src/hooks/useEmbeddings.ts) | Uses [`useDb()`](client/src/hooks/useEmbeddings.ts:14), [`SyncManager`](client/src/hooks/useEmbeddings.ts:35), `db.embeddings`. CachedEmbedding type from `../db/db`. |
| [`client/src/hooks/useImageDates.ts`](client/src/hooks/useImageDates.ts) | Uses [`useDb()`](client/src/hooks/useImageDates.ts:12), `db.imageDates` bulkPut/bulkDelete |
| [`client/src/hooks/useKnowledgeBaseDocs.ts`](client/src/hooks/useKnowledgeBaseDocs.ts) | Uses [`useDb()`](client/src/hooks/useKnowledgeBaseDocs.ts:19), [`SyncManager`](client/src/hooks/useKnowledgeBaseDocs.ts:40), `db.kbDocuments`. CachedKbDocument type from `../db/db`. |
| [`client/src/hooks/useCivitaiDetailCache.ts`](client/src/hooks/useCivitaiDetailCache.ts) | Uses [`useDb()`](client/src/hooks/useCivitaiDetailCache.ts:14), `db.civitaiModels` get/put/delete |
| [`client/src/hooks/useCivitaiThumbnailCache.ts`](client/src/hooks/useCivitaiThumbnailCache.ts) | Uses [`useDb()`](client/src/hooks/useCivitaiThumbnailCache.ts:11), `db.civitaiThumbnails` get/put/bulkDelete |

### 3.4 Canvas state files to modify

| File | IndexedDB usage |
|------|-----------------|
| [`client/src/features/canvas/canvasStateUtils.ts`](client/src/features/canvas/canvasStateUtils.ts:162) | Imports [`getDb()`](client/src/features/canvas/canvasStateUtils.ts:162), [`loadPersistedStateAsync()`](client/src/features/canvas/canvasStateUtils.ts:244-254) reads from `db.canvasDocuments`, [`persistStateAsync()`](client/src/features/canvas/canvasStateUtils.ts:260-277) writes to `db.canvasDocuments`. **Keep the localStorage fallback** (already synchronous, works without IndexedDB). |
| [`client/src/features/canvas/state/coreState.ts`](client/src/features/canvas/state/coreState.ts) | Loads from IndexedDB on first mount ([line 34](client/src/features/canvas/state/coreState.ts:34)), persists to IndexedDB debounced ([line 50](client/src/features/canvas/state/coreState.ts:50)). **Remove IndexedDB calls, keep localStorage.** |
| [`client/src/features/canvas/state/document.ts`](client/src/features/canvas/state/document.ts:42-45) | Deletes canvas document from IndexedDB via [`getDb()`](client/src/features/canvas/state/document.ts:44). **Remove the IndexedDB delete.** |

### 3.5 Debug panel to remove or repurpose

| File | Dexie usage |
|------|-------------|
| [`client/src/components/shared/CacheDebugPanel.tsx`](client/src/components/shared/CacheDebugPanel.tsx) | Entirely based on [`useDb()`](client/src/components/shared/CacheDebugPanel.tsx:29), [`db[t]`](client/src/components/shared/CacheDebugPanel.tsx:44) table counts, [`clearAllCache()`](client/src/components/shared/CacheDebugPanel.tsx:61). **Delete or repurpose** as a server-health panel. |

### 3.6 TypeScript types to clean up

| File | What to change |
|------|----------------|
| [`client/src/types/api.ts`](client/src/types/api.ts) | Check for any Dexie-related imports or types |

### 3.7 Dependencies to remove

| File | Dependency |
|------|-----------|
| [`client/package.json`](client/package.json:14) | [`"dexie": "^4.4.3"`](client/package.json:14) |

---

## Summary: File Count

| Category | Files to DELETE | Files to MODIFY |
|----------|:--------------:|:---------------:|
| **Electron** — entire `electron/` directory | ~4 core + hundreds in `resources/` | — |
| **Electron** — build/packaging scripts | 2 | 1 |
| **Electron** — server helpers | 0 | 1 |
| **Electron** — documentation | 0 | 1 |
| **SQLite** — engine/connection | 0 | 1 |
| **SQLite** — configuration | 0 | 3 |
| **SQLite** — session/setup | 0 | 2 |
| **SQLite** — migration helpers | 0 | 2 |
| **SQLite** — alembic migrations | 0 | ~15 |
| **SQLite** — dependencies | 0 | 2 |
| **SQLite** — tests | 0 | 3 |
| **IndexedDB/Dexie** — `db/` directory | 4 | — |
| **IndexedDB/Dexie** — entry point | 0 | 1 |
| **IndexedDB/Dexie** — hooks | 0 | 8 |
| **IndexedDB/Dexie** — canvas | 0 | 3 |
| **IndexedDB/Dexie** — debug panel | 1 | 0 |
| **IndexedDB/Dexie** — dependencies | 0 | 1 |

---

## Recommended Execution Order

```mermaid
flowchart TD
    A[1. Delete electron/ directory] --> B[2. Remove electron build/packaging scripts]
    B --> C[3. Update server helpers for AIRUNNER_STATIC_DIR]
    C --> D[4. Update README.md documentation]
    D --> E[5. Remove aiosqlite from dependencies]
    E --> F[6. Rewrite database/conf to PostgreSQL-only]
    F --> G[7. Remove SQLite helpers from engine.py, session.py, setup_database.py]
    G --> H[8. Clean up migration helpers (column.py, foreign_key.py)]
    H --> I[9. Clean up alembic migration files (remove SQLite dialect branches)]
    I --> J[10. Update test files to use PostgreSQL test DB]
    J --> K[11. Delete client/src/db/ directory]
    K --> L[12. Remove DbProvider from main.tsx]
    L --> M[13. Rewrite all 8 hooks to be pure server-fetch]
    M --> N[14. Clean up canvas persistence (remove IndexedDB, keep localStorage)]
    N --> O[15. Remove/repurpose CacheDebugPanel]
    O --> P[16. Remove dexie from client/package.json]
    P --> Q[17. npm install to update lockfiles]
```
