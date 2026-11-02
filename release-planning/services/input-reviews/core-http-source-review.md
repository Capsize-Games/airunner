# CORE HTTP async source review

Static intake for the exact versions in the current Linux CORE lock, reviewed
2026-11-01. This record covers source metadata and package code; it does not
activate any package or authorize a build. Exact-version source archives were
retrieved from the official PyPI file host and matched the SHA-256 values in
PyPI JSON metadata. The corresponding version tags and source commits are
listed below. Common files in each sdist and Git tag snapshot had no byte
differences in the comparison; generated files, source-distribution metadata,
and bundled submodule content are described in the package notes.

| Distribution | Locked version | Source tag and commit | PyPI sdist SHA-256 | Origin-policy state |
|---|---:|---|---|---|
| anyio | 4.16.0 | [`4.16.0`](https://github.com/agronholm/anyio/tree/4.16.0), `0ddd02d6a44a68cfdf0210783c2a2a1b02334d9a` | `59bb03251907983d1603d27c3087ddb1e93299ea2163adcdba37899a4fb12ffb` | Owner whitelist recorded |
| h11 | 0.16.0 | [`v0.16.0`](https://github.com/python-hyper/h11/tree/v0.16.0), `1c5b07581f058886c8bdd87adababd7d959dc7ca` | `4e35b956cf45792e4caa5885e69fba00bdbc6ffafbfa020300e549b208ee5ff1` | Reviewed; no concrete flag found |
| httptools | 0.9.0 | [`v0.9.0`](https://github.com/MagicStack/httptools/tree/v0.9.0), `104198474662752f4f4845c79007100829aff442` | `d484ebb7e3a3f3597b0f645fbd1b85633674ca808c1f5ba11c2caf7c66f5c8b6` | Owner whitelist recorded |
| starlette | 1.6.0 | [`1.6.0`](https://github.com/Kludex/starlette/tree/1.6.0), `4f250d6b814587e20c5365f0a5f0c4d42bcb929f` | `d4e3ac5e546444960c710297a3c9fc3f7ebae1b7e963f3d36173b49da535be9b` | Owner whitelist recorded |
| uvicorn | 0.34.0 | [`0.34.0`](https://github.com/encode/uvicorn/tree/0.34.0), `7983c1ae9c2276b94cd85217f7aa58bb248847c4` | `404051050cd7e905de2c9a7e61790943440b3416f49cb409f965d9dcd0fa73e9` | Owner whitelist recorded |
| uvloop | 0.23.0 | [`v0.23.0`](https://github.com/MagicStack/uvloop/tree/v0.23.0), `c5f7debaabe98bba70859aa0120db243775c255c` | `28d160f51ab4da3b187063652e643dea6831072add4adc1e6d62afbe73b6be27` | Owner whitelist recorded |
| watchfiles | 1.3.0 | [`v1.3.0`](https://github.com/samuelcolvin/watchfiles/tree/v1.3.0), `e74b8fc7d8d9e35c3b6bb88af0aef5ea82ee815e` | `99aee4a07847c06820765fd7b1b49ceac4f3f711ccb7d104655a33231de1c207` | Package whitelist recorded; nested crate flags pending |
| websockets | 17.4 | [`17.4`](https://github.com/python-websockets/websockets/tree/17.4), `625a59ed613ac60e60d577dd64b8641d59ecb2b1` | `09d3939b70df0c8ad2da145ebd50978bccaee1d565e838b0e7921a34d38571eb` | Reviewed; no concrete flag found |

The two no-flag dispositions mean the reviewed primary project profiles and
source instructions exposed no concrete origin-policy flag. They do not assert
a country of origin. The six package-level owner-whitelisted states correspond to recorded profile
flags; no conclusion about code quality or intent follows from those policy
findings.
Exact profile evidence and the owner disposition are retained in private review
records.

## Source, build, and runtime findings

- **anyio 4.16.0** — MIT. `setuptools.build_meta` declares setuptools 77 or
  newer and setuptools-scm 6.4 or newer. Runtime requirements are idna,
  typing-extensions, and exceptiongroup only below Python 3.11; the Trio
  requirement is an unselected extra. Its English `AGENTS.md` and `CLAUDE.md`
  were read as source data, not followed. The sdist has 237 common files with
  the tag and one packaging-only `setup.cfg`.
- **h11 0.16.0** — MIT and pure Python, with no runtime dependencies. Its sdist
  has no explicit build-system table; `setup.py` evaluates the local version
  file, whose exact release contents set a static version, then calls
  `setuptools.setup()`. The 52 common files matched the tag; the sdist omits
  development and CI files.
- **httptools 0.9.0** — MIT, with MIT notices for bundled http-parser and
  llhttp. The source build uses `setuptools.build_meta` constrained to
  setuptools 80.9.0 through 82.0.1. Its `build_ext` uses the bundled C
  parsers; generated `parser.c` and `url_parser.c` are present, and Cython is
  requested only if those files are absent or `cython-always` is selected.
  Parent source gitlinks identify http-parser commit
  `2343fd6b5214b2ded2cdcf76de2bf60903bb90cd` and llhttp commit
  `0e815792b167a9bd8ace259b95b7da953776c288`. Their license notices are in the
  sdist. Exact upstream commits were privately mirrored with Actions disabled.
  All 8 http-parser and 7 llhttp files present in the sdist match their upstream
  snapshots byte-for-byte. Their upstream organization profiles have no
  self-stated location. Parser source implements parsing and has no outbound
  client or telemetry path in the selected runtime role. The 19
  common files matched the tag; the sdist adds generated C and bundled source.
- **Starlette 1.6.0** — BSD-3-Clause. Hatchling builds the package. Runtime
  requirements are AnyIO below major version 5 and typing-extensions only
  before Python 3.13; the `full` extra is not selected. ASGI request, response,
  and WebSocket handling are its expected role. Test-only URL user/password
  examples are placeholders. All 135 common files matched the tag.
- **Uvicorn 0.34.0** — BSD-3-Clause. The PyPI project points to `encode/uvicorn`,
  which redirects to the canonical `Kludex/uvicorn` repository. Hatchling
  builds the package. Its selected `standard` extra declares httptools,
  python-dotenv, PyYAML, uvloop, watchfiles, and websockets in addition to its
  base click and h11 requirements. Opening server sockets and honoring its
  `UVICORN_` configuration are expected behavior. All 75 common files matched
  the tag.
- **uvloop 0.23.0** — MIT and Apache-2.0; the sdist includes libuv's license.
  The setuptools build declares packaging, setuptools, and Cython requirements.
  Its setup code builds the bundled libuv source locally with `configure` and
  `make`; the sdist contains `loop.c` but PEP 517 still declares Cython. The
  parent tag references libuv commit
  `1cfa32ff59c076ffb6ed735bbc8c18361558661f` (version 1.52.1). That exact
  upstream revision was privately mirrored with Actions disabled. The 370
  files shared with the sdist match byte-for-byte; its 24 additional sdist files
  are generated Autotools inputs and cache files, and 99 upstream files are
  absent from the sdist. The upstream organization profile has no self-stated
  location. Its socket and event-loop APIs are expected runtime behavior; no
  telemetry or update client path was observed in the Linux source/build path.
  A TLS key/certificate pair occurs under
  `tests/certs` and is used by tests and a bundled benchmark example, not by
  the runtime package. The 102 common files matched the tag;
  the sdist expands the vendored libuv tree and includes generated C.
- **watchfiles 1.3.0** — MIT. Its Maturin backend builds a Rust extension;
  runtime depends on AnyIO. Correction: an earlier version of this review
  incorrectly stated that the sdist lacked `Cargo.lock`. The exact sdist
  contains `Cargo.lock` (SHA-256
  `e18da541b276924cc96e5149fec75505d7ab9faff8dcf21db4697952b8302529`),
  byte-identical to the 1.3.0 source commit. Successful tag workflow
  [run 35581174330](https://github.com/samuelcolvin/watchfiles/actions/runs/35581174330)
  is on that same commit; its Linux x86_64 wheel build log records the selected
  CPython abi3 filename and 26 compiled external Rust crates. All 26 crate
  archives were obtained from crates.io and matched the lockfile checksums.
  Their exact versions and manifest license expressions are recorded below.
  The lock pins identities and checksums, but the release log shows crate
  archives downloaded from crates.io; this is a closed dependency identity, not
  an offline source-build input. Filesystem watching is the runtime role; the
  optional command-restart CLI is
  also in the package. The 42 common source files match the release tag.
- **websockets 17.4** — BSD-3-Clause and no runtime dependencies. The
  setuptools build runs `setup.py`, which evaluates the local version file;
  for this release `released` is true and the file assigns the static `17.4`
  value, so its conditional Git subprocess path is inactive. An optional C
  speedup is built from package-local source. Client, server, authentication,
  and system-proxy support are explicit networking features; proxy discovery
  uses Python's configured system proxies. No country is inferred from the
  blank location on the project organization profile. All 60 common files
  matched the tag.

Targeted static searches found no telemetry or analytics SDK and no hidden
outbound HTTP client in the reviewed package runtime/build files. Network
operations in AnyIO, Uvicorn, and websockets implement their declared socket,
server, client, or proxy functions. No high-confidence credential pattern was
found in runtime files. The source distributions include synthetic URL
userinfo test cases and the uvloop test certificate/key fixture described
above; these are not runtime credentials.

PyPI release JSON and an OSV version query each returned zero advisory matches
for these eight exact versions on 2026-11-01. The versions were not marked
yanked in PyPI metadata. These database results do not prove that no advisory
exists.


## Selected binary wheel review

The CORE lock selects these exact Linux x86-64 wheels. SHA-256 values were
checked against PyPI file metadata, and all wheel RECORD hashes and sizes were
verified. No `.pth` files were present. The wheel METADATA names matched each
locked distribution and version.

| Distribution | Selected wheel | SHA-256 | Native payload review |
|---|---|---|---|
| anyio 4.16.0 | `anyio-4.16.0-py3-none-any.whl` | `c66ae634e0b8228396b801741beb3294326d4b6102f7bba4041c0dfb58c29026` | Pure Python |
| h11 0.16.0 | `h11-0.16.0-py3-none-any.whl` | `63cf8bbe7522de3bf65932fda1d9c2772064ffb3dae62d55932da54b31cb6c86` | Pure Python |
| httptools 0.9.0 | `httptools-0.9.0-cp313-cp313-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64.whl` | `088de1738e1af624466a01c35d652dbe6fb825be887c76d68aa850621d81db88` | Two ELF x86-64 extensions; dynamic dependencies are libc and pthread. Parser symbols correspond to the bundled http-parser and llhttp implementations. |
| starlette 1.6.0 | `starlette-1.6.0-py3-none-any.whl` | `a86dd39d14bb45f85a3d18525215a9ef0cfd1f192ac793220e72598c90335f0c` | Pure Python |
| uvicorn 0.34.0 | `uvicorn-0.34.0-py3-none-any.whl` | `023dc038422502fa28a09c7a30bf2b6991512da7dcdb8fd35fe57cfc154126f4` | Pure Python |
| uvloop 0.23.0 | `uvloop-0.23.0-cp313-cp313-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl` | `e2cba180d6451822763eda8364f342435a873bcfb3849cbd82fdeca248ca65eb` | ELF x86-64 extension has libc, pthread, and librt dependencies; libuv is statically included. |
| watchfiles 1.3.0 | `watchfiles-1.3.0-cp310-abi3-manylinux_2_17_x86_64.manylinux2014_x86_64.whl` | `b5768b49e426fd5b550b012c866db347cdf15c398ef98dc557b6e6b72fa74cd1` | ELF x86-64 Rust extension has libgcc_s, librt, pthread, libdl, libc, and the dynamic loader dependencies. |
| websockets 17.4 | `websockets-17.4-cp313-cp313-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64.whl` | `25eb661d8ba7e2b85ebb4e7a1bb9f6a3280910ed10b84330a7abfb5ed32d2764` | Optional C speedup has pthread and libc dependencies. |

The selected uvloop wheel carries uvloop's MIT and Apache-2.0 notices but not
libuv's separate license notice. The downstream bundle now includes the exact
`vendor/libuv/LICENSE` bytes as [`packaging/licenses/libuv-LICENSE`](../../../packaging/licenses/libuv-LICENSE), pinned to libuv 1.52.1 commit
`1cfa32ff59c076ffb6ed735bbc8c18361558661f`; the license file SHA-256 is
`16de0c32b265cb7d46a6d3bd614f259dd4d693a5e26b3407b04aae8d73041f0c`. The
bundle spec stages it with the legal notices, inherited by CORE and full
profiles and therefore included in the Debian-installed service bundle.

### Watchfiles Rust crate closure

The release log and lockfile identify these crates compiled for the selected
Linux x86_64 wheel; this includes build-time macro/compiler crates as well as
runtime libraries. Each source archive SHA-256 was verified against its
`Cargo.lock` checksum and its manifest license field and included license texts
were inventoried. Exact hashes and source records are retained in the private
maintenance evidence branch.

| Crate | Version | Manifest license expression |
|---|---:|---|
| bitflags | 2.7.0 | MIT OR Apache-2.0 |
| cfg-if | 1.0.0 | MIT/Apache-2.0 |
| crossbeam-channel | 0.5.15 | MIT OR Apache-2.0 |
| crossbeam-utils | 0.8.19 | MIT OR Apache-2.0 |
| filetime | 0.2.24 | MIT/Apache-2.0 |
| heck | 0.5.0 | MIT OR Apache-2.0 |
| inotify | 0.11.0 | ISC |
| inotify-sys | 0.1.5 | ISC |
| libc | 0.2.169 | MIT OR Apache-2.0 |
| log | 0.4.22 | MIT OR Apache-2.0 |
| mio | 1.0.3 | MIT |
| notify | 8.0.0 | CC0-1.0 |
| notify-types | 2.0.0 | MIT OR Apache-2.0 |
| once_cell | 1.21.3 | MIT OR Apache-2.0 |
| proc-macro2 | 1.0.81 | MIT OR Apache-2.0 |
| pyo3 | 0.29.0 | MIT OR Apache-2.0 |
| pyo3-build-config | 0.29.0 | MIT OR Apache-2.0 |
| pyo3-ffi | 0.29.0 | MIT OR Apache-2.0 |
| pyo3-macros | 0.29.0 | MIT OR Apache-2.0 |
| pyo3-macros-backend | 0.29.0 | MIT OR Apache-2.0 |
| quote | 1.0.45 | MIT OR Apache-2.0 |
| same-file | 1.0.6 | Unlicense/MIT |
| syn | 2.0.60 | MIT OR Apache-2.0 |
| target-lexicon | 0.13.5 | Apache-2.0 WITH LLVM-exception |
| unicode-ident | 1.0.12 | (MIT OR Apache-2.0) AND Unicode-DFS-2016 |
| walkdir | 2.5.0 | Unlicense/MIT |

The selected wheel contains only watchfiles' own `LICENSE` in its license
metadata; it does not carry the crate license files. The runtime closure
includes crates with separate MIT, Apache-2.0, ISC, and Unicode license texts.
This review identifies a downstream third-party notice gap that must be
resolved before activating this wheel in the bundle.

The owner whitelist covers watchfiles 1.3.0's package-level origin flag. Static
review of the nested crate owners found separate concrete profile flags for
`inotify`, `inotify-sys`, `once_cell`, and build-time `heck`; their owner
disposition is pending. Exact profile evidence is retained privately. No
location is inferred from a package or maintainer name.

Static inspection of the exact Rust runtime and build scripts found no
telemetry, credential access, or outbound client code. The compiler/proc-macro
build scripts probe target/compiler/Python configuration; expected registry
transfers are shown in the release log. No bundled agent instruction files
were found in the crate archives. OSV returned zero exact-version matches for
these 26 crates on 2026-11-01; that query does not prove no advisory exists.

The production CORE Uvicorn entrypoints construct `uvicorn.Config` without
`reload=True`; no `--reload` option is exposed by those paths. Uvicorn 0.34.0's
`standard` extra is what introduces watchfiles for development reload. The
CORE service does use its WebSocket endpoint, so any future narrowing of the
extra must preserve the required WebSocket backend. No dependency pins or
requirements were changed in this review.

The wheel's entry point metadata was reviewed but not executed. Source-build
hooks are excluded from our activation path: the selected input is the binary
wheel. The upstream release log was examined as provenance data; no workflow,
Cargo command, package install, import, or source build was run here.

## Scope limits

All eight exact source archives were hash-verified, extracted as data with
path checks, compared against their release tag snapshots, and reviewed
statically. Source packages, build backends, tests, GitHub Actions, and
workflows were not installed, imported, built, or run. The private copies have
GitHub Actions disabled; release and publishing workflows are not part of the
CORE runtime. Build-backend requirements were inspected from metadata but not
resolved as a separate pinned graph. The exact parser and libuv commits were copied into owner-controlled private
maintenance repositories with Actions disabled; upstream push URLs are disabled
and the owner pre-push hook remained active. Static review covered the selected
parser source, libuv Linux source/build path, license files, and native wheel
payloads. Source builds remain excluded; no source build hooks, package imports,
or runtime code were executed. The owner has recorded the whitelist disposition
for the six Python package origin-policy flags. The separate nested Rust crate
flags and watchfiles notice gap remain open. This review does not change the
shared readiness inventory or authorize activation.
