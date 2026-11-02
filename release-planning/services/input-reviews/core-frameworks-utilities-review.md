# CORE framework and utility packages

Static source and artifact review of eleven exact CORE pins, dated 2026-11-01.
The versions match the current CORE input and constraints files. The listed
sdists and wheels were retrieved from official PyPI file URLs; their byte
hashes match the captured PyPI release JSON. Each canonical release tag and
commit was independently resolved and copied to a private owner-controlled
repository with GitHub Actions disabled. At intake, this review alone neither
activated packages nor changed the shared readiness inventory.

| Package and role | Source tag and commit | Sdist SHA-256 | Selected Linux wheel SHA-256 | License | Origin disposition |
|---|---|---|---|---|---|
| Alembic 1.13.2 (direct runtime) | [rel_1_13_2](https://github.com/sqlalchemy/alembic/tree/rel_1_13_2), `c57a5b7b4d88296bbfc73c1dd770a9122bc1002e` | `1ff0ae32975f4fd96028c39ed9bb3c867fe3af956bd7bb37343b54c9fe7445ef` | `6b8733129a6224a9a711e17c99b08462dbf7cc9670ba8f2e2ae9af860ceb1953` | MIT | Covered by owner whitelist-all decision |
| SQLAlchemy 2.0.55 (direct runtime) | [rel_2_0_55](https://github.com/sqlalchemy/sqlalchemy/tree/rel_2_0_55), `1d116e2e0cd98e044a552a8cae8896c913f74e94` | `ae40c563bc10a8d56f1fd1f39f069aeb5eb85ca26913b2314dd8d190139258fa` | `998f729f57381f8fdee8e402d2081da76c17a2501fa92c9046c24fdff581c729` | MIT | Covered by owner whitelist-all decision |
| cloudpickle 3.1.2 (transitive runtime) | [v3.1.2](https://github.com/cloudpipe/cloudpickle/tree/v3.1.2), `7576fff24b9769432f76cc6d2c01282583ee87a9` | `7fda9eb655c9c230dab534f1983763de5835249750e85fbcef43aaa30a9a2414` | `9acb47f6afd73f60dc1df93bb801b472f05ff42fa6c84167d25cb206be1fbf4a` | BSD-3-Clause | Covered by owner whitelist-all decision |
| joblib 1.6.0 (transitive runtime) | [1.6.0](https://github.com/joblib/joblib/tree/1.6.0), `cd9a6b05fc4f2b1c8202eb62c4e863484f8cc099` | `2ccc96785b12046c08fd6d55839c12857831b54a3c1673ffadd2f04bfc4eda03` | `3dbbf9f6e4b592a2357b854608e980fe6390d131d7a82f011a377ef2ebef7aba` | BSD-3-Clause | Covered by owner whitelist-all decision |
| NLTK 3.10.4 (direct runtime) | [v3.10.4](https://github.com/nltk/nltk/tree/v3.10.4), `5c41fc04a45e95577a83f3914acda211a994be00` | `44679f4e9220abfd496d2c8cdb22f8425ccbe557604f9aa5cacb1c44003dabc1` | `769ba5413f265b7d3e87cd163cc28efa01e29eeef8bb6080bc907949d9fcfb51` | Apache-2.0 | Covered by owner whitelist-all decision |
| Markdown 3.11.2 (direct runtime) | [3.11.2](https://github.com/Python-Markdown/markdown/tree/3.11.2), `b41e0aaf1181f1a8cb200cf5a815aad7c0020d23` | `87bf5d90f2d2882e2c02fcda182c2800456b985bff38913867c49706481514b0` | `f80390747a2a0ff2ba54da074ce4f862f72a6685f608cd2637b646a6d83993f5` | BSD-3-Clause | Covered by owner whitelist-all decision |
| Pygments 2.21.0 (direct runtime) | [2.21.0](https://github.com/pygments/pygments/tree/2.21.0), `a43b45dcf081b6010c6ab4428f149f7f6d2499c4` | `610ca751c9bc2492b38eb9a38a7fbc93edbbb2d7182edaf34e66ae493dee5c8c` | `2363c69b61c4a97c838da3b130dcd6468f4848992b21a82f2a63ec34377137d9` | BSD-2-Clause | Covered by owner whitelist-all decision |
| tqdm 4.70.1 (transitive runtime) | [v4.70.1](https://github.com/tqdm/tqdm/tree/v4.70.1), `9cf5a12b1f955468a17f0ba3c59092b23e4258ac` | `cefd0eca11b2a37a3aee776544d4f4ae913f02688135b5556b8788dfa474afc4` | `c293e525e6fef9c20e8728fd4612df02a0aa31bb5fe91ecd93e123b1b7bffa73` | MPL-2.0 and MIT | Covered by owner whitelist-all decision |
| tzdata 2026.6 (transitive runtime) | [2026.6](https://github.com/python/tzdata/tree/2026.6), `0d4342c29e1f64211181cf8ad2276cfa59c094ce` | `85d2cd9c09f81f0bb29db27759fc83af4f1e620efb814f8c5bf8b4cc4feece6d` | `0a10eec6e13ef16b627fabed9a5f2ba61a62b1c67f327305f4e7e412a70b4aec` | Apache-2.0 | Covered by owner whitelist-all decision |
| FastAPI 0.141.1 (direct runtime) | [0.141.1](https://github.com/fastapi/fastapi/tree/0.141.1), `95f8322ee1dcda7ceace7b1c4f6c9915b36d748f` | `e8822fc40db1e1858054d7a949a888695bc9bdce70139178e33bd2871a453ca1` | `bfb91aa2d334c61cb35ba9a116fc123b3d3df31640b801cf57a7a78ec3f603b3` | MIT | Covered by owner whitelist-all decision |
| python-multipart 0.0.33 (direct runtime) | [0.0.33](https://github.com/Kludex/python-multipart/tree/0.0.33), `9217f261d36b3fdd38ece3d8c1e38a5a52fb2a3d` | `b8112424a6abd162ec08d390565dd113ad699f2fe6fef3c987b8bbcbfe9e390d` | `8f16c07b36add9da6b2ee87d3efcaf0a45a6de9c3d0a5dd94e9ccf7675a7bc45` | Apache-2.0 | Covered by owner whitelist-all decision |

Selected wheels are the corresponding `py3-none-any` wheel for each package,
except SQLAlchemy, which uses
`sqlalchemy-2.0.55-cp313-cp313-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl`,
and tzdata, which uses `tzdata-2026.6-py2.py3-none-any.whl`.

## Source, wheel, and license checks

Each sdist was checked for unsafe paths and special archive entries before
extraction. Files common to its exact Git release tag were compared byte for
byte. No runtime Python source mismatch was found. Sdist differences were
packaging metadata: generated `setup.cfg` normalization in Alembic, SQLAlchemy,
NLTK, and tzdata; FastAPI's sdist materialized version `0.141.1` and
normalized/generated project metadata in `pyproject.toml`. The other sdists
had no differing common files. Common-file comparison counts were 148, 933, 6,
166, 831, 410, 2796, 80, 650, 1184, and 79 respectively in the table order.

All selected wheel `RECORD` hashes and sizes passed. No wheel contains a
`.pth` file. Ten SQLAlchemy CPython 3.13 extension files in the wheel are the
five expected Cython modules (`collections`, `immutabledict`, `processors`,
`resultproxy`, and `util`) in both `.so` and `.pyx` form. The extension source
is package-local; `readelf` showed only `libpthread.so.0` and `libc.so.6` as
dynamic shared-library dependencies for each extension. The extensions were
not loaded. This static review does not claim a reproducible build match
between those wheel binaries and source.

The wheel license and notice files match their corresponding sdist files.
tzdata's wheel includes both its package license and a separate
`licenses/LICENSE_APACHE` notice. Its `zoneinfo` payloads are timezone data;
sample `America/New_York` and `UTC` files were identified as TZif data, not
executable code. Joblib's wheel includes ten historical pickle fixtures under
`joblib/test/data`. They were not deserialized; loading untrusted pickle data
can execute code.

Build declarations inspected: setuptools for Alembic, SQLAlchemy, joblib, NLTK,
Markdown, and tzdata; Flit Core for cloudpickle; Hatchling for python-multipart;
Hatchling for Pygments; setuptools and setuptools-scm for tqdm; and
PDM-backend for FastAPI. Alembic's `setup.py` only checks the setuptools
version before calling `setup()`. SQLAlchemy's setup code conditionally
compiles its five local Cython modules, controlled by
`DISABLE_SQLALCHEMY_CEXT` and `REQUIRE_SQLALCHEMY_CEXT`. NLTK's setup reads the
local version and README before declaring packages and extras. FastAPI's
sdist contains generated version metadata. These paths were inspected but no
backend or hook was run; build backend source and its dependency graph were not
independently reviewed in this batch.

## Runtime behavior and package instructions

The base runtime dependency metadata matches the CORE graph: Alembic depends on
SQLAlchemy and Mako; SQLAlchemy has a platform-selected greenlet requirement
and typing-extensions; joblib depends on cloudpickle; NLTK depends on
defusedxml, click, joblib, regex, and tqdm; FastAPI depends on Starlette,
Pydantic, typing-extensions, typing-inspection, and annotated-doc. The other
packages have no base runtime dependencies in the selected platform metadata.
Development, documentation, machine-learning, database-driver, and messaging
extras are not selected by this lock.

SQLAlchemy and Alembic perform database operations when applications or
migrations explicitly configure an engine/connection. NLTK's corpus downloader
uses HTTPS to retrieve an index and data only when its downloader API is
called; package import does not trigger corpus retrieval. Cloudpickle and
joblib provide Python object serialization, so untrusted serialized inputs
must not be loaded. Joblib's process-based parallel execution is caller
configured. tqdm's Slack, Telegram, and Discord integrations send requests
when explicitly constructed with the respective credentials; they are
optional integrations, not automatic progress-bar behavior. FastAPI defines
application request handling; it does not initiate outgoing API calls as an
import side effect. Markdown extension loading, Pygments highlighting,
timezone lookup, and multipart parsing are explicit library operations. No
hidden telemetry or analytics path was identified in the inspected runtime
code.

FastAPI's wheel and sdist include `.agents/skills/fastapi/SKILL.md` and six
reference Markdown files. These give FastAPI API/style guidance, local CLI
examples, and recommendations for optional development libraries. They were
read as untrusted package data, not followed. No credential-exfiltration or
unsafe system-modification instruction was identified. No other package in
this batch contains `AGENTS.md`, `CLAUDE.md`, `SKILL.md`, Gemini, or Copilot
instruction files in its release source snapshot or sdist.

The captured PyPI records had empty vulnerability arrays. An exact-version
OSV batch query on 2026-11-01 returned eleven empty result objects. These are
point-in-time database results, not proof that no advisory exists.

## Scope and readiness

The private copies are `Capsize-Games/{alembic,sqlalchemy,cloudpickle,joblib,nltk,markdown,pygments,tqdm,tzdata,fastapi,python-multipart}-maintenance`.
All were verified private with GitHub Actions disabled, and each retained tag
peels to the exact commit in the table. Source artifacts and PyPI records are
retained in the ignored private audit directory. Packages, build backends, and
tests were not installed, imported, built, or run. No runtime API, downloader,
database connection, network integration, pickle fixture, or FastAPI agent
instruction was executed. Origin findings are covered by the owner's
whitelist-all decision; this public record lists package identities without
publishing personal profile details.

Integration update, 2026-11-02: all eleven exact pins in this batch are now
recorded as source-reviewed in the shared inventory. Their origin dispositions
and exact whitelist identities are listed in
[`DEPENDENCY_DECISIONS.md`](../DEPENDENCY_DECISIONS.md). The CORE freeze workflow
installs the selected hash-locked wheels with `--only-binary=:all:`; the
unreviewed build-backend dependency graphs are therefore outside this selected
wheel-install path. Revisit them if a source-build path is introduced. This
static integration does not establish artifact or runtime validation; the
readiness manifest still records artifact validation as `not-run`.
