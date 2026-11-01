# Services

`services/` contains AI Runner's headless daemon and API implementation. It owns request routing, runtime coordination, downloads, persistence, and service lifecycle behavior for the model workers used by other applications.

Importable Python code is under `services/src/airunner_services/`. The main console entry points are declared in [`setup.py`](setup.py): `airunner-daemon`, `airunner-headless`, and `airunner-service`, along with download and maintenance commands.

## Package profiles and dependencies

`services/setup.py` declares the `core`, `llm-native`, `stt-native`, `art-python`, `tts-python`, `headless`, `desktop`, and `development` extras, among others. `desktop` is a legacy package-extra name for a broader service profile; it does not include the retired Qt interface.

The base package metadata requires `airunner-common~=6.1.7` and `facehuggershield==1.0.0`. The CI workflow uses pinned source checkouts for these dependencies because their PyPI releases are paused or yanked. No general external install instructions for those sources are established here. The TTS-related extras also require `airunner-tts-vendor`; [issue #2413](https://github.com/Capsize-Games/airunner/issues/2413) records unresolved PyPI availability. Since `headless` and `desktop` include TTS dependencies, their names alone do not establish that dependency resolution succeeds.

For a local development environment, first confirm that the required dependencies are available from an approved source. Then create an isolated environment with `uv` and install the service package and development tools:

```bash
uv venv --python 3.13 .venv
uv pip install --python .venv/bin/python -e "./services[development]"
```

This command uses the current package metadata; it cannot supply dependencies that are unavailable from the configured indexes.

## Run the service

The `airunner-headless` console command supervises a daemon and exposes its HTTP API. It binds to loopback by default. A non-loopback bind requires `AIRUNNER_API_KEY`; `--insecure-no-auth` disables that requirement and should not be used for a network-facing deployment.

For a container-based checkout, use the development compose file. It builds from the repository and mounts the local service and native source. For the published-image configuration, use the release compose file, which has no source bind mounts:

```bash
docker compose -f docker-compose.dev.yml run --rm --service-ports airunner
docker compose -f docker-compose.release.yml run --rm --service-ports airunner
```

Both definitions bind port `127.0.0.1:8080` and mount the configured data and Hugging Face cache directories. The release compose file references `ghcr.io/capsize-games/airunner/airunner:linux-headless`; image publication and startup are not verified here. The repository's dependency publication gaps may also affect builds that request the `tts-python` extra.

## Checks

Run focused tests after setting up the documented dependencies:

```bash
.venv/bin/python -m pytest services/tests/test_service_bootstrap.py -q
```

The test suite includes runtime smoke and functional checks that can require sidecars, model files, or GPU capacity. Report skips and missing runtime resources as unverified; they are not evidence that a workload ran.

See the [repository README](../README.md) for dependency and Docker context, [CONTRIBUTING.md](../CONTRIBUTING.md) for contributor guidance, and [SECURITY.md](../SECURITY.md) for the security reporting process.
