# Native runtimes v0.3.0

## Release and input identity

- Repository: `Capsize-Games/airunner-native`; default branch `master`.
- Merged source: `3d1806423402f47d1f7612a8cd8fc70d48c5a3c2`.
- Annotated tag: `v0.3.0`; tag object `9262d36579aefa471c5bec217b3d93e81faa2678`.
- [Immutable release](https://github.com/Capsize-Games/airunner-native/releases/tag/v0.3.0).
- [Build, native OS smoke and publication run](https://github.com/Capsize-Games/airunner-native/actions/runs/41745941955).
- The exact source and tag are preserved in the private native maintenance copy
  under `review/v0.3.0`. Its GitHub Actions remain disabled.

All nine published assets were independently downloaded. Sizes and SHA-256
values match GitHub asset digests; each archive checksum and external provenance
record matches the source, tag and platform. This is a new release; existing
release tags and assets were preserved.

| Asset | Archive SHA-256 |
|---|---|
| Linux CPU | `59adcd438fed44c63ed65a4b17cfbf4afbdecaba164cfeec3d300b909dd5d9e0` |
| Windows CPU | `b7f671b693b1a78c6d100e5287306bd5a05420a5ef46c7d5d7fd4e72882c7aa1` |
| Linux CUDA SM120a | `c7ba474841f4a57ac3253cca0abf49b9e48160ef91782d99981cf2c0017860ff` |

CPU pins remain llama.cpp `47a39665e7081dc482feec169961acc09750a5c4`
(`b10000`) and whisper.cpp `d1be6fde11ac6e0407606b4e42fe72d34add8037`
(`v1.9.5`). The reviewed Whisper authentication patch SHA-256 is
`572fe28464c442cc5df657fde57a19acc2a9f8031670a0c4f0e5a97bf38e440b`.
It guards requests before routing with the documented health exception; credentials
are read from a bounded private key file rather than exposed in process arguments.

The CUDA profile uses llama.cpp `7acb4e8cd2ce21f457d1298e75fad729520d263c`,
source tree `5a77024ea13397365f3be1610bee5573b0c42f1f`, plus the reviewed
all-layer MTP offload patch SHA-256
`09ce5a6113a69416dfa721f4be19c4d70f75c4b36028ece9926786c5bba814a4`.
Its producer is `7495314cf3a7c9391eb8ee48aab8b74f3e38b659`, recipe digest
`020b43658e528a726972e0cff647510263e755c1ec0a045833936a3f4a674d76`.
The nine producer recipe files are unchanged at the publication source.

## Bounded review and verification

Review covers pinned native inputs and patches, build isolation and provenance,
archive validation, complete runtime/license payload staging, producer recipe
identity, native child authentication, Windows runtime imports, CUDA wrapper
library confinement, exact manifest inventories and immutable publication.
The CUDA runtime libraries were matched to reviewed wheel members; ELF dependency
and runpath records were checked. The wrapper sets its own library path and
changes to `/` before execution. Required upstream/runtime notices are retained.
Toolchain packages supplied by hosted runner repositories remain outside this
bounded source review; this does not claim exhaustive upstream-line or compiler
review. Reviewed runtime origin exceptions remain recorded in
[DEPENDENCY_DECISIONS.md](../DEPENDENCY_DECISIONS.md).

The promotion checksum defect was fixed before publication: original candidate
README and inventories are retained under `provenance/candidate-inputs/`, fresh
checksums cover current profile files, the profile manifest includes those
checksums, and the archive checksum binds the complete package. Regression tests
verify original bytes, exact inventory closure, real `sha256sum --check`, tamper
rejection and deterministic archive output.

Merged-source input CI passed 89 tests without skips. Local discovery passed
87 tests and skipped two because the patched Whisper source was unavailable
locally. The hosted workflow prepared that exact source and ran both tests.
CPU Linux and Windows builds and native OS version/help smoke checks passed.
The published-event-only verification job was skipped on workflow dispatch;
the promotion job performed and passed immutable publication verification itself.
Independent API readback confirmed stable, non-draft, immutable state and all
nine assets. No second release-event execution is claimed.

## CUDA acceptance and limits

The accepted candidate completed native inference on an RTX 5080, using the exact
Qwen3.5-9B Q8_0 model SHA-256
`b58fe056b5435070240de259f3f981aa38fee96825bbd78c088d5fd90e46f2b5`,
32,768-token context and 34/34 offloadable layers. Authentication, an actual
answer, typed child-failure handling and owned-process cleanup passed. The
public-safe receipt is embedded in `provenance/promotion.json`; private device
identifiers, process IDs and host paths are excluded. The application archive
verifier also accepted the promoted profile and its independent pins.

This establishes the native boundary and published asset identities. It does
not establish the normal application API, frozen service inference/cancellation,
Docker operation, broad model quality, warm P95 latency or multimodal acceptance.
Those remain scoped to their incremental releases. Models and the NVIDIA driver
are supplied separately. CORE does not require CUDA for installation.
