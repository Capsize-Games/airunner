# Fix: Daemon Connection Timeout Due to Dev Build Token Mismatch

## Problem Summary

Running `./scripts/run_airunner_dev.sh` fails when the GUI attempts to submit art generation work to the local daemon. The daemon starts successfully and listens on `127.0.0.1:8188`, but the GUI client's `_wait_until_ready()` loop times out after 20 seconds with:

```
SDWorker Error: Timed out waiting for daemon to become ready
```

## Root Cause Analysis

### The Flow

1. GUI app (`App`) creates a [`GuiDaemonClient`](src/airunner/daemon_client/gui_daemon_client.py:35) with `detect_stale_dev_daemon=True` (set from `DEV_ENV`, which defaults to `1` in dev mode).

2. When art generation is requested, [`ensure_connected()`](src/airunner/daemon_client/gui_daemon_client.py:89) is called. Since the daemon isn't running, it launches a subprocess and enters [`_wait_until_ready()`](src/airunner/daemon_client/gui_daemon_client.py:559).

3. `_wait_until_ready()` polls the daemon's `/api/v1/health` endpoint. Once the daemon is up (at `12:42:58` in the user's log), health checks **succeed** — the daemon returns a valid JSON payload including `dev_build_token`.

4. However, [`_stale_dev_daemon_reason()`](src/airunner/daemon_client/gui_daemon_client.py:608) compares the client's expected dev build token against the daemon's reported token. **They never match.**

5. Since the stale check returns non-None, `_wait_until_ready()` continues polling — it never logs the mismatch, silently retrying until the 20-second startup timeout expires.

### The Dev Build Token Mismatch

There are **two separate implementations** of `current_dev_build_token()` that scan **different directory trees**:

| Component | File | Scanned Directory |
|-----------|------|-------------------|
| GUI client | [`src/airunner/dev_build_token.py`](src/airunner/dev_build_token.py:24) | `src/airunner/` (hardcoded to `Path(__file__).resolve().parent`) |
| Daemon | [`services/src/airunner_services/dev_build_token.py`](services/src/airunner_services/dev_build_token.py:24) | Repo root (walks up from `__file__` to find `pyproject.toml`) |

Additionally, the `_skip_path()` filters differ:

| | GUI client | Daemon |
|---|-----------|--------|
| Skipped dirs | `__pycache__`, `tests`, `vendor` | `.git`, `__pycache__`, `airunner.egg-info`, `build`, `dist`, `node_modules`, `tests`, `venv`, `vendor` |

**Result**: The GUI client generates a token based on the newest `.py` file in `src/airunner/`, while the daemon generates one based on the newest `.py` file in the entire repo (including `services/`, `api/`, `model/`, etc.). These tokens will virtually **never** match because:
- They scan different file sets
- The newest `.py` file across the entire repo is almost certainly not in `src/airunner/`

## Proposed Fix

### Strategy

Unify the dev build token generation so both the GUI client and the daemon scan the **same directory tree** (the repo root) with the **same skip logic**.

### Option A: Fix the GUI client to match the daemon (Recommended)

Update [`src/airunner/dev_build_token.py`](src/airunner/dev_build_token.py) to:

1. Add the `_find_repo_root()` helper (copy from the services version)
2. Change `_scan_source_tree(Path(__file__).resolve().parent)` to `_scan_source_tree(_find_repo_root(Path(__file__).resolve()))`
3. Update `_skip_path()` to include the same set of skipped directories as the services version (`.git`, `airunner.egg-info`, `build`, `dist`, `node_modules`, `venv`)

This makes the GUI client scan the entire repo, matching the daemon's behavior.

### Option B: Extract a shared implementation (Cleaner but larger refactor)

Create a single `current_dev_build_token()` function in a shared location (e.g., `airunner_model` or a new `airunner_common` package) and have both `src/airunner/dev_build_token.py` and `services/src/airunner_services/dev_build_token.py` import from it.

### Recommendation

**Option A** is the minimal, lowest-risk fix. The two files already have nearly identical code. Option A ensures the tokens match without requiring changes to the daemon or any import restructuring.

## Implementation Steps

### Step 1: Fix `src/airunner/dev_build_token.py`

- Add `_find_repo_root()` function matching the services version
- Update `_scan_source_tree` call to use `_find_repo_root(Path(__file__).resolve())`
- Update `_skip_path()` to include all directories from the services version

### Step 2: Verify

Run `./scripts/run_airunner_dev.sh` and confirm:
- No stale daemon detection during initial connection
- Art generation succeeds via daemon
- If source files change while the daemon is running, a new daemon is correctly recycled on next request

## Affected Files

| File | Change |
|------|--------|
| [`src/airunner/dev_build_token.py`](src/airunner/dev_build_token.py) | Add `_find_repo_root()`, update scan root, expand `_skip_path` |
| No changes to services daemon code | — |

## Risk Assessment

- **Low risk**: The dev build token is only used for detecting stale daemons in dev mode (`DEV_ENV=1`). It has no effect in production/bundled builds.
- The stale detection becomes **more accurate** because both sides now scan the same files.
- If `pyproject.toml` is not found, `_find_repo_root` falls back to `start.parent`, which would be the source directory — same as the current behavior. The daemon already handles this gracefully.
