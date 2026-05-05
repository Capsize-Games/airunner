# Deliverable-First Workflows

## Product Definition

AIRunner should be treated as a local AI workflow workbench.

The user asks for outcomes, not for intermediate tools. Chat, search,
STT, TTS, image generation, and coding are capabilities AIRunner uses to
produce durable artifacts.

The two primary product wedges are:

- Research Brief Builder
- Meeting-to-Deliverables

Coding remains important, but it moves behind the scenes. When a
workflow needs custom logic, AIRunner may create a helper project under
`~/.local/share/airunner/Projects`. That helper is an internal operator
asset, not the final product the user asked for.

## Workflow 1: Research Brief Builder

### Purpose

Take a research request, gather source material, capture evidence, and
produce a reviewable brief package.

### Expected Inputs

- Research question or topic
- Scope constraints
- Required outputs or decision context
- Optional source preferences or exclusions

### Output Package Contract

A research brief package should contain these durable artifacts:

- **Request envelope**: The original request, scope, constraints, and run
  metadata.
- **Source ledger**: The sources considered, their metadata, access time,
  and status such as accepted, rejected, or unresolved.
- **Evidence ledger**: Extracted facts, quotations, numeric claims, and
  each item's provenance.
- **Brief document**: Executive summary, supported findings, open
  questions, and recommended next actions.
- **Review metadata**: Confidence notes, gaps, and verification status.

### Validation Rules

- Every supported claim should point to evidence in the source ledger.
- Numeric facts should retain provenance and units.
- Unsupported or conflicting findings should remain visible as open
  questions rather than being silently collapsed into the summary.
- The final brief should be reviewable without reopening the original
  chat transcript.

### Storage And Retrieval Expectations

- Research artifacts should be stored as first-class workflow outputs.
- The system should be able to retrieve source, evidence, and brief data
  separately.
- Future retrieval should support reuse of evidence without rerunning the
  full workflow.

## Workflow 2: Meeting-to-Deliverables

### Purpose

Take meeting notes or transcripts and convert them into actionable,
editable deliverables.

### Expected Inputs

- Meeting transcript, notes, or audio-derived transcript
- Optional attendees, agenda, and context
- Optional desired output formats

### Output Package Contract

A meeting deliverable pack should contain these durable artifacts:

- **Meeting envelope**: Raw input references, participants, timestamps,
  and run metadata.
- **Structured extraction**: Decisions, owners, deadlines, risks,
  unresolved questions, and follow-up requirements.
- **Deliverable pack**: Action-item list, decision log, follow-up draft,
  and editable working documents.
- **Review metadata**: Approval state, low-confidence items, and edits
  made during review.

### Validation Rules

- Decisions, owners, and deadlines should be represented explicitly.
- Low-confidence or conflicting extractions should remain visible.
- Final deliverables should be editable and persistable outside chat
  history.
- The approved pack should preserve traceability back to the source
  meeting input.

### Storage And Retrieval Expectations

- Meeting input, structured extraction, and approved deliverables should
  be stored separately.
- AIRunner should be able to reopen and revise a deliverable pack without
  re-ingesting the original meeting input.
- Retrieval should support later workflows such as follow-up reminders or
  project planning.

## Hidden Coding And Helper Projects

When AIRunner needs code to finish a workflow, it may create a helper
project. That helper should be treated as workflow infrastructure.

Each helper project should eventually carry:

- A short purpose statement
- The workflow or artifact it supported
- An input contract
- An output contract
- Reuse notes
- Enough metadata to search before generating a new helper

The guiding rule is simple: users should ask AIRunner for outcomes such
as research briefs or meeting deliverables, not for one-off scripts.