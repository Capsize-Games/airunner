# Dockerfile for AI Runner - headless server only
# Provides HTTP API for LLM, Art generation, TTS, STT, and Vision
# consumed by airunnerweb. The former Qt desktop GUI was removed.
#
# Usage:
#   Headless mode: docker compose run --rm airunner --headless

# Base image pinned to NVIDIA CUDA 12.9.2 on Ubuntu 24.04. The tag is listed
# as supported by NVIDIA's CUDA container source revision
# eca680d0ef074c6f8c36069ca766539d8879527b. Verify/refresh with:
#   docker buildx imagetools inspect nvidia/cuda:12.9.2-devel-ubuntu24.04
# Manifest-list digest. amd64 child digest:
# sha256:420850a3fd665171b3f1fd08946c51d50468d732a46d6c42345ea04444755048
FROM nvidia/cuda:12.9.2-devel-ubuntu24.04@sha256:16656a1ef115bca9e1f820c6349876f1486d2b3c9a0e615773799fe402960dc5

# Prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Default install profile is the vendor-free Linux release aggregate.
# It does not include development tooling or the deferred OpenVoice/Melo
# vendor package.
ARG AIRUNNER_INSTALL_PROFILES=linux-release

# Fail before any apt/pip/network installs when an explicitly selected
# historical profile would activate the quarantined TTS vendor.
RUN case ",${AIRUNNER_INSTALL_PROFILES}," in \
    *,tts-python,*|*,headless,*|*,desktop,*|*,all,*|*,all_dev,*|*,all_native,*|*,all_dev_native,*|*,windows,*|*,openvoice,*|*,melotts,*|*,openvoice_cn,*|*,openvoice_jp,*|*,openvoice_kr,*|*,openvoice_tw,*|*,gruut_support,*) \
        echo "ERROR: AIRUNNER_INSTALL_PROFILES activates deferred airunner-tts-vendor; use linux-release while OpenVoice/Melo remain deferred" >&2; exit 1;; \
    *) exit 0;; \
esac

# The staged artifact manifest and lock cover exactly the linux-release extra.
# Other profile values cannot reuse this dependency graph safely.
RUN if [ "${AIRUNNER_INSTALL_PROFILES}" != "linux-release" ]; then \
        echo "ERROR: reviewed Docker inputs cover only AIRUNNER_INSTALL_PROFILES=linux-release" >&2; \
        exit 1; \
    fi

