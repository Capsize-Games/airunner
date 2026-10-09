# Safety evaluator selection (Linux v1) — DRAFT, not approved

Issue: https://github.com/Capsize-Games/airunner/issues/2094 (S07).
Parent: https://github.com/Capsize-Games/airunner/issues/2083.
Prereq: [R02](https://github.com/Capsize-Games/airunner/issues/2086)
(`release-planning/linux-v1/hardware-models.md` §2: policy models "Undecided").

Status: **DRAFT for owner/specialist approval. Nothing here is approved.**
Paper research only: model cards, licenses, published benchmarks. No model
was downloaded, no GPU was used, no abusive imagery was obtained, generated,
or published. No implementation in this issue.

## 1. Scope

Two required evaluator slots: (a) offline contextual text review of
generation requests (input side, complements the hash matcher and the
optional LLM-judge layer in `content_safety/semantic.py`); (b) offline
image review of generated output (output side, behind
`art/utils/nsfw_checker.py`, which today calls the SD safety checker and
fails closed). Per the issue, adult-NSFW detection or age estimation alone
is not sufficient: nudity-only detectors cannot satisfy slot (a) at all.

## 2. Candidate comparison

| Candidate | Slot | License / access | Local fit | Uncertainty | Key limitation |
|---|---|---|---|---|---|
| SD Safety Checker (incumbent) | image | Upstream license genuinely unspecified; RAIL-adjacent lineage | tiny CLIP add-on; runs where Z-Image runs | boolean only, no calibrated score | documented false positives; under-generalizes; evadable |
| NudeNet classifier+detector | image, nudity only | AGPL-3.0 (copyleft) | CPU/GPU, ONNX available | per-class scores + boxes | nudity-only; female-skewed training data; ~90% academic |
| LAION/OpenNSFW2-type CLIP/ResNet filter | image | varies; verify per weight release | lightweight, CPU-viable | probability score | same under-generalization class as incumbent |
| Llama Guard 3 (1B/8B) / 4 (12B multimodal) | text / text+image | Llama Community (gated, not OSI-approved, use-policy + MAU clause) | 1B small; 8B/12B heavy on shared 16 GB GPU | safe/unsafe + category codes | prompt-injection susceptible; single-benchmark scores vary (77-98% F1 by source) |
| ShieldGemma (2B text) / 2 (4B image) | text / image | Gemma Terms of Use (gated, restrictive) | 2B small; 4B vision needs GBs VRAM | Yes/No probability per policy | gated weights; narrow policy set on image side |
| API moderation (OpenAI, Azure, Perspective) | — | commercial / API | **excluded: needs network** | scores | violates the offline core; reference point only |

Sources: §7. "Local fit" is upstream-size reasoning, not measured here.

## 3. Selection status (approval required)

- Image slot: **retain SD Safety Checker as baseline, PENDING** legal
  review of its unspecified upstream license. NudeNet **rejected**
  (copyleft + nudity-only). OpenNSFW2-type **deferred** (no efficacy gain
  evidenced over incumbent for the extra integration).
- Contextual text slot: **no selection made — BLOCKER.** Candidates
  (Llama Guard, ShieldGemma, Qwen3-Guard-class) all need license approval
  plus a 16 GB shared-VRAM residency ruling before any efficacy review.
  Unsupported efficacy remains a release blocker per acceptance.
- No efficacy claim here rests on synthetic unit tests.

## 4. Proposed thresholds (require owner/specialist approval)

Effectiveness (measured by qualified parties on curated sets, §5):
E1 image recall >= 0.90 at FPR <= 0.10 on neutral sets; E2 text
classifier F1 >= 0.85 on an MLCommons-aligned set; E3 combined pipeline
recall >= 0.95 on the specialist abuse set. Latency/VRAM: L1 text check
p95 <= 500 ms CPU / <= 200 ms GPU per request; L2 image check p95 <= 2 s
per image on the 16 GB baseline; L3 safety stack <= 2 GB resident VRAM
alongside generation models (or explicit unload/reload ruling); L4 keep
the existing 5 s semantic-judge timeout (`semantic.py`).

## 5. Safe fixtures + specialist procedure

Safe neutral fixtures (this repo may hold): everyday-photo sets (e.g.
COCO-style), clothed-portrait and landscape images, benign prompt lists;
assert only pipeline plumbing (verdict recorded, fail-closed on missing
model, no content in logs). Sensitive evaluation: qualified authorized
parties curate abuse-case sets **off-repo**, run E1-E3/L1-L4, and return
**aggregate metrics only** — no imagery, no policy vocabulary in
source, issues, or logs. Results recorded in §6 when received.

## 6. Acceptance checklist + pending results

- [ ] PENDING owner/legal: SD checker license ruling; text-evaluator
  license + VRAM residency ruling; threshold (E1-E3/L1-L4) approval.
- [ ] PENDING specialist: E1-E3/L1-L4 measured results (aggregates only).
- [ ] PENDING release: text-slot selection or explicit unavailable stamp.
- Reviewer: ______ (owner/specialist) Date: ______ Operator: ______

## 7. Sources

SD checker FPs/license: diffusers PR #862 discussion; CompVis#239;
rail license note; SafeGen (arXiv 2404.06666) under-generalization.
NudeNet AGPL + ~90%: ai-engine.net comparison; bomberbot training-data
note. Llama Guard license/taxonomy/F1: PurpleLlama model cards; LG3-Vision
(arXiv 2411.10414); vdf.ai on-prem comparison; aitechconnect taxonomy
table. ShieldGemma terms/scores: official model card (ai.google.dev).
