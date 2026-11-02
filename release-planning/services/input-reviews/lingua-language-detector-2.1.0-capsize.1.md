# Lingua language detector 2.1.0+capsize.1

**Disposition:** reviewed Linux CPython 3.13 candidate. This input is suitable
for the matching Linux x86_64 CPython 3.13 target after the parent lock and
selected-artifact manifest are updated to this wheel hash. It is not a
manylinux portability claim.

## Source and maintenance history

- Upstream source: `pemistahl/lingua-rs` tag `v1.7.0`, commit
  `c6eea404d8e09b7f455da2da79f7f6f0e149ce76`.
- Private maintenance repository: `Capsize-Games/lingua-python-maintenance`.
- PR #1 merged to its actual default branch `master` at
  `ed300698b165e48f52166fc9a102c47e5a491c2c`.
- Annotated tag: `v2.1.0-capsize.1`.
- Private release: <https://github.com/Capsize-Games/lingua-python-maintenance/releases/tag/v2.1.0-capsize.1>.
- GitHub Actions is disabled in that repository. No CI checks ran. The private
  repository plan did not permit branch protection configuration; no branch
  protections were changed.

The Python distribution version is `2.1.0+capsize.1`; the Rust package remains
at upstream version `1.7.0`. The patch updates PyO3 to `0.29.2` and
`crossbeam-epoch` to `0.9.20`. It restores enum copy/deepcopy and enum-valued
property identity behavior that changed under PyO3 0.29. All 75 language model
features and Python pickle support remain enabled.

## Source and dependency review

The review covered the project Rust and Python runtime, embedded language model
source trees, packaging metadata, selected Linux normal/build dependencies, and
their build scripts. The selected tree contains 67 registry crates. Exact
Cargo archives match the locked checksums; source archive hashes, license
texts, and build-script paths are recorded in the private source repository.
Fifteen selected build scripts were reviewed. The selected hooks make compiler,
target, or Python configuration probes; no selected hook has network,
telemetry, credential, or unrelated process behavior.

The first exact selected-tree OSV query reported `crossbeam-epoch 0.9.18`
(`RUSTSEC-2026-0204`) and PyO3 0.24.0 advisories `GHSA-36hh-v3qg-5jq4`,
`GHSA-chgr-c6px-7xpp`, `GHSA-pph8-gcv7-4qj5`, `RUSTSEC-2025-0020`,
`RUSTSEC-2026-0176`, and `RUSTSEC-2026-0177`. The selected graph now uses
PyO3 0.29.2 and crossbeam-epoch 0.9.20. The follow-up exact-version query for
all 67 selected crates returned no findings on 2026-11-02. The report is
scoped to this selected graph and query date; it does not characterize dormant
development or non-Linux lock entries.

The upstream Apache-2.0 project license is preserved. The wheel declares 127
license files: the project license, 125 license/notice texts for the selected
Cargo graph, and the Cargo notice manifest. Three notice texts omitted from
their crate archives are tied to exact upstream Git blobs. The selected notice
scope does not claim every Cargo.lock entry is compiled or linked.

## Artifact and verification

- Wheel: `lingua_language_detector-2.1.0+capsize.1-cp313-cp313-linux_x86_64.whl`
- SHA-256: `54e28516c3700995cd9336eee0d569f7e8fc41fdbe2c7f36602e1da7edd000db`
- Extension SHA-256: `165734b9334a5ab06c6a74b88fafd8a36804c535d45d0c8db994ecb4458d854e`
- Platform: Linux x86_64, CPython 3.13. The ELF symbol ceiling is GLIBC 2.34;
  no manylinux or non-Linux portability claim is made.
- Build: Maturin 1.16.0, Rust 1.99.1, Python 3.13.5, one Cargo job,
  `CARGO_NET_OFFLINE=true`, isolated HOME/Cargo cache, no production
  credentials, no model downloads, and no GPU workload.
- The wheel RECORD covers all 135 members. All 127 `License-File`
  declarations resolve to unique hashed wheel paths.
- The CycloneDX SBOM preserves component versions and dependency references.
  Its local source refs and purls are bound to merge SHA
  `ed300698b165e48f52166fc9a102c47e5a491c2c`; it contains no local filesystem
  paths or `file://` references.
- Exact installed wheel verification: 71 upstream Python tests passed; 2
  wheel-packager tests passed; all 75 languages loaded; the all-language
  detector classified an English sentence as English.

Full Rust workspace tests, WebAssembly tests, PyPy, Windows, macOS, and an
Ubuntu 24 runtime job were not run. No PyPI or crates.io publication occurred.
