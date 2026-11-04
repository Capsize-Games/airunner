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

# Validate every staged .deb and the associated lock receipt before the first
# package installation in this image build.
RUN --network=none \
    --mount=type=bind,from=reviewed-inputs,source=postgresql,target=/tmp/release-inputs/postgresql,ro \
    --mount=type=bind,from=reviewed-inputs,source=postgresql-build-supplement,target=/tmp/release-inputs/postgresql-build-supplement,ro \
    set -eu; \
    (cd /tmp/release-inputs/postgresql && sha256sum -c SHA256SUMS); \
    (cd /tmp/release-inputs/postgresql-build-supplement && sha256sum -c SHA256SUMS)

# The full Linux/NVIDIA image carries both CPU sidecars and the separately
# verified CUDA profile. Validate the staged tree offline before it enters an
# image layer; shipping the profile does not start a model or backend.
RUN --network=none \
    --mount=type=bind,from=reviewed-inputs,source=native-runtime,target=/tmp/release-inputs/native-runtime,ro \
    set -eu; \
    payload=/tmp/release-inputs/native-runtime/payload; \
    test -d "$payload"; \
    (cd "$payload" && sha256sum -c SHA256SUMS); \
    test -x "$payload/bin/llama-server"; \
    test -x "$payload/bin/whisper-server"; \
    test -f "$payload/share/airunner/licenses/llama.cpp-LICENSE"; \
    test -f "$payload/share/airunner/licenses/whisper.cpp-LICENSE"; \
    test -f "$payload/share/airunner/source_provenance.env"; \
    test -f "$payload/share/airunner/native-payload-receipt.json"; \
    test -x "$payload/share/airunner/native-runtimes/cuda-sm120a/bin/llama-server-cuda"; \
    test -f "$payload/share/airunner/native-runtimes/cuda-sm120a/profile-manifest.json"

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

# Install the reviewed Noble libpq closure and the glibc build compatibility
# supplement from verified local inputs. Full package control metadata comes
# from the verified .debs, so apt sees Provides/Breaks/Replaces/Multi-Arch.
RUN --network=none \
    --mount=type=bind,from=reviewed-inputs,source=postgresql,target=/tmp/release-inputs/postgresql,ro \
    --mount=type=bind,from=reviewed-inputs,source=postgresql-build-supplement,target=/tmp/release-inputs/postgresql-build-supplement,ro \
    set -eu; \
    runtime_inputs=/tmp/release-inputs/postgresql; \
    supplement_inputs=/tmp/release-inputs/postgresql-build-supplement; \
    (cd "$runtime_inputs" && sha256sum -c SHA256SUMS); \
    (cd "$supplement_inputs" && sha256sum -c SHA256SUMS); \
    repo=/tmp/airunner-postgresql-local; \
    mkdir -p "$repo/debs"; \
    cp "$runtime_inputs"/debs/*.deb "$repo/debs/"; \
    cp "$supplement_inputs"/debs/*.deb "$repo/debs/"; \
    cp "$runtime_inputs/install-packages.txt" "$repo/install-packages.txt"; \
    cat "$supplement_inputs/install-packages.txt" >> "$repo/install-packages.txt"; \
    : > "$repo/Packages"; \
    for deb in "$repo"/debs/*.deb; do \
        metadata="$(dpkg-deb -f "$deb")"; \
        filename="${deb##*/}"; \
        size="$(stat -c %s "$deb")"; \
        digest="$(sha256sum "$deb")"; digest="${digest%% *}"; \
        printf '%s\nFilename: debs/%s\nSize: %s\nSHA256: %s\n\n' \
            "$metadata" "$filename" "$size" "$digest" >> "$repo/Packages"; \
    done; \
    gzip -c -n -9 "$repo/Packages" > "$repo/Packages.gz"; \
    packages_sha="$(sha256sum "$repo/Packages")"; packages_sha="${packages_sha%% *}"; \
    packages_size="$(stat -c %s "$repo/Packages")"; \
    compressed_sha="$(sha256sum "$repo/Packages.gz")"; compressed_sha="${compressed_sha%% *}"; \
    compressed_size="$(stat -c %s "$repo/Packages.gz")"; \
    { printf 'Origin: AIRunner reviewed local PostgreSQL runtime inputs\nLabel: AIRunner Noble libpq runtime plus glibc build supplement\nSuite: noble-local\nCodename: noble-local\nArchitectures: amd64\nComponents: main\nDate: %s\nDescription: Hash-verified Ubuntu package inputs\nSHA256:\n' "$(date -Ru)"; \
      printf ' %s %s Packages\n %s %s Packages.gz\n' "$packages_sha" "$packages_size" "$compressed_sha" "$compressed_size"; } \
        > "$repo/Release"; \
    mkdir -p /usr/share/doc/airunner/release-inputs/postgresql \
        /usr/share/doc/airunner/release-inputs/postgresql-build-supplement; \
    cp "$runtime_inputs/SHA256SUMS" "$runtime_inputs/install-packages.txt" \
        "$runtime_inputs/staging-receipt.json" \
        "$runtime_inputs/postgresql-libpq-noble-runtime-lock.json" \
        /usr/share/doc/airunner/release-inputs/postgresql/; \
    cp "$supplement_inputs/SHA256SUMS" "$supplement_inputs/install-packages.txt" \
        "$supplement_inputs/staging-receipt.json" \
        "$supplement_inputs/postgresql-libpq-noble-build-supplement-lock.json" \
        /usr/share/doc/airunner/release-inputs/postgresql-build-supplement/; \
    apt_source=/tmp/airunner-postgresql-runtime.sources.list; \
    printf '%s\n' 'deb [trusted=yes] file:/tmp/airunner-postgresql-local ./' > "$apt_source"; \
    apt-get \
        -o Dir::Etc::sourcelist="$apt_source" \
        -o Dir::Etc::sourceparts=- \
        -o APT::Get::List-Cleanup=0 \
        update; \
    cp "$repo"/debs/*.deb /var/cache/apt/archives/; \
    xargs -r apt-get \
        -o Dir::Etc::sourcelist="$apt_source" \
        -o Dir::Etc::sourceparts=- \
        --no-download --no-remove --no-install-recommends -y install \
        < "$repo/install-packages.txt"; \
    rm -f "$apt_source"; \
    rm -rf "$repo" /var/lib/apt/lists/* /var/cache/apt/archives/*.deb /var/cache/apt/archives/partial/*

