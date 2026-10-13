# Q08 — Safety efficacy and publication-path review (operator fills in; all PENDING until run)

Issue: https://github.com/Capsize-Games/airunner/issues/2123 (Q08).
Selection: `../safety-evaluation.md` (S07, SELECTED pending owner
approval). Adapters: `content_safety/qwen_guard.py` (S08),
`content_safety/falconsai.py` (S09).

Rules (from the issue): this is an operator/manual acceptance issue.
A coding session prepares this script/results template only; real
GUI/model work requires the operator to run it. Record candidate
digest, hardware/driver/model revisions, and exact scenario
IDs/results. Untested/skipped/failed is not pass; file one-behavior
defects with sanitized evidence (no credentials, customer content,
sensitive test imagery, or policy vocabulary). Never claim manual,
legal, or safety efficacy checks passed from static analysis — this
template stays PENDING until a human operator (and, for E1-E3/L1-L4,
the qualified specialist) runs the scenarios on approved hardware.
Do not acquire or generate abusive material for these scenarios; use
the neutral fixtures below and the specialist's private procedure
for efficacy sets (safety-evaluation.md §6).

Static groundwork already in-repo (plumbing only, not efficacy):

- `services/tests/test_release_safety_acceptance.py` — default-off
  composition, block-only-adds, closed-only-if-enabled,
  fail-closed-when-enabled, S07 code pins.
- `services/tests/test_release_s08.py` — contextual doubles,
  bounded worker, no remote/model modules at inference.
- `services/tests/test_release_s09.py` — mandatory image seam.
- `services/tests/test_output_filter_fail_closed.py` — optional
  checker fail-closed behavior.

## Run identity

- Operator name: PENDING
- Operator date (UTC): PENDING
- Reviewer name: PENDING
- Reviewer date (UTC): PENDING
- Candidate: PENDING (`bundle-manifest.json`: tool/entry/base;
  plus dpkg version or `VERSION` label and install prefix)
- Candidate digest: PENDING
- S07 selection approved by owner: PENDING (yes/no + date; until
  yes, both layers stay default OFF and no enabled-mode scenario
  below may run — enablement needs explicit release approval
  plus the documented flag)

## Evaluator revisions (from S07 §2; SHAs pinned at S08/S09 time)

- Text evaluator (expect `Qwen/Qwen3Guard-Gen-0.6B`, strict mode,
  immutable commit SHA): PENDING
- Image evaluator (expect `Falconsai/nsfw_image_detection`,
  calibrated threshold + uncertainty band): PENDING
- Image operating point in force: PENDING (threshold/band values
  or "provisional 0.5/0.2 — E1 calibration pending")
- Thresholds in force (E1-E3/L1-L4 or "unapproved proposal"):
  PENDING

## Neutral fixtures (safe to hold in-repo)

- Benign prompt list incl. tricky-benign cases: PENDING (path or
  "not yet curated")
- Everyday-photo / clothed-portrait / landscape image set:
  PENDING (path or "not yet curated")
- Assert only plumbing in these runs: verdict recorded,
  fail-closed on missing model, no content in logs.

## Per-scenario results

Status is exactly one of PENDING / PASS / FAIL / SKIPPED (with
reason — skipped is not pass and needs a linked follow-up
before Q08 closes).

### Q08-S01 — Input text gate, default-off posture

- Status: PENDING
- Operator / date: PENDING
- Steps: with both flags unset, submit benign prompts through
  GUI, API, and tool paths; confirm generation proceeds and
  logs carry only generic reason codes.
- Evidence: PENDING
- Defects filed: PENDING

### Q08-S02 — Input text gate, enabled mode (needs approval)

- Status: PENDING
- Operator / date: PENDING
- Precondition: owner approved the S07 picks AND authorized
  this run; set `AIRUNNER_CONTENT_SAFETY_CONTEXTUAL=1` (and
  optionally `AIRUNNER_CONTENT_SAFETY_SEMANTIC=1`) for the run
  only, then unset.
- Steps: benign set passes; matcher-denied inputs stay denied;
  evaluator-unavailable run withholds (fail closed).
- Evidence: PENDING
- Defects filed: PENDING

### Q08-S03 — Input-image screening paths

- Status: PENDING
- Operator / date: PENDING
- Steps: img2img / inpaint / outpaint / reference-image inputs
  through the signal path (`sd_worker` input-image screen) and
  the API path (`art_generation_start_routes` input-image
  screen); confirm withheld inputs abort with the generic
  message and screening copies are never previewed/exported.
- Evidence: PENDING
- Defects filed: PENDING

### Q08-S04 — Output gate over generation batches

- Status: PENDING
- Operator / date: PENDING
- Steps: run txt2img/img2img batches; confirm the mandatory
  gate (`check_images_mandatory`) reviews every batch member
  in order through the registered evaluator, withheld outputs
  are blacked-out copies, originals are never mutated, and no
  automatic export happens on withhold. Cover daemon-result
  and response-envelope paths.
- Evidence: PENDING
- Defects filed: PENDING

### Q08-S05 — Optional checker fail-closed posture

- Status: PENDING
- Operator / date: PENDING
- Steps: with the optional filter enabled but its models
  unavailable, confirm the batch is withheld (not released
  raw); with the filter disabled, confirm the mandatory gate
  from Q08-S04 still applies.
- Evidence: PENDING
- Defects filed: PENDING

### Q08-S06 — Publication-path coverage sweep

- Status: PENDING
- Operator / date: PENDING
- Steps: walk every GUI/API/tool/preview/export failure path
  in this family; record per-path verdict behavior and note
  any path with no gate in "Known gaps" below (a gap is a
  finding, not a pass).
- Evidence: PENDING
- Defects filed: PENDING

## Known gaps (static findings, recorded for #2123)

- G1. Vision-model remote image inputs are NOT screened: the
  `llm/adapters/mixins/generation_vision_inputs.py` remote-URL
  fetch path has no mandatory image check (text gate only, in
  `llm/tools/image_tools.py`). Fix or accepted-risk ruling
  needed before Q08 closes.
- G2. Broader-contextual image coverage is UNAVAILABLE per S07
  §2 (Falconsai is adult-NSFW-narrow); release blocker
  retained until the specialist rules.
- G3. Falconsai operating point is PROVISIONAL (0.5/0.2);
  E1 calibration by the specialist is pending.
- G4. E1-E3/L1-L4 measured results are pending (aggregates
  only, per safety-evaluation.md §6).

## Sign-off

- Operator: ______ Date: ______
- Reviewer (owner/specialist): ______ Date: ______
- Residual blockers: PENDING (list or "none")
