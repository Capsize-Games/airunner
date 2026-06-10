# syntax=docker/dockerfile:1
# ---------------------------------------------------------------------------
# AI Runner — local development image (open-core).
#
# One slim base for dev and prod: torch's Linux wheels bundle their own CUDA
# runtime, so GPU support in dev needs only `--gpus` passthrough on the host
# (nvidia-container-toolkit) — no heavy nvidia/cuda base image required.
#
# The service package is installed EDITABLE and the working source is
# bind-mounted at runtime (see docker-compose.yml) for live reload. This image
# never bundles the private `extensions/` tree (see .dockerignore); extensions
# are bind-mounted in dev.
# ---------------------------------------------------------------------------
FROM python:3.13-slim-bookworm

# Which extras to install. "server" pulls the full local ML stack (torch,
# llama-cpp-python, diffusers, …) so GPU features work in dev. Override with
# --build-arg EXTRAS=core for a lighter, API-only dev image.
ARG EXTRAS=server

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    AIRUNNER_BASE_PATH=/data \
    DEV_ENV=1

# System libraries: build toolchain for llama-cpp-python / native wheels plus
# the runtime shared libs Pillow / OpenCV / audio stacks expect.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential cmake git curl pkg-config \
        libgl1 libglib2.0-0 libsndfile1 ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy the service source and install it editable. The BuildKit pip cache mount
# keeps the (large) wheel downloads — torch, etc. — across rebuilds so editing
# code never re-downloads dependencies.
# README.md is needed at build time — package_metadata.py reads it from
# the repo root to populate the package's long_description.
COPY README.md ./
COPY server ./server
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -e "./server[${EXTRAS}]"

COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Per-user data / model cache lives on a named volume.
RUN mkdir -p /data
VOLUME ["/data"]

EXPOSE 8080
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["airunner-server", "--host", "0.0.0.0", "--port", "8080"]
