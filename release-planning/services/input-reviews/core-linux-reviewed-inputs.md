# CORE exact-pin review evidence

This record covers the seven exact pins with source-level evidence found for
the current Linux CORE lock. Its scope is limited to the cited artifacts and
build paths; it is not a blanket approval for later versions.

| Distribution | Exact version | Source identity | Artifact evidence | Current policy state |
|---|---:|---|---|---|
| airunner-common | 6.1.8 | `733b0f4c8fb38952866e9cf7be2cc69793a46e92` | Release wheel `ac2110ecbcd965c9a773405494bcecb3d1c6c5f127d22fde81d37478b94088fd`; RECORD and vendored module hashes verified | Owner source |
| python-dotenv | 1.2.2 | `36004e0e34be7665ff2b11a8a4005144f76f176d` | Wheel `1d8214789a24de455a8b8bd8ae6fe3c6b69a5e3d64aa8a8e5d68e694bbcb285a`; RECORD inspected | Exact-pin owner exception recorded |
| pyinstaller | 6.12.0 | `31dbe9ff477716e4790aa317bc9da68766d20659` | Source archive `1834797be48ce1b26015af68bdeb3c61a6c7500136f04e0fc65e468115dec777`; setup path, license, matching Linux hooks, and relevant advisory inspected | Origin exception recorded 2026-11-01 |
| pyinstaller-hooks-contrib | 2026.9 | `222e37fea0d8300595af3601a4f42d2fcf634a37` | Source archive `2748767901acb5cecd1304652b6c7add5bffcff1d71d01207fe24a5d42942a56`; matched CORE hooks and license inspected; PyPI vulnerability metadata was empty | Origin exception recorded 2026-11-01 |
| setuptools | 84.2.1 | `3895f9829fc0e51882981773a823a658eb1d1636` | Wheel `ca140b45d5325a9478f880e351484f62fef15f336462e449ca0c03c873d589c2`; RECORD and active PEP 517 build path reviewed | Reviewed packaging-tool origin disposition recorded 2026-11-01 |
| wheel | 0.48.0 | `21c4da4c54c3b354cc22dc7f6f6374ffcd560e84` | Wheel `3217dcc807155e45db462d7ef2431f5ddda0d7273b700d05a67b271ceb1287ab`; RECORD reviewed | Reviewed packaging-tool origin disposition recorded 2026-11-01 |
| packaging | 26.3 | `929fd4b1410ac7ef61ef3f45b2f5d7e87711a9b5` | Wheel `d7193f7c8e4e93f444fde0262bf90af30e16fa0ad0ad44cb553c87339b23cd1c`; RECORD reviewed | Reviewed packaging-tool origin disposition recorded 2026-11-01 |

For setuptools, wheel, and packaging, the source and artifact review evidence
uses official PyPI metadata and cached wheel contents. The raw wheel archives
were not present for independent rehashing in that review; metadata digests
matched the cache records and extracted files passed RECORD checks. The
setuptools review is limited to the active build path and its expected
`distutils-precedence.pth` behavior. The hooks review covers the matched CORE
hook set, not every hook in that project. The PyInstaller advisory review is
scoped to the configured `onedir` mode.

The readiness inventory keeps source review and origin-policy state separate.
The seven pins above, eight Python primitives, eight HTTP async packages
(including the bounded Watchfiles Rust closure), eight client/template
dependencies, eleven framework/utility packages, and nine numeric/native
packages account for all 51 locked distributions. The two newest batches are
`core-frameworks-utilities-review.md` and `core-numeric-native-review.md`.
Static source review and origin disposition are recorded for all 51 exact
pins. See `DEPENDENCY_DECISIONS.md` for the exact package and nested-crate
origin whitelist identities.

This static inventory does not establish a reproducible native build, exact
wheel-to-source binary match, frozen startup, clean-install success, or runtime
behavior. The framework/utility batch did not execute build backends or
independently review their dependency graphs. The numeric/native batch did not
load native extensions or establish which of the 101 locked pydantic-core Rust
crates were linked into the wheel. Its notice payload is a lock-scoped superset
of original notices, not a claim that every locked crate shipped in that
binary. Continue with isolated candidate builds and artifact/runtime checks;
the manifest records artifact validation as `not-run`.