# Install Python 3.13.
RUN set -e; \
    add-apt-repository ppa:deadsnakes/ppa -y; \
    apt-get update; \
    apt-get install -y python3.13 python3.13-dev && rm -rf /var/lib/apt/lists/*

# Check the reviewed OS closure after all subsequent system package installs.
RUN python3.13 - <<'PY'
import json
from pathlib import Path
import subprocess

receipt_paths = (
    (Path("/usr/share/doc/airunner/release-inputs/postgresql/staging-receipt.json"), "runtime", 24),
    (Path("/usr/share/doc/airunner/release-inputs/postgresql-build-supplement/staging-receipt.json"), "build-supplement", 2),
)
format_field = chr(36) + "{Version}"
checked = 0
for receipt_path, kind, expected_count in receipt_paths:
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt.get("kind") != kind or receipt.get("package_count") != expected_count:
        raise SystemExit(f"reviewed PostgreSQL {kind} receipt has an unexpected shape")
    for package in receipt["packages"]:
        name = package["package"]
        expected = package["version"]
        result = subprocess.run(
            ["dpkg-query", "-W", "-f=" + format_field, name],
            check=True, capture_output=True, text=True, timeout=10,
        )
        actual = result.stdout.strip()
        if actual != expected:
            raise SystemExit(
                f"reviewed PostgreSQL runtime drift: {name} expected {expected}, got {actual}"
            )
        checked += 1
print(f"verified {checked} reviewed Ubuntu PostgreSQL runtime/build package identities")
PY

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

# Native speech is compiled from the reviewed source lock before the image
# build. Preserve its source archive, license texts, data and component receipt.
COPY --from=reviewed-inputs /native-speech/ /opt/airunner-speech/
COPY --from=reviewed-inputs /native-runtime/payload/ /opt/airunner/
RUN test -x /opt/airunner-speech/bin/espeak-ng && \
    test -s /opt/airunner-speech/share/espeak-ng-data/phondata && \
    install -m 0755 /opt/airunner-speech/bin/espeak-ng /opt/airunner/bin/espeak-ng && \
    cp -a /opt/airunner-speech/share/espeak-ng-data /opt/airunner/share/espeak-ng-data && \
    ln -s /opt/airunner/bin/espeak-ng /usr/bin/espeak-ng && \
    ln -s /opt/airunner/share/espeak-ng-data /usr/share/espeak-ng-data

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
ENV AIRUNNER_BUNDLE_ROOT=/opt/airunner

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
