# B02 and v6.1.1 review

**Verdict: FAIL for PR #2169; v6.1.1 is not qualified as a completed desktop release.**

Reviewed PR #2169 at `ed7d010c1709ed79b41924bc053e07e981453892`, based on released commit `76ed9ffa606e415142490e795a9c52d9229893ca`. The GitHub v6.1.1 release exists and contains no attached installer/binary assets. It describes itself as a release-preparation batch. No merge, tag, release modification or application edit was performed during this review.

## B02 blockers

1. **P1 — turn indexes race.** `services/src/airunner_services/llm/companion/repository.py:110-124` assigns the next index from a count without serializing writers or enforcing a unique session/index constraint. Two concurrent distinct completions both computed index 0 and committed it. Subsequent ordering is ambiguous. Serialize index allocation within the storage transaction and enforce the intended uniqueness invariant; test concurrent writers.
2. **P1 — concurrent replay is not idempotent.** The select-before-insert at repository lines 80-94 races with another completion for the same `(chatbot_id, call_chain_id, role)`. One writer raises `sqlalchemy.exc.IntegrityError` rather than returning the already persisted result. A unique constraint prevents duplicate rows, but does not make this API idempotent under concurrent delivery. Handle conflict/retry atomically and return the existing record.
3. **P2 — exact four-hour boundary differs from upstream.** Repository line 64 reuses only for `< 4 hours`; pinned upstream `8157628abfd99f8305db754ca640e4a870d046ed`, `llm/session_manager.py:42`, rotates only for `> 4 hours`. An exact four-hour request starts session 2 instead of reusing session 1. The supplied test named `test_exactly_at_gap_boundary_still_reuses_the_session` actually advances by four hours **minus one microsecond** (test file line 116), masking this discrepancy. Test the real boundary and preserve the characterized rule or document an approved behavior change.
4. **P2 — bounded recall is implemented as an unbounded read.** `get_recent_turns` calls `.all()` before slicing the requested limit. A request for 20 turns loads the entire session transcript, even when the limit is zero. Push ordering/limit into SQL and reverse the limited result for chronological output.

## Executed B02 verification

The supplied B02 suite passed: **13 passed**. Three additional neutral tests against temporary SQLite databases all failed:

- Exact four-hour boundary: assertion `2 == 1` failed.
- Two distinct concurrent completions: returned indexes `[0, 0]`.
- Two concurrent deliveries of the same completion: UNIQUE constraint failure.

The concurrency tests use barriers immediately after the real database lookups/counts to force a valid competing-writer interleaving; they do not replace SQL results or persistence logic. Reproduction file: `/tmp/airunner-b02-review/test_review_b02.py`. Log: `/tmp/airunner-b02-checks.log`.

## Released download blockers remain

**D01 checksum propagation remains incomplete.** The curated model metadata has not acquired immutable revisions/checksums, and normal `_download_model` calls still pass a branch revision without `expected_sha256` (`huggingface_download_worker.py:676`; GGUF dispatch also omits a digest). Most verification therefore still runs with `None`. Supporting an optional helper argument is not the same as verifying curated downloads end to end.

**D02 still accepts a resume with no actual validator.** At worker lines 1124-1126, an empty stored sidecar equals an absent response validator converted to an empty string. That proves neither content identity nor immutability. A real-worker reproduction with a fake HTTP response produced:

```
partial bytes: OLD!
identity sidecar: empty
206 bytes: NEW!
response ETag / Last-Modified: absent
promoted result: OLD!NEW!
marked complete: True
```

Reproduction: `/tmp/airunner-b02-review/repro_download.py`; log `/tmp/v611-download-repro.log`. B02 does not change this worker, so the result applies to v6.1.1 as well. Restart/reject unverifiable partials unless a verified immutable digest protects finalization. Do not call empty validators a fail-closed identity check.

## Report verification and remaining uncertainty

- Several earlier corrections are present: omission/null output caps are now resolved, zero CFG is accepted, diagnostics export no longer copies exception messages, package-build support files were added, and the companion inference protocol now has cancellation. This review does not carry forward the old verdict against unchanged assumptions where fixes exist.
- B02's failed smoke job reports missing **radon** and **diffusers** during collection. The v6.1.1 master run reports the same two missing modules. This supports those failures being pre-existing relative to B02; it does not demonstrate successful runtime behavior or establish that every earlier batch PR was regression-free.
- I have not independently established the report's claim that all 30 failures from the broad local sweep are pre-existing. A race caused by concurrent source editing is a contaminated run; resource-contention claims need isolated reruns and an unchanged baseline. Passing on the latest master after the changes cannot alone establish a before/after comparison for those same changes.
- No real model, GUI, GPU acceptance or installer verification was performed. Source release publication is not proof of a working paid desktop installer.

The older Spark correction automation remains paused. No changes were sent to another agent during this review.

## Combined suite result

Re-ran the report's named combined set at the exact PR head: `test_release_{s01,s02,d01,d02,d03,d04,o01,o02,o03,p01,b01,b02}.py` plus `test_download_security.py`. Result: **199 passed**, 349 warnings, 38.22 seconds (the report says 202; that count was not reproduced). The three additional failing review tests were run separately, not included in that 199. Log: `/tmp/v611-release-checks.log`.

The combined suite includes the revised source-distribution build check. It does not cover the concurrency/boundary/empty-validator cases demonstrated above. All execution used the isolated review checkout and temporary application/SQLite paths. PR head and open status were rechecked after verification and remained unchanged.
