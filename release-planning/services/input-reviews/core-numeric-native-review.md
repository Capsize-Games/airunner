# CORE numeric and native input review

Static review of the nine exact versions in the current Linux CORE lock,
completed 2026-11-01. The selected wheels and sdists came from the official
PyPI file metadata and host and match the recorded SHA-256 values. The source
archives and release refs were inspected as data. No package was installed,
imported, built, tested, or activated; no model or GPU work ran.

## Exact inputs

Every selected wheel SHA-256 also occurs in `package/constraints-linux-core.txt`.
Wheel `RECORD` hashes and sizes were validated; no `.pth` files were present.
The metadata name and version matched the lock for each wheel.

| Distribution | Selected Linux CPython 3.13 x86-64 wheel | Wheel SHA-256 | Sdist SHA-256 | Source tag and commit |
|---|---|---|---|---|
| NumPy 2.2.5 | `numpy-2.2.5-cp313-cp313-manylinux_2_17_x86_64.manylinux2014_x86_64.whl` | `2ba321813a00e508d5421104464510cc962a6f791aa2fca1c97b1e65027da80d` | `a9c0d994680cd991b1cb772e8b297340085466a6fe964bc9d4e80f5e2f43c291` | [`v2.2.5`](https://github.com/numpy/numpy/tree/v2.2.5), `7be8c1f9133516fe20fd076f9bdfe23d9f537874` |
| pandas 3.1.0 | `pandas-3.1.0-cp313-cp313-manylinux_2_24_x86_64.manylinux_2_28_x86_64.whl` | `de6d0fc96e8551b83f400bf212611a0b3a2b389594d20a2540dacc61b21e7bce` | `ecb9b2d8a817b1e1ba1fdb90c0abe9eab31b4fdf2562b7a56b86ac66ace17e49` | [`v3.1.0`](https://github.com/pandas-dev/pandas/tree/v3.1.0), `c6f46769b808eb60218189d089dd67841b44f1b9` |
| Pillow 13.0.0 | `pillow-13.0.0-cp313-cp313-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl` | `5f56499c1a74d2b862beb0c33b8016f99d095858455df9d21583bbbc1c15b582` | `cdcd1ba258178f7356d74170c9a81ba4eab6a5d55748bc402a5a2a6fe6be3510` | [`13.0.0`](https://github.com/python-pillow/Pillow/tree/13.0.0), `293218ad059d994baf1777d882911bed6a49704a` |
| psutil 7.2.2 | `psutil-7.2.2-cp36-abi3-manylinux2010_x86_64.manylinux_2_12_x86_64.manylinux_2_28_x86_64.whl` | `076a2d2f923fd4821644f5ba89f059523da90dc9014e85f8e45a5774ca5bc6f9` | `0746f5f8d406af344fd547f1c8daa5f5c33dbc293bb8d6a16d80b4bb88f59372` | [`release-7.2.2`](https://github.com/giampaolo/psutil/tree/release-7.2.2), `9eea97dd6f1d16ea33f5144c8925f1ce7a0688e1` |
| greenlet 3.5.6 | `greenlet-3.5.6-cp313-cp313-manylinux_2_24_x86_64.manylinux_2_28_x86_64.whl` | `f98e8215e172f567ce80eeaed9107fb4d32b6c44f26983d9b8334658136a205a` | `8e67c43bdfc88d5fee6db0d3e40175b362fc95fb85f0412d233b9b203c53a575` | [`3.5.6`](https://github.com/python-greenlet/greenlet/tree/3.5.6), `abfe740315a9926ff180c622cf02f122c07f9126` |
| regex 2026.9.29 | `regex-2026.9.29-cp313-cp313-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl` | `d49c18f1ea294cf4adde2e5ac256e98c82ea9d708462ce4bf799dffa7cfe8a2c` | `8b5fcc4771732191b2b7d1dd68d8f0353f47f8d90b6150f6dce58bf1112442cb` | [`2026.9.29`](https://github.com/mrabarnett/mrab-regex/tree/2026.9.29), `0e8cb0596ba6572c66e5d153a1d7c901b381e15e` |
| PyYAML 6.0.2 | `PyYAML-6.0.2-cp313-cp313-manylinux_2_17_x86_64.manylinux2014_x86_64.whl` | `70b189594dbe54f75ab3a1acec5f1e3faa7e8cf2f1e08d9b561cb41b845f69d5` | `d584d9ec91ad65861cc08d42e834324ef890a082e591037abe114850ff7bbc3e` | [`6.0.2`](https://github.com/yaml/pyyaml/tree/6.0.2), `41309b0bcb4559edb1d691d47199035ef539d785` |
| Pydantic 2.14.2 | `pydantic-2.14.2-py3-none-any.whl` | `7efbf7507b937931cd32a5755acb00ea1cf5ccb1d4e8067a5850d5069e382118` | `fb7b2db6cefe8414dd612edeede49c4c433acb0432b0f92b95024e45f66c505d` | [`v2.14.2`](https://github.com/pydantic/pydantic/tree/v2.14.2), `aa540acc29960fb394312cf97d888c99f9686814` |
| pydantic-core 2.50.2 | `pydantic_core-2.50.2-cp313-cp313-manylinux2014_x86_64.manylinux_2_17_x86_64.whl` | `31a1fb3ffbd1195b24490f671d12623dd4c9bfa56d6af0a299fa43b516134f5b` | `1b0e8dc3932cf4e9ed5727570325cacc716b9409ffc794a221c0ccc72e8eb775` | [`pydantic v2.14.2`](https://github.com/pydantic/pydantic/tree/v2.14.2), same commit as Pydantic; the source is under `pydantic-core/` |

The selected wheel `RECORD` counts were: NumPy 875, pandas 1,557, Pillow 138,
psutil 15, greenlet 98, regex 9, PyYAML 23, Pydantic 110, and pydantic-core
10 validated entries. psutil's `cp36-abi3` wheel supports CPython 3.13 through
the stable ABI.

The exact upstream release refs are retained in owner-controlled private
repositories with Actions disabled: `numpy-maintenance`,
`pandas-maintenance`, `pillow-maintenance`, `psutil-maintenance`,
`greenlet-maintenance`, `regex-maintenance`, `pyyaml-maintenance`, and
`pydantic-maintenance`. Each `source-review/<tag>` branch points at the commit
listed above. The pydantic-core source is the matching subdirectory in the
pydantic repository. The PyPI sdists' common files match those tag snapshots:
NumPy 2,275/2,275; pandas 1,624/1,624; Pillow 1,721/1,721; greenlet 125/125;
regex 16/16; PyYAML 634/634; Pydantic 343/343; and pydantic-core 283/283.
psutil has 199 identical files among 201 shared files; only `HISTORY.rst` and
`docs/index.rst` differ, with the sdist stating 2026-01-18 and the release tag
2026-01-28. No psutil runtime source file differed.

## Package, build, and runtime scope

- **NumPy** — BSD-3-Clause. Its selected wheel contains native CPython modules
  and bundled OpenBLAS. The wheel's `LICENSE.txt` includes the bundled
  OpenBLAS, LAPACK, and compiler-runtime notices. The sdist uses the
  `meson-python` backend with Cython and includes vendored Meson. Its runtime
  metadata has no base requirements. File-source helpers can read URLs; this
  is explicit data-loading behavior.
- **pandas** — BSD-3-Clause. The wheel contains compiled modules and carries
  license files for the bundled/source subprojects, including xsimd and
  fast_float. The sdist uses Meson, Cython, and `meson-python`; its bundled
  `xsimd-14.2.0` and `fast_float-8.2.10` sources and notices are present. Base
  requirements are NumPy and python-dateutil; tzdata is conditional for
  Windows and Emscripten. HTTP URL handling is an explicit data-import
  feature.
- **Pillow** — MIT-CMU. Its wheel bundles shared codec/image libraries under
  `pillow.libs` (including AVIF, Brotli, FreeType, HarfBuzz, JPEG, LCMS,
  OpenJPEG, PNG, TIFF, WebP, XAU/XCB, zlib, and zstd dependencies). The wheel's
  70,307-byte license file includes corresponding third-party license text.
  The sdist's English `AGENTS.md` was read as untrusted project guidance, not
  followed; its instructions describe Pillow development and test commands.
  The wheel has no base Python requirements. Its custom build backend probes
  local compiler/library settings. The selected wheel does not run that
  backend.
- **psutil** — BSD-3-Clause. Its selected wheel contains the Linux system
  inspection extension. Its process, network-interface, and connection APIs
  inspect local OS state; they are the package's stated runtime role. The
  source setup uses setuptools; the wheel has no base runtime dependency.
- **greenlet** — MIT and PSF-2.0, with both license files in the wheel. The
  wheel contains its context-switching extension and two test extensions.
  Source builds use setuptools; there are no base runtime dependencies and
  no runtime network client was observed in the reviewed package source.
- **regex** — Apache-2.0 and CNRI-Python; both notices are included. The wheel
  contains one native extension. The sdist uses setuptools and contains no
  bundled external runtime library or base Python requirement.
- **PyYAML** — MIT. The selected wheel contains its `_yaml` extension, linked
  only to system `libpthread` and `libc`. The sdist's local PEP 517 backend
  delegates to setuptools and can use Cython when building from source. It
  also contains a CPython 3.12 `.pyc` for that backend; its code object was
  disassembled with Python 3.12's standard library without execution. It is a
  setuptools/config-settings shim and is absent from the selected wheel. The
  wheel has no base Python requirement.
- **Pydantic** — MIT and pure Python. Its base requirements are Pydantic Core,
  `typing-extensions`, `annotated-types`, and `typing-inspection`; extras are
  not selected. Source packaging uses Hatchling and a README metadata plugin.
- **pydantic-core** — MIT. The selected wheel contains one Rust extension,
  dynamically linked only to standard system libraries. Its sdist uses
  Maturin/PyO3, has `typing-extensions>=4.16.0` as a base requirement, and
  contains a `Cargo.lock` with 101 registry crates. The exact 101 crates.io
  archives were downloaded and verified against their lockfile
  SHA-256 checksums; the lock hash is
  `d4c7d4bce9e5cd2f661f22fef35216a2340776ca76885606c40934b579663b11`.
  Each archive's manifest/license paths, build-script presence, and bundled
  instruction-file paths were inventoried. No agent instruction files were
  found. Static targeted searches found no outbound HTTP client, telemetry
  client, or credential-key pattern in the reviewed crate/build files; URL
  parsing and entropy APIs are part of the declared validation/runtime
  behavior. The lock includes platform-specific crates; this review does not
  claim the wheel's build log identifies exactly which crate objects were
  linked. The wheel itself contains only the pydantic-core MIT license file;
  the downstream notice payload is now retained in
  `packaging/licenses/pydantic-core-rust-crates/`. Its source manifest binds
  180 original legal/attribution files across all 101 exact Cargo.lock crate
  entries to their lock checksums and records every copied file's SHA-256.
  This is deliberately a lock-scoped notice superset; it does not claim that
  every locked crate was compiled or linked into the selected Linux wheel.
  r-efi's `AUTHORS` file contains its license and copyright notices and is
  included verbatim. The wit-bindgen-rt 0.39.0 crate archive has no license
  text, so the three applicable license files are included verbatim from its
  exact source commit `f2393e6e98fa5f9236cac580db8a3fc9de6a4b70`; that source
  and the crate archives are retained in private GitHub repositories with
  Actions disabled. The pydantic-core source for 2.50.2 is the
  `pydantic-core/` subdirectory of `pydantic/pydantic` tag `v2.14.2` at
  `aa540acc29960fb394312cf97d888c99f9686814`; the separate archived
  `pydantic/pydantic-core` repository does not contain this selected release.

For all nine package releases, the captured PyPI vulnerability arrays were
empty. An OSV exact-version query on 2026-11-01 returned zero records for the
nine Python distributions and separately for all 101 locked Cargo crates.
These database results are limited snapshots, not proof that no advisory
exists.

Targeted source searches found no telemetry SDK or hidden outbound client in
the reviewed package/runtime paths. URL/file access in NumPy and pandas is
documented input behavior; Pillow viewer/display helpers use local display
facilities; psutil reads local OS process/network state. No production
credential access was observed. These searches are scoped evidence, not a
proof that arbitrary callers cannot use these libraries to access external
data or the local system.

GitHub API profile fields for NumPy, pandas, Pillow, greenlet, regex, PyYAML,
and Pydantic identities checked had no self-stated location; that is not a
claim of United States origin. The psutil source owner profile `giampaolo`
self-states `Italy`; the owner whitelist decision for the reviewed dependency
graph is recorded separately. No origin was inferred from names.

This record documents static input review only. It does not establish a
reproducible native build, exact wheel-to-source binary match, frozen startup,
clean-install success, or runtime behavior. The selected CORE freeze install
uses hash-pinned wheels with `--only-binary=:all:`, so source-build backend
execution is not part of that path. Revisit backend review if source builds
are introduced.

Integration update, 2026-11-02: all nine exact pins in this batch are now
recorded as source-reviewed in the shared inventory. The psutil location flag
is covered by the owner whitelist; the other eight pins have reviewed-no-flag
origin dispositions. `pydantic-core` is the subdirectory distribution in the
same Pydantic release source and uses the Pydantic project profile already
checked above. See [`DEPENDENCY_DECISIONS.md`](../DEPENDENCY_DECISIONS.md)
for the complete exact whitelist list. Pydantic Core's downstream legal notice
payload is recorded in `packaging/licenses/pydantic-core-rust-crates/`; it is a
lock-scoped superset covering 101 Cargo.lock crates and does not assert that
each one was linked into the selected Linux wheel. The shared readiness record
allows isolated candidate installation/build work, while artifact validation
remains `not-run`.
