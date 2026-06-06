# Hybrid Runtime Migration Guide

This guide captures the migration order, rollout gates, and stop conditions
for the hybrid AIRunner product.

The rule for this plan is simple: do not start the next slice until the
current gate is satisfied. Each phase has a cutover target, explicit issues,
and a stop condition that keeps the rewrite incremental instead of all at
once.

Scope note:
This migration plan covers the hybrid runtime refactor through daemon-backed
runtime boundaries, Linux bundle metadata, and CI alignment. It does not yet
deliver the final end-user packaging target of "install AIRunner, click run,
no system Python required". That productization work is tracked separately in
#82.

## Delivery Order

### Phase 0: Runtime Foundation

Scope:
- Define ownership boundaries between the app, daemon, runtime registry, and
  adapters.
- Stabilize the v2 API and IPC contract before any modality cutovers.

Issues:
- #51 Define runtime module layout and ownership boundaries
- #52 Define the v2 core API and IPC envelope
- #53 Add runtime registry and provider selection
- #54 Add local fallback adapters for current Python model managers
- #55 Add runtime contract and adapter tests
- #56 Refactor the existing daemon into a reusable core lifecycle service

Gate:
- Runtime contracts exist and are covered by tests.
- The daemon lifecycle is reusable outside the app process.
- The registry can select either local fallback or isolated runtimes.

Stop condition:
- Do not move any modality to an isolated runtime until the registry,
  adapters, and daemon lifecycle are stable.

### Phase 1: LLM First Cutover

Scope:
- Move local LLM inference to llama.cpp first.
- Use the LLM slice to prove the daemon, runtime registry, route migration,
  and GUI/daemon launch model.

Issues:
- #57 Extract local LLM orchestration from direct transformers inference
- #58 Implement a llama.cpp native binary launcher and client
- #59 Migrate LLM API routes and workers to the runtime client
- #60 Update model download and conversion flow for GGUF-first local LLMs
- #61 Add LLM load, cancellation, concurrency, and performance smoke tests
- #62 Add daemon control, status, and runtime health endpoints
- #63 Refactor daemon entrypoints to launch or connect to the daemon
- #64 Add a daemon client with auto-launch and reconnect behavior
- #65 Simplify workers so they stop owning model lifecycles

Gate:
- LLM requests route through the runtime client by default.
- Headless and GUI entrypoints can both connect to or auto-launch the daemon.
- Load, cancellation, concurrency, and runtime-health coverage exists.

Cutover criteria:
- GGUF llama.cpp is the primary local LLM path.
- Direct in-process transformers ownership is no longer the default request
  path.

Stop condition:
- Do not start STT until the daemon-backed launch model and runtime-health
  controls are proven by the LLM slice.

### Phase 2: STT Isolation

Scope:
- Separate audio capture from STT execution.
- Move STT execution into a whisper.cpp native binary client and validate
  timeout and recovery behavior.

Issues:
- #66 Separate audio capture and queueing from STT execution
- #67 Implement a whisper.cpp native binary launcher and client
- #68 Migrate STT API routes and workers to the runtime client
- #69 Add STT timeout, recovery, and live-audio smoke tests

Gate:
- Audio capture stays in-process, but STT execution runs through the runtime
  client.
- Timeout, crash recovery, and live-audio smoke coverage pass.

Cutover criteria:
- STT no longer executes directly inside the app worker graph.

Stop condition:
- Do not isolate art or TTS until STT proves the modality-specific runtime
  boundary and recovery model.

### Phase 3: Art And TTS Isolation

Scope:
- Move art inference and TTS synthesis into supervised Python runtimes.
- Refactor scheduling so art and TTS runtimes do not depend on app-owned model
  lifecycles.

Issues:
- #70 Move art inference into an isolated Python runtime
- #71 Move TTS synthesis into an isolated Python runtime
- #72 Refactor model and resource scheduling for out-of-process runtimes
- #73 Migrate art and TTS API routes and workers to runtime clients
- #74 Add art and TTS crash recovery and soak tests

Gate:
- Art and TTS execution paths run through daemon-backed runtime clients.
- Scheduler behavior no longer assumes in-process model ownership.
- Recovery and soak coverage exists for both modalities.

Cutover criteria:
- Art and TTS workloads can restart independently of the app.

Stop condition:
- Do not move to packaging and rollout hardening until all four modalities use
  the hybrid runtime model.

### Phase 4: Packaging, Security, Bundles, And CI

Scope:
- Lock down plugin loading and runtime filesystem boundaries.
- Split package profiles, render relocatable Linux bundles, and align CI with
  the new artifact graph.

Issues:
- #75 Replace unrestricted plugin loading with a manifest and allowlist model
- #76 Add local-only runtime security boundaries and explicit runtime
  directories
- #77 Split dependency and package profiles for hybrid deployment
- #78 Build Linux desktop and daemon bundle and service templates
- #79 Refactor CI for native binary bundles, and contract tests

Gate:
- Runtime config, log, cache, socket, and model directories are explicit.
- Linux installers, service templates, Docker builds, and release workflows all
  understand the new profile and bundle layout.

Cutover criteria:
- Linux desktop and daemon delivery artifacts can be built from explicit
  profile lists and relocatable bundle metadata.

