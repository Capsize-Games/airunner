# Fleet audit: airunner product boundary and shared-platform plan

Issue: Capsize-Games/airunner#2233 (fleet parent Capsize-Games/hq#24,
index hq#36). Base: `742a686c2`, branch `batch8/audit`, plus the
uncommitted wave/batch stack (`debian/`, companion `llm/`,
content-safety additions) present in the worktree — `debian/` in
particular is not at base.
Date: 2026-10-08. Planning only: no code, CI, or packaging changed.

## 1. Canonical identity and boundary

- GitHub: `Capsize-Games/airunner` (public; keeps name, history,
  stargazers, PyPI package per #2199). License: GPL-3.0-only
  (`LICENSE`, `RELICENSING.md`, issue #2058).
- Local checkouts: `Projects/airunnerdesktop` and
  `Projects/airunner_old` both exist; both point at this repo.
  `Projects/airunner` points at the `airunnerweb` remote.
  Reconciliation of the two `airunner`-repo checkouts is an open
  question (section 8).
- Separate remotes (verified via `gh api`): `airunnerweb`
  (private) and `airunner-common` (public, extracted in #2197).
- Product: single-user Qt desktop AI app (LLM, art, TTS, STT)
  plus its headless engine/daemon; not a shared platform.
- Runtime: Python 3.13, PySide6 GUI, CUDA 12.9.1 container base,
  torch cu129, llama.cpp sidecars (section 4).
- Deployment channels (all in-tree): PyPI (`services`, `native`,
  `.` via `pypi-dispatch.yml`), GHCR images (`:linux-headless`,
  `:linux-desktop`, `:latest` via `docker-release.yml`), Debian
  (`debian/`, `airunner-services` + systemd unit),
  `deployment/systemd/`, `packaging/linux/airunner.desktop`,
  `install.sh`, `docker-compose.yml`.
- Protected constraints: public history retained; content-safety
  policy bytes and release credentials stay out of shared
  packages/commits (S06 `release-policy` environment).

## 2. Tree structure (verified at base)

`src/airunner/` = Qt desktop app. `services/src/airunner_services/`
= headless engine (API, DB/migrations, runtimes, workers).
`native/src/airunner_native/` = launcher, crash handler,
repo-path resolution. `shared/` is untracked leftovers (0 tracked
files: stale pre-#2197 `airunner_common` outputs, not in git;
candidate for deletion); `airunner-common` is an external dep
(`airunner-common~=6.1` in `native/setup.py`).
Boundary enforcement: `scripts/check_import_boundaries.py` with
explicit per-entry allowlist (`scripts/import_boundary_allowlist.py`,
issue #2193). Repo-split context: #2185, #2198-#2201 (all open).

## 3. Dependency table (verified pins)

| Dependency | Current | Proposed authority | Note |
|---|---|---|---|
| python | 3.13 | product-local | CI env + Docker base |
| torch | 2.13.0+cu129 | product-local | setuptools must stay <82 (#2057) |
| PySide6 | 6.9.0 | product-local | desktop only (`setup.py`) |
| transformers / diffusers / sentence_transformers | 5.8.1 / 0.38.0 / 5.6.1 | product-local | services only |
| llama-cpp-python | 0.3.21 | product-local | native runtime sidecar |
| facehuggershield | 1.0.0 | product-local | supply-chain (#2036) |
| airunner-common | ~=6.1 | external (own repo) | extracted #2197 |
| CUDA base | 12.9.1-devel, digest-pinned | product-local | `Dockerfile` (#2036) |

Policy: shipped artifacts pin exact versions (#2200, #2191);
no ranges at install time. No `capsize-*` platform package is
imported anywhere in `src/`, `services/`, or `native/` (only
company-name mentions in legal/about docs).

## 4. Keep / migrate / retire decisions

- Qt desktop (`src/`): KEEP local. Product GUI; #2199 target state.
- Headless engine (`services/`, incl. all SQLAlchemy models and
  migrations): KEEP local pending #2198. Data-loss risk owner.
- Native launcher (`native/`): KEEP local. Product-specific.
- Settings/contracts/logging/layout/version: MIGRATED (#2197,
  `airunner-common`). Consumer: all three dists. No further action.
- Static metadata vendoring in each `setup.py`: KEEP (#2038,
  #2061; required for independent sdist/wheel builds).
- Policy data (`.dat`) + S06 provisioning: KEEP local, never
  shared. No consumer outside this product's release pipeline.
- Duplicated-infra scan vs `capsize-commons`, `capsize-platform`,
  `capsize-sites`, `@capsizellc/ui`, hq#33 native/game standards:
  no package-level duplication verified from this tree alone;
  no extraction proposed. See open questions.

Per the scope guard: this repository remains an independent
product boundary. No new extraction has a verified consumer,
so section 5 records only the completed one.

## 5. Extraction record

- `airunner-common` (#2197): DONE before this audit. API shape:
  installed package + `~=` pin. Rollback: re-pin to prior
  release. Provenance: git history of both repos.
- Future extractions: none approved. Each needs a consumer, API
  shape, compatibility test, and rollback/provenance plan
  before any PR (acceptance criterion, #2233).

## 6. Migration metadata

No `capsize.json` or `justfile` was added: none exists in-tree,
and the repo cannot yet support the contract (split phases in
#2185 incomplete; release orchestration #2200 and contributor
workflow #2201 still open). Revisit after #2198/#2199 land.

## 7. Open questions

1. Which checkout (`airunnerdesktop` vs `airunner_old`) is
   canonical, and what differs between them?
2. Which platform packages (if any) accept GPL-3.0-only code?
   This gates every future extraction direction.
3. hq#33 native/game standards text: does `native/` overlap it?
4. Before/after source-footprint numbers for hq#36: which
   measurement script is canonical?
5. Owner/maintainer identity for the hq#36 row update.

## 8. hq tracker updates

Not performed from this worktree (read-only audit). hq#36 row
and hq#24 workstream still need links to this file plus the
footprint measurements once Q4 is answered.
