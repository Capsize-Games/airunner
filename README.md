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

- `core`, `llm-native`, `stt-native`, `art-python`, `tts-python`, and `tts-python-core`
- `headless`, which aggregates LLM, STT, art, and TTS runtime extras
- `desktop`, a legacy extra name for a broader service profile; it does not install a GUI
- `linux-release`, the current Linux candidate aggregate, which excludes the TTS vendor
- `development`, for contributor and packaging tools

For the published distribution name, `airunner-services[development]` denotes the development extra. The local editable-install command below uses the checkout path instead.

Some extras still cannot be resolved from the configured public indexes. PyPI
publication of `airunner-common` and `facehuggershield` remains paused;
`airunner-common==6.1.8` is available from its reviewed
[GitHub release](https://github.com/Capsize-Games/airunner-common/releases/tag/v6.1.8),
and FacehuggerShield is optional through the `legacy-shield` extra and excluded
from `linux-release`. The evaluation workflow checks out pinned
`airunner-common` source for compatibility tests. Separately, the TTS extras
depend on `airunner-tts-vendor`; issue
[#2413](https://github.com/Capsize-Games/airunner/issues/2413) records unresolved
PyPI availability. `tts-python`, `headless`, `desktop`, `all`, `all_dev`,
`all_native`, `all_dev_native`, and `windows` inherit that dependency and are not
available from the configured public indexes. The validated offline V6 input
lock for `linux-release` does not establish clean public-index resolution for
other profiles.

The Linux `linux-release` aggregate excludes `airunner-tts-vendor`; OpenVoice
and Melo support are deferred from that release profile. Its V6 hash lock is
generated and validated for 244 reviewed inputs; see the
[V6 input validation record](release-planning/services/input-reviews/linux-release-v6-input-validation.md).
This offline input validation is separate from clean public-index resolution for
paused distributions, and from final frozen-artifact and model acceptance.

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
inputs="$(mktemp -d /tmp/airunner-docker-inputs.XXXXXX)"
python scripts/stage_docker_release_inputs.py --output-dir "$inputs"
AIRUNNER_DOCKER_REVIEWED_INPUTS="$inputs" \
  docker compose -f docker-compose.dev.yml run --rm --service-ports airunner

# Use the image reference in the release compose file.
docker compose -f docker-compose.release.yml run --rm --service-ports airunner
```

The development build stages hash-pinned runtime, builder, and pip bootstrap wheels outside the checkout. The Dockerfile uses the reviewed pip wheel to bootstrap the system Python because these inputs do not include a reviewed `uv` executable; dependency installation then uses the staged hash locks without an index. Set `GH_TOKEN` in the environment with read access to this repository's Actions artifacts before staging; the command does not print or persist the token. The staging command copies only the reviewed release source files and notices into the prepared context. Compose fails with a message pointing here when `AIRUNNER_DOCKER_REVIEWED_INPUTS` is unset.

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
