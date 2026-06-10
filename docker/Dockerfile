# syntax=docker/dockerfile:1
# ---------------------------------------------------------------------------
# AI Runner — local development image (open-core).
#
# Fast path (default): pulls pre-built base images from GHCR so local builds
# are ~20 s instead of ~15 min.  The heavy CUDA compile and pip install work
# is done once by CI and cached as OCI images.
#
# Offline / CI fallback: set BUILD_LLAMA_CUDA_LOCAL=1 to compile llama-cpp-
# python from scratch and BUILD_DEPS_LOCAL=1 to install all pip deps locally.
#
#   docker compose -f docker-compose.yml -f docker-compose.gpu.yml build
#   BUILD_LLAMA_CUDA_LOCAL=1 ./scripts/docker.sh build   # offline mode
# ---------------------------------------------------------------------------

# Build a CUDA-enabled llama-cpp-python?  Set to 1 for GPU GGUF inference.
ARG AIRUNNER_LLAMA_CUDA=0
# Keep in sync with scripts/install.sh's pinned version.
ARG LLAMA_CPP_VERSION=0.3.26
# Build revision for the GHCR llama-cuda-builder image. Bump this (and the
# matching value in .github/workflows/build-base-images.yml) whenever the
# builder's compile flags change but LLAMA_CPP_VERSION stays the same, so the
# GHCR tag changes and stale local/CI caches don't serve the old wheel.
ARG LLAMA_BUILDER_REV=2
# Wheel source: "1" = pull from GHCR (fast, default).  "local" = compile
# from source (slow, for offline / CI without registry access).
ARG LLAMA_WHEEL_SOURCE=1
# Deps source: "0" = pull from GHCR (fast, default).  "1" = install all
# pip deps from scratch (slow, for dependency changes or offline builds).
ARG BUILD_DEPS_LOCAL=0

# -- Wheel source selection -------------------------------------------------

# Pre-built CUDA wheel image on GHCR.  Built from docker/builder.Dockerfile
# and pushed by .github/workflows/build-base-images.yml on version bumps.
FROM ghcr.io/capsize-games/airunner/llama-cuda-builder:v${LLAMA_CPP_VERSION}-${LLAMA_BUILDER_REV} AS llama-cuda-1

