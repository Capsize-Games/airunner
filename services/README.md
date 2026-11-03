# Services

`services/` contains AI Runner's headless daemon and API implementation. It owns request routing, runtime coordination, downloads, persistence, and service lifecycle behavior for the model workers used by other applications.

Importable Python code is under `services/src/airunner_services/`. The main console entry points are declared in [`setup.py`](setup.py): `airunner-daemon`, `airunner-headless`, and `airunner-service`, along with download and maintenance commands.

## Package profiles and dependencies

`services/setup.py` declares the `core`, `llm-native`, `stt-native`, `art-python`, `tts-python`, `tts-python-core`, `headless`, `desktop`, `linux-release`, and `development` extras, among others. `desktop` is a legacy package-extra name for a broader service profile; it does not include the retired Qt interface.

The base package requires `airunner-common~=6.1.8`. Its reviewed wheel is published in the [common v6.1.8 GitHub release](https://github.com/Capsize-Games/airunner-common/releases/tag/v6.1.8); PyPI publication remains paused. FacehuggerShield is optional through the `legacy-shield` extra.

The legacy `tts-python` extra requires `airunner-tts-vendor`; the `headless`, `desktop`, `all`, `all_dev`, `all_native`, `all_dev_native`, and `windows` aggregates inherit it. [Issue #2413](https://github.com/Capsize-Games/airunner/issues/2413) records unresolved PyPI availability, so these vendor-bearing profiles are not available from the configured public indexes. The current `linux-release` profile selects `tts-python-core`, which omits OpenVoice/Melo and the legacy pyttsx3 local-playback dependency. The headless eSpeak HTTP path uses the bounded eSpeak NG CLI renderer described below. Legacy `llm` and `tts-python` extras retain their playback dependency; they are not the Linux release profile. The full ML release lock and artifact/model acceptance remain unfinished.

For a local development environment, first confirm that the required dependencies are available from an approved source. Then create an isolated environment with `uv` and install the service package and development tools:

```bash
uv venv --python 3.13.5 .venv
uv pip install --python .venv/bin/python -e "./services[development]"
```

This command uses the current package metadata; it cannot supply dependencies that are unavailable from the configured indexes.

## Run the service

The `airunner-headless` console command supervises a daemon and exposes its HTTP API. It binds to loopback by default. A non-loopback bind requires `AIRUNNER_API_KEY`; `--insecure-no-auth` disables that requirement and should not be used for a network-facing deployment.

### Application content policy

Application content moderation is disabled by default. Set `AIRUNNER_CONTENT_POLICY_MODE=enforce` before starting the service to enable the existing text and image policy integration. The accepted values are exactly `disabled` and `enforce`; if the variable is set to any other value, service startup rejects the configuration. With enforcement enabled, unavailable policy data or image evaluators continue to fail closed. Set `AIRUNNER_CONTENT_SAFETY_ENFORCE_SIGNED=1` when the deployment requires a signed bundled policy corpus and trust store; packaged execution alone does not require them. This signing setting accepts `1`, `true`, `yes`, or `on` as true and `0`, `false`, `no`, or `off` as false, ignoring case and surrounding whitespace; other values are rejected.

For a container-based checkout, use the development compose file. It builds from the repository and mounts the local service and native source. For the published-image configuration, use the release compose file, which has no source bind mounts:

```bash
docker compose -f docker-compose.dev.yml run --rm --service-ports airunner
docker compose -f docker-compose.release.yml run --rm --service-ports airunner
```

Both definitions bind port `127.0.0.1:8080` and mount the configured data and Hugging Face cache directories. The release compose file references `ghcr.io/capsize-games/airunner/airunner:linux-headless`; image publication and startup are not verified here. The repository's dependency publication gaps may also affect builds that request the `tts-python` extra.

## Native LLM backend selection

`AIRUNNER_LLAMA_BACKEND` accepts `auto` (the default), `cpu`, or `cuda-sm120a`.
Backend selection is separate from the GGUF model's context and sampling
profile. `auto` uses CPU for a zero GPU-layer request; a request for GPU layers
requires a verified CUDA profile. Selecting `cpu` explicitly sets GPU layers to
zero. An unavailable or malformed requested GPU profile returns
`native_backend_unavailable`; it does not start the CPU executable instead.

The CUDA profile belongs under
`$AIRUNNER_BUNDLE_ROOT/share/airunner/native-runtimes/cuda-sm120a/` with its
`profile-manifest.json`, wrapper, server, libraries and notices. The selector
checks its file inventory, hashes, modes and declared source/producer identities
before launch. Registry construction defers optional GPU verification, so a
missing profile does not prevent CORE startup or health queries. Health metadata
reports whether selection is deferred or unavailable. Selected artifact
capabilities do not prove physical device use; observed device and offloaded
layer fields remain unknown until measured.

This profile targets Linux x86_64 and compute capability 12.0. The selector
maps NVIDIA devices in PCI order and sets the child to that order; it currently
rejects `CUDA_VISIBLE_DEVICES` overrides. The CUDA launch pins its device and
disables automatic model fitting, preserving the requested model and context.
The candidate artifact has not yet passed packaged GPU acceptance or been
published as a verified profile.

## TTS HTTP API

`POST /api/v1/tts/synthesize` accepts `text`, `model_type`, `voice`, and `speed`. To use the headless eSpeak CLI renderer, select it explicitly:

```json
{"text":"Hello.","model_type":"Espeak","voice":"en-us","speed":1.0}
```

Use `GET /api/v1/tts/voices?model_type=Espeak` to read the voice IDs reported by the installed eSpeak executable. This request runs its bounded voice-catalog command; it does not start the playback worker or synthesize audio. The returned IDs depend on the installed voice data. `GET /api/v1/tts/voices` without `model_type` reads metadata from an already-ready runtime and does not start one.

The eSpeak renderer accepts speeds from `0.5` through `4.0`, where `1.0` maps to eSpeak rate `100`. The shared HTTP request schema accepts `0.25` through `4.0`; eSpeak returns `422` for values below its supported rate. An unknown voice or model type returns `422`. An unavailable voice catalog or executable returns `503`, and a synthesis timeout returns `504`. OpenVoice is unavailable in this release and returns `503` when selected.

## Checks

Run focused tests after setting up the documented dependencies:

```bash
.venv/bin/python -m pytest services/tests/test_service_bootstrap.py -q
```

The test suite includes runtime smoke and functional checks that can require sidecars, model files, or GPU capacity. Report skips and missing runtime resources as unverified; they are not evidence that a workload ran.

See the [repository README](../README.md) for dependency and Docker context, [CONTRIBUTING.md](../CONTRIBUTING.md) for contributor guidance, and [SECURITY.md](../SECURITY.md) for the security reporting process.
