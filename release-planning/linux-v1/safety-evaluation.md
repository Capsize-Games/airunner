# Safety evaluator selection (Linux v1) — SELECTED, pending owner approval

Issue: https://github.com/Capsize-Games/airunner/issues/2094 (S07).
Parent: https://github.com/Capsize-Games/airunner/issues/2083.
Prereq: [R02](https://github.com/Capsize-Games/airunner/issues/2086)
(`release-planning/linux-v1/hardware-models.md` §2: policy models "Undecided").

Status: **SELECTED — this is the researcher's firm recommendation, not an
approval.** Owner approval of the picks (§2) and qualified-specialist
measurement (§6) are still required before release. Until then the code
stays exactly as it is: both safety layers default OFF and the S08/S09
seams keep their current behavior. S08/S09 remain seams; no adapter is
implemented in this issue.

Paper research only (lookups dated 2026-10-09): Hugging Face model API
metadata (`cardData.license`, parameter counts), model cards, READMEs,
papers, and vendor technical reports, plus byte sizes via HTTP HEAD. No
model was downloaded, no GPU was used, no abusive imagery was obtained,
generated, or published. Sizes marked "computed" are 2 bytes/param (bf16)
or 4 bytes/param (fp32) from verified parameter counts, not downloads.

## 1. Scope

Two required evaluator slots: (a) offline contextual text review of
generation requests (input side, complements the hash matcher and the
optional LLM-judge layer in `content_safety/semantic.py`); (b) offline
image review of generated output (output side, behind
`art/utils/nsfw_checker.py` and the `content_safety/image_verdict.py`
seam). Per the issue, adult-NSFW detection or age estimation alone is
not sufficient: nudity-only detectors cannot satisfy slot (a) at all,
and slot (b) needs more than a nudity boolean to be fully satisfied
(see §2: the broader-contextual image requirement is marked unavailable).

Seam contracts the picks must fit (already implemented, unchanged here):

- Text (`semantic.py`, S08): `Judge = dict[str, str] -> SemanticVerdict`
  via `set_evaluator` (falls back to the `set_judge` seam). Fail-closed:
  only an explicit allowed verdict allows; unavailable, timeout (5 s),
  error, or ambiguity all deny. One shared worker (`CONTEXTUAL_MAX_WORKERS
  = 1`). Gate order in `content_safety_gate.py` (matcher, then optional
  semantic, then required contextual) is unchanged.
- Image (`image_verdict.py`, S09): `ImageEvaluator` maps one batch to
  per-item `True` (withhold) / `False` (release) / `None` (uncertain,
  withheld); missing evaluator, errors, and batch-length mismatches all
  withhold. A probability output lets the S09 adapter express uncertainty;
  a boolean-only model cannot.

Out of scope: the optional user-toggled `nsfw_filter` path keeps its
existing model and flow; this selection governs the mandatory slots only.

## 2. Recommendation

- Text slot (a): **SELECT `Qwen/Qwen3Guard-Gen-0.6B`** (Apache-2.0,
  752M params, ~1.5 GB bf16 computed, ungated). Step-up within the same
  family pre-approved for S08 to adopt on measurement grounds only:
  **`Qwen/Qwen3Guard-Gen-4B`** (Apache-2.0, 4.41B params, ~8.8 GB bf16
  computed) if the specialist finds the 0.6B below E2.
- Image slot (b): **SELECT `Falconsai/nsfw_image_detection` as a NARROW
  evaluator** (Apache-2.0, 86M params, 343 MB safetensors measured,
  ungated), with its adult-NSFW-only coverage explicitly recorded as a
  limitation. **Broader-contextual image coverage (violence, self-harm,
  hate, weapons beyond nudity/sexual content): no selectable candidate —
  marked UNAVAILABLE, release blocker retained.** The incumbent SD
  safety checker is **SUPERSEDED** for the mandatory slot (§3.2).

## 3. Evidence

### 3.1 Text/contextual candidates

| Candidate | Size (verified) | License / access (verified) | Offline / airgap | Efficacy evidence (published, not measured here) | Seam fit | Verdict |
|---|---|---|---|---|---|---|
| Qwen3Guard-Gen-0.6B | 752M params; ~1.5 GB bf16 (computed); Q4 ~0.5 GB | Apache-2.0 (`cardData.license`, card); ungated; 177k downloads observed | Single Hub download, then fully local; CPU-plausible; no telemetry | Vendor tech report (arXiv:2510.14276) Tables 2-3: English prompt F1 avg 88.1 vs PolyGuard-Qwen-7B 87.0, WildGuard-7B 85.8, NemoGuard-8B 82.9, LG3-8B 79.4, LG4-12B 75.9; English response F1 avg 82.0, top of the same table. Structured `Safety: Safe/Unsafe/Controversial` + `Categories:` output (9 categories incl. jailbreak); 119 languages. CAVEATS: vendor-reported; averages use the optimal strict/loose mode per benchmark; weak spots exist (OpenAIMod-prompt strict 66.5 vs LG3-8B 79.5) | Structured verdict parses to allow / deny / ambiguous-deny; strict mode (Controversial→unsafe) matches fail-closed; transformers ≥4.51 (pinned 5.8.1 OK); ≤128 new tokens plausibly inside the 5 s budget (reasoned, unmeasured) | **SELECT** |
| Qwen3Guard-Gen-4B | 4.41B params; ~8.8 GB bf16 (computed); Q4 ~2.5 GB | Apache-2.0; ungated; 63k downloads observed | Local; GPU-resident (no CPU expectation) | Same report: prompt 89.3 / response 83.7; same caveats as 0.6B | Same adapter as 0.6B (same output format) | **Step-up option** (S08 adopts only if 0.6B misses E2) |
| Granite Guardian 3.1-2b | 2.53B params; ~5 GB bf16 (computed) | Apache-2.0 (`cardData.license`, card); ungated | Local; GPU-preferred at bf16 | Own card: aggregate harm F1 0.75 (ToxicChat 0.60, OAI-mod 0.68, HarmBench 0.80, xstest_RR 0.43); jailbreak recall 0.90 on ToxicChat; paper arXiv:2412.07724. Card states English-only ("only trained and tested on English data") | Instruction-following guard; adapter-parseable verdicts; 3.4x the params of the pick | Runner-up (permissive license + IBM paper, but larger, English-only, weaker public-suite F1s) |
| Llama Guard 3 1B | 1.5B params; ~3 GB bf16 (computed); INT4 variant per card | `llama3.2` (gated Llama Community: use policy + MAU clause, not OSI-approved) | Local after gated access; airgap friction (account + ToU acceptance) | PurpleLlama card, internal MLCommons test: English F1 0.899 / FPR 0.090 (INT4 0.904/0.084); 13-hazard MLCommons taxonomy; 8 languages; prompt+response. Card limitations: prompt-injection susceptible; factual categories (S5/S8/S13) need larger systems | Generative safe/unsafe + S-codes; parses cleanly; smallest gated option | Alternative iff owner accepts Llama terms |
| ShieldGemma 2B | 2.6B params; ~5 GB bf16 (computed) | Gemma Terms of Use (gated, restrictive) | Same gating friction as Llama Guard | Paper arXiv:2407.21772 (SG-9B +10.8% AU-PRC vs LlamaGuard1); 4 harm types (narrower taxonomy than LG3/Qwen/Granite) | Yes/No probability per policy | Alternative (narrower taxonomy + gated) |
| WildGuard 7B | 7.2B params; ~14.5 GB bf16 (computed) | Apache-2.0 (`cardData.license`); paper arXiv:2406.18495 | Local in principle | Strong third-party numbers (Qwen report: prompt 85.8 / response 79.9) | Fine, but 7B cannot co-reside on the 16 GB baseline alongside generation (GPT-OSS 20B 4-bit alone is ~14 GB per R02 §3) | Reject on footprint (an unload/reload ruling could revive it) |
| Reuse shipped chat LLM as judge (Qwen3.5-9B via `make_llm_judge`) | 0 new weights | Already-shipped terms | Local | No published safety-evaluation numbers for this configuration; uncalibrated SAFE/UNSAFE prompting; needs the chat model resident during art generation (shared-VRAM contention); prompt-injection susceptible | Already supported by the seam today | Deferred; stays available as defense-in-depth, not the required evaluator |
| Detoxify-class toxicity BERTs | ~100-300 MB | Apache-2.0 | Local, CPU-trivial | Toxicity-only: no policy categories, no jailbreak handling | N/A | Reject (insufficient coverage) |
| API moderation (OpenAI, Azure, Perspective) | — | Commercial / API | **Excluded: needs network** | Scores | N/A | Excluded (violates the offline core; reference only) |

Why Qwen3Guard-Gen-0.6B wins: it is the only text candidate that is
simultaneously permissively licensed (Apache-2.0, GPL-3.0-compatible,
no NC clause, no gating), small enough for CPU/offline use (0.75B),
multilingual (119 languages for a chat product), structurally matched
to the fail-closed seam (tri-class verdict with an explicit middle
state that maps to deny-as-ambiguous), and supported by published
benchmark evidence competitive with 7-8B guards. No other candidate
combines all five; §4 records what is given up versus each alternative.

### 3.2 Image candidates

| Candidate | Size (verified) | License / access (verified) | Offline / airgap | Efficacy evidence | Seam fit | Verdict |
|---|---|---|---|---|---|---|
| Falconsai/nsfw_image_detection | 86M params (F32); 343 MB safetensors (measured) | Apache-2.0 (card front-matter + `cardData.license`); ungated | Fully local; CPU ms-scale (reasoned, unmeasured); ~0 VRAM | **ONE vendor number only**: the card's training log reports `eval_accuracy` 0.980 on an undisclosed split of the proprietary 80k-image set — no benchmark name, no recall/FPR breakdown, no published operating point. Training data proprietary and undisclosed (bias unauditable). Binary normal/nsfw only | `image-classification` pipeline on the pinned transformers stack (no new deps); probability output enables a threshold + uncertainty band (`None` → withheld), which boolean models cannot express | **SELECT (narrow)** — coverage gap explicit, E1 measurement mandatory |
| SD Safety Checker (incumbent) | 1.2 GB `.bin` fp32 (measured); legacy format, no safetensors | **Unspecified** (`cardData.license` null, verified 2026-10-09); RAIL-adjacent lineage | Local where Z-Image runs | Documented false positives (diffusers PR #862; CompVis#239); under-generalization (SafeGen, arXiv:2404.06666); boolean-only, no calibrated score | Already adapted in `nsfw_checker.py`, but boolean-only cannot express uncertainty | **SUPERSEDE** for the mandatory slot (worse license story, 3.5x the bytes, worse semantics than the pick) |
| LlavaGuard-v1.2-0.5B-OV-hf | 894M params (F16); ~1.8 GB (computed) | **Research-gated ToU, no license tag**: card requires accepting terms stating the model is "mainly targeted toward researchers and is meant to be used in research", with access-revocation rights. Code repo is Apache-2.0 but that does not license the weights; base (`lmms-lab/llava-onevision-qwen2-0.5b-ov`) is Apache-2.0 but the finetune weights' terms are the gating ToU | Gated download; GPU-needed for latency (third-party CPU reports of 10-30 s/image) | Paper (arXiv:2406.05113) tables cover the 7B/13B/34B v1.0 family only (held-out Acc ~89-91% vs NSFW-1/2 ~50-51%, Q16 69.7%; 9-category taxonomy O1-O9). **No published numbers for the 0.5B-OV variant**; 518 downloads observed | Generative Safe/Unsafe + category + rationale; parseable, but a 32K-context VLM per image is the heaviest integration here | Deferred (research terms bar paid-product shipment; 0.5B unevidenced). Revisit if the authors publish clear weights terms |
| ShieldGemma-2-4B (image) | 4B-class per vendor announcement (~8 GB bf16); Hub metadata auth-blocked this session (gated) | Gemma Terms of Use (gated, restrictive) | Gated; GBs of VRAM | Vendor-reported image-safety results per the official card (ai.google.dev, as previously cited); gated weights could not be independently checked here | Yes/No probability per policy | Deferred (terms + footprint) |
| Llama Guard 4 12B (multimodal) | 12B | `other` (Llama 4 Community) | 12B cannot co-reside on 16 GB | Vendor card | Multimodal prompt+response+image | Reject (footprint + terms) |
| NudeNet classifier+detector | CPU/GPU, ONNX available | AGPL-3.0 (copyleft: combined work must go out under AGPL terms per GPLv3 §13 — owner/counsel decision required regardless) | Local | ~90% academic claim; female-skewed training data; nudity-only | Per-class scores + boxes | Reject, upheld (copyleft + nudity-only) |
| Q16 / LAION-CLIP probes, OpenNSFW2-type | Lightweight | No maintained, clearly-licensed weights release found | Local | Same under-generalization class as the incumbent | Probability scores where maintained | Deferred (license murk + no evidenced gain over the pick) |
| Prompted open VLM (e.g. Qwen2-VL-2B-Instruct, Apache-2.0) as policy judge | ~2B | Apache-2.0 (license-clean) | Local, GPU-preferred | **Zero published safety-classification metrics** for this use; uncalibrated; prompt-sensitive | Seam allows it; evidence does not support selecting it | Deferred (could be specialist-measured later) |

Why Falconsai despite near-zero evidence: the image slot has no
candidate that is simultaneously license-clean, small/offline, and
independently evidenced — the pick's sole number is a vendor
training-log accuracy on undisclosed data. Falconsai is license-clean
(Apache-2.0), tiny (343 MB, CPU-resident), transformers-native (no new
dependencies), and its probability output is the only shortlisted
signal that can express the seam's uncertainty state. The incumbent loses on every axis except
incumbency; every broad-coverage VLM guard is barred by research/gated
terms, footprint, or missing per-variant evidence. The honest consequence
is recorded in §2: narrow selection now, broader-contextual coverage
explicitly unavailable, E1 measurement mandatory before release.

## 4. Explicit tradeoffs

T1. 0.6B guard vs larger guards. The pick trades raw classification
headroom for footprint and latency. Mitigations: the 4B step-up is
pre-approved on measurement grounds (§2); the hash matcher in front of
it already blocks known-bad inputs deterministically, so the guard only
sees matcher-clean traffic.
T2. Vendor-reported text evidence. The Qwen numbers come from the
vendor's own report with optimal-mode-per-benchmark averaging. They are
not independent. Mitigation: E2 must be measured by the specialist on a
fixed strict-mode configuration; the pick stands or falls on that gate.
T3. Qwen vs Granite (both Apache-2.0). Granite has an IBM paper and
broader risk types (jailbreak, RAG groundedness) but is 3.4x the params,
English-only, and weaker on shared public suites. If the product were
English-only and GPU-resident, Granite 3.1-2b would be the pick; it is
not, so Qwen leads with Granite as the documented runner-up.
T4. Qwen vs Llama Guard 3 1B. LG3-1B has the MLCommons-aligned taxonomy
and a strong English F1 (0.899), but Llama Community gating (use policy,
MAU clause, non-OSI terms) is a licensing step-change for a paid GPL
release versus Apache-2.0. If owner/counsel ever blesses Llama terms,
LG3-1B is the first alternative to re-open.
T5. Narrow image pick. Falconsai covers adult-NSFW only, its only
published number is a vendor training-log accuracy (0.980) on an
undisclosed split, and its training data is unauditable. This is the weakest part
of this recommendation and is stated plainly: broader-contextual image
review stays a release blocker. The alternatives were worse, not better
(research-gated terms, unspecified licenses, or 4-12B footprints).
T6. Superseding the incumbent. SDSC is already wired and "free", but its
license is genuinely unspecified, it is 3.5x the bytes, boolean-only,
and has documented FP/under-generalization problems. Keeping it would
trade a small integration saving for a permanent legal and quality gap.
The optional `nsfw_filter` path is unaffected by this verdict.
T7. No new runtime dependencies either way. Both picks run on the pinned
`torch`/`transformers`/`safetensors` stack (licenses.md §3.1); weights
are downloaded post-install like all other models (licenses.md §6), so
the bundle-spec weight exclusion is unaffected. Community GGUF builds of
the 0.6B exist but are third-party provenance: S08 uses the official
weights via transformers, or a first-party quant with recorded lineage.
T8. Pinning. All model references must resolve to immutable commit SHAs
at S08/S09 time (cf. licenses.md BLOCKER B-3 on branch pins); the SHAs
observed in this session are lookup-date observations, not pins.

## 5. Proposed thresholds (require owner/specialist approval)

Effectiveness (measured by qualified parties on curated sets, §6):
E1 image recall >= 0.90 at FPR <= 0.10 on neutral sets, measured at the
S09-chosen operating threshold with the uncertainty band counted as
withheld (conservative); E2 text classifier F1 >= 0.85 on an
MLCommons-aligned set, measured in fixed strict mode
(Controversial→unsafe, matching the fail-closed mapping); E3 combined
pipeline recall >= 0.95 on the specialist abuse set. Latency/VRAM: L1
text check p95 <= 500 ms CPU / <= 200 ms GPU per request; L2 image check
p95 <= 2 s per image on the 16 GB baseline; L3 safety stack <= 2 GB
resident VRAM alongside generation models (Qwen-0.6B bf16 ~1.5 GB fits;
Falconsai is CPU-resident; or explicit unload/reload ruling); L4 keep
the existing 5 s semantic-judge timeout (`semantic.py`).

## 6. Safe fixtures + specialist procedure

Safe neutral fixtures (this repo may hold): everyday-photo sets (e.g.
COCO-style), clothed-portrait and landscape images, benign prompt lists
including tricky-benign cases (XSTest-style: benign prompts that naive
guards refuse — fail-closed over-refusal breaks UX, so benign-set FPR
must be measured, not just abuse recall); assert only pipeline plumbing
(verdict recorded, fail-closed on missing model, no content in logs).
Sensitive evaluation: qualified authorized parties curate abuse-case
sets **off-repo**, run E1-E3/L1-L4, and return **aggregate metrics
only** — no imagery, no policy vocabulary in source, issues, or logs.
Per-pick measurement notes: (a) Qwen-0.6B in fixed strict mode on an
MLCommons-aligned set plus a benign-heavy set (the Granite card's own
xstest_RR 0.43 is the cautionary example for why); escalate to the 4B
step-up only on a recorded E2 miss. (b) Falconsai threshold +
uncertainty-band calibration on neutral sets first (no vendor operating
point is published), then E1 at that point. Results recorded in §7 when
received.

## 7. Acceptance checklist + pending results

- [x] S07 researcher: text evaluator SELECTED (§2, Qwen3Guard-Gen-0.6B +
  4B step-up); image narrow evaluator SELECTED (Falconsai);
  broader-contextual image coverage explicitly marked UNAVAILABLE
  (blocker retained). No efficacy claim here rests on synthetic unit
  tests; no implementation in this issue.
- [ ] PENDING owner: approve/reject the §2 picks (including the
  broader-contextual image gap and the retained blocker); approve
  thresholds (E1-E3/L1-L4); confirm Apache-2.0 weights terms are
  acceptable for the paid GPL release (no NC/gating issues found, but a
  coding agent cannot clear licensing).
- [ ] PENDING specialist: E1-E3/L1-L4 measured results (aggregates only).
- [ ] PENDING release: S08/S09 adapters implemented against the approved
  picks; P11 (licenses.md BLOCKER B-9) re-inventoried with pinned SHAs
  once the picks are approved.
- Reviewer: ______ (owner/specialist) Date: ______ Operator: ______

## 8. Sources

Lookups 2026-10-09. HF model API (`cardData.license`, params,
downloads): `Qwen/Qwen3Guard-Gen-0.6B` (apache-2.0, 752M),
`Qwen/Qwen3Guard-Gen-4B` (apache-2.0, 4.41B),
`ibm-granite/granite-guardian-3.1-2b` (apache-2.0, 2.53B),
`ibm-granite/granite-guardian-3.1-8b` (apache-2.0, 8.2B),
`meta-llama/Llama-Guard-3-1B` (llama3.2, 1.5B),
`meta-llama/Llama-Guard-4-12B` (other, multimodal),
`google/shieldgemma-2b` (gemma, 2.6B),
`allenai/wildguard` (apache-2.0, 7.2B),
`Falconsai/nsfw_image_detection` (apache-2.0, 86M),
`CompVis/stable-diffusion-safety-checker` (license null),
`AIML-TUDA/LlavaGuard-v1.2-0.5B-OV-hf` (license null, gated ToU),
`lmms-lab/llava-onevision-qwen2-0.5b-ov` (apache-2.0, base).
Byte sizes via HTTP HEAD: Falconsai `model.safetensors` 343,223,968;
SDSC `pytorch_model.bin` 1,216,067,303.
Text efficacy: Qwen3Guard tech report (arXiv:2510.14276) Tables 2-6;
Qwen3Guard GitHub README (output format, `transformers>=4.51`,
1.19M training samples, 119 languages); Granite Guardian 3.1-2b card
(harm F1 table, jailbreak recall, English-only) and paper
(arXiv:2412.07724); Llama Guard 3-1B card (PurpleLlama `MODEL_CARD.md`:
taxonomy, eval table, limitations); ShieldGemma paper
(arXiv:2407.21772); WildGuard paper (arXiv:2406.18495); vdf.ai
open-weight guard comparison 2026 (license/coverage cross-check).
Image efficacy: Falconsai card (training-log `eval_accuracy` 0.980 on an undisclosed split; proprietary 80k set);
LlavaGuard paper (arXiv:2406.05113) Tables 1-8 (v1.0 7B/13B/34B only)
and repo (`ml-research/llavaguard`, Apache-2.0 code, gated weights);
SDSC FPs/license: diffusers PR #862 discussion, CompVis#239, SafeGen
(arXiv:2404.06666); NudeNet AGPL + ~90%: ai-engine.net comparison,
bomberbot training-data note. In-repo: `hardware-models.md` (16 GB
baseline, §3 VRAM estimates), `licenses.md` §3.1 (pinned stack), §6
(post-install weights), B-3 (SHA pinning), B-9 (re-inventory trigger).
