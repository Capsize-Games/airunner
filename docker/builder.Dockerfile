# syntax=docker/dockerfile:1
# ---------------------------------------------------------------------------
# Standalone CUDA-enabled llama-cpp-python wheel builder.
#
# Built and pushed to ghcr.io by CI when LLAMA_CPP_VERSION changes.  The
# produced image contains /wheels/llama_cpp_python-*.whl — the compiled CUDA
# wheel.  The local docker/Dockerfile pulls this image instead of recompiling.
#
#   docker build --build-arg LLAMA_CPP_VERSION=0.3.26 -f docker/builder.Dockerfile -t llama-cuda-builder .
# ---------------------------------------------------------------------------

ARG LLAMA_CPP_VERSION=0.3.26

FROM python:3.13-slim-bookworm
ARG LLAMA_CPP_VERSION
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    CUDA_HOME=/usr/local/cuda-13.0

# Build toolchain
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential cmake git curl ca-certificates gnupg \
    && rm -rf /var/lib/apt/lists/*

# NVIDIA CUDA apt repo (debian12 = bookworm).
RUN curl -fsSL -o /tmp/cuda-keyring.deb \
        https://developer.download.nvidia.com/compute/cuda/repos/debian12/x86_64/cuda-keyring_1.1-1_all.deb \
    && dpkg -i /tmp/cuda-keyring.deb \
    && apt-get update && apt-get install -y --no-install-recommends \
        cuda-nvcc-13-0 cuda-cudart-dev-13-0 cuda-driver-dev-13-0 \
        cuda-cccl-13-0 libcublas-dev-13-0 \
    && rm -rf /var/lib/apt/lists/* /tmp/cuda-keyring.deb

# ggml-cuda links the CUDA *driver* API (libcuda / cuMem*, cuDevice*).  The
# real driver is absent at build time, so cuda-driver-dev-13-0 provides the
# driver stub (libcuda.so) at the standard toolkit stubs path.  The genuine
# libcuda.so.1 is supplied by the host GPU driver at runtime via nvidia-
# container-toolkit.
ENV PATH=${CUDA_HOME}/bin:${PATH} \
    CMAKE_BUILD_PARALLEL_LEVEL=8 \
    LIBRARY_PATH=${CUDA_HOME}/lib64/stubs:${CUDA_HOME}/targets/x86_64-linux/lib/stubs

# ggml-cuda links the CUDA *driver* API (libcuda / cuMem*, cuDevice*).  The
# driver stub SONAME is libcuda.so.1 but the file is named libcuda.so.  ld
# does NOT search -L paths to resolve a shared lib's NEEDED dependencies — it
# only uses -rpath-link and the default linker paths — so a symlink in the
# stubs dir alone is not enough.  Publish the stub under the name the linker
# expects (libcuda.so.1) on a standard linker directory and run ldconfig so
# both the link step and transitive resolution resolve the driver symbols.
# The genuine libcuda.so.1 is provided by the host GPU at runtime.
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
    # GGML_NATIVE=OFF disables -march=native so the wheel does not bake in
    # the CI builder's CPU instructions (e.g. AVX-512). Without this, hosts
    # that lack those instructions (e.g. AMD Ryzen, which has AVX2 but no
    # AVX-512) crash with SIGILL ("Illegal instruction") on model load. We
    # target a portable AVX2 baseline that all modern x86-64 CPUs support.
    && CMAKE_ARGS="-DGGML_CUDA=on -DCMAKE_CUDA_ARCHITECTURES=89;90;120 \
-DGGML_NATIVE=OFF -DGGML_AVX=ON -DGGML_AVX2=ON -DGGML_FMA=ON -DGGML_F16C=ON" \
       pip wheel --no-cache-dir --no-deps -w /wheels \
        "llama-cpp-python==${LLAMA_CPP_VERSION}"

VOLUME ["/wheels"]
