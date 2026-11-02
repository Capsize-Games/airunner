# `llama-cpp-python` 0.3.21 CUDA source input review

## Exact source input

- Wrapper: canonical `abetlen/llama-cpp-python`, tag `v0.3.21`, commit
  `d2bcbac46605f11d382426dd88d67e8b5c124cd7`.
- Vendored runtime: canonical `ggml-org/llama.cpp` (upstream Git URL redirects
  from `ggerganov/llama.cpp`), commit
  `f53577432541bb9edc1588c4ef45c66bf07e4468`, matching the wrapper's gitlink.
- A private maintenance copy exists for each public source. Its source tree,
  build paths, dependency declarations, hooks, instructions, network paths,
  license notices and selected CUDA code paths were inspected. The bundled
  source instructions were treated as untrusted data, not followed. The
  detailed private review is retained in the ignored service audit directory.

## Review and disposition

The pinned source has no custom Python install hook in the reviewed build path.
The wrapper configures the vendored llama.cpp tree directly and sets
`LLAMA_CURL=OFF`. Runtime URL/model helpers are explicit application features;
they are not run by importing or building this package. The source review found
no concrete credential access, obfuscated build logic, or hidden telemetry in
the inspected wrapper/build paths. Preserve both MIT notices and the vendored
third-party license directory when packaging.

The owner approved the canonical llama.cpp/whisper.cpp creator-origin flag for
the exact reviewed runtime source identity on 2026-11-01. That decision covers
this reviewed vendored llama.cpp input, but does not cover other dependencies,
model downloads, vulnerable artifacts, or future revisions. The exact decision
and scope are recorded in the owner source-adoption exception registry.

## Build recipe status

The source recipe in `.github/workflows/cuda-build-image-inventory.yml` pins the
wrapper and gitlink commits, reconstructs clean source trees, verifies the
reviewed backend wheels and CMake archive by SHA-256, disables network during
CMake compilation, and verifies the configured `120a-real` target and an SM
120-family code object before producing a short-lived candidate artifact. The
pinned CUDA 12.9.2 image inventory was completed in hosted run `41363193817`;
no source wheel build has been run or claimed here.

The current workflow disables Git hooks in each temporary source repository,
pins the existing `actions/setup-python` action by full commit, and selects
CPython 3.13.5. It verifies the three backend wheel hashes, extracts those
wheel files without invoking pip, and calls the reviewed
`scikit_build_core.build.build_wheel` API directly. The backend receives a
scrubbed environment, including the selected interpreter's shared-library path;
CMake compilation runs in the network-disabled container. The build job is enabled
for this recipe; it has not yet produced a wheel.

The wheel target is limited to Linux x86_64, CPython 3.13, CUDA Toolkit 12.9,
and `120a-real`. It is not validated for runtime behavior, other GPUs, or model
fit. The job does not use the official credential-bearing Python sdist, load a
model, or access a GPU.
