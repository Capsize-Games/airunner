# Linux LLM and agent dependency source review

**Status (2026-11-02):** artifact intake and targeted source review are in
progress. This record does not make the 35-package batch ready for activation.
The 35-pin dependency environment has not been installed or run. A separate
local SDK maintenance wheel and focused fake-client tests are described below;
they are not a candidate environment or artifact acceptance run.

## Scope

The candidate graph assigns these 35 exact inputs to `llm_and_agents`:

```text
beautifulsoup4==4.15.0
breadability==0.1.21
chardet==7.6.0
cryptography==50.0.2
diskcache==5.6.3
distro==1.9.0
httpcore2==2.13.1
httpx2==2.13.1
jsonpatch==1.33
langchain-core==1.3.3
langchain-ollama==1.0.0
langchain-protocol==0.0.19
langgraph==1.0.8
langgraph-checkpoint==4.2.0
langgraph-prebuilt==1.0.7
langgraph-sdk==0.3.15
langsmith==0.14.4
lingua-language-detector==2.1.0
llama-cloud==0.1.23
mistral-common==1.12.0
ollama==0.6.3
orjson==3.13.0
ormsgpack==1.12.2
pydantic-extra-types==2.11.1
rank-bm25==0.2.2
requests-toolbelt==1.0.0
sentencepiece==0.2.1
sniffio==1.3.1
soupsieve==2.10
sumy==0.11.0
tenacity==9.2.1
tiktoken==0.14.0
truststore==0.10.4
uuid-utils==0.17.1
zstandard==0.25.0
```

The exact candidate constraints are recorded in
`.headlesscode/service-audit-2026-11-02/linux-release-lock/constraints-linux-nvidia-cu129-linux-release.candidate.txt`.
The candidate resolution evidence identifies this as a metadata-only
Python 3.13/Linux x86_64, binary-only resolution; it is not an installed
environment.

## Artifact intake

PyPI release metadata and artifact digests were collected for all 35 pins.
The selected candidate-compatible wheel hash for each package matches the
candidate constraints. PyPI wheel and source archives were downloaded for 34
packages, and their SHA-256 values match the published PyPI metadata. No sdist
is published for `lingua-language-detector==2.1.0`; its selected CPython 3.13
manylinux x86_64 wheel was separately downloaded and its SHA-256
`f154830ed190a0b0cdb5983a3a92b7456a4b097eca96843352d26d86ade5fb12` matches
both PyPI and the candidate constraints. Its wheel `RECORD` digests were
checked for all seven entries carrying a digest. These checks establish
artifact identity only, not source safety.

The private intake directory contains the captured PyPI metadata and archives:
`.headlesscode/service-audit-2026-11-02/llm-and-agents-source-review/`.

## Source and advisory findings

