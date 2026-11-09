# Art providers

AI Runner generates images through one of two art providers.
The caller selects the provider on every request. There is no
silent fallback between them.

`GenerationRequest.provider` accepts `Literal["local", "muse"]`
and defaults to `"local"`. Omitting `provider` therefore means
`provider="local"`. An explicit `provider="muse"` request that
fails is returned as an error; it is never retried locally, and
a failed `provider="local"` request is never retried through
Muse. See [No silent fallback](#no-silent-fallback).

## Local vs Muse

| Aspect | `provider="local"` | `provider="muse"` |
| --- | --- | --- |
| Where it runs | On the host, local runtime | Meta cloud API |
| Runtime descriptor | `provider="local"` | `provider="muse"` |
| Deployment mode | `local_fallback` / `sidecar` | `cloud` |
| Model source | Installed local model | `muse-image-1.0` (default) |
| API key required | No | Yes, `MODEL_API_KEY` |
| Network required | No | Yes, HTTPS to Meta |
| Prompt leaves host | No | Yes, sent to Meta |

`RuntimeMode.CLOUD` has the value `"cloud"`. The Muse client
registers its runtime descriptor with `provider="muse"` and
deployment mode `cloud`, so health and registry output show
which provider would serve a request before it is sent.

## Providers

### Local (default)

Requests with `provider="local"`, or with no `provider` field,
run on the installed local art runtime. No API key is read and
no network call is made for generation. The `model` field, when
set, names the local model exactly as it does today.

### Muse (Meta)

Requests with `provider="muse"` call the Meta image API:

- Method and path: `POST {base}/images/generations`
- Default base URL: `https://api.meta.ai/v1`
- Default model: `muse-image-1.0`, sent as the `model` field
- Authentication: the value of `MODEL_API_KEY`, sent only as
  the outbound credential to Meta

Results arrive either as base64 image data or as image URLs.
URL results are fetched over HTTPS only; plain `http://` URLs
are rejected. Fetches honor the configured timeout and the
configured maximum image size, and oversized or timed-out
fetches fail the request instead of returning partial data.

## Environment variables

Set these in the shell or in `.env` copied from `.env.example`.
Every value below ships empty in `.env.example`.

| Variable | Required | Default |
| --- | --- | --- |
| `MODEL_API_KEY` | Muse only | unset |
| `AIRUNNER_MUSE_BASE_URL` | No | `https://api.meta.ai/v1` |
| `AIRUNNER_MUSE_MODEL` | No | `muse-image-1.0` |
| `AIRUNNER_MUSE_TIMEOUT_S` | No | client default |
| `AIRUNNER_MUSE_MAX_IMAGES_PER_JOB` (default 8) and `AIRUNNER_MUSE_MAX_IMAGE_BYTES` | No | client default |

Purposes, in table order: Meta API key; base URL override;
model override; request timeout in seconds; maximum image
size in bytes.

Notes:

- The API key is read only from the `MODEL_API_KEY`
  environment variable. There is no other key source, and no
  key belongs in request bodies, config files, or this repo.
- `AIRUNNER_MUSE_BASE_URL` replaces `{base}` in
  `POST {base}/images/generations`. Keep it an HTTPS URL.
- `AIRUNNER_MUSE_MODEL` replaces the default `muse-image-1.0`
  model name when a deployment must pin a different model.
- `AIRUNNER_MUSE_TIMEOUT_S` bounds each Meta request and
  each HTTPS fetch of a URL result.
- `AIRUNNER_MUSE_MAX_IMAGES_PER_JOB` (default 8) and `AIRUNNER_MUSE_MAX_IMAGE_BYTES` caps the decoded size of
  each returned image, whether it arrived as base64 or via a
  URL fetch.

## Request and response shape

Generation is `POST /api/v1/art/generate`. The request body
is `GenerationRequest`; the only provider-specific field is
`provider`. The runtime returns a `ResponseEnvelope` whose
payload and metadata have a fixed shape for both providers:

- `payload`: `{images: [b64, ...]}`, one base64-encoded image
  per returned image, in result order
- `metadata`: `{provider, model, image_count}`, where
  `provider` is `"local"` or `"muse"`, `model` is the model
  that served the request, and `image_count` equals
  `len(payload["images"])`

The HTTP response for `POST /api/v1/art/generate` remains
`{job_id, status}`; read the envelope shape above at the
runtime boundary, not from the job response.

## Privacy and secret handling

- `provider="local"`: the prompt and any input image stay on
  the host. Nothing is sent to Meta.
- `provider="muse"`: the prompt (and any input image the API
  accepts) is sent to Meta to generate the image. Do not use
  Muse for prompts or images that must not leave the host.
- The API key never leaves the process except as the outbound
  credential to Meta. It is never written to `metadata`,
  logs, or error messages.
- The prompt is never written to envelope `metadata`. Error
  messages and log lines do not include the key or the prompt;
  they may include the provider, model, status, and counts.
- Returned images are handled the same for both providers
  after fetch: size-capped in memory, with no extra network
  access beyond the single HTTPS fetch for URL results.

## Errors

Errors are explicit. A failed request does not change provider
behind the caller's back.

| Situation | Result |
| --- | --- |
| Unknown `provider` value | Request validation error (`422`) |
| `provider="muse"`, `MODEL_API_KEY` unset | Error before any Meta call |
| Meta rejects the key or request | Upstream error, no local retry |
| Meta timeout | Timeout error, no local retry |
| URL result is not `https://` | Error, URL is not fetched |
| URL fetch exceeds size cap | Error, partial data discarded |
| Local runtime unavailable | Error, no Muse retry |

Error text never contains the API key or the prompt. When
debugging, log the provider, model, HTTP status, and
`image_count` only.

## No silent fallback

Fallback would hide cost, privacy, and availability changes:
a request the caller meant to keep on the host must never be
sent to a cloud API because the local runtime was busy, and a
cloud failure must never be masked by different local output.
Selection is therefore exactly the validated `provider`
value, defaulting to `"local"`. To change provider, the
caller sends a new request with the other `provider` value.

## Pricing and limits

This document does not state Muse pricing, rate limits, or
quotas. No price or limit figure is confirmed here. Confirm
current pricing, limits, and model availability in the Meta
dashboard for the account that owns `MODEL_API_KEY` before
enabling Muse for real traffic.

## Examples

Both examples call the local service at
`http://127.0.0.1:8080`. Adjust the host and port to your
deployment, and add your service auth header if you set one.

Local provider (explicit; omitting `provider` is identical):

```bash
curl -sS -X POST http://127.0.0.1:8080/api/v1/art/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "a lighthouse at dusk, flat color poster",
    "provider": "local",
    "num_images": 1
  }'
```

Muse provider (key comes from the environment only):

```bash
export MODEL_API_KEY="<key from the Meta dashboard>"
curl -sS -X POST http://127.0.0.1:8080/api/v1/art/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "a lighthouse at dusk, flat color poster",
    "provider": "muse",
    "num_images": 1
  }'
```

Direct calls to Meta (for connectivity checks only; the
service normally makes this call):

```bash
curl -sS -X POST https://api.meta.ai/v1/images/generations \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${MODEL_API_KEY}" \
  -d '{
    "model": "muse-image-1.0",
    "prompt": "a lighthouse at dusk, flat color poster"
  }'
```

## Launch

1. Copy `.env.example` to `.env` if you have not already.
2. To enable Muse, set `MODEL_API_KEY` in `.env` (or the
   service environment) to the key from the Meta dashboard.
   Leave it empty to keep Muse disabled; local generation
   is unaffected.
3. Optionally pin `AIRUNNER_MUSE_BASE_URL`,
   `AIRUNNER_MUSE_MODEL`, `AIRUNNER_MUSE_TIMEOUT_S`, or
   `AIRUNNER_MUSE_MAX_IMAGES_PER_JOB` (default 8) and `AIRUNNER_MUSE_MAX_IMAGE_BYTES`. Empty means default.
4. Restart the service so it picks up the environment.
5. Send one `provider="local"` request and one
   `provider="muse"` request using the examples above.
   Confirm the Muse envelope `metadata` shows
   `provider="muse"`, the expected `model`, and an
   `image_count` matching the payload.
6. Confirm pricing and limits in the Meta dashboard before
   routing production traffic to Muse.

## Rollback

1. Remove `provider="muse"` from callers, or stop sending
   it; requests without a provider use `provider="local"`.
2. Clear `MODEL_API_KEY` (set it empty) and restart the
   service. Muse requests then fail fast with an explicit
   error instead of calling Meta.
3. Clear any `AIRUNNER_MUSE_*` overrides you set, and
   restart again if the base URL or model pin must go.
4. Re-send a `provider="local"` request to confirm local
   generation still works.

Rollback never requires a data migration: provider choice
is per-request and no provider state is stored in results
beyond the `metadata` fields described above.
