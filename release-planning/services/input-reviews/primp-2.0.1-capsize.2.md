# Primp 2.0.1+capsize.2 review

## Disposition

The V3 diagnostic graph selects `primp==2.0.1+capsize.2`. This exact wheel passed static archive and RECORD checks, the production dependency-notice collector, and an isolated import/API-shape check. The complete Linux release graph remains uninstalled and inactive. No HTTP client was constructed and no request was sent.

The earlier `2.0.1+capsize.1` wheel is superseded and quarantined. Its exact wheel SHA-256 is `a10efe27c95726635736d8b933bbf41a3a3e134ba28e7e8dcc6d0931584f6026`. Its `RECORD` contains the noncanonical member path `primp-2.0.1+capsize.1.dist-info/licenses/local-crates//LICENSE` with a doubled slash. The production collector reported a generic path-traversal error for this malformed path; the path is noncanonical, and the checked archive does not show an actual path outside the wheel. The `.1` artifact was rejected and must not be activated. The `.2` review below is bound to its own source and wheel.

## Source identity and bounded security review

- Canonical upstream: `deedy5/primp`, tag `v2.0.1`, commit `cf29cd94f339c1a69ec7f271f532f0f2411aa06e`.
- Owner-controlled private maintenance release: tag `capsize-primp-v2.0.1.2`, merged commit `9a07d3d284f1d9f5312db653a50318517b994416`. Repository Actions are disabled; no CI result is claimed.
- The bounded private source review covered the Rustls fork ports, the Python/Rust binding and selected Linux normal/build graph. It compared the Rustls security changes with their upstream counterparts. The recorded changes cover fragmented-handshake alignment, debug-secret redaction, Brotli input consumption, ECH rejection, and authenticated session-hint handling. Two incomplete ports found during source comparison were corrected before the `.1` wheel was built. This is a bounded review of those paths, not a line-by-line audit of the full dependency graph.
- In the `.1` private source review, offline Rustls tests passed: 196 library tests and 220 API tests. The recorded commands used `CARGO_NET_OFFLINE=true`, `--locked`, and `--offline`. They exercise local fixtures; they do not establish live TLS interoperability or Primp HTTP-client behavior.
- The exact `.1` to `.2` source comparison confirms that no Rust runtime source file changed in `.2`. It changes local version metadata in `Cargo.lock` and three Cargo manifests, and hardens `tools/package_wheel.py`: canonical POSIX wheel-path validation, duplicate member and ambiguous `METADATA` rejection, safe `License-File` regeneration, and validation of generated archive and RECORD paths. The added path tests cover rejected noncanonical aliases and accepted canonical names; the `.2` build receipt records 9 passed. The source delta summary is retained at `.headlesscode/service-audit-2026-11-02/primp-2.0.1-capsize.2-acceptance/source-delta-summary.json`.
- The `.2` wheel's embedded Cargo notice manifest identifies the selected Linux normal/build graph. Among its selected crates are `rustls==0.23.46`, `rustls-webpki==0.103.16`, `rustls-pki-types==1.15.1`, `tokio==1.53.3`, `tokio-rustls==0.26.5`, `hyper==1.11.1`, `h2==0.4.19`, `pyo3==0.29.2`, `pyo3-async-runtimes==0.29.0`, and `aws-lc-rs==1.18.1`. These identities are taken from the wheel's exact-hash-bound notice manifest; this list is not a separate semantic audit of each crate.
- The manifest records 230 selected Linux normal/build registry crates and 418 registry packages in the broader Cargo lock. The latter includes development and platform-specific entries and does not mean every package was compiled or linked. The exact `.2` sidecar does not provide a package-attributed OSV result for every selected crate; no blanket advisory-clear claim is made here.

The `.2` build receipt records Python 3.13.5, Maturin 1.16.0, Rust 1.99.1, locked offline Cargo resolution, and no package-index access during the build. Build hooks were not run as part of this acceptance check.

## Wheel and notice verification

The `.2` wheel is `primp-2.0.1+capsize.2-cp310-abi3-linux_x86_64.whl`, 7,338,369 bytes, SHA-256 `036f35339074f9fee6b40393db87104c3aaa5a204577203b61bd00f0980cad99`. Its `linux_x86_64` tag is not a manylinux portability claim.

The wheel was checked without importing it before installation:

- All 416 ZIP members had canonical, unique paths and passed ZIP CRC validation.
- All 415 payload rows in the 416-row `RECORD` matched their SHA-256 and size; the `RECORD` self-row was empty as required.
- The wheel metadata declares 408 `License-File` entries. All 408 files exist under its `.dist-info/licenses/` tree and are covered by `RECORD`.
- The wheel contains no `.pth` startup member.

The production collector was run against a fresh environment containing only this exact wheel. `collect_dependency_notices` copied 408 notice files; `verify_dependency_notice_manifest` returned no problems. The isolated one-pin collector lock binds SHA-256 `036f35339074f9fee6b40393db87104c3aaa5a204577203b61bd00f0980cad99`. This verifies this wheel's notices; it does not validate whole-graph notice aggregation. The wheel's Rust notice manifest contains 401 records; this is a different count from the 408 `License-File` declarations and collected files.

## Isolated acceptance

A fresh `uv` environment used CPython 3.13.5. Only the exact local wheel was installed, with no dependencies, indexes disabled, and hashes required:

```text
uv venv --python 3.13.5 /tmp/airunner-primp-2.0.1-capsize.2-acceptance-env
UV_OFFLINE=1 PIP_NO_INDEX=1 uv pip install --python /tmp/airunner-primp-2.0.1-capsize.2-acceptance-env/bin/python --no-index --no-deps --only-binary :all: --require-hashes --find-links package/wheelhouse -r .headlesscode/service-audit-2026-11-02/primp-2.0.1-capsize.2-acceptance/requirements-primp.txt
```

In a separate `env -i` process with temporary `HOME`, XDG cache and `TMPDIR`, Python isolated mode imported `primp`, confirmed distribution version `2.0.1+capsize.2`, and confirmed `primp.Client` is exported as a type. No client was constructed, no network request was attempted, and no model or GPU was used.

Receipts are retained in `.headlesscode/service-audit-2026-11-02/primp-2.0.1-capsize.2-acceptance/`: `wheel-integrity.json`, `collector-result.json`, `import-smoke-result.json`, `source-delta-summary.json`, and `acceptance-receipt.json`.

## Limits

No live TLS interoperability test, HTTP request, Windows build, manylinux audit, full AIRunner graph install/import, service integration test, model download, or GPU workload was performed. These results establish exact artifact integrity, bounded source and notice review, and a narrow import/API check only. The V3 graph remains diagnostic-only and inactive.