The LangChain monorepo copy is private at
[`Capsize-Games/langchain-maintenance`](https://github.com/Capsize-Games/langchain-maintenance).
GitHub Actions are disabled. It preserves upstream history and these exact
release branches and tags:

| Package | Release | Upstream commit | Package path |
| --- | --- | --- | --- |
| `langchain-core` | 1.3.3 | `5039dfec1f8e78459540a7f1b52fb0d6d82e3f07` | `libs/core` |
| `langchain-ollama` | 1.0.0 | `69c6e7de5973bfbc50f52a67e090cbb90005186a` | `libs/partners/ollama` |
| `langchain-huggingface` | 1.2.2 | `6fb37dba71da807af60aa7b909f71f0625a666bf` | `libs/partners/huggingface` |
| `langchain-text-splitters` | 1.1.2 | `58c4e5bbdd9d18d7fe7ec83b5a05477d06fe2a8e` | `libs/text-splitters` |

The pinned package metadata uses `hatchling.build`; the inspected package
release metadata declares MIT. The repository `AGENTS.md` and pre-commit
configuration were read as untrusted source content. They were not followed
and no hooks or package build commands were run. The source review for these
three packages is shared with the RAG/document batch; it is not complete merely
because the private copy exists.
The exact `langchain-ollama==1.0.0` source tag is also present in that copy at
`69c6e7de5973bfbc50f52a67e090cbb90005186a`.

The LangGraph monorepo copy is private at
[`Capsize-Games/langgraph-maintenance`](https://github.com/Capsize-Games/langgraph-maintenance).
GitHub Actions are disabled. It preserves source history and reviewed release
branches/tags for `langgraph` 1.0.8, 1.0.10, and 1.2.14; `langgraph-sdk`
0.3.15 and 0.4.6; and `langgraph-prebuilt` 1.0.7 and 1.1.0. The exact
candidate-compatible patched set is:

| Package | Candidate pin | Source commit | PyPI wheel SHA-256 |
| --- | --- | --- | --- |
| `langchain-core` | 1.4.7 | `51578289bb1f696a643e0740be1441039d8af8ce` | `bcadd51951140ecdcba98311dbd931ba5de02a5ba8a2288dad5069c1eea2a13d` |
| `langgraph` | 1.2.14 | `70dd64065bffaa3b6ab61a33f1f020fb54db8efa` | `e3f5f8ff4259f9281b73ff50fc9ef5cc3b025b8936b8283ecdca7cc0c4128690` |
| `langgraph-prebuilt` | 1.1.0 | `3614e88c58af63f597764218646e85c49952b2da` | `51e311747d755b751d5c6b39b0c1446124d3a7643d2515017e6714b323508fc9` |
| `langgraph-sdk` | 0.4.6 | `55b0e36c51d2922b11640b980fcfca1064243a96` | `57122b02bda41d37a97a5e09eb018aa8c9b3dc85c433880073779bd9324b7eea` |
| `langgraph-checkpoint` | 4.2.0 | `f55e77274dad40897ef7b2d52cc7c0b85b792247` | `0547fd228935a0b758865de3a3d6d7a2537c308895d0f9ab092ce9151b5da942` |

The five compatible-set wheels were subsequently downloaded to the ignored
intake directory and their local SHA-256 values match the PyPI metadata above.
PyPI lists no advisories for these five pins. This verifies artifact identity,
not runtime behavior or full source safety.

The LangGraph 1.2.14 `pyproject.toml` directly requires core `>=1.4.7,<2`,
checkpoint `>=4.1.0,<5`, SDK `>=0.4.6,<0.5`, and prebuilt `>=1.1.0,<1.2`.
Thus checkpoint 4.2.0 satisfies the declared range. LangGraph 1.0.10 still
requires SDK `<0.4` and prebuilt `>=1.0.8,<1.1`; it cannot be combined with the
fixed SDK 0.4.6. Keep the current pins out of a candidate that activates these
advisory-affected components until the fixed compatible set is adopted.

The `langchain-core==1.4.7` source ref is now present in the private LangChain
copy as branch `review/langchain-core-1.4.7` and tag `langchain-core==1.4.7`.
Its project metadata declares `hatchling.build`, MIT, and
`langchain-protocol>=0.0.14` (the candidate's 0.0.19 meets this range). The
package tree differs from 1.3.3 across 139 files, so a focused source and
compatibility review remains necessary; the ref's presence is not approval.
Comparing the hash-matched 1.3.3 and 1.4.7 wheels shows 90 changed package
files and one removed module out of 182 old/181 new package files. A bounded
scan of added Python lines in changed modules found no new HTTP, socket,
subprocess, pickle, dynamic import, or `eval`/`exec` call pattern. The package
metadata keeps MIT and the same runtime requirements except that
`langchain-protocol` now requires `>=0.0.14`; the selected 0.0.19 satisfies
it. This narrows the source-change review but does not establish API
compatibility or replace full behavior review.
The LangGraph root `AGENTS.md` was also read as untrusted data; it only
prescribes format/lint/test commands when modifying repository code. The
1.2.14 root has no `.pre-commit-config.yaml`. Its package metadata uses
`hatchling.build`; no workflow, hook, or package command was run.

The shared `pydantic/httpx2` source is privately copied at
[`Capsize-Games/httpx2-maintenance`](https://github.com/Capsize-Games/httpx2-maintenance),
with Actions disabled and upstream tag `v2.13.1` at
`d91c9f4236523eb5978ca800944fa0078f17409f`. Both `httpx2==2.13.1` and
`httpcore2==2.13.1` are packages from this monorepo. Their PyPI metadata
declares BSD-3-Clause, names Tom Christie as author and Pydantic Services Inc.
as maintainer, and uses Hatchling with dynamic-version build helpers. The
source declares `httpx2`'s runtime dependency on exactly matching
`httpcore2==version`; TLS setup uses `truststore` and the documented
`SSL_CERT_FILE`/`SSL_CERT_DIR` environment variables. These are expected client
behaviors, not evidence of unexpected telemetry. The root `AGENTS.md` and
`CLAUDE.md` were read as untrusted text; no source instructions or hooks were
run. The Python package code and dependency behavior still need review before
activation. PyPI reports no advisories for these two pins.

PyPI lists these affected inputs and advisories:

| Current input | Advisory | Review finding |
| --- | --- | --- |
| `langgraph==1.0.8` | [GHSA-g48c-2wqr-h844 / CVE-2026-28277](https://github.com/langchain-ai/langgraph/security/advisories/GHSA-g48c-2wqr-h844) | Versions through 1.0.9 are affected. A writer to a persistent checkpoint store can supply crafted msgpack checkpoint data that may trigger unsafe object reconstruction on load. The compatible candidate moves to 1.2.14. The service-specific checkpoint path and strict-mode behavior are reviewed below. |
| `langgraph-sdk==0.3.15` | [GHSA-fvww-7h3r-vfhp / CVE-2026-104873](https://github.com/langchain-ai/langgraph/security/advisories/GHSA-fvww-7h3r-vfhp) | Versions 0.1.45 through 0.4.3 can apply resource-scoped `actions=` authorization decorators resource-wide. Fixed in 0.4.4. |
| SDK upgrade guard (`0.4.4`–`0.4.5`) | [GHSA-3fx2-cqw9-xr3c / CVE-2026-118667](https://github.com/langchain-ai/langgraph/security/advisories/GHSA-3fx2-cqw9-xr3c) | The current SDK 0.3.15 is outside this advisory's affected range. SDK versions 0.4.0 through 0.4.5 have unencoded path identifiers in v3 streaming; fixed in 0.4.6. LangGraph 1.2.14 requires SDK 0.4.6 or later. |
| `diskcache==5.6.3` | [GHSA-w8v5-vhqr-4h9v / CVE-2025-69872](https://github.com/advisories/GHSA-w8v5-vhqr-4h9v) | A writer to the cache directory can cause code execution when a cached value is read; the reviewed advisory has no fixed release listed. |

The application source currently builds local `StateGraph` workflows and uses
its own `DatabaseCheckpointSaver`; the inspected saver keeps its checkpoint
state in process and reconstructs it from application chat history. No
`langgraph_sdk`, `RemoteGraph`, or `auth.on` use was found in the service
source. This narrows the observed checkpoint threat path but does not remove
the package advisory or authorize retaining the vulnerable pin.

### Fixed LangGraph closure and service-specific checkpoint handling

The proposed compatible closure is `langchain-core==1.4.7`,
`langgraph==1.2.14`, `langgraph-prebuilt==1.1.0`,
`langgraph-sdk==0.4.6`, and `langgraph-checkpoint==4.2.0`. The exact wheel
SHA-256 values in the ignored `artifacts/fixed-wheels/verification.json` were
recomputed from the local files and match its PyPI hashes. The candidate
metadata declares that LangGraph 1.2.14 requires core `>=1.4.7,<2`,
checkpoint `>=4.1.0,<5`, prebuilt `>=1.1.0,<1.2`, and SDK `>=0.4.6,<0.5`;
the selected pins satisfy those ranges. Each of the five wheel metadata records
reports MIT and no PyPI advisory. The local fixed wheels were inspected as
archives; no wheel was installed or imported.

The private LangGraph maintenance checkout is on `review/langgraph-1.2.14`;
the matching SDK, prebuilt, and checkpoint release refs are present there. The
reviewed package projects use the declared Hatchling backend. No package build,
hook, workflow, or repository instruction was run. For `langchain-core==1.4.7`,
the private LangChain copy records commit
`51578289bb1f696a643e0740be1441039d8af8ce`; the inspected source bytes came
from the locally captured, hash-matched wheel rather than a checked-out
1.4.7 worktree. Static inspection found its Mermaid API renderer can send graph
syntax to `https://mermaid.ink` when that explicit rendering method is called;
no AIRunner service call to `draw_mermaid_png` or `draw_mermaid` was found.

The fixed SDK encodes path parameters through `_quote_path_param` before
interpolating identifiers into its REST and streaming routes. Its default
client helper may read LangGraph/LangSmith/LangChain API keys from the
environment when callers omit an explicit key; this is SDK authentication
behavior. No LangGraph SDK client or those API key names are used by the
service source search. The checkpoint package also contains the optional
`MemorySaver` import/export pickle path; AIRunner does not instantiate that
saver. `JsonPlusSerializer` defaults `pickle_fallback` to false.

Targeted source inspection of the fixed LangGraph and checkpoint wheels found
that `LANGGRAPH_STRICT_MSGPACK=true` makes `JsonPlusSerializer` default to its
safe msgpack type set. During graph compilation, LangGraph derives an allowlist
from state and channel schemas and applies it through the checkpointer's
`with_allowlist` method when available. Without the environment setting, the
serializer defaults to permissive msgpack reconstruction with a warning. The
checkpoint serializer's pickle fallback is disabled by default; it is separate
from the msgpack strict-mode control.

The service does not currently persist serialized LangGraph checkpoints.
`WorkflowManager` constructs `DatabaseCheckpointSaver`, and the graph builder
passes that saver to `workflow.compile(checkpointer=...)`. Its `put` and
`get_tuple` implementations retain checkpoint objects in the process-local
`_checkpoint_state` mapping and rebuild fallback state from application chat
messages. They do not call the inherited serializer, read msgpack or pickle
checkpoint bytes, or use a persistent LangGraph checkpointer. Repository search
found no other saver implementation or LangGraph SDK client use in the service.
Thus the advisory's checkpoint-store deserialization path was not found in the
current service-owned saver. This is a scoped code-path finding, not a claim
that arbitrary database writes or unrelated serializers are safe.

For this service, the concrete disposition is to replace the affected
`langgraph==1.0.8` and incompatible older SDK/prebuilt pins with the fixed
compatible closure above. No additional strict-msgpack runtime setting is
required to protect the current `DatabaseCheckpointSaver`, because it does not
deserialize through that serializer. If the service later adopts a persistent
LangGraph saver or uses the inherited serializer, enable
`LANGGRAPH_STRICT_MSGPACK=true` and verify its schema-derived allowlist against
the saved state before activation. This review did not change dependency locks
or runtime environment configuration, and no workflow execution was run.

The service creates `llama_cpp.Llama` directly and does not call
`LlamaDiskCache` or `set_cache`. In the reviewed `llama-cpp-python` 0.3.21
source, the optional server creates `LlamaDiskCache` only when
`settings.cache` is true and `settings.cache_type == "disk"`; server defaults
are `cache=false` and `cache_type="ram"`. No `llama_cpp.server` use was found
in service source. Its default disk path is `.cache/llama_cache`. The unsafe
disk-cache path remains present in the dependency and must not be enabled or
exposed without a verified mitigation; no cache contents were opened or loaded.

The exact `diskcache==5.6.3` source is privately copied at
[`Capsize-Games/diskcache-maintenance`](https://github.com/Capsize-Games/diskcache-maintenance),
with Actions disabled, tag `v5.6.3`, and commit
`323787f507a6456c56cce213156a78b17073fe00`. In `diskcache/core.py`, the
default `Disk` serializer pickles non-primitive keys and values, then uses
`pickle.load` for cache reads. This matches the published advisory's affected
behavior. The package declares Apache-2.0, has no runtime dependencies, and its
legacy setuptools `setup.py` defines a test command but no custom install
command. The service does not create this cache today; there is no fixed
upstream release in the reviewed advisory, so the unsafe disk-cache option
remains excluded from activation.

To prevent this transitive package from being imported or installed by the
base `llama-cpp-python` dependency, its private maintenance copy was patched
from the CUDA handoff source commit `d2bcbac46605f11d382426dd88d67e8b5c124cd7`.
`diskcache` is now an explicit `disk` extra and is imported only when
`LlamaDiskCache` is constructed. `LlamaRAMCache` and the `LlamaCache` alias
remain in the base package; `LlamaDiskCache` remains available with the extra.
AIRunner uses no disk-cache API, and the wrapper server defaults remain
`cache=false` and `cache_type="ram"`. This is dependency isolation for the
service path, not a fix to the diskcache vulnerability; the extra remains
unsafe and is not enabled for AIRunner.

The patch is committed as `72c921c` in private pull request
[Capsize-Games/llama-cpp-python-maintenance#7](https://github.com/Capsize-Games/llama-cpp-python-maintenance/pull/7),
merged to the repository's `review-v0.3.21` default branch at
`52a8b14134713c53f72ba8cfea78a83393950d5c`, and released under annotated tag
`v0.3.21+capsize.1` ([private source release](https://github.com/Capsize-Games/llama-cpp-python-maintenance/releases/tag/v0.3.21%2Bcapsize.1)).
Three source-only AST/metadata checks passed. GitHub Actions are disabled for
the maintenance repository, so no CI checks were available; the native C++
build and full upstream test suite were not run. The main project lock, setup,
CUDA recipe, and candidate artifact have not yet adopted or validated this
change. The 35-pin candidate remains blocked until the selected AIRunner input
is rebuilt and resolved without activating the vulnerable diskcache package.

`lingua-language-detector==2.1.0` has no published sdist. The corresponding
native implementation is present in the private
[`Capsize-Games/lingua-rs-maintenance`](https://github.com/Capsize-Games/lingua-rs-maintenance)
copy at upstream tag `v1.7.0`, commit
`c6eea404d8e09b7f455da2da79f7f6f0e149ce76`; that Rust tag's `pyproject.toml`
declares the same Python distribution version, 2.1.0, and its release workflow
builds the PyO3 wheel on `v1.*` tags. Its wheel upload time is consistent with
that release tag. This is provenance evidence, not a reproducible-build or
artifact-attestation claim. The private copy has Actions disabled. The Rust
release uses Apache-2.0 and its optional Python feature includes PyO3 and
`serde-pickle`; source contains pickle state methods on Python enum wrappers.
The application language-detection helper only builds a detector for six
languages and calls `detect_language_of`; no application pickle path was found.
The related `lingua-py` docs/training repository was also privately copied at
tag `v2.1.0` for context; the native wheel build is sourced from `lingua-rs`.
No package code, workflows, Python pickle APIs, or model profiles were run
or loaded.

An archive-member scan identified repository instruction files in the
chardet, cryptography, and LangSmith source archives. Those instructions were
read as untrusted data rather than followed. No build, hook, test, or package
code was run.

## Review boundary and next work

The initial update completed a targeted source review of the fixed LangGraph
closure and checked its applicability to the service-owned saver. The
package-specific table below adds bounded source and caller findings for the
remaining exact inputs, but does not complete the 35-pin batch. Hash-matched
source archives are available for 34 inputs; that does not substitute for
owner-private source copies, complete per-pin instruction/hook/build and
advisory review, or artifact/runtime acceptance. The `diskcache==5.6.3` input
in the original batch remains affected by its advisory. The private Llama
wrapper change removes it from the wrapper's base dependency and lazy-loads it
only through an explicit `disk` extra; the extra is not selected, and the
underlying package is not fixed. The exact new frozen graph must confirm the
package is absent from the service install. No model or candidate package was
loaded as part of this review.

During the original archive inspection, no candidate package was installed,
built, or executed, and no model weights, live graph, or pickle cache data were
read. The later Mistral boundary regression test and its exact import scope are
recorded below.

## Additional targeted source inspection (2026-11-02)

The exact source archives for `distro==1.9.0`, `chardet==7.6.0`,
`cryptography==50.0.2`, `sentencepiece==0.2.1`,
`mistral-common==1.12.0`, `beautifulsoup4==4.15.0`,
`requests-toolbelt==1.0.0`, `ollama==0.6.3`, and the listed small pure-Python
utilities were scanned and selected source files inspected directly from the
hash-verified archives. This was static inspection only; the archives were not
extracted to importable trees and no package code or build hook was run.

`distro`'s subprocess calls are conditional OS-information probes for
`lsb_release -a`, `uname -rs`, and (on AIX) `oslevel`; errors are caught and
returned as absent values. A source search found no AIRunner service import or
call to `distro`, so these probes are not in the observed service path.

`chardet` declares Hatchling as its backend. Its optional Cython build hook
returns without running unless `HATCH_BUILD_HOOK_ENABLE_MYPYC` is exactly `1`
or `true`; when enabled, it writes a temporary setup script for the package's
own `_kernel.py` and invokes it with the current Python executable. This
candidate selects a prebuilt wheel, so this sdist build hook is excluded from
the candidate install path and was not run. `cryptography`'s sdist has a Rust
build backend and release/test scripts with subprocess use; those scripts were
not run. `sentencepiece`'s sdist `setup.py` invokes shell `pkg-config` probes
and may call `build_bundled.sh`/CMake to compile its bundled native library.
That sdist build is also outside the binary-only candidate install path; the
setup script was read but not run. A binary-only resolution does not establish
that building these sdists is safe or supported.

The AIRunner Mistral native-tokenization path converts LangChain human message
content to `MistralUserMessage` and passes the request to
`MistralTokenizer.encode_chat_completion`. In the inspected Mistral source,
`ImageURLChunk` accepts data URLs, file URIs, and HTTP(S), and its HTTP(S)
branch calls `download_image(url=url, timeout=None)`. AIRunner's own multimodal
streaming helper currently serializes PIL images as base64 data URLs, and the
legacy Ollama compatibility route renders only string content. The native
adapter now rejects HTTP(S) URLs in structured `image` and `image_url` chunks
before constructing Mistral messages, using stable error code
`remote_image_url_unsupported_for_mistral_native`. Inline data URLs, local
image references, and ordinary text that mentions HTTP URLs remain accepted.
No fetch is added at this layer.

For `beautifulsoup4`, application callers pass already available HTML strings
to `BeautifulSoup(..., "html.parser")`; the inspected `requests-toolbelt`
package provides opt-in Requests adapters and no direct AIRunner import was
found. `ollama` and `langchain-ollama` are used as configured local-provider
clients; their HTTP behavior follows the configured Ollama endpoint. No model
or Ollama endpoint was contacted. The additional archive scan found pickle
examples in test files and subprocesses in build/release/test files for several
native distributions; those are not evidence of runtime calls by AIRunner.

Additional caller tracing found `sumy` used with `PlaintextParser.from_string`
for already available text, not its URL fetch helper. Its English tokenizer
uses NLTK; the separate CORE source review records the app's explicit NLTK
resource setup and pickle-safe `punkt` loading. `rank-bm25` is an optional local
search scorer with an in-app fallback. `langsmith` can send traces to its
service when its opt-in environment configuration is enabled; no such setting
or direct LangSmith client use was found in AIRunner source. `tiktoken` can
download a vocabulary file on cache miss when `get_encoding` is called, but no
direct AIRunner import or call was found. `llama-cloud` is an API client with
explicit network methods and caller-supplied API credentials; no AIRunner
import or call was found. These are source-usage findings, not proof that
indirect consumers can never activate an optional code path.

The Mistral tokenizer path is narrower than the package's download APIs:
AIRunner initializes `MistralTokenizer.from_file` from a selected local
`tekken.json`; it does not call `from_hf_hub`. The Tekken implementation builds
`tiktoken.Encoding` from that local file's ranks and does not call
`tiktoken.get_encoding`, so this path does not invoke tiktoken's built-in
encoding cache-miss downloader. Mistral Common still exposes optional
Hugging Face tokenizer download methods and image/audio URL loaders; they are
not treated as safe merely because the traced AIRunner path does not call
them. The native adapter's structured HTTP(S) image rejection is recorded
above.

The exact `httpx2==2.13.1` and `httpcore2==2.13.1` source is available from
the private `httpx2-maintenance` copy at tag `v2.13.1`, commit
`d91c9f4236523eb5978ca800944fa0078f17409f`; the copied source tree carries
`AGENTS.md` and `CLAUDE.md`, which were read only as untrusted package content.
Both wheels and source archives have matching PyPI digests. The wheel
metadata declares BSD-3-Clause, and both wheel license files match their
source `LICENSE.md` files. Their project metadata uses Hatchling with
`uv-dynamic-versioning` and `hatch-fancy-pypi-readme`; the dynamic-version
backend/build tooling was inspected from metadata but not run. No PyPI
advisory was listed for these pins.

The active HTTP behavior is conventional client behavior: `httpx2` sends
requests through its coupled `httpcore2==2.13.1` transport to caller-supplied
URLs. The transport supports direct connections and configured HTTP/SOCKS
proxies. TLS verification defaults to the system trust store through
`truststore`; `SSL_CERT_FILE` and `SSL_CERT_DIR` are explicit overrides, and
the API also exposes an explicit `verify=False` option. This is not a
background telemetry path. The service does not import either package
directly; `httpx2` is a LangSmith dependency, whose trace sending remains
opt-in as described above. No live request or TLS handshake was made.

### Per-pin source-review disposition

The following is a disposition of the original 35-input candidate. Four
LangGraph-family selections are now replaced in the proposed graph by the
fixed compatible closure: `langgraph==1.2.14`,
`langgraph-prebuilt==1.1.0`, `langgraph-sdk==0.4.6+capsize.1` (local wheel),
and `langchain-core==1.4.7`; `langgraph-checkpoint==4.2.0` remains. The exact
locked graph is still owned by the release integrator. “Scoped” means there
is concrete source and caller evidence in this record; it does not mean the
package has passed full audit, private-copy, build, or runtime acceptance.

| Original exact input | Static disposition | Remaining boundary |
| --- | --- | --- |
| `beautifulsoup4==4.15.0` | Scoped: app parses supplied HTML with `html.parser`; dependency `soupsieve` is used for selectors. | Source archive contains pickle references in tests only; no wheel code execution or full source review. |
| `breadability==0.1.21` | Scoped: app uses text extraction; wheel includes BSD license; URL client script is not called by the traced path. | The script's fetch behavior remains available in the package; no private maintenance copy or live fetch. |
| `chardet==7.6.0` | Scoped: optional Cython hook is gated by `HATCH_BUILD_HOOK_ENABLE_MYPYC`; candidate uses a wheel. | Hook/build excluded and unrun; instruction files were treated as untrusted. |
| `cryptography==50.0.2` | Scoped: wheel is the Apache-2.0 OR BSD-3-Clause artifact; the sdist release scripts use subprocesses. | No build scripts or crypto package code were run; no direct feature-specific service trace. |
| `diskcache==5.6.3` | Confirmed unsafe pickle-on-read behavior and GHSA-w8v5-vhqr-4h9v / CVE-2025-69872. Private Llama wrapper moves it to an opt-in disk extra and lazy import. | The package remains vulnerable and must remain absent from the selected base install; the patch does not fix diskcache. |
| `distro==1.9.0` | Scoped: subprocess use probes OS information; service search found no caller. | Probe code was not executed; no private copy. |
| `httpcore2==2.13.1` | Scoped source and TLS behavior reviewed above; coupled exactly to `httpx2==2.13.1`. | No network/TLS test; optional protocols and proxy modes were not exercised. |
| `httpx2==2.13.1` | Scoped source and caller behavior reviewed above; standard caller-directed HTTP client. | No request made; service has no direct import, and LangSmith trace path is opt-in. |
| `jsonpatch==1.33` | Scoped as LangChain Core's RFC 6902 utility dependency; wheel includes modified BSD license. | No standalone service caller or package-specific private copy; behavior was not separately tested. |
| `langchain-core==1.3.3` | Original pin is superseded by the fixed `1.4.7` candidate; fixed wheel and source commit evidence are recorded above. | The 1.4.7 wheel diff is boundedly reviewed above, but service API compatibility is untested; Mermaid rendering can contact mermaid.ink when called. |
| `langchain-ollama==1.0.0` | Scoped as an Ollama client used with the configured local provider endpoint; wheel and source archive inspected. | No endpoint contacted; no private copy or provider integration test. |
| `langchain-protocol==0.0.19` | Its sdist contains generated TypedDict/Literal protocol declarations and a `py.typed` marker; metadata and source declare MIT. No transport or runtime client is present. | No separate caller test; no GitHub source was used for this artifact review. |
| `langgraph==1.0.8` | Superseded by fixed `1.2.14` due GHSA-g48c-2wqr-h844 / CVE-2026-28277. | Fixed graph has not been installed or run; see service saver analysis above. |
| `langgraph-checkpoint==4.2.0` | Scoped: fixed-compatible closure dependency; `JsonPlusSerializer` has strict msgpack mode and pickle fallback defaults false. | Service's process-local saver does not serialize through it; no persistent-checkpoint runtime test. |
| `langgraph-prebuilt==1.0.7` | Superseded by fixed-compatible `1.1.0`. | No package import or graph execution. |
| `langgraph-sdk==0.3.15` | Superseded by `0.4.6+capsize.1`; fixes the scoped authorization/path-encoding advisory chain and requires websockets `>=17.4,<18`. | New wheel's focused fake-client transport tests passed; full SDK suite and CI were unavailable. |
| `langsmith==0.14.4` | Scoped: remote trace export is opt-in; no setting or direct client was found in service source. | Network client remains available to indirect callers; no live trace or private copy. |
| `lingua-language-detector==2.1.0` | Wheel hash and seven RECORD digests verified; private Rust source tag/version mapping and Apache-2.0 notice reviewed. | No sdist; release wheel was not reproducibly rebuilt and detector/model profiles were not loaded. |
| `llama-cloud==0.1.23` | Scoped: caller-driven API client; no AIRunner import/call found. | No service use found; no endpoint request or private copy. |
| `mistral-common==1.12.0` | Scoped: native tokenizer loads a local file; structured remote image chunks are now rejected by the AIRunner adapter before package URL fetch. | Package still exposes image/audio/tokenizer download APIs; no model or remote URL used. |
| `ollama==0.6.3` | Scoped: HTTP client follows configured Ollama endpoint; service provider use is explicit. | No daemon contacted; no private copy or integration runtime test. |
| `orjson==3.13.0` | Scoped native wheel metadata and source archive; wheel contains its Apache, MIT, and MPL notices. A 44-file source notice supplement is recorded below. | Final bundle collector must include the supplement and verify it against this wheel hash. |
| `ormsgpack==1.12.2` | Scoped native wheel; Apache-2.0 and MIT notices are present in the wheel. It is a LangGraph checkpoint dependency. | Service's current saver does not call the checkpoint serializer; native code was not imported. |
| `pydantic-extra-types==2.11.1` | Scoped metadata/source scan; optional type validators, no package-level network startup identified. | No direct service import found; no private copy or feature-specific test. |
| `rank-bm25==0.2.2` | Scoped as optional local scoring with in-app fallback; no network behavior identified. | Feature is optional; no activation or ranking test in this review. |
| `requests-toolbelt==1.0.0` | Scoped: provides opt-in Requests adapters/helpers; no direct AIRunner import found. | Helpers were not exercised; no private copy. |
| `sentencepiece==0.2.1` | Scoped native sdist setup/build probes; candidate selects a binary wheel, so build hook path is excluded. A five-file source notice supplement is recorded below. | Final bundle collector must include the supplement and verify it against this wheel hash. |
| `sniffio==1.3.1` | Scoped as a small AnyIO runtime dependency; MIT/Apache notices ship in wheel. | No standalone service caller or private copy. |
| `soupsieve==2.10` | Scoped through BeautifulSoup selector use; MIT notice ships in wheel. | No standalone direct service import or private copy. |
| `sumy==0.11.0` | Scoped: caller uses `PlaintextParser.from_string`; no URL fetch helper in the traced path. | NLTK tokenizer resource setup is covered by CORE review; no summarizer runtime test here. |
| `tenacity==9.2.1` | Scoped: retry policy helper; HTTP 429 wait strategy only classifies response state and does not issue requests. | No service path test in this review. |
| `tiktoken==0.14.0` | Scoped: Mistral Tekken path constructs `Encoding` from local ranks; its built-in downloader is not called on that path. | Other direct `get_encoding` callers could fetch on cache miss; no service-wide exhaustive indirect-call proof. |
| `truststore==0.10.4` | Scoped as the HTTPX2 TLS system-root provider; environment CA overrides are explicit. | No TLS handshake or certificate environment test. |
| `uuid-utils==0.17.1` | Scoped native wheel and BSD-3-Clause notice; no direct AIRunner import found. | No native import or private copy. |
| `zstandard==0.25.0` | Scoped native wheel and BSD-3-Clause wrapper notice; no direct AIRunner import found. The bundled Zstandard library's BSD license is preserved below. | Final bundle collector must include the supplement and verify it against this wheel hash; no native import or decompression test. |

Source notice texts are now preserved byte-for-byte in
`packaging/licenses/orjson-3.13.0-supplement/` (44 package and vendored-crate
license files) and `packaging/licenses/sentencepiece-0.2.1-supplement/` (the
project notice and four bundled-library notices), plus the bundled Zstandard
library BSD notice in `packaging/licenses/zstandard-0.25.0-supplement/`. Each directory's
`source-manifest.json` binds the file SHA-256 values and sizes to the exact
pin, hash-verified sdist, and selected candidate wheel. This closes the
evidence/copy gap for these texts; the dependency notice collector still needs
to explicitly include the supplements in the final bundle and verify the
bound wheel hashes. Neither wheel was repacked.

The wheel archive scan also found several sdist instruction files (including
chardet, cryptography, LangSmith, HTTPX2, and others); these were treated as
untrusted data, not followed. No sdist build was performed. The intake JSON
still labels published artifact rows `artifact-hashes-verified-review-pending`;
that status is accurate because artifact hash checks and the bounded source
observations above do not satisfy private-copy and full review requirements.

The exact package archives for `jsonpatch`, `pydantic-extra-types`,
`rank-bm25`, `sniffio`, `soupsieve`, and `tenacity` contain utility/model or
retry code, not package-level network startup. Tenacity's inspected optional
wait strategy can classify HTTP 429 responses and references `requests`; it
does not send requests itself. `orjson`, `ormsgpack`, `sentencepiece`,
`uuid-utils`, and `zstandard` include native code or native build inputs; the
application has no direct `orjson`, `ormsgpack`, `uuid_utils`, or `zstandard`
import in the searched service tree. The Rust-backed language detector was
reviewed separately above. `breadability` includes a standalone client script
that can fetch a URL; AIRunner does not invoke that script in the traced
content-extraction path. No archive instructions, build hooks, tests, or
package commands were run during this static scan.

This document records bounded, package-specific static dispositions for the
LLM partition. The authoritative candidate partition contains 40 exact pins,
not the 35 shown in the earlier intake snapshot. The five omitted pins and
their artifact/source evidence are recorded below. Earlier package rows retain
their stated exclusions and limitations; this record does not upgrade any
missing evidence or imply runtime/build acceptance. Private-copy and runtime
acceptance remain separate from static source review.

The Mistral boundary regression test was run with the existing project `.venv`:
6 passed, with one existing Pydantic deprecation warning. It imported the
AIRunner adapter and the already installed `langchain_core.messages` module;
it did not call Mistral Common, load a model, fetch an image, or access the
network. No candidate wheel was installed or built for this test.

### WebSocket compatibility in the frozen graph

The frozen security-replacement constraints selected `websockets==16.1`
because `langgraph-sdk==0.4.6` declares `websockets>=14,<17`. This pin is not
safe for the current service runtime: AIRunner starts Uvicorn with its
`standard` extra and exposes FastAPI WebSocket routes, so the Uvicorn
`websockets` backend is used when that dependency is present. Upstream's 17.4
changelog states that all earlier implementations were affected by memory
exhaustion from messages fragmented into more than 4096 frames; 17.4 adds the
frame-count cap. The 16.1 changelog does not contain that fix. Do not activate
16.1 for the service WebSocket listener.

The existing private `websockets-maintenance` source copy has the reviewed
17.4 source branch at commit `625a59ed613ac60e60d577dd64b8641d59ecb2b1`; the
core HTTP review records its release artifact and source checks. The exact
`langgraph-sdk==0.4.6` private source branch is
`review/sdk-0.4.6` at upstream commit
`55b0e36c51d2922b11640b980fcfca1064243a96`. Its async transport imports
`websockets.asyncio.client.connect`; its sync transport imports
`websockets.sync.client.connect`; both pass `additional_headers`,
`ping_interval`, and `ping_timeout`. Those names and parameters are present in
the privately reviewed 17.4 source. The SDK's stream default is SSE, and no
SDK client use was found in AIRunner.

The private SDK maintenance branch changes only the package version to
`0.4.6+capsize.1` and the `websockets` dependency bound to `>=17.4,<18`; its
transport behavior is unchanged. It was merged to the private repository's
review branch and released as `sdk==0.4.6+capsize.1`. The offline wheel is
staged at `package/wheelhouse/langgraph_sdk-0.4.6+capsize.1-py3-none-any.whl`;
its hash, RECORD entries, runtime source identity, dependency metadata, and
embedded MIT license were checked against the private source. Twenty-eight
existing async and sync SDK WebSocket transport test functions passed against
the 17.4 source tree with in-process fake clients. The repository's pytest
config could not run these tests because `pytest-asyncio` is absent in the
pre-existing `.venv` (`Unknown config option: asyncio_mode`); the functions
were invoked directly after confirming they require no fixtures. No real
WebSocket server, external network, or model was used. The wheel is not yet
selected by the shared frozen graph; root owns that resolution. Do not retain
the vulnerable `websockets==16.1` service runtime pin while that update is
pending.


### Corrected partition scope: five omitted exact pins

The authoritative `role_partition.llm_and_agents` list in
`.headlesscode/service-audit-2026-11-02/linux-release-lock/compel-resolution-comparison.json`
contains 40 packages. The earlier intake note counted 35 and omitted the five
pins below. These package records close that scope-count discrepancy; they do
not claim that the other 35 rows' explicit limitations have been resolved.

Each exact release's PyPI release JSON, wheel, and sdist were inspected as data.
The wheel and sdist SHA-256 values below were checked against the release file
metadata. Wheel RECORD entry hashes and sizes were independently checked: all
entries passed (8 jsonpointer, 43 jsonschema, 28 jsonschema-specifications,
19 referencing, 9 rpds-py). Python modules shared between wheel and sdist
matched byte-for-byte for jsonpointer (1/1), jsonschema (37 common files),
jsonschema-specifications (4/4), and referencing (13/13). rpds-py is a native
wheel, so the binary module cannot be equated byte-for-byte with Rust source.

| Exact pin | Selected Linux CPython 3.13 wheel (SHA-256) | sdist (SHA-256) | Reviewed source tag commit |
|---|---|---|---|
| `jsonpointer==3.2.0` | `jsonpointer-3.2.0-py3-none-any.whl` — `3e25c9bcadf5ae20c3420922234eaba1ae36ab9bef64cd72454aeaceb0b29aad` | `jsonpointer-3.2.0.tar.gz` — `807db557622fbe07a0d49e19cf4795a269d55eee5ba345fb9959d148eba5ef94` | `v3.2.0` — `f1f238bf996310f28b938801c41edbe255418cf7` |
| `jsonschema==4.26.0` | `jsonschema-4.26.0-py3-none-any.whl` — `d489f15263b8d200f8387e64b4c3a75f06629559fb73deb8fdfb525f2dab50ce` | `jsonschema-4.26.0.tar.gz` — `0c26707e2efad8aa1bfc5b7ce170f3fccc2e4918ff85989ba9ffa9facb2be326` | `v4.26.0` — `a7277432b0f7bcd0551f6e589d30457017125df4` |
| `jsonschema-specifications==2025.9.1` | `jsonschema_specifications-2025.9.1-py3-none-any.whl` — `98802fee3a11ee76ecaca44429fda8a41bff98b00a0f2838151b113f210cc6fe` | `jsonschema_specifications-2025.9.1.tar.gz` — `b540987f239e745613c7a9176f3edb72b832a4ac465cf02712288397832b5e8d` | `v2025.9.1` — `3b846010c34ce254d8ced23023451d1d64de37f5` |
| `referencing==0.37.0` | `referencing-0.37.0-py3-none-any.whl` — `381329a9f99628c9069361716891d34ad94af76e461dcb0335825aecc7692231` | `referencing-0.37.0.tar.gz` — `44aefc3142c5b842538163acb373e24cce6632bd54bdb01b21ad5863489f50d8` | `v0.37.0` — `944ed5a20bc5125f2349156cbdc365daac0e67e6` |
| `rpds-py==2026.9.1` | `rpds_py-2026.9.1-cp313-cp313-manylinux_2_17_x86_64.manylinux2014_x86_64.whl` — `7868b85224291c6cb6759f9b5adb9745f486d226f62b16a614dd5a2a5ab2b35b` | `rpds_py-2026.9.1.tar.gz` — `4793ef7f78268b124b73fa933440f01d258bbae01de9fa53e9080c9ab0425a12` | `v2026.9.1` — `fc7a1853152f23ee056c07fc97bb2a63557553ed` |

Private copies of all five upstream repositories were created and their tags
are present in local mirrors under the ignored review-evidence directory.
GitHub API readback on 2026-11-02 confirmed all five repositories are private
and Actions are disabled. The mirrors are `Capsize-Games/python-json-pointer-maintenance`,
`Capsize-Games/jsonschema-maintenance`,
`Capsize-Games/jsonschema-specifications-maintenance`,
`Capsize-Games/referencing-maintenance`, and `Capsize-Games/rpds-maintenance`.
No automatic upstream sync was configured. No source files were changed.

Source and artifact review findings:

- `jsonpointer` is a pure-Python single-module BSD-3-Clause/Modified BSD
  distribution. Its sdist `setup.py` reads package metadata/docstrings from
  the module and invokes setuptools; no custom build hook or network/credential
  behavior was found in the inspected package source. The wheel retains
  `LICENSE.txt` and `AUTHORS`.
- `jsonschema` is MIT-licensed and includes `COPYING`; its source declares
  runtime dependencies on attrs, jsonschema-specifications, referencing, and
  rpds-py. Optional `format` extras include jsonpointer, while the frozen
  resolved graph also includes jsonpointer. The build backend is Hatchling with
  hatch-vcs and hatch-fancy-pypi-readme build requirements. The package exposes
  a CLI entry point. Its `validators` module has URI retrieval mechanisms for
  explicit reference resolution, including urllib and requests-backed paths.
  AIRunner service source contains no direct imports or calls to these five
  distributions in the searched `services/src` tree. This does not prove that
  a transitive consumer never supplies an external schema or URI.
- `jsonschema-specifications` and `referencing` are MIT-licensed and retain
  their `COPYING` files. Both use Hatchling plus hatch-vcs; their declared
  dependencies explain the resolver chain to referencing and rpds-py.
  Referencing's resolver can retrieve remote resources when an application
  explicitly supplies retrieval behavior; no automatic startup fetch or
  credential access was found in the reviewed package source.
- `rpds-py` is MIT-licensed and retains `LICENSE`. It is a Rust/PyO3 extension
  built with maturin; the inspected `build.rs` only emits a macOS linker flag.
  Its Cargo manifest declares rpds, archery, and PyO3. No Python setup hook,
  credential access, or custom network behavior was found in the source. The
  selected Linux wheel is a manylinux CPython 3.13 binary, so source-to-binary
  reproducibility and native runtime behavior remain unverified.
- PyPI exact-release vulnerability arrays were empty for all five releases at
  the time of artifact collection. This is only a registry advisory-data check,
  not proof that no vulnerability exists.

The evidence directory `.headlesscode/service-audit-2026-11-02/llm-five-pin-review/`
contains the reviewed archives and wheels; it is ignored and is not a distributable
notice bundle. No packages were installed or imported, no source build or test
was run, and no schema validation/network fetch/native extension behavior was
exercised. These five pins now have static artifact/source/private-copy
dispositions; runtime acceptance remains pending.


### SDK wheel build-tool closure

A follow-up audit covered the build backend recorded by the private SDK wheel
manifest. The SDK source tag is the reviewed private merge
`28e4b0a334570b2c122853b03ce1cd06012b83dc` (upstream `55b0e36c51d2922b11640b980fcfca1064243a96` plus private change `a6627459f438ed4999e6574edc00e8af9a4a865b`). Its `libs/sdk-py/pyproject.toml` requests only `hatchling` as build backend and selects a wheel containing `langgraph_sdk`; it declares no custom build hooks, dynamic metadata hooks, or extra build plugins. The version source is `langgraph_sdk/__init__.py`, whose version assignment is static. The project tree contains no custom `hatch` build hook configuration.

The prior wheel manifest recorded Hatchling `1.33.0` but did not bind its
resolved dependencies to hashes. The installed build-tool cache and the
Hatchling wheel metadata identify this exact closure on Python 3.13.5:

| Build input | Selected wheel SHA-256 | sdist SHA-256 | Reviewed upstream tag commit | License in wheel |
|---|---|---|---|---|
| `hatchling==1.33.0` | `hatchling-1.33.0-py3-none-any.whl` — `415290b84f464d2884303fca8974d38e7b85579069fab02a15db0828fbb1446d` | `4c422bd4d554fcff5de5b73e9596f85e41e9f97f7e553d8f7595ecb31a627bef` | `hatchling-v1.33.0` — `c93b5427189f68a1f113b7f282b5ad11cecf00f0` | MIT; `LICENSE.txt` retained |
| `packaging==26.3` | `d7193f7c8e4e93f444fde0262bf90af30e16fa0ad0ad44cb553c87339b23cd1c` | `94edc256424af38762eb31306eed28beb9f0efc50a8837492c9d6fd6004aed79` | `26.3` — `929fd4b1410ac7ef61ef3f45b2f5d7e87711a9b5` | Apache-2.0 OR BSD-2-Clause; both full notices retained |
| `pathspec==1.1.1` | `a00ce642f577bf7f473932318056212bc4f8bfdf53128c78bbd5af0b9b20b189` | `17db5ecd524104a120e173814c90367a96a98d07c45b2e10c2f3919fff91bf5a` | `v1.1.1` — `ecf71a99ca739479d450b9830f43416ea0c519c7` | MPL-2.0; `LICENSE` retained |
| `pluggy==1.7.0` | `7dd7b0d8832ba3cb632c306926ded123429211b83641b35dc5c41ad2d34f9bec` | `d1eaa46ebb595891b860ab086b4d09c8588af65ebd4361b8e8f4bb8920b90ba8` | `1.7.0` — `4c7f6365f2dde09c11e72db67d0f615231d64c19` | MIT; `LICENSE` retained |
| `tomlkit==0.15.2` | `05562412163a3037b94497385fb7f9204c637bc605af7a48199e41cf2272f437` | `83e32755ba1d20d9340bd069ee97e9f6232ba2346b63ffcba425de01f7e327a6` | `0.15.2` — `a0b15ebb09167ede584fc36ad5362fc3039b0530` | MIT; `LICENSE` retained |
| `trove-classifiers==2026.9.21.13` | `8b1ff4f9c191b1040b71c37f1e445ab99732911e3cd91de52838453a854d7a17` | `0a9ebc8d4e2f3e8a22848c5258033035bec17a3012ac3fea16dbaa764489eb71` | `2026.9.21.13` — `bc832553ebe6114e7682f09bc59bda6552da37cd` | Apache-2.0; `LICENSE` retained |

All six build-tool source repositories have private maintenance copies; Actions
were disabled and read back via GitHub API on 2026-11-02. The exact release tags
are present in the copies. The repositories are `hatchling-maintenance`,
`packaging-maintenance`, `pathspec-maintenance`, `pluggy-maintenance`,
`tomlkit-maintenance`, and `trove-classifiers-maintenance`. Source tarballs,
wheels, release JSON, and local full mirrors are retained only under the ignored
`.headlesscode/service-audit-2026-11-02/build-tool-review/` evidence directory.

Static source/artifact findings: all six selected wheels are pure-Python wheels,
and all their RECORD digests and sizes verified. The package modules implement
build metadata/file selection, path matching, plugin dispatch, TOML parsing, and
classifier data. No package-level telemetry, credential lookup, hidden network
call, or install hook was found in the selected wheel/runtime code. Hatchling
supports user-defined build hooks and includes a separate binary-builder path
that invokes Cargo; the SDK configuration selects its ordinary wheel builder
and declares no such hook or binary target. The isolated rebuild below uses only
the six audited wheels and disables package indexes. The sdists were treated as
data: packaging and pathspec declare Flit build backends, tomlkit declares
Poetry Core, trove-classifiers declares setuptools/calver, and pluggy has
setuptools configuration. These source build backends and test/dev tools are not
installed or invoked by this SDK wheel rebuild.

The pluggy sdist includes `AGENTS.md`, which points to `CLAUDE.md`; both were
read as untrusted data. They request broad test and pre-commit commands; those
instructions were not followed. Source CI/workflow files were inspected as data
and not run. GitHub's private-copy Actions setting is false for every mirror.
PyPI release JSON reported no vulnerability entries for these exact six build
inputs on 2026-11-02; this bounded registry query is not proof that no issue
exists.

An offline wheel rebuild was completed after this review, from the same private
merge commit and with only the six hash-pinned local wheels above in an isolated
Python 3.13.5 environment. The command was `hatchling build --target wheel
--directory dist --no-hooks` from the exact `libs/sdk-py` tree, with a cleared
environment (`env -i`), `PIP_NO_INDEX=1`, and `UV_OFFLINE=1`. The output SHA-256
is `51008d325af07b706e32f1fb06e99af3779d075e21a63d49fcd77d2e8ad85d9b`
(162,502 bytes), byte-identical to the staged candidate wheel. All 50 RECORD
rows verified, its 45 Python runtime files match the private merged source
tree, and the file list, METADATA, and MIT license digest match the staged wheel
exactly. The first staged build had recorded only the backend name/version; this
rebuild closes the build-input hash gap for this artifact. It does not establish
SDK runtime behavior, release acceptance, or model acceptance. The recreated
wheel and exact build requirements file are retained only in the ignored review
evidence directory; no tracked package artifact or manifest was overwritten.
