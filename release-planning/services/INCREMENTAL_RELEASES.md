# Incremental service releases

Owner direction, 2026-11-03: release small usable service increments through
CI/CD. The original issue inventory and SRV architecture remain the project
backlog. A release is complete when its own declared contract is delivered and
verified; the project is complete only when all retained work is resolved.

## Release slices

| Slice | Delivered contract | Blocking evidence | Later work that does not block this slice |
|---|---|---|---|
| R0: Native runtimes | Independently versioned CPU sidecars and optional Linux CUDA SM120a profile | Reviewed source and licenses; native OS startup; GPU acceptance for the CUDA asset; complete checksummed immutable assets | Full application, Docker and multimodal acceptance |
| R1: Headless LLM MVP | Linux service package, authenticated API, one supported native LLM backend, SQLite persistence, streaming, cancellation and clean worker shutdown | Fresh installed-artifact startup; authenticated real-model answer through the normal API; unauthorized request rejection; actual streamed content; cancellation and worker cleanup; SQLite migration/restart/data preservation; exact-source CI and downloaded package identity | ART, audio, embeddings/RAG, PostgreSQL, Docker, Windows application packaging, exhaustive model benchmarks and apt repository publication |
| R2: Audio and retrieval | Separate small releases for verified STT, TTS and document/retrieval capabilities; each declares its own supported backend and formats | Installed-artifact success and error paths for the capability being added; relevant auth, isolation, cancellation and persistence checks; rights-cleared fixtures and reported quality measurements | Other modalities and unrelated benchmark targets |
| R3: ART worker | Supported image-generation modes through the service | Actual selected model generation through the installed API; output dimensions/count/decode/persistence; unsupported-mode rejection; cancellation, resource admission and cleanup | Unrelated storage, audio and distribution work |
| R4: Distribution and optimization | Independently releasable Docker, PostgreSQL, apt delivery and measured performance improvements | Each selected distribution/database path passes its own artifact and upgrade checks; each optimization includes comparable before/after measurements | Other unfinished roadmap items |

R1 is a target contract, not a claim that the current CORE package already
supports model execution. Close its native import/packaging gaps before shipping
that contract. Use the existing reviewed CORE dependency closure where sufficient;
do not pull the full ML stack into R1 without a demonstrated runtime requirement.
A verified CUDA asset may be optional and separately installed; R1 does not need
to bundle every accelerator or guarantee an unmeasured latency target.

## CI/CD contract

1. Keep pull requests small and tied to one shipped capability or defect. Run
   deterministic unit, API, migration and packaging contracts for affected paths.
2. Build a source-bound candidate on the default branch using reviewed pinned
   inputs. Automatically install it on an isolated clean target and run the
   selected slice's artifact acceptance. Reuse unchanged input review evidence.
3. Promote the exact passing source and artifact set with an unused annotated
   version tag and an immutable GitHub release. Verify downloaded bytes, notices,
   source identity and checksums. Do not rebuild different bytes after acceptance
   or append new assets to a published immutable release.
4. Publish supported capabilities, measured results, known limitations and exact
   exclusions with each release. Unavailable capabilities return explicit errors;
   their routes or extras must not imply that the backend shipped successfully.
5. Run broad quality, latency and hardware matrices independently of the fast
   release lane. A confirmed regression in a shipped contract blocks its next
   release; unfinished future capabilities and unmeasured performance ambitions
   stay in their own milestones. Never turn skipped, quarantined or deferred work
   into a passing result.

No new human approval gate is introduced. Existing auth, isolation, data
preservation, source review, licenses and owned-process boundaries remain in
force. The owner has authorized commit, push, merge, tag and release.

## Work in progress and tracking

Keep one application release slice active at a time. Parallel workers may prepare
future slices, but their incomplete work does not expand the active release's
exit criteria. Finish R0 already in publication, then concentrate integration and
acceptance on R1. Do not add a new prerequisite without showing that its absence
breaks the active slice's declared contract.

Use release milestones and linked Kanban cards. Retain existing subsystem issues
and attach follow-up evidence there; do not close an entire subsystem issue merely
because one release slice shipped. Record the merged SHA, tag, release URL,
local checks, CI checks, installed-artifact checks and exclusions per release.
Mattermost notification of whole-project completion remains reserved for actual
completion of the retained project scope.