Stop condition:
- Do not declare the migration complete until the rollout guide and issue tree
  are documented and auditable.

### Phase 5: Rollout Guide And Handoff

Scope:
- Freeze the migration order, acceptance gates, and implementation checklist.
- Make future feature work call out phase impact and cutover risk explicitly.

Issues:
- #80 Write migration docs, rollout gates, and a phased implementation
  checklist

Gate:
- The sequence, gates, and stop conditions are documented.
- Future issue intake includes rollout and dependency context.

Cutover criteria:
- The team can resume the plan from the issue tree and docs without reconstructing
  the architecture from memory.

## Post-Migration Productization

The completed migration issue tree establishes the runtime architecture needed
for end-user distribution, but it does not by itself ship AIRunner as a
consumer-ready desktop application.

That follow-on product requirement was implemented in #82: AIRunner now has a
native launcher, embedded-Python bundle assembly, pinned bundled binaries,
and installable Linux and Windows artifacts with installer validation.

That delivered scope includes:
- a native launcher/bootstrapper built for each target platform
- embedded Python bundled inside the install artifact
- pinned `llama.cpp` and `whisper.cpp` binaries included in the package
- installable Linux and Windows artifacts with fresh-machine smoke coverage

This distinction matters:
- the hybrid migration is complete as an architecture and runtime-boundary
  project
- end-user distribution was separate packaging and release-engineering work
  built on top of that runtime foundation

## Rollout Gates Summary

| Gate | Required outcome | Cutover target |
|------|------------------|----------------|
| Foundation | Registry, adapters, IPC, and daemon lifecycle are stable | Safe runtime abstraction |
| LLM | llama.cpp path is primary and daemon-backed | LLM cutover |
| STT | whisper.cpp client path is live with recovery coverage | STT cutover |
| Art/TTS | supervised Python runtimes own modality execution | Art/TTS cutover |
| Packaging/CI | profiles, bundles, service templates, and CI artifacts match the runtime graph | Linux bundle and CI alignment |
| Rollout docs | sequence and gates are durable and auditable | Migration handoff |
| End-user distribution | embedded runtime, native launcher, and installer artifacts exist | No-Python product delivery |

## Implementation Checklist

### Epic #45: Runtime Abstraction And IPC Foundation

- [x] #51 Define runtime module layout and ownership boundaries
- [x] #52 Define the v2 core API and IPC envelope
- [x] #53 Add runtime registry and provider selection
- [x] #54 Add local fallback adapters for current Python model managers
- [x] #55 Add runtime contract and adapter tests
- [x] #56 Refactor the existing daemon into a reusable core lifecycle service

### Epic #47: Local LLM Runtime Migration

- [x] #57 Extract local LLM orchestration from direct transformers inference
- [x] #58 Implement a llama.cpp native binary launcher and client
- [x] #59 Migrate LLM API routes and workers to the runtime client
- [x] #60 Update model download and conversion flow for GGUF-first local LLMs
- [x] #61 Add LLM load, cancellation, concurrency, and performance smoke tests

### Epic #46: Core Daemon App Refactor

- [x] #62 Add daemon control, status, and runtime health endpoints
- [x] #63 Refactor daemon entrypoints to launch or connect to the daemon
- [x] #64 Add a GUI daemon client with auto-launch and reconnect behavior
- [x] #65 Simplify App, MainWindow, and WorkerManager so they stop owning model
  lifecycles

### Epic #48: STT Native Runtime Migration

- [x] #66 Separate audio capture and queueing from STT execution
- [x] #67 Implement a whisper.cpp native binary launcher and client
- [x] #68 Migrate STT API routes and workers to the runtime client
- [x] #69 Add STT timeout, recovery, and live-audio smoke tests

### Epic #49: Art And TTS Python Runtime Isolation

- [x] #70 Move art inference into an isolated Python runtime
- [x] #71 Move TTS synthesis into an isolated Python runtime
- [x] #72 Refactor model and resource scheduling for out-of-process runtimes
- [x] #73 Migrate art and TTS API routes and workers to runtime clients
- [x] #74 Add art and TTS crash recovery and soak tests

### Epic #50: Security, Packaging, CI, And Rollout Hardening

- [x] #75 Replace unrestricted plugin loading with a manifest and allowlist
  model
- [x] #76 Add local-only runtime security boundaries and explicit runtime
  directories
- [x] #77 Split dependency and package profiles for hybrid deployment
- [x] #78 Build Linux desktop and daemon bundle and service templates
- [x] #79 Refactor CI for native binary bundles, and contract tests
- [x] #80 Write migration docs, rollout gates, and a phased implementation
  checklist

### Follow-On Epic #82: No-Python End-User Distribution

- [x] Define the distribution contract and bundle manifest for end-user
  installs
- [x] Build a native AIRunner launcher/bootstrapper
- [x] Produce pinned llama.cpp and whisper.cpp binaries for Linux and Windows
- [x] Assemble embedded Python and AIRunner into installable bundles
- [x] Add installer/runtime smoke tests and release validation

## Operational Rule For Future Work

Any new feature or migration change should answer three questions before it is
scheduled:

1. Which phase or gate does it change?
2. Does it advance the current cutover or reopen an earlier stop condition?
3. Which issue or rollout checklist item must be updated with the new plan?