# Local fallback: compile llama-cpp-python with CUDA from source.  Identical
# to docker/builder.Dockerfile — kept inline so --build-arg
# BUILD_LLAMA_CUDA_LOCAL=local works without a separate file.
FROM python:3.13-slim-bookworm AS llama-cuda-local
ARG LLAMA_CPP_VERSION
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    CUDA_HOME=/usr/local/cuda-13.0
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential cmake git curl ca-certificates gnupg \
    && rm -rf /var/lib/apt/lists/*
RUN curl -fsSL -o /tmp/cuda-keyring.deb \
        https://developer.download.nvidia.com/compute/cuda/repos/debian12/x86_64/cuda-keyring_1.1-1_all.deb \
    && dpkg -i /tmp/cuda-keyring.deb \
    && apt-get update && apt-get install -y --no-install-recommends \
        cuda-nvcc-13-0 cuda-cudart-dev-13-0 cuda-driver-dev-13-0 \
        cuda-cccl-13-0 libcublas-dev-13-0 \
    && rm -rf /var/lib/apt/lists/* /tmp/cuda-keyring.deb
ENV PATH=${CUDA_HOME}/bin:${PATH} \
    CMAKE_BUILD_PARALLEL_LEVEL=8 \
    LIBRARY_PATH=${CUDA_HOME}/lib64/stubs:${CUDA_HOME}/targets/x86_64-linux/lib/stubs
RUN set -e \
    && STUB="$(find ${CUDA_HOME} -name libcuda.so 2>/dev/null | head -1)" \
    && if [ -z "${STUB}" ]; then \
         echo "FATAL: libcuda.so stub not found — is cuda-driver-dev-13-0 installed?" >&2; \
         exit 1; \
       fi \
    && echo "CUDA driver stub: ${STUB}" \
    && ln -sf "${STUB}" /usr/lib/x86_64-linux-gnu/libcuda.so.1 \
    && ldconfig \
    && ldconfig -p | grep -q libcuda.so.1 \
    # GGML_NATIVE=OFF avoids baking in the build host's CPU instructions
    # (e.g. AVX-512). Hosts without them (AMD Ryzen has AVX2 but no AVX-512)
    # otherwise crash with SIGILL on model load. Target a portable AVX2 set.
    && CMAKE_ARGS="-DGGML_CUDA=on -DCMAKE_CUDA_ARCHITECTURES=89;90;120 \
-DGGML_NATIVE=OFF -DGGML_AVX=ON -DGGML_AVX2=ON -DGGML_FMA=ON -DGGML_F16C=ON" \
       pip wheel --no-cache-dir --no-deps -w /wheels \
        "llama-cpp-python==${LLAMA_CPP_VERSION}"

# Empty stand-in so COPY --from=llama-wheels works unconditionally.
FROM python:3.13-slim-bookworm AS llama-cuda-none
RUN mkdir -p /wheels

FROM llama-cuda-none AS llama-wheels-0
FROM llama-cuda-${LLAMA_WHEEL_SOURCE} AS llama-wheels-1
FROM llama-wheels-${AIRUNNER_LLAMA_CUDA} AS llama-wheels

# -- Main image -------------------------------------------------------------
# Defaults for build-time overrides.
ARG AIRUNNER_LLAMA_CUDA
ARG LLAMA_WHEEL_SOURCE=1
ARG BUILD_DEPS_LOCAL=0
# Which extras to install.  "server" pulls the full local ML stack (torch,
# llama-cpp-python, diffusers, …) so GPU features work in dev.  Override with
# --build-arg EXTRAS=core for a lighter, API-only dev image.
ARG EXTRAS=server

# Base image: BUILD_DEPS_LOCAL=0 → pre-installed deps from GHCR (fast, default).
# BUILD_DEPS_LOCAL=1 → slim Python, install everything from scratch (slow).
FROM ghcr.io/capsize-games/airunner/server-deps:py3.13 AS base-0
FROM python:3.13-slim-bookworm AS base-1
FROM base-${BUILD_DEPS_LOCAL} AS base

# Re-declare ARGs so they are available inside this stage (ARGs declared
# before FROM are only visible to the FROM instruction itself).  Defaults
# must be repeated here; bare `ARG FOO` inherits from --build-arg but not
# from the preamble scope in all BuildKit versions.
ARG AIRUNNER_LLAMA_CUDA
ARG LLAMA_WHEEL_SOURCE=1
ARG BUILD_DEPS_LOCAL=0
ARG EXTRAS=server

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    AIRUNNER_BASE_PATH=/data \
    DEV_ENV=1 \
    # Let the (optionally CUDA-built) llama-cpp-python find the CUDA 13 runtime
    # libs that torch's cu130 wheels ship — avoids needing CUDA in this image.
    LD_LIBRARY_PATH=/usr/local/lib/python3.13/site-packages/nvidia/cu13/lib \
    # Force bitsandbytes to use the CUDA 13.0 backend.  Without this it
    # auto-detects CPU at install time (no GPU during docker build) and
    # caches that choice, causing "undefined symbol: cquantize_blockwise_bf16_nf4"
    # at runtime when the text encoder tries to use 4-bit quantization.
    BNB_CUDA_VERSION=130

# When building from the slim Python image (BUILD_DEPS_LOCAL=1), install system
# libraries and pip deps.  When using the pre-built base (BUILD_DEPS_LOCAL=0),
# these are already in the image — only the editable source link is needed.
WORKDIR /app
COPY README.md ./
COPY server ./server
RUN --mount=type=cache,target=/root/.cache/pip \
    if [ "${BUILD_DEPS_LOCAL}" = "1" ]; then \
        apt-get update && apt-get install -y --no-install-recommends \
            build-essential cmake git curl pkg-config \
            libgl1 libglib2.0-0 libsndfile1 ffmpeg \
        && rm -rf /var/lib/apt/lists/* \
        && pip install -e "./server[${EXTRAS}]"; \
    else \
        pip install -e "./server[${EXTRAS}]"; \
    fi

# Swap the CPU llama-cpp-python for the CUDA build when requested.  The wheels
# dir is empty when AIRUNNER_LLAMA_CUDA=0, so this is a no-op for CPU images.
# Verification checks the package filesystem (import loads the .so which
# requires libcuda.so.1, only available at *runtime* via GPU passthrough).
COPY --from=llama-wheels /wheels /tmp/llama-wheels
RUN if [ "${AIRUNNER_LLAMA_CUDA}" = "1" ]; then \
        pip install --force-reinstall --no-deps --no-cache-dir /tmp/llama-wheels/*.whl \
        && python -c "\
import pathlib, importlib.util; \
spec = importlib.util.find_spec('llama_cpp'); \
pkg = pathlib.Path(spec.origin).parent if spec else None; \
cuda = pkg and list(pkg.glob('lib/*cuda*')); \
assert cuda, 'CUDA libs missing — wheel was not a CUDA build'; \
print(f'llama-cpp-python CUDA build OK ({cuda[0].name})') \
"; \
    fi; \
    rm -rf /tmp/llama-wheels

COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Per-user data / model cache lives on a named volume.
RUN mkdir -p /data
VOLUME ["/data"]

EXPOSE 8080
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["airunner-server", "--host", "0.0.0.0", "--port", "8080"]
