# AIRunner native sidecars v0.2.3

## Release identity

- Repository: `Capsize-Games/airunner-native`
- Default branch: `master`
- Merged source SHA: `35a029f765bd25abdf792b968f229ea1f72ca5e2`
- Annotated tag: `v0.2.3` (tag object `1199f9a823c4fde6beb23d5e12d6593d989d7edc`, peeling to the merged SHA)
- Release: https://github.com/Capsize-Games/airunner-native/releases/tag/v0.2.3
- GitHub release state: published, stable, immutable; repository-only immutable release setting is enabled.
- Workflow run: https://github.com/Capsize-Games/airunner-native/actions/runs/41462967294

## Archive identity and provenance

The published archives were downloaded independently. Their calculated SHA-256 values match each archive's `.sha256` manifest, the GitHub asset digest, and the embedded provenance record. Both provenance files name merged source SHA `35a029f765bd25abdf792b968f229ea1f72ca5e2` and `refs/tags/v0.2.3`.

| Platform | Archive SHA-256 | GitHub asset digest |
| --- | --- | --- |
| Linux | `bc22b5928d3b566299fd7cf4cc4c2495bd54a978d0db244c232aaa094f91b15e` | `sha256:bc22b5928d3b566299fd7cf4cc4c2495bd54a978d0db244c232aaa094f91b15e` |
| Windows | `4755b91f564d56eac6ccb7027cd86a3bb18456354388e4d80e98f30cb2ce5bb1` | `sha256:4755b91f564d56eac6ccb7027cd86a3bb18456354388e4d80e98f30cb2ce5bb1` |

The remaining published asset digests are:

- Linux provenance: `sha256:1eb3fac49f22a0f6b9de5e5ef5add5889a3aaecbcdf60e6280572e88c26f9047`
- Linux checksum manifest: `sha256:61e644b5bc741d6f1fc536daad685ec0bfb7da2aa1ca796280d4daf2aa3d26d6`
- Windows provenance: `sha256:a0382472eea88712331b0f59defe9e931c4df599d5eb1a2a9717debc27f0f647`
- Windows checksum manifest: `sha256:a3bd93c8a31d590e8b87125d83a0b026111021e5c304a3d83909a744d59be605`

The bundle provenance pins llama.cpp commit `47a39665e7081dc482feec169961acc09750a5c4` (`b10000`) and whisper.cpp commit `d1be6fde11ac6e0407606b4e42fe72d34add8037` (`v1.9.5`). Both builds declare `GGML_NATIVE=OFF` and CUDA disabled. Windows declares static MinGW runtime linkage.

## CI and smoke evidence

Run `41462967294` completed successfully on the exact merged source SHA. Linux and Windows pinned builds and packaging passed. The Windows dynamic MinGW import check passed. The corresponding import-check step was skipped on Linux because it checks Windows executables. Native-OS smoke jobs launched the Linux and Windows `llama-server` and `whisper-server` binaries without model downloads or server startup: llama `--version` and `--help`, plus whisper `--help`, completed successfully on each native OS.

The `verify-published-release` job was skipped because this run was `workflow_dispatch`, not a `release` event. GitHub did not schedule a separate release-event run for the release created with `GITHUB_TOKEN`. The `promote-release` job itself passed its post-publish API assertions for a stable, non-draft, immutable release. A separate read-only GitHub API query confirmed that state and the six asset digests after publication.

No model files were downloaded and no GPU workload was run. These receipts establish archive provenance, native process startup/help behavior, and release immutability; they do not establish model inference, GPU behavior, or performance parity.

## License files present

Linux archive:

- `share/airunner/licenses/llama.cpp-LICENSE`
- `share/airunner/licenses/whisper.cpp-LICENSE`

Windows archive additionally includes:

- `share/airunner/licenses/GPL-3.txt`
- `share/airunner/licenses/mingw-gcc-runtime-copyright.txt`
- `share/airunner/licenses/mingw-runtime-source.txt`
- `share/airunner/licenses/winpthreads-COPYING.txt`

## Bounded source review

The exact released commit and its annotated tag were preserved in the owner-controlled private `Capsize-Games/airunner-native-maintenance` repository under branch `review/v0.2.3` and tag `v0.2.3`. That repository is private, GitHub Actions is disabled, and no upstream synchronization is configured. The private copy was compared from its reviewed base `0554185f27ac7db8f58e1ae8d59ba041e4118e62` to release SHA `35a029f765bd25abdf792b968f229ea1f72ca5e2`; the exact pinned upstream source commits were unchanged for llama.cpp (`47a39665e7081dc482feec169961acc09750a5c4`) and whisper.cpp (`d1be6fde11ac6e0407606b4e42fe72d34add8037`).

The bounded review covers the active builder, release workflow, archive packaging, Windows import checker, and fixture tests; exact third-party source and license review is recorded in the private maintenance review `review/native-pin-intake-2026-11-01.md`. The release delta adds explicit OpenMP-preserving builds, static Windows runtime linkage, Windows import checks, archive/provenance packaging, immutable-tag/release identity checks, and the required upstream/runtime license files. Action references in the workflow are immutable SHAs. The build fetches only the two canonical pinned source repositories; the reviewed CPU build disables RPC and CUDA and disables optional model-download/multimedia paths. The Windows runtime DLL and corresponding notices/source references are included. The source pins and upstream licenses are unchanged from the reviewed inputs.

No unresolved source-origin, license, credential, telemetry, agent-instruction, or unexpected-network finding remains in this bounded scope. The GitHub native build and native-OS smoke workflow passed as recorded above. No real models or GPU workload were run; third-party apt toolchain packages are supplied by the runner's package repositories, so their contents are outside this source review. This status does not claim exhaustive review of every upstream line or runtime behavior. `source_review_status` is now `reviewed` for the exact source SHA and scope stated here; the fail-closed gate remains in place for any other source pin.

The prior empty draft release records for `v0.2.0` and `v0.2.1` were removed after inspection; their tags were preserved. Existing `v0.2.2` release/tag/assets were left unchanged.
