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

The initial owner exception covered the canonical llama.cpp/whisper.cpp
creator-origin flag for the reviewed runtime identity. The owner's later
standing decision covers origin flags for every reviewed dependency and
reviewed transitive component; see `../DEPENDENCY_DECISIONS.md`. It therefore
covers the origin flag for reviewed llama.cpp revision
`7acb4e8cd2ce21f457d1298e75fad729520d263c`. Source changes, build behavior,
licenses, advisories, model inputs and actual runtime acceptance still need
their own evidence; the origin exception does not preapprove those checks.

## Build recipe status

The source recipe in `.github/workflows/cuda-build-image-inventory.yml` pins the
wrapper commit and validates its original gitlink, reconstructs the reviewed
backend source from a separately pinned llama.cpp commit, verifies the
reviewed backend wheels and CMake archive by SHA-256, disables network during
CMake compilation, and verifies the configured `120a-real` target and an SM
120-family code object before producing a short-lived candidate artifact. The
pinned CUDA 12.9.2 image inventory was completed in hosted run `41363193817`.
The first source-wheel attempt, run `41371760061`, failed during CMake discovery
before compilation and produced no wheel. Its scrubbed environment omitted the
backend's CI marker, leaving a five-second tool-discovery timeout around Docker
startup. The recipe now retains that marker and explicitly probes CMake first.

The current workflow disables Git hooks in each temporary source repository,
pins the existing `actions/setup-python` action by full commit, and selects
CPython 3.13.5. It verifies the three backend wheel hashes, extracts those
wheel files without invoking pip, and calls the reviewed
`scikit_build_core.build.build_wheel` API directly. The backend receives a
scrubbed environment, including the selected interpreter's shared-library path;
CMake compilation runs in the network-disabled container. The interpreter
installer receives `PIP_NO_INDEX=1` to prevent a network upgrade of its bundled
pip. The first failed run did upgrade pip to 26.2.2 during interpreter setup;
that run does not establish a validated build input or wheel. A later corrected
recipe produced the short-lived `.1` candidate reviewed for the V4 graph. Its
9B Qwen3.5 Q8_0/32k runtime probe exposed a pinned-source architecture gap: the
exact backend requested recurrent tensor `blk.32.ssm_conv1d.weight` from the
appended MTP block, which is dense and does not contain that tensor. Loading
failed before material GPU allocation; this was not an out-of-memory result.

The wheel target is limited to Linux x86_64, CPython 3.13, CUDA Toolkit 12.9,
and `120a-real`. It is not validated for runtime behavior, other GPUs, or model
fit. The job uses the clean reconstructed Git source, loads no model, and
accesses no GPU.

## Qwen3.5 MTP source update

The new candidate uses wrapper tag `v0.3.21` at
`d2bcbac46605f11d382426dd88d67e8b5c124cd7`, retains the reviewed
diskcache-optional patch, and sets package version `0.3.21+capsize.2`. Its
vendored llama.cpp source is pinned to upstream commit
`7acb4e8cd2ce21f457d1298e75fad729520d263c`, which distinguishes trunk layers
from appended MTP layers. The full f535-to-7acb source delta and build-surface
review are documented in the private ignored evidence file
`.headlesscode/service-audit-2026-11-02/linux-release-lock/llama-qwen35-mtp-source-update-review.md`.

The hosted recipe explicitly disables the server, UI, prebuilt UI and app
targets because this source revision adds optional UI asset provisioning that
can run `npm install` or fetch a prebuilt asset. CUDA compilation remains
network disabled. The recipe and source update are committed on the service PR.
Run `41541686308` for commit `d5050a3a097df6d841dd1d01799c96b62050467a` passed
the image inventory and was still compiling at the time of this review. The
wheel hash, RECORD, SM120a object, notices, install/import check and repeat
Qwen3.5 9B Q8_0 32k service acceptance remain pending. No model or GPU
execution occurred in the build job.

The matching private wrapper source update was merged in PR #8 as
`053cd860baa7d94a42d62908e37487155e662d9d`. Its unique annotated tag
`v0.3.21+capsize.2` is pushed and verified to peel to that merge. The
[private source release](https://github.com/Capsize-Games/llama-cpp-python-maintenance/releases/tag/v0.3.21%2Bcapsize.2)
was published and read back. Private Actions remain disabled; the three
focused static diskcache tests passed locally, and no private CI run is
claimed. CUDA wheel and model acceptance remain separate pending checks.
