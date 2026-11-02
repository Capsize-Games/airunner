# Kornia Rust wheel 0.2.0+capsize.2 review

## Source and artifact identity

- Private maintenance source tag: `v0.2.0-capsize.2`
- Merged source commit: `496257a15d3f38142549d0a57a48ba026b452cd0`
- Source archive: `kornia-rs-v0.2.0-capsize.2.tar.gz`, SHA-256 `4543ffa2295d5e3fdcc4741b6f1df7427f56eda03e3bd88d52be1982c0fed6bb`, 4,938,257 bytes.
- Cargo.lock SHA-256: `c05866ecbe4dfc397dc485a901d86dde847b11673f28e287f0838b815e6e42cf`.
- Wheel: `kornia_rs-0.2.0+capsize.2-cp313-cp313-manylinux_2_39_x86_64.whl`, SHA-256 `b976d7383abfff07811f3d7c1659d3c209709a514ca8289f02dbb646018ca5f2`, 4,615,211 bytes.
- The wheel was built from the exact source tag with the default CPU and TurboJPEG feature set, offline Cargo/Maturin, and one Cargo build job. It targets CPython 3.13 on x86_64 Linux and uses the `manylinux_2_39` ABI floor. CUDA was not enabled. No model weights or GPU workload were downloaded or run.

## Review scope and changes

The review covered the exact private source revision, its Cargo.lock dependencies, build configuration, the selected CPU/TurboJPEG feature graph, generated wheel metadata and SBOM, and packaged license notices. The owner-controlled maintenance copy has Actions disabled. No production credentials were used. The build was offline.

The fixed dependency changes preserve the existing feature surface:

- PyO3 and its family move from 0.28.3 to 0.29.2, with the compatible NumPy Rust binding updated to 0.29.0 and its changed type-object API call updated.
- The optional DLPack bridge uses the reviewed private `dlpack-rs` 0.3.4 compatibility release.
- `quick-xml` is 0.41.0, including the corresponding reviewed `little_exif` source update.
- `anyhow` is 1.0.103. TurboJPEG remains enabled.
- `bincode` 2.0.1 remains. RustSec classifies RUSTSEC-2025-0141 as unmaintained; it does not identify a vulnerability or patched version. The reviewed selected decoding paths use fixed-size PLY fields and a bounded BoW reader that checks declared block counts before allocation. The public decoding traits and file formats remain available.
- `paste` 1.0.15 remains. RUSTSEC-2024-0436 is an unmaintained notice, not a vulnerability. It is used at compile time by macro consumers; replacement would require changing those consumers and revalidating the selected kernels. No feature was removed for this disposition.

Advisory references: [RUSTSEC-2026-0176](https://rustsec.org/advisories/RUSTSEC-2026-0176.html), [RUSTSEC-2026-0177](https://rustsec.org/advisories/RUSTSEC-2026-0177.html), [RUSTSEC-2026-0190](https://rustsec.org/advisories/RUSTSEC-2026-0190.html), [RUSTSEC-2026-0194](https://rustsec.org/advisories/RUSTSEC-2026-0194.html), [RUSTSEC-2026-0195](https://rustsec.org/advisories/RUSTSEC-2026-0195.html), [RUSTSEC-2025-0141](https://rustsec.org/advisories/RUSTSEC-2025-0141.html), and [RUSTSEC-2024-0436](https://rustsec.org/advisories/RUSTSEC-2024-0436.html).

The fixed versions address the applicable PyO3, `anyhow`, and `quick-xml` advisories. In the reviewed `little_exif` path, `BytesStart::attributes()` is used; the `NsReader`-specific namespace allocation path described by RUSTSEC-2026-0195 was not found, but the selected update also includes its fixed release. No finding in this review required dropping the selected CPU/TurboJPEG features.

## Verification

- Final sanitized wheel import reports version `0.2.0+capsize.2`.
- CPU, package, and image-buffer tests: 24 passed.
- DLPack tests: 15 passed, 4 skipped because Torch is not installed, 1 deselected by `-k 'not cuda'`.
- SBOM sanitizer tests: 2 passed.
- The final wheel contains 338 CycloneDX components and 339 dependency records (829 edges). Sanitization replaced nine local/private source references and retained the 329 registry component identities, versions, hashes, and license metadata. All dependency edges remained bound to the same identities. Wheel RECORD validation passed. The wheel contains no `/tmp/`, `file:`, or private Git host strings.
- On the exact .2 tag, focused PLY test: 1 passed; `kornia-bow`: 29 passed. Earlier source validation on this release line reported 246 passed, 2 failed, and 1 ignored in the `kornia-3d` suite. The two failures—one frozen solver digest and one sparse-vs-dense accuracy assertion—were reproduced against the exact upstream v0.2.0 source and original lockfile. They are recorded as existing upstream baseline failures, not passed results.

## License and SBOM delivery

The wheel includes the Kornia project license. Third-party Rust notice texts are supplied in `packaging/licenses/kornia-rs-0.2.0-capsize.2-supplement/THIRD_PARTY_NOTICES.txt`, with their source/checksum manifest in `notice-manifest.json`; the notice companion must remain with the wheel. The manifest binds the selected x86_64 Linux normal/build graph, private source tag, Cargo.lock, wheel, and each notice text. It does not claim every graph node is compiled or linked. The adjacent `source-manifest.json` passed the repository's `source_notice_supplements.py` loader against the exact wheel hash and produced 329 hash-verified source notice files. It omits one canonical SPDX MIT reference text because that text is not an upstream source file; the complete Rust notice manifest and aggregate notice asset retain it.

The sanitized SBOM SHA-256 is `d7b1da30e4e0f932455d85cc35bdf06259190283bdedab89ad511ef97a0ca7e4`; the raw pre-sanitization SBOM SHA-256 was `def5861ef1ec4fbcde8417346f26eeff95abda28df8152d235043212e60d9c85`. Sanitization removes local/private build paths while preserving component identities and dependency connectivity.

No PyPI publication or deployment was performed. This review records build and test evidence only; it does not claim human testing or review.

## Private source release receipt

- PR #3 merged on 2026-11-02 at `496257a15d3f38142549d0a57a48ba026b452cd0`.
- Annotated tag `v0.2.0-capsize.2` points to that merged commit. The earlier `v0.2.0-capsize.1` source-only release was left unchanged.
- Release: [v0.2.0-capsize.2](https://github.com/Capsize-Games/kornia-rs-maintenance/releases/tag/v0.2.0-capsize.2).
- The release contains the wheel, exact source archive, CycloneDX SBOM, complete Rust notice manifest, loader-compatible source manifest, aggregate third-party notices, and build provenance. Each downloaded release asset's SHA-256 matched its local reviewed artifact.
- GitHub Actions remain disabled for the private maintenance repository, so this release has no CI run. Verification results above are local, offline results.
