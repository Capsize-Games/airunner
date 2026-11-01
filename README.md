# AI Runner

AI Runner provides model workers, runtime orchestration, persistence, and HTTP/WebSocket APIs for other applications. This repository contains the headless service; the Qt desktop application and paid desktop storefront are retired.

AI Runner is GPL-3.0-only software. It is built and released by one engineer at [Capsize LLC](https://capsize.online). [Sponsorship](https://github.com/sponsors/w4ffl35) supports project maintenance.

[Report a bug](https://github.com/Capsize-Games/airunner/issues/new?template=bug_report.md) · [Request a feature](https://github.com/Capsize-Games/airunner/issues/new?template=feature_request.md) · [Report a vulnerability](https://github.com/Capsize-Games/airunner/security/advisories/new)

## Repository packages

| Path or project | Role |
|---|---|
| [`services/`](services/README.md) | Daemon, FastAPI routes, runtime orchestration, downloads, and persistence |
| [`native/`](native/README.md) | Python launcher and runtime layout helpers |
| [`airunner-common`](https://github.com/Capsize-Games/airunner-common) | Shared contracts and settings required by the service packages |
| [`airunner-native`](https://github.com/Capsize-Games/airunner-native) | Builds and publishes the llama.cpp and whisper.cpp sidecars |

## Install and dependency status

The package metadata requires Python 3.13.3 or newer. The Linux CUDA profile pins a CUDA 12.9 PyTorch stack. The repository does not define a validated general-purpose hardware or language support matrix; model and runtime requirements vary by workload.

The package metadata currently declares these service extras:

- `core`, `llm-native`, `stt-native`, `art-python`, and `tts-python`
- `headless`, which aggregates LLM, STT, art, and TTS runtime extras
- `desktop`, a legacy extra name for a broader service profile; it does not install a GUI
- `development`, for contributor and packaging tools

For the published distribution name, `airunner-services[development]` denotes the development extra. The local editable-install command below uses the checkout path instead.

Some dependency publication issues affect clean installs. The CI workflow checks out pinned source revisions of `airunner-common` and `facehuggershield` because their PyPI releases are paused or yanked; this repository does not yet document a general external installation route for those sources. Separately, the TTS extras depend on `airunner-tts-vendor`; issue [#2413](https://github.com/Capsize-Games/airunner/issues/2413) records unresolved PyPI availability. `tts-python`, `headless`, and `desktop` inherit that dependency. These profile names describe package metadata and do not mean that a clean public-index resolution has passed.

When the required dependencies are available from an approved package source, an isolated contributor environment can be created with `uv`:

```bash
uv venv --python 3.13 .venv
uv pip install --python .venv/bin/python -e "./services[development]" -e ./native
```

This command is not a workaround for the dependency availability issues above. Check the package source and resolver result before using the environment.

## Docker Compose

The repository has separate compose files for checkout development and the published image:

```bash
# Build from the checkout and mount services/native source read-only.
docker compose -f docker-compose.dev.yml run --rm --service-ports airunner

# Use the image reference in the release compose file.
docker compose -f docker-compose.release.yml run --rm --service-ports airunner
```

Both compose files bind host port `127.0.0.1:8080` and mount the local AI Runner data and Hugging Face cache directories. `--service-ports` publishes the configured port for `docker compose run`. The release compose file references `ghcr.io/capsize-games/airunner/airunner:linux-headless`; registry availability and runtime behavior have not been verified in this documentation update.

The headless CLI defaults to loopback. Binding it to a non-loopback address requires `AIRUNNER_API_KEY`; the `--insecure-no-auth` option bypasses that check and should not be used for a network-facing service. The health endpoint is `/health`.

## Development checks

After resolving the required package dependencies, run focused service tests from the repository root:

```bash
.venv/bin/python -m pytest services/tests/test_service_bootstrap.py -q
```

Runtime smoke and functional checks may require sidecars, model files, or GPU capacity. A test that skips or lacks those resources does not establish runtime support. See [CONTRIBUTING.md](CONTRIBUTING.md) for contributor setup and review guidance.

## Project information

- [Services package guide](services/README.md)
- [Native package guide](native/README.md)
- [Systemd deployment guide](deployment/systemd/README.md)
- [Agent evaluation tests](docs/agent-eval-tests.md)
- [Layered product architecture](docs/architecture/layered_product_architecture.md)
- [License](LICENSE)
- [Security policy](SECURITY.md)