# Install system dependencies required by the selected runtime profiles.
RUN set -e; \
    profile_match() { \
        printf '%s' ",${AIRUNNER_INSTALL_PROFILES}," | \
            grep -Eq ",($1),"; \
    }; \
    packages="software-properties-common curl wget git build-essential"; \
    packages="$packages cmake pkg-config libprotobuf-dev"; \
    packages="$packages protobuf-compiler"; \
    if profile_match 'stt-native|tts-python-core|linux-release|headless|desktop|all|all_dev|all_native|all_dev_native'; then \
        packages="$packages ffmpeg libsndfile1 portaudio19-dev"; \
        packages="$packages pulseaudio libasound2-dev"; \
    fi; \
    if profile_match 'openvoice_jp|openvoice_kr|all_native|all_dev_native'; then \
        packages="$packages mecab libmecab-dev mecab-ipadic-utf8"; \
    fi; \
    apt-get update && apt-get install -y $packages && \
    rm -rf /var/lib/apt/lists/*

# Install Python 3.13.
RUN set -e; \
    add-apt-repository ppa:deadsnakes/ppa -y; \
    apt-get update; \
    apt-get install -y python3.13 python3.13-dev && rm -rf /var/lib/apt/lists/*

# Keep application wheels separate from Debian's Python packages. This image's
# supported offline bootstrap uses the standard-library environment creator and
# the reviewed, hash-pinned pip wheel rather than a network bootstrap installer.
RUN python3.13 -m venv --without-pip /opt/airunner-venv
ENV VIRTUAL_ENV=/opt/airunner-venv
ENV PATH="/opt/airunner-venv/bin:${PATH}"

# Set working directory
WORKDIR /app

# Copy project files: services-only (headless daemon + FastAPI) plus
# the local native package. The former root GUI package (setup.py +
# src/airunner) was removed. airunner_common moved to its own
# repository and is a normal published dependency now (issue #2197),
# resolved from PyPI by services/native's own declared dependency.
COPY pyproject.toml README.md LICENSE THIRD_PARTY_NOTICES.md ./
COPY services/ ./services/
COPY native/ ./native/

# Install from the exact runtime and builder wheelhouses staged by the release
# workflow. Bind mounts keep wheel archives out of image layers. The runtime
# lock installs first; the reviewed build closure then supports source installs
# without dependency resolution or build isolation. Provenance inputs remain in
# the image for inspection, while installed distributions retain their license
# files under site-packages.
RUN --mount=type=bind,from=reviewed-inputs,source=runtime,target=/tmp/release-inputs/runtime,ro \
    --mount=type=bind,from=reviewed-inputs,source=builder,target=/tmp/release-inputs/builder,ro \
    --mount=type=bind,from=reviewed-inputs,source=bootstrap,target=/tmp/release-inputs/bootstrap,ro \
    --mount=type=bind,from=reviewed-inputs,source=release-source,target=/tmp/release-inputs/source,ro \
    set -e; \
    mkdir -p /usr/share/doc/airunner/release-inputs/bootstrap; \
    cp /tmp/release-inputs/bootstrap/artifact-sources.json \
        /usr/share/doc/airunner/release-inputs/bootstrap/; \
    cp /tmp/release-inputs/bootstrap/selected-lock.txt \
        /usr/share/doc/airunner/release-inputs/bootstrap/; \
    cp /tmp/release-inputs/bootstrap/requirements.txt \
        /usr/share/doc/airunner/release-inputs/bootstrap/; \
    cp /tmp/release-inputs/bootstrap/staging-receipt.json \
        /usr/share/doc/airunner/release-inputs/bootstrap/; \
    PYTHONPATH=/tmp/release-inputs/bootstrap/pip-26.2.2-py3-none-any.whl \
        python3.13 -m pip install \
            --no-index --find-links=/tmp/release-inputs/bootstrap --no-deps \
            --require-hashes -r /tmp/release-inputs/bootstrap/requirements.txt; \
    pip_licenses="$(python3.13 -c 'import importlib.metadata as m; print(m.distribution("pip").locate_file("pip-26.2.2.dist-info/licenses"))')"; \
    test -d "$pip_licenses"; \
    mkdir -p /usr/share/doc/airunner/legal/bootstrap-pip; \
    cp -a "$pip_licenses/." /usr/share/doc/airunner/legal/bootstrap-pip/; \
    mkdir -p /usr/share/doc/airunner/release-inputs/runtime \
        /usr/share/doc/airunner/release-inputs/builder; \
    cp /tmp/release-inputs/runtime/artifact-sources.json \
        /usr/share/doc/airunner/release-inputs/runtime/; \
    cp /tmp/release-inputs/runtime/selected-lock.txt \
        /usr/share/doc/airunner/release-inputs/runtime/; \
    cp /tmp/release-inputs/runtime/requirements.txt \
        /usr/share/doc/airunner/release-inputs/runtime/; \
    cp /tmp/release-inputs/runtime/staging-receipt.json \
        /usr/share/doc/airunner/release-inputs/runtime/; \
    cp /tmp/release-inputs/builder/artifact-sources.json \
        /usr/share/doc/airunner/release-inputs/builder/; \
    cp /tmp/release-inputs/builder/selected-lock.txt \
        /usr/share/doc/airunner/release-inputs/builder/; \
    cp /tmp/release-inputs/builder/requirements.txt \
        /usr/share/doc/airunner/release-inputs/builder/; \
    cp /tmp/release-inputs/builder/staging-receipt.json \
        /usr/share/doc/airunner/release-inputs/builder/; \
    PIP_CONFIG_FILE=/dev/null python3.13 -m pip install \
        --no-index --find-links=/tmp/release-inputs/runtime \
        --require-hashes -r /tmp/release-inputs/runtime/requirements.txt; \
    PIP_CONFIG_FILE=/dev/null python3.13 -m pip install \
        --no-index --find-links=/tmp/release-inputs/builder --no-deps \
        --require-hashes -r /tmp/release-inputs/builder/requirements.txt; \
    known_profiles="$(python3.13 -c 'import types; src = open("./services/setup.py").read().replace("setup(**build_services_setup_kwargs(package_source_dir=\"src\"))", ""); m = types.ModuleType("probe"); m.__file__ = "./services/setup.py"; exec(compile(src, "setup.py", "exec"), m.__dict__); print(",".join(sorted(m.build_services_extras_require())))')"; \
    checked_profiles=""; \
    for profile in $(printf '%s' "${AIRUNNER_INSTALL_PROFILES}" | tr ',' ' '); do \
        case ",${known_profiles}," in \
            *",${profile},"*) checked_profiles="${checked_profiles},${profile}";; \
            *) echo "ERROR: unknown AIRUNNER_INSTALL_PROFILES entry '${profile}'. Known services extras: ${known_profiles}. The desktop GUI is removed; use 'linux-release' for the vendor-free release aggregate." >&2; exit 1;; \
        esac; \
    done; \
    service_profiles="${checked_profiles#,}"; \
    if [ -n "${service_profiles}" ]; then \
        PIP_CONFIG_FILE=/dev/null python3.13 -m pip install \
            --no-index --no-deps --no-build-isolation \
            -e "./services[${service_profiles}]"; \
    else \
        PIP_CONFIG_FILE=/dev/null python3.13 -m pip install \
            --no-index --no-deps --no-build-isolation -e ./services; \
    fi; \
    PIP_CONFIG_FILE=/dev/null python3.13 -m pip install \
        --no-index --no-deps --no-build-isolation -e ./native; \
    PIP_CONFIG_FILE=/dev/null python3.13 -m pip uninstall -y \
        altgraph pyinstaller pyinstaller-hooks-contrib wheel; \
    PYTHONPATH=/tmp/release-inputs/source/scripts python3.13 \
        /tmp/release-inputs/source/scripts/collect_runtime_dependency_notices.py \
        --spec /tmp/release-inputs/source/packaging/linux/services-bundle-spec.toml \
        --repo-root /tmp/release-inputs/source \
        --bundle-dir /usr/share/doc/airunner

# Create non-root user for running the container
# docker-compose may override the runtime UID/GID; avoid hard-coding 1000 here
RUN set -eux; \
    if ! getent group airunner >/dev/null; then groupadd -r airunner; fi; \
    if ! id -u airunner >/dev/null 2>&1; then useradd -r -g airunner -m -s /bin/bash airunner; fi; \
    mkdir -p /home/airunner/.local/share/airunner; \
    mkdir -p /home/airunner/.cache/huggingface; \
    chown -R airunner:airunner /home/airunner; \
    chown -R airunner:airunner /app; \
    true

# Copy entrypoint script
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV AIRUNNER_ENVIRONMENT=production
ENV HOME=/home/airunner
ENV HF_HOME=/home/airunner/.cache/huggingface
ENV AIRUNNER_DATA_DIR=/home/airunner/.local/share/airunner

# Expose the API port (used in headless mode)
EXPOSE 8080

# Health check for headless mode: the /health endpoint is exempt from the
# loopback X-Airunner-Token requirement (services api/server.py), so a plain
# curl is sufficient. The check FAILS when the API is down (no `|| exit 0`);
# in GUI mode there is no HTTP server on 8080, so the container is simply
# reported unhealthy.
HEALTHCHECK --interval=30s --timeout=10s --start-period=180s --retries=3 \
    CMD curl -f http://localhost:8080/health

# Use the headless entrypoint script (no GUI mode remains)
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]

CMD []
