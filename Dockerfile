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

# Install pip for Python 3.13
RUN curl -sS https://bootstrap.pypa.io/get-pip.py | python3.13

# Upgrade pip tooling (install system-wide; no venv inside the container)
RUN python3.13 -m pip install --upgrade pip setuptools wheel

# Build llama-cpp-python from source when the llm-native profile is used.
# Default to CPU builds so local dev works without NVIDIA drivers.
# To enable CUDA builds, pass: --build-arg AIRUNNER_ENABLE_CUDA=1
ARG AIRUNNER_ENABLE_CUDA=0
ARG GGML_CUDA_ARCHITECTURES=
RUN set -e; \
    if printf '%s' ",${AIRUNNER_INSTALL_PROFILES}," | \
        grep -Eq ',(llm-native|linux-release|headless|desktop|all|all_dev|all_native|all_dev_native),'; then \
        if [ "${AIRUNNER_ENABLE_CUDA}" = "1" ]; then \
            if [ -z "${GGML_CUDA_ARCHITECTURES}" ]; then \
                echo "ERROR: AIRUNNER_ENABLE_CUDA=1 requires GGML_CUDA_ARCHITECTURES" >&2; \
                echo "Pass e.g. --build-arg GGML_CUDA_ARCHITECTURES=120 for sm_120 (RTX 5080)" >&2; \
                echo "so the image never silently builds a wrong-arch llama.cpp." >&2; \
                exit 1; \
            fi; \
            CUDA_STUB_DIR="/usr/local/cuda/targets/x86_64-linux/lib/stubs"; \
            if [ ! -f "${CUDA_STUB_DIR}/libcuda.so" ]; then \
                echo "CUDA stub libcuda.so not found at ${CUDA_STUB_DIR}/libcuda.so"; \
                exit 1; \
            fi; \
            ln -sf "${CUDA_STUB_DIR}/libcuda.so" \
                "${CUDA_STUB_DIR}/libcuda.so.1"; \
            export LD_LIBRARY_PATH="${CUDA_STUB_DIR}:${LD_LIBRARY_PATH:-}"; \
            export LIBRARY_PATH="${CUDA_STUB_DIR}:${LIBRARY_PATH:-}"; \
            export CMAKE_ARGS="-DGGML_CUDA=on -DCMAKE_EXE_LINKER_FLAGS=-Wl,-rpath-link,${CUDA_STUB_DIR}"; \
            if [ -n "${GGML_CUDA_ARCHITECTURES}" ]; then \
                export CMAKE_ARGS="${CMAKE_ARGS} -DGGML_CUDA_ARCHITECTURES=${GGML_CUDA_ARCHITECTURES} -DCMAKE_CUDA_ARCHITECTURES=${GGML_CUDA_ARCHITECTURES}"; \
            fi; \
        else \
            export CMAKE_ARGS="-DGGML_CUDA=off"; \
        fi; \
        export FORCE_CMAKE=1; \
        python3.13 -m pip install --no-cache-dir \
            --no-binary=llama-cpp-python \
            "llama-cpp-python==0.3.21"; \
    fi

# Set working directory
WORKDIR /app

# Copy project files: services-only (headless daemon + FastAPI) plus
# the local native package. The former root GUI package (setup.py +
# src/airunner) was removed. airunner_common moved to its own
# repository and is a normal published dependency now (issue #2197),
# resolved from PyPI by services/native's own declared dependency.
COPY pyproject.toml README.md ./
COPY services/ ./services/
COPY native/ ./native/

# Install each local package explicitly in dependency order
# (services -> native). services/native setup.py no longer imports
# airunner_common at build time (issue #2038), so --no-build-isolation
# is no longer required.
# The services extras pin CUDA builds of torch (torch==2.13.0+cu129 etc.),
# which are only published on the PyTorch CUDA index (download.pytorch.org),
# not PyPI; the extra index is passed to the services install so the pinned
# +cu129 wheels resolve inside the CUDA base image.
# The debian python3-cryptography (pulled in by the deadsnakes/other apt
# packages above) has no RECORD file, so pip cannot upgrade it to the pinned
# cryptography==50.0.2 and aborts with "uninstall-no-record-file". Purge it
# before the pip installs so the pinned version installs cleanly.
RUN set -e; \
    if dpkg -l python3-cryptography >/dev/null 2>&1; then \
        apt-get purge -y python3-cryptography; \
    fi; \
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
        python3.13 -m pip install \
            --extra-index-url https://download.pytorch.org/whl/cu129 \
            -e "./services[${service_profiles}]"; \
    else \
        python3.13 -m pip install -e ./services; \
    fi; \
    python3.13 -m pip install -e ./native

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
