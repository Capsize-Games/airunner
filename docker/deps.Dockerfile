# syntax=docker/dockerfile:1
# ---------------------------------------------------------------------------
# Pre-installed server dependency base image.
#
# Built and pushed to ghcr.io when server/package_metadata.py dependencies
# change.  Contains all pip deps for `server[server]` plus the system packages
# (libgl, ffmpeg, etc.) the runtime needs.  The local docker/Dockerfile pulls
# this image, so `pip install -e server[server]` only creates the .pth link
# and swaps in the CUDA llama-cpp-python wheel — no heavy downloads.
#
#   docker build -f docker/deps.Dockerfile -t airunner-server-deps .
# ---------------------------------------------------------------------------

FROM python:3.13-slim-bookworm

# System libraries the runtime expects (Pillow, OpenCV, audio stacks).
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential cmake git curl pkg-config \
        libgl1 libglib2.0-0 libsndfile1 ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# README.md is needed at install time — package_metadata.py reads it from
# the repo root to populate the package's long_description.
COPY README.md ./
COPY server ./server

# Install all server[server] deps.  Includes llama-cpp-python (CPU) which is
# replaced with the CUDA wheel at image build time when AIRUNNER_LLAMA_CUDA=1.
# Using --no-cache-dir because BuildKit cache mounts behave differently across
# buildx drivers; the image is rebuilt infrequently enough that warm-cache
# benefit is marginal.
RUN pip install --no-cache-dir "./server[server]"
