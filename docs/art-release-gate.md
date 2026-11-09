# Art release gate: Muse provider (Meta)

Scope: Capsize-Games/airunner #2453 / #2458 (W5). This gate covers
the optional cloud art route only. The local route is unchanged.

## Frozen contract

- `GenerationRequest.provider` is `Literal[local, muse]`, default
  `local`. No silent fallback from `muse` to `local`.
- The Muse client registers as provider `muse`, deployment
  `cloud` (`RuntimeMode.CLOUD = "cloud"`).
- Meta endpoint: `POST {base}/images/generations` with model
  `muse-image-1.0`. Default base is `https://api.meta.ai/v1`.
- The API key comes only from the `MODEL_API_KEY` environment
  variable. Overrides: `AIRUNNER_MUSE_BASE_URL`,
  `AIRUNNER_MUSE_MODEL`, `AIRUNNER_MUSE_TIMEOUT_S`,
  `AIRUNNER_MUSE_MAX_IMAGE_BYTES`.
- Success uses `ResponseEnvelope` with
  `payload = {images: [b64, ...]}` and
  `metadata = {provider, model, image_count}`. The key and the
  prompt never appear in metadata, logs, or errors.
- URL results are fetched over https only, with a size cap and a
  timeout.

## Feature flag

The flag is the presence of `MODEL_API_KEY` in the service
process environment:

- Set and non-blank: `muse_art_enabled()` in
  `services/src/airunner_services/runtimes/bootstrap.py` returns
  true and the Muse art route is registered at registry build.
- Unset, empty, or whitespace-only: the predicate returns false
  and no `muse` route is registered. Requests naming provider
  `muse` then fail explicitly instead of falling back to local.
- If the key is set but the Muse client module cannot be
  imported, bootstrap fails closed: no `muse` route, no crash,
  local routes still register.

There is no config-file flag and no runtime toggle. Changing the
flag requires a process restart (see Rollback).

## Compose evidence

Both compose files use an explicit `environment:` list, not a
generic passthrough and not `env_file:`. They now forward
`MODEL_API_KEY` plus `AIRUNNER_MUSE_BASE_URL`, `AIRUNNER_MUSE_MODEL`,
`AIRUNNER_MUSE_TIMEOUT_S`, `AIRUNNER_MUSE_MAX_IMAGE_BYTES`, and
`AIRUNNER_MUSE_MAX_IMAGES_PER_JOB` (all defaulting to empty), so a
host-exported `MODEL_API_KEY` reaches the container. Never commit
a real key to a compose file, `.env.example`, or this document.

Capacity is per provider: local and Muse jobs each get their own
art slot (`capacity=1` per provider), so a long cloud call does
not block local GPU jobs and vice versa.

## Rollback

1. Unset `MODEL_API_KEY` in the service environment (host shell,
   compose `environment:` entry, or secret store).
2. Restart the service so the runtime registry is rebuilt
   (`docker compose ... run` again, or restart the daemon).
3. Confirm the `muse` route is absent: a `GenerationRequest`
   with provider `muse` must fail explicitly, and local
   generation must still succeed.
4. No data migration is involved. Rollback does not affect
   local models, jobs, or stored outputs.

## Smoke checklist

Run after enabling the flag, before calling the gate passed:

- [ ] Without `MODEL_API_KEY`: service starts, local art
      generation succeeds, provider `muse` fails explicitly.
- [ ] With `MODEL_API_KEY`: service starts and the registry
      contains route `art / muse / cloud`.
- [ ] One `muse` generation returns a `ResponseEnvelope` whose
      payload is `{images: [b64, ...]}` and whose metadata is
      exactly `{provider, model, image_count}`.
- [ ] Logs and error responses for that request contain neither
      the key nor the prompt text.
- [ ] A result returned as a URL is fetched over https only;
      an `http://` result, an oversized body, and a timed-out
      fetch each fail without a local fallback.
- [ ] Provider `local` still succeeds in the same process,
      proving no silent cross-provider fallback occurred.
- [ ] `pytest services/tests/test_art_muse_bootstrap_gate.py`
      passes (bootstrap gate, happy / sad / bad).

## Gate criteria (all required)

1. Focused tests pass:
   `services/tests/test_art_muse_bootstrap_gate.py` (predicate,
   route absent without key, route present with key, blank key
   rejected, missing client module fails closed).
2. W1 Muse client is present
   (`airunner_services.runtimes.muse_art_client`) and registers
   provider `muse` / deployment `cloud`. Until W1 lands, the
   route-present test exercises a stand-in module with the same
   registration contract.
3. Compose passthrough for `MODEL_API_KEY` is in place for the
   target deployment (see Compose evidence) and no secret is
   committed.
4. Every smoke checklist item above is checked on the target
   deployment, including the rollback drill (unset + restart).
5. No key or prompt appears in metadata, logs, or errors in
   the smoke evidence.

## Open dependencies

- W1: real `muse_art_client` module and its
  `register_muse_art_client` helper. Bootstrap imports it
  lazily and fails closed while it is absent.
- W2: also edits `bootstrap.py`; the W5 bootstrap change is
  limited to the `muse_art_enabled` predicate, the
  `_register_muse_art_client` helper, and the two-line gated
  call at the end of `build_runtime_registry`. Expect a small
  merge conflict there and keep the gated call last.
