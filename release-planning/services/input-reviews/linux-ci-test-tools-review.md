# Linux CI test-tool input review

Review date: 2026-11-02

## Scope and disposition

This is a separate, test-only input layer for Linux x86_64 and CPython 3.13. It binds 11 exact distributions in `package/constraints-linux-ci-tools.txt`; the selected lock SHA-256 is `5fa26bf0a79215505c55631e2e03dc44773a48206814f6d255f361144b342360`, also recorded in `package/linux-ci-tools-artifact-sources.json`. The five test-tool packages below have package-specific source and wheel review. Six supporting runtime wheels are reused from the reviewed Linux V4 CORE graph; their exact identities and evidence are listed below. The test lock is installed after the reviewed CORE profile with `--no-deps --require-hashes`. None of these packages is added as a service runtime dependency by this test-only layer.

The exact upstream tags and commits are present in owner-controlled private repositories with Actions disabled and automatic upstream synchronization disabled. The verified repository and selected-ref details are in the ignored private-copy receipt at `.headlesscode/service-audit-2026-11-02/linux-ci-tools-review/private-source-copy-verification.json`.

| Distribution | Pin | Selected wheel SHA-256 | License | Source identity |
|---|---:|---|---|---|
| `iniconfig` | 2.3.0 | `f631c04d2c48c52b84d0d0549c99ff3859c98df65b3101406327ecc7d53fbf12` | MIT | tag `v2.3.0`, commit `7faed13ae50bad7c5da3f5782f254a8a7736bb84` |
| `pluggy` | 1.7.0 | `7dd7b0d8832ba3cb632c306926ded123429211b83641b35dc5c41ad2d34f9bec` | MIT | tag `1.7.0`, commit `4c7f6365f2dde09c11e72db67d0f615231d64c19` |
| `pytest` | 9.1.1 | `37a86b45efb9a47a61a36449063e8e18d0cab3161329fc099eb21783169c4f0c` | MIT | tag `9.1.1`, commit `cf470ec0bf7eb89cd97dd56df4859eae5db46447` |
| `pytest-timeout` | 2.4.0 | `c42667e5cdadb151aeb5b26d114aff6bdf5a907f176a007a30b940d3d865b5c2` | MIT | tag `2.4.0`, commit `ddabc934535081a5bf9ba7c9ca5b494aeaf8f665` |
| `responses` | 0.26.3 | `74474f799334ac4f37d93b6437ecc3bb1bb5c77a8d31780a338643be2dce0af8` | Apache-2.0 | tag `0.26.3`, commit `cb13954973dc0c1508668cd75603b203b0925c4a` |

The six test-tool support packages reuse their selected Linux V4 CORE wheel
hashes and source-review records. The machine-readable
[CORE dependency inventory](core-linux-dependency-inventory.json) binds each
identity to its review record and evidence hash; the
[test-tool artifact manifest](../../../package/linux-ci-tools-artifact-sources.json)
binds the selected wheel filename, size, URL and SHA-256.

| Supporting distribution | Version | Selected CORE wheel SHA-256 | CORE source review |
|---|---:|---|---|
| `certifi` | 2026.10.23 | `e9b54de76e530bb6cf0ccd036787103acb58fd42ba930ea8bf948ddbaa2f61d1` | [Clients and templates](core-clients-templates-review.md) |
| `charset-normalizer` | 3.5.2 | `7218e8f32b0956cfcd048fd42d9d5779809745ca1d86113ca56f66e7ae1549c4` | [Clients and templates](core-clients-templates-review.md) |
| `idna` | 3.20 | `ab7ae7122974553370f0bdb919e1a960b2cd1bc1ef0276416d896db81c14582c` | [Python primitives](core-python-primitives-review.md) |
| `pygments` | 2.21.0 | `2363c69b61c4a97c838da3b130dcd6468f4848992b21a82f2a63ec34377137d9` | [Numeric and native](core-numeric-native-review.md) |
| `requests` | 2.34.2 | `2a0d60c172f83ac6ab31e4554906c0f3b3588d37b5cb939b1c061f4907e278e0` | [Clients and templates](core-clients-templates-review.md) |
| `urllib3` | 2.8.0 | `0cf3cae568d36aa9576b28dfb35f11328f1cb974ca7647d9475ebb86c75ac6e3` | [Clients and templates](core-clients-templates-review.md) |

## Bounded review

The review compared exact selected wheel contents, RECORD hashes and sizes, shipped Python modules against the pinned source tag, and wheel license members against the tagged source license. Every selected wheel RECORD was valid; all shipped Python files matched the pinned source byte-for-byte. The bounded source/config review covered build metadata, plugin registration, install hooks, and network or credential behavior relevant to the selected packages. No source/build hook was executed, no package was installed or imported during that review, and no package tests were run as part of source review.

PyPI version metadata reports no vulnerability entries for these exact pins. Pytest 9.1.1 is newer than the published CVE-2025-71176 fix in 9.0.3. `pytest-timeout` 2.5.0 is yanked, so 2.4.0 is selected. Its active configured 30-second timeout can signal a failing test; thread mode may hard-exit without teardown or JUnit output. Pytest's pastebin plugin can make a network request only when explicitly selected; the candidate CI command does not pass `--pastebin`. The `responses` package patches Requests transports for mock responses; no independent network client or telemetry path was found in shipped package code. `iniconfig` is parser-only. `pluggy==1.7.0` was previously reviewed as an exact artifact in the LLM source review.

This records source and artifact input review, not release acceptance. The candidate lock and artifact manifest are exact hash inputs; the CI stager validates wheel size and SHA-256 before installation. Runtime graph installation must occur first, followed by this test-only layer with `--no-deps`, then the editable service package with `--no-deps` and `pip check`. A fresh local CPython 3.13.5 environment installed the 51-pin CORE CI closure plus this 11-pin test layer from local staged wheels; `uv pip check` reported all 56 packages compatible. The import-boundary pytest command passed 7 tests, and the focused input/gate suite passed 35 tests. These are local environment results, not hosted CI or release acceptance.
