# Service evaluation targets

Owner direction, 2026-11-03: define targets for the best quality and lowest
latency. These are engineering acceptance targets, not measured results or
claims of quality parity. Record failures and optimize against them; do not
silently lower targets to turn a failed run green.

## Release selection

Owner direction, 2026-11-03: use incremental MVP releases. These targets remain
the engineering backlog and benchmark reference; completing every row is not a
prerequisite for the first service release. Select shipped capabilities and
blocking checks through [INCREMENTAL_RELEASES.md](INCREMENTAL_RELEASES.md).
Authentication, isolation, data integrity and owned-worker correctness remain
blocking for shipped paths. Record measured latency and benchmark misses; do not
advertise an unproven SLA or label a deferred benchmark passed. A later change
that affects a shipped path reruns that path's relevant acceptance checks.

## Reference conditions

Use the declared Linux/NVIDIA 16 GB service target, exact reviewed release
inputs and recorded CPU, RAM, GPU, driver, source and artifact identities.
Record other workload and available capacity. Never stop unrelated applications
or count a capacity-rejected run as a model result.

Keep the Qwen3.5-9B Q8_0 / 32,768-context scenario unchanged. Record the complete
prompt, template, tool configuration, actual input/output token counts, seed,
sampling settings and thinking preference. A smaller context/model or different
quantization is a separate experiment, not a replacement for that scenario.
Use the verified E5 artifact, declared Whisper backend, eSpeak voice and exact
Z-Image artifact/4-bit configuration for their respective scenarios.

Measure the normal authenticated API. Direct component tests are diagnostic
until repeated through the service and final installed/frozen artifact. Report
source, wheel, container and frozen results separately.

## Correctness and quality

| Area | Target and required evidence |
|---|---|
| Critical service behavior | 100% of deterministic authentication, isolation, data-retention, error, admission and cancellation regressions pass. Zero false-success responses, cross-bot/tenant passages, lost completed results or unowned running work. |
| Grounded answers | At least 19 of 20 fixed questions correctly answer from synthetic supplied sources. Every citation resolves to a retrieved source ID; zero invented quotations or citations. Publish prompts, sources, outputs and scoring rules. This characterizes the fixture set, not general factuality. |
| Memory correction and recall | All 10 fixed correction/recall sequences return the latest stored fact and preserve separation between two bots/tenants. Include persistence/restart and an explicit unknown-fact case. Application mood/persona policy is outside this service benchmark. |
| Tool selection | At least 19 of 20 fixed scenarios choose the expected tool or correctly choose no tool. Every executed call has valid arguments and the expected bounded effect. Unsupported/failed tools and tool-only replies must be represented truthfully in every case. |
| Long context | At least 19 of 20 exact synthetic retrieval questions succeed at recorded positions near the beginning, middle and end of a prompt approaching the supported 32k context limit. Record tokenizer counts and output headroom; configuring a 32k context alone is not this test. |
| Document lifecycle | Every advertised format imports through the service using real format fixtures. Reindex/cancel/restart/delete/failure recovery preserve prior data and source attribution. Changing embedding identity requires explicit compatible reindexing. |
| STT | Word error rate no greater than 10% over 20 rights-cleared, reproducible utterances. Freeze reference transcripts and normalization before scoring; also report per-utterance errors, silence, cancellation and unavailable-backend behavior. Synthetic speech results are not real-speaker/noise robustness claims. |
| TTS | All requests return complete, decodable, non-silent audio with correct declared format and bounded duration. On 20 fixed pronunciation phrases, STT round-trip word error rate no greater than 15%; label this limited round-trip metric, not a naturalness score. |
| ART | All outputs meet requested dimensions/count, decode, persist and remain retrievable. For 20 neutral fixed prompts, score subject, requested attributes, layout and major visual defects using a published rubric: at least 90% of rubric criteria pass, with no severely corrupted output. Identify assistant-scored visual assessment separately from automated file checks; no human review or safety-efficacy claim. Exercise only modes the selected backend supports and explicitly reject unsupported ones. |

## Latency and resource targets

Use at least 30 comparable warm observations for medians and nearest-rank P95.
Keep short and long inputs separate. Report individual values, failures and
sample count; a timeout is a failed observation, not a removed outlier. For
process-cold loads, report three individual trials and their maximum. Do not
claim storage-cold behavior when the operating-system file cache is warm.

| Operation | Initial target on the reference profile |
|---|---|
| CORE health/status, no model loading | P95 at most 50 ms over 200 requests at concurrency four. |
| Warm LLM first visible token | Median at most 1 s; P95 at most 2 s for the fixed short-input set, with no more than 1,024 total provider-reported input tokens. Exclude keepalive/tool-status frames from first-token timing. Report larger actual prompts separately. |
| Warm LLM decoding | At least 40 generated tokens/s for fixed 128-token outputs; P95 complete response at most 6 s for the short-input set. Count actual provider tokens, not characters. |
| Process-cold Qwen load | Maximum 60 s across three trials on a verified local SSD copy of the same model bytes. Also report existing-storage measurements; a cache copy must be explicit and must not alter the original model. |
| Cancellation and unload | Request cancellation acknowledged within 250 ms P95; physical generation stops within 2 s P95 after a visible token, or within 10 s during long prefill. LLM weight release within 5 s, with a bounded retained CUDA context; full daemon exit removes all task-owned GPU allocations. |
| E5 retrieval | Warm query plus retrieval P95 at most 1 s for queries up to 128 tokens against the fixed 100-chunk corpus. Record embedding and retrieval times separately. |
| eSpeak TTS | Warm complete-response P95 at most 500 ms for phrases up to 200 characters. |
| Whisper STT | Real-time factor at most 2 for the fixed 5–30 s CPU reference clips. Record thread count and per-clip latency; benchmark any supported GPU path separately. |
| Z-Image Turbo | Warm generation P95 at most 20 s for one 512×512 image, eight declared inference steps, fixed seeds and supported 4-bit path. Record text encoding, denoising, VAE and persistence times separately. Do not generalize to larger images/batches. |
| Repeated lifecycles | No orphan task/process, lost reservation or unbounded memory growth over 20 sequential request/cancel/unload cycles. Record baseline/peak/post-release RAM and GPU memory and explain retained runtime caches. |

These latency targets apply only when resource admission passes and the test
load matches the reference conditions. Report queue wait, model load, inference
and end-to-end time separately. A fast admission rejection is not a fast model
response.

## Optimization procedure

First run and retain the baseline. Rank measured costs, change one relevant
factor, and repeat identical workloads with the same model identity and quality
fixtures. Prefer changes that improve latency without reducing quality. Keep
both results when there is a tradeoff; do not claim one configuration is best
from a single favorable measurement. Test service loading, prompt/tokenization,
worker queues, copies, model placement and caches before changing model quality.

Every target miss becomes explicit work on the existing subsystem issue, with
its source/artifact identity and evidence. Final release reporting must list
measured passes, misses and exclusions. No target in this file has passed merely
because it was written down.
