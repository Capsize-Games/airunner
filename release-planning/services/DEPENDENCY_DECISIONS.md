# Dependency review and origin decisions

Owner decision, 2026-11-01: accept origin-policy flags for this project’s reviewed dependencies, including reviewed HTTP transitive components. Keep this list visible and continue source, artifact, vulnerability and license checks. No further package-by-package origin permission is needed.

The CORE candidate has 51 distributions. Static source review and origin disposition are recorded for all 51 exact pins. This list records policy and review state; executable, model and release acceptance are tracked separately. The machine-readable [inventory](input-reviews/core-linux-dependency-inventory.json) binds exact review records and hashes.

| CORE distribution | Version | Source review | Origin disposition |
|---|---:|---|---|
| [airunner-common](https://github.com/Capsize-Games/airunner-common/releases/tag/v6.1.8) | 6.1.8 | Recorded | Owner source |
| [alembic](https://pypi.org/project/alembic/1.13.2/) | 1.13.2 | Recorded | Observed origin flag accepted by owner whitelist |
| [altgraph](https://pypi.org/project/altgraph/0.17.5/) | 0.17.5 | Recorded | Observed origin flag accepted by owner whitelist |
| [annotated-doc](https://pypi.org/project/annotated-doc/0.0.5/) | 0.0.5 | Recorded | Observed origin flag accepted by owner whitelist |
| [annotated-types](https://pypi.org/project/annotated-types/0.8.0/) | 0.8.0 | Recorded | Observed origin flag accepted by owner whitelist |
| [anyio](https://pypi.org/project/anyio/4.16.0/) | 4.16.0 | Recorded | Observed origin flag accepted by owner whitelist |
| [certifi](https://pypi.org/project/certifi/2026.10.23/) | 2026.10.23 | Recorded | No concrete origin flag observed |
| [charset-normalizer](https://pypi.org/project/charset-normalizer/3.5.2/) | 3.5.2 | Recorded | Observed origin flag accepted by owner whitelist |
| [click](https://pypi.org/project/click/8.5.0/) | 8.5.0 | Recorded | No concrete origin flag observed |
| [cloudpickle](https://pypi.org/project/cloudpickle/3.1.2/) | 3.1.2 | Recorded | Observed origin flag accepted by owner whitelist |
| [defusedxml](https://pypi.org/project/defusedxml/0.7.1/) | 0.7.1 | Recorded | Observed origin flag accepted by owner whitelist |
| [fastapi](https://pypi.org/project/fastapi/0.141.1/) | 0.141.1 | Recorded | Observed origin flag accepted by owner whitelist |
| [greenlet](https://pypi.org/project/greenlet/3.5.6/) | 3.5.6 | Recorded | Observed origin flag accepted by owner whitelist |
| [h11](https://pypi.org/project/h11/0.16.0/) | 0.16.0 | Recorded | No concrete origin flag observed |
| [httptools](https://pypi.org/project/httptools/0.9.0/) | 0.9.0 | Recorded | Observed origin flag accepted by owner whitelist |
| [idna](https://pypi.org/project/idna/3.20/) | 3.20 | Recorded | No concrete origin flag observed |
| [jinja2](https://pypi.org/project/jinja2/3.1.6/) | 3.1.6 | Recorded | No concrete origin flag observed |
| [joblib](https://pypi.org/project/joblib/1.6.0/) | 1.6.0 | Recorded | Observed origin flag accepted by owner whitelist |
| [mako](https://pypi.org/project/mako/1.4.3/) | 1.4.3 | Recorded | No concrete origin flag observed |
| [markdown](https://pypi.org/project/markdown/3.11.2/) | 3.11.2 | Recorded | Observed origin flag accepted by owner whitelist |
| [markupsafe](https://pypi.org/project/markupsafe/3.0.4/) | 3.0.4 | Recorded | No concrete origin flag observed |
| [nltk](https://pypi.org/project/nltk/3.10.4/) | 3.10.4 | Recorded | Observed origin flag accepted by owner whitelist |
| [numpy](https://pypi.org/project/numpy/2.2.5/) | 2.2.5 | Recorded | No concrete origin flag observed |
| [packaging](https://pypi.org/project/packaging/26.3/) | 26.3 | Recorded | Observed origin flag accepted by owner whitelist |
| [pandas](https://pypi.org/project/pandas/3.1.0/) | 3.1.0 | Recorded | No concrete origin flag observed |
| [pillow](https://pypi.org/project/pillow/13.0.0/) | 13.0.0 | Recorded | No concrete origin flag observed |
| [psutil](https://pypi.org/project/psutil/7.2.2/) | 7.2.2 | Recorded | Observed origin flag accepted by owner whitelist |
| [pydantic](https://pypi.org/project/pydantic/2.14.2/) | 2.14.2 | Recorded | No concrete origin flag observed |
| [pydantic-core](https://pypi.org/project/pydantic-core/2.50.2/) | 2.50.2 | Recorded | No concrete origin flag observed |
| [pygments](https://pypi.org/project/pygments/2.21.0/) | 2.21.0 | Recorded | No concrete origin flag observed |
| [pyinstaller](https://pypi.org/project/pyinstaller/6.12.0/) | 6.12.0 | Recorded | Observed origin flag accepted by owner whitelist |
| [pyinstaller-hooks-contrib](https://pypi.org/project/pyinstaller-hooks-contrib/2026.9/) | 2026.9 | Recorded | Observed origin flag accepted by owner whitelist |
| [python-dateutil](https://pypi.org/project/python-dateutil/4.0.0/) | 4.0.0 | Recorded | No concrete origin flag observed |
| [python-dotenv](https://pypi.org/project/python-dotenv/1.2.2/) | 1.2.2 | Recorded | Observed origin flag accepted by owner whitelist |
| [python-multipart](https://pypi.org/project/python-multipart/0.0.33/) | 0.0.33 | Recorded | Observed origin flag accepted by owner whitelist |
| [pyyaml](https://pypi.org/project/pyyaml/6.0.2/) | 6.0.2 | Recorded | No concrete origin flag observed |
| [regex](https://pypi.org/project/regex/2026.9.29/) | 2026.9.29 | Recorded | No concrete origin flag observed |
| [requests](https://pypi.org/project/requests/2.34.2/) | 2.34.2 | Recorded | No concrete origin flag observed |
| [setuptools](https://pypi.org/project/setuptools/84.2.1/) | 84.2.1 | Recorded | No concrete origin flag observed |
| [sqlalchemy](https://pypi.org/project/sqlalchemy/2.0.55/) | 2.0.55 | Recorded | Observed origin flag accepted by owner whitelist |
| [starlette](https://pypi.org/project/starlette/1.6.0/) | 1.6.0 | Recorded | Observed origin flag accepted by owner whitelist |
| [tqdm](https://pypi.org/project/tqdm/4.70.1/) | 4.70.1 | Recorded | Observed origin flag accepted by owner whitelist |
| [typing-extensions](https://pypi.org/project/typing-extensions/4.16.0/) | 4.16.0 | Recorded | Observed origin flag accepted by owner whitelist |
| [typing-inspection](https://pypi.org/project/typing-inspection/0.4.4/) | 0.4.4 | Recorded | Observed origin flag accepted by owner whitelist |
| [tzdata](https://pypi.org/project/tzdata/2026.6/) | 2026.6 | Recorded | Observed origin flag accepted by owner whitelist |
| [urllib3](https://pypi.org/project/urllib3/2.8.0/) | 2.8.0 | Recorded | Observed origin flag accepted by owner whitelist |
| [uvicorn](https://pypi.org/project/uvicorn/0.34.0/) | 0.34.0 | Recorded | Observed origin flag accepted by owner whitelist |
| [uvloop](https://pypi.org/project/uvloop/0.23.0/) | 0.23.0 | Recorded | Observed origin flag accepted by owner whitelist |
| [watchfiles](https://pypi.org/project/watchfiles/1.3.0/) | 1.3.0 | Recorded | Observed origin flag accepted by owner whitelist |
| [websockets](https://pypi.org/project/websockets/17.4/) | 17.4 | Recorded | No concrete origin flag observed |
| [wheel](https://pypi.org/project/wheel/0.48.0/) | 0.48.0 | Recorded | Observed origin flag accepted by owner whitelist |

## Exact origin whitelist identities

The owner decision accepts the concrete origin-policy flags recorded for these
reviewed exact package pins (package name and version):

`alembic==1.13.2`, `altgraph==0.17.5`, `annotated-doc==0.0.5`, `annotated-types==0.8.0`, `anyio==4.16.0`, `charset-normalizer==3.5.2`, `cloudpickle==3.1.2`, `defusedxml==0.7.1`, `fastapi==0.141.1`, `greenlet==3.5.6`, `httptools==0.9.0`, `joblib==1.6.0`, `markdown==3.11.2`, `nltk==3.10.4`, `packaging==26.3`, `psutil==7.2.2`, `pyinstaller==6.12.0`, `pyinstaller-hooks-contrib==2026.9`, `python-dotenv==1.2.2`, `python-multipart==0.0.33`, `sqlalchemy==2.0.55`, `starlette==1.6.0`, `tqdm==4.70.1`, `typing-extensions==4.16.0`, `typing-inspection==0.4.4`, `tzdata==2026.6`, `urllib3==2.8.0`, `uvicorn==0.34.0`, `uvloop==0.23.0`, `watchfiles==1.3.0`, `wheel==0.48.0`.

The Watchfiles wheel also contains reviewed Rust transitive crates with
concrete profile flags: `inotify 0.11.0`, `inotify-sys 0.1.5`, `once_cell
1.21.3`, and `heck 0.5.0`. Those exact crate identities are covered by the
owner whitelist recorded in the [HTTP source review](input-reviews/core-http-source-review.md).
No country is inferred from a blank profile or a package name. This whitelist
records origin-policy disposition only; it does not replace source, license,
security, or artifact checks.

Additional reviewed runtime and build inputs:

| Input | Exact input or revision | Current result |
|---|---|---|
| Python docopt | 0.6.2; `944641a7357376a43151bd4a3ca44f9c07c4d1ae` | Origin accepted; offline wheel and parser smoke passed |
| llama.cpp native sidecar | b10000; `47a39665e7081dc482feec169961acc09750a5c4` | Origin accepted; native v0.2.3 Linux/Windows build and CLI/import checks passed; model inference remains unverified |
| whisper.cpp native sidecar | v1.9.5; `d1be6fde11ac6e0407606b4e42fe72d34add8037` | Origin accepted; native v0.2.3 Linux/Windows build and CLI/import checks passed; model inference remains unverified |
| llama-cpp-python | 0.3.21+capsize.3; private wrapper merge `5156c34af6d4920cddc5aba75618b1dd1c23e590`, vendored llama.cpp `7acb4e8cd2ce21f457d1298e75fad729520d263c` | Reviewed optional-Diskcache, MTP and ctypes ABI fixes; compiled build41545665728 and notice producer41554942120 passed; actual Qwen GPU inference returned200, exact-output and reload acceptance remain open |
| scikit-build-core | 1.1.1; `67040d09985ea5683038943676f31550b5f4faf5` | Reviewed backend input; isolated CUDA wheel build passed; runtime acceptance pending |
| pathspec | 1.1.1 | Reviewed backend input |
| pip bootstrap wheel | 26.2.2; SHA-256 `fd7f4dfa8190e014013b9f08f3e973f4e4c26ffd179a204895533a7254813a70` | Reviewed source and wheel; hosted offline Python bootstrap passed |
| Kitware CMake | 3.31.6; source `859ca5c4d7396a011a462878179bc173e1283731` | Pinned official archive; hosted isolated version check passed |
| NVIDIA CUDA image | 12.9.2 devel Ubuntu 24.04; index `16656a1ef115bca9e1f820c6349876f1486d2b3c9a0e615773799fe402960dc5` | Supported image inventory and isolated CUDA wheel build passed; inference pending |

Watchfiles’ selected Linux wheel includes the following 26 compiled crates. Their exact sources and original notices are recorded in the [HTTP review](input-reviews/core-http-source-review.md). The owner accepted origin flags for their reviewed transitive scope, including inotify, inotify-sys, once_cell and heck.

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

Excluded OpenVoice/Melo and legacy Shield components remain outside the enabled release profile.

## Full Linux diagnostic graph: 243 exact distributions

The current selected diagnostic graph is `constraints.linux-release-v5.selected.txt` (local audit evidence), SHA-256 `63461b6a5fe1cd72e689ccf459a86f8d98f5cce78bd41b0c6351a71e521ed006`. It contains 243 distributions, each bound to one reviewed wheel hash. V5 replaces the V4 CUDA wrapper with the notice-complete 0.3.21+capsize.3 wheel; the other 242 artifacts are unchanged. The exact offline install, dependency check, all 77 service requirements and production notice verification (1,734 files) passed. The raw V4 diagnostic splice was rejected for a malformed continuation and retained as failed evidence. Portable staging and final artifact/model acceptance remain separate checks.

The list below enumerates every exact V4 distribution. All 243 selected wheel files passed hash, size, ZIP and RECORD checks. A fresh project environment installed the selected wheels with hash enforcement, no dependency resolution or builds, and kernel network denial; `uv pip check` passed. All 77 direct service base and Linux release requirements match the installed metadata. Production notice collection and verification passed for all 243 distributions and 1,732 notice files. These checks do not establish full model, GPU, API, or frozen-artifact acceptance. Component-specific runtime results are recorded separately. Reviewed origin flags are covered by the owner's standing whitelist, including reviewed transitives. This does not clear actual source, advisory, license or runtime findings. Native crate notice manifests linked below enumerate their separately reviewed scopes; they are not additional Python distributions.

```text
accelerate==1.14.0+capsize.1
aiohappyeyeballs==2.7.1
aiohttp==3.14.4
aiosignal==1.4.0
airunner-common==6.1.8
alembic==1.13.2
annotated-doc==0.0.5
annotated-types==0.8.0
anyio==4.16.0
attrs==26.1.0
audioop-lts==0.2.2
audioread==3.1.0
automat==25.4.16
babel==2.18.0
beautifulsoup4==4.15.0
bitsandbytes==0.46.1
breadability==0.1.21
cattrs==26.2.1
certifi==2026.10.23
cffi==2.1.1
chardet==7.6.0
charset-normalizer==3.5.2
click==8.5.0
cloudpickle==3.1.2
compel==2.4.0+capsize.1
constantly==23.10.4
courlan==1.4.0
cryptography==50.0.2
cssselect==1.5.0
cuda-bindings==12.9.9
cuda-pathfinder==1.8.3
cuda-toolkit==12.9.1
datasets==5.0.1
dateparser==1.1.8
ddgs==9.16.0
decorator==5.3.1
deepcache==0.1.1
defusedxml==0.7.1
diffusers==0.38.0
dill==0.3.8
distro==1.9.0
docopt==0.6.2
ebooklib==0.19
fastapi==0.141.1
filelock==4.2.1
flatbuffers==25.9.23
frozenlist==1.8.0
fsspec==2026.6.0
gguf==0.17.1
google-api-core==2.42.0
google-api-python-client==2.201.0
google-auth==2.61.0
google-auth-httplib2==0.4.4
googleapis-common-protos==1.75.5
greenlet==3.5.6
h11==0.16.0
hf-xet==1.7.0
htmldate==1.10.0
httpcore==1.0.9
httpcore2==2.13.1
httplib2==0.32.0
httptools==0.9.0
httpx==0.28.1
httpx2==2.13.1
huggingface-hub==1.33.0
hyperlink==21.0.0
idna==3.20
importlib-metadata==9.0.1
incremental==24.11.0
inflect==7.5.0
itemadapter==0.13.1
itemloaders==1.5.0
jinja2==3.1.6
jmespath==1.1.0
joblib==1.6.0
jsonpatch==1.33
jsonpointer==3.2.0
jsonschema==4.26.0
jsonschema-specifications==2025.9.1
justext==3.0.2
kornia==0.8.3
kornia-rs==0.2.0+capsize.2
langchain-core==1.4.7
langchain-huggingface==1.2.2
langchain-ollama==1.0.0
langchain-protocol==0.0.19
langchain-text-splitters==1.1.2
langgraph==1.2.14
langgraph-checkpoint==4.2.0
langgraph-prebuilt==1.1.0
langgraph-sdk==0.4.6+capsize.1
langsmith==0.14.4
lazy-loader==0.6
librosa==0.11.0
libzim==3.7.0+capsize.2
lingua-language-detector==2.1.0+capsize.1
llama-cloud==0.1.23
llama-cpp-python==0.3.21+capsize.3
llvmlite==0.50.0
loguru==0.7.3
lxml==6.1.3
lxml-html-clean==0.4.5
mako==1.4.3
markdown==3.11.2
markdown-it-py==4.2.0
markupsafe==3.0.4
mdurl==0.1.2
mistral-common==1.12.0
mobi==0.4.1
more-itertools==11.1.0
mpmath==1.3.0
msgpack==1.2.3
multidict==6.9.1
multiprocess==0.70.16
narwhals==2.26.0
networkx==3.4.2
nltk==3.10.4
numba==0.68.0
numpy==2.2.5
nvidia-cublas-cu12==12.9.1.4
nvidia-cuda-cupti-cu12==12.9.79
nvidia-cuda-nvrtc-cu12==12.9.86
nvidia-cuda-runtime-cu12==12.9.79
nvidia-cudnn-cu12==9.20.0.48
nvidia-cufft-cu12==11.4.1.4
nvidia-cufile-cu12==1.14.1.1
nvidia-curand-cu12==10.3.10.19
nvidia-cusolver-cu12==11.7.5.82
nvidia-cusparse-cu12==12.5.10.65
nvidia-cusparselt-cu12==0.8.1
nvidia-nccl-cu12==2.29.7
nvidia-nvjitlink-cu12==12.9.86
nvidia-nvshmem-cu12==3.4.5+capsize.1
nvidia-nvtx-cu12==12.9.79
ollama==0.6.3
openmeteo-requests==1.4.0
openmeteo-sdk==1.28.0
opentelemetry-api==1.45.1
optimum==1.25.1
orjson==3.13.0
ormsgpack==1.12.2
packaging==26.3
pandas==3.1.0
parsel==1.12.1
pillow==13.0.0
platformdirs==4.12.4
pooch==1.9.0
primp==2.0.1+capsize.2
propcache==0.5.4
protego==0.7.0
proto-plus==1.29.0
protobuf==7.36.2
psutil==7.2.2
pyarrow==25.0.1
pyasn1==0.6.5
pyasn1-modules==0.4.2
pycountry==24.6.1
pycparser==3.1
pydantic==2.14.2
pydantic-core==2.50.2
pydantic-extra-types==2.11.1
pydispatcher==2.0.7
pygments==2.21.0
pyopenssl==26.4.0
pyparsing==3.3.3
pypdf==6.21.4
python-dateutil==4.0.0
python-dotenv==1.2.2
python-multipart==0.0.33
pytz==2026.5
pyyaml==6.0.2
queuelib==1.10.0
rank-bm25==0.2.2
referencing==0.37.0
regex==2026.9.29
requests==2.34.2
requests-cache==1.2.1
requests-file==3.0.1
requests-toolbelt==1.0.0
retry-requests==2.0.0
rich==15.0.0
rpds-py==2026.9.1
safetensors==0.8.0
scikit-learn==1.9.1
scipy==1.18.1
scrapy==2.17.0
sentence-transformers==5.6.1
sentencepiece==0.2.1
service-identity==24.2.0
setuptools==84.2.1
shellingham==1.5.4
six==1.17.0
sniffio==1.3.1
sounddevice==0.5.1
soundfile==0.14.0
soupsieve==2.10
soxr==1.1.0
sqlalchemy==2.0.55
standard-aifc==3.13.0
standard-chunk==3.13.0
standard-imghdr==3.13.0
standard-sunau==3.13.0
starlette==1.6.0
sumy==0.11.0
sympy==1.14.0
tenacity==9.2.1
threadpoolctl==3.7.0
tiktoken==0.14.0
timm==1.0.30
tld==0.13.2
tldextract==5.4.0
tokenizers==0.23.1+capsize.1
tomesd==0.1.3
torch==2.13.0+cu129
torchaudio==2.11.0+cu129.capsize.1
torchcodec==0.16.0+cu129
torchvision==0.28.0+cu129.capsize.1
tqdm==4.70.1
trafilatura==2.0.0
transformers==5.22.0
triton==3.7.1+capsize.2
truststore==0.10.4
twisted==26.10.0
typeguard==4.6.0
typer==0.27.3
typing-extensions==4.16.0
typing-inspection==0.4.4
tzdata==2026.6
tzlocal==5.4.4
uritemplate==4.2.0
url-normalize==3.0.1
urllib3==2.8.0
uuid-utils==0.17.1
uvicorn==0.34.0
uvloop==0.23.0
w3lib==2.5.0
watchfiles==1.3.0
websockets==17.4
xxhash==4.0.1
yarl==1.25.1
zipp==4.1.1
zope-interface==8.6
zstandard==0.25.0

```

### Evidence and current dispositions

| Scope | Recorded evidence | Disposition and limits |
|---|---|---|
| Source review | The dated input-review records are linked below. Each states its candidate hash, exact bounded scope, and exclusions. The 243 graph hash above differs from the hashes in several review records. | Source review is incomplete as a graph-wide, exact-pin inventory. Do not infer unlisted packages were reviewed. |
| Origin whitelist | The 243 identities above are visible current graph inputs; the CORE table and linked native crate manifests retain their exact scopes. The owner authorized reviewed origin exceptions, including transitive components. | No further origin-only approval is required. Do not infer an origin from a package name, and do not treat this exception as approval of unreviewed or unsafe code. |
| Kornia | The [Kornia source and notice review](input-reviews/linux-shared-source-review.md) covers `kornia-rs==0.2.0` and its exact 184-crate Linux normal/build Cargo graph; the companion notice manifest binds the source revision and Cargo.lock checksum. | **Activation hold:** the selected 184-crate graph reports `anyhow==1.0.102` (`RUSTSEC-2026-0190`), `bincode==2.0.1` (`RUSTSEC-2025-0141`, unmaintained), `paste==1.0.15` (`RUSTSEC-2024-0436`, unmaintained), `pyo3==0.28.3` (four advisories; fixed in 0.29.0), and `quick-xml==0.37.5` (`RUSTSEC-2026-0194` and `RUSTSEC-2026-0195`). The review identified a reachable quadratic-attribute parser path for untrusted image XMP. The notice supplement does not resolve these findings. |
| CUDA and native wheels | The [CUDA review](input-reviews/linux-cuda-source-review.md) records 25 exact wheel inputs, 115 statically inspected ELF members, and candidate RUNPATH changes; original wheels remain preserved. | **Activation hold:** CUDA Toolkit 12.9.1 has an official 12.9 EULA source supplement. NCCL wheel notice, source `LICENSE.txt`, and `ThirdPartyNotices.txt` are separate records because they differ in scope. Open findings are the Torchaudio bundled CTC notice and exact BSD notice source; TorchVision bundled image-library license provenance; Triton wheel LLVM/MLIR license closure and network-capable source-build hook; and the NVSHMEM subset license and artifact evidence. These are recorded in the candidate source review; no GPU binary was loaded. |
| Audio/TTS/STT | The [audio review](input-reviews/linux-audio-source-review.md) records 20 exact pins and artifact/source checks for its candidate graph. | Legacy `pyttsx3` remains quarantined and excluded from this headless graph. OS-provided eSpeak NG package provenance and runtime/audio checks are outside the recorded pip evidence. |
| RAG/document inputs | The [RAG review](input-reviews/linux-rag-source-review.md) covers nine original pins. The [Libzim replacement review](input-reviews/libzim-3.7.0-source-review.md) binds `libzim==3.7.0+capsize.2`, patched source, complete native source inputs, and Ubuntu 24 workflow 41517812860. | The original unpinned HTTP build hook and unknown native closure are superseded by the replacement. Exact-wheel target import/create/read/search passed. Full graph, real corpus, parser resource limits and model acceptance remain open. |
| LLM/agent inputs | The [LLM review](input-reviews/linux-llm-source-review.md) records package-specific reviews, replacement artifacts, and separate exclusions. | Its batch labels and candidate graph do not bind all current 243 pins. `diskcache` was removed from this diagnostic graph; older cache-advisory findings do not establish a finding for a package absent from this graph. Runtime/model acceptance remains pending. |
| Build tools | The SDK artifact review records `hatchling==1.33.0`, `packaging==26.3`, `pathspec==1.1.1`, `pluggy==1.7.0`, `tomlkit==0.15.2`, and `trove-classifiers==2026.9.21.13`, with exact wheel/sdist hashes and source commits; the SDK wheel rebuild was byte-identical. A separate build-tool wheelhouse records `setuptools==84.2.1`, `wheel==0.48.0`, and `packaging==26.3` with selected wheel hashes. | These are reviewed build inputs for the recorded SDK/artifact workflow; they are not evidence that the 243 graph is fully reviewed or that build tools belong in the runtime environment. |

### Native source and notice scopes

The following sidecars document native-source or notice scopes attached to selected artifacts. Their counts describe the specific locked source graphs or wheel manifests stated in each file, not a universal compiled-code count.

| Distribution or artifact | Exact recorded native scope | Evidence and limit |
|---|---|---|
| `pydantic-core==2.50.2` | 101 registry crates in its selected sdist Cargo.lock; 180 notice files | [Rust crate notice manifest](../../packaging/licenses/pydantic-core-rust-crates/pydantic-core-rust-crates.source.json) is a notice superset; build evidence does not establish that all 101 crates were compiled. |
| `primp==2.0.1+capsize.2` | 418 packages in Cargo.lock; 230 registry crates in selected Linux normal/build graph | The [replacement review](input-reviews/primp-2.0.1-capsize.2.md) and [Rust notice manifest](../../packaging/licenses/primp-rust-crates-capsize-2.0.1/cargo-notices-manifest.json) bind the exact candidate. Its 408 notices passed production collection/verification in an isolated hash-pinned environment; version and Client export import passed. No HTTP client/request or model was run. The earlier noncanonical .1 wheel is quarantined. |
| `tokenizers==0.23.1+capsize.1` | 165 registry crates in Cargo.lock; 343 notice files | [Patched Tokenizers notice manifest](../../packaging/licenses/tokenizers-rust-crates-capsize-0.23.1/tokenizers-rust-crates.source.json) binds the local candidate. A separate upstream feature-selection analysis counted 117 normal/build crates; it does not prove the linker’s exact compiled subset. |
| `watchfiles==1.3.0` | 26 compiled crates in the selected Linux wheel manifest | The 26-crate table above is a wheel-level record from the CORE review; verify exact version and wheel correspondence before applying it to another candidate artifact. |
| CUDA selected wheels | 25 artifact pins; 115 ELF members inspected | [CUDA wheel review](input-reviews/linux-cuda-source-review.md) records static ELF and RECORD evidence; there was no import, load, or GPU runtime validation. |

The exact diagnostic graph does not replace the project’s release lock. Next required work is a machine-bound inventory connecting each graph pin to exact source/artifact evidence, resolution of the listed security and notice holds, then active-lock generation and isolated validation. Real model and hardware acceptance are also unrun.

### Separate Linux candidate build and test inputs

The 243-pin V4 runtime graph does not include the candidate test runner or PyInstaller. Keep these exact inputs visible as separate layers; none is a service runtime dependency.

| Purpose | Exact package identities | Evidence | Candidate handling |
|---|---|---|---|
| Deterministic tests | `iniconfig==2.3.0`, `pluggy==1.7.0`, `pytest==9.1.1`, `pytest-timeout==2.4.0`, `responses==0.26.3` | [CI test-tool source review](input-reviews/linux-ci-test-tools-review.md); [hash lock](../../package/constraints-linux-ci-tools.txt); [artifact manifest](../../package/linux-ci-tools-artifact-sources.json) | Staged by exact wheel hash and size, installed after the runtime graph with `--no-deps --require-hashes`. Not activated as runtime dependencies. |
| PyInstaller candidate build | `altgraph==0.17.5`, `packaging==26.3`, `pyinstaller==6.12.0`, `pyinstaller-hooks-contrib==2026.9`, `setuptools==84.2.1`, `wheel==0.48.0` | [CORE freeze input review](input-reviews/core-linux-freeze-inputs.md); [CORE exact-pin inventory](input-reviews/core-linux-dependency-inventory.json); [builder lock](../../package/constraints-linux-builder-tools.txt); [builder artifact manifest](../../package/linux-builder-tools-artifact-sources.json) | Kept separate from the runtime profile; staged from canonical PyPI URLs with exact SHA-256 and size, then installed after runtime with `--no-deps --require-hashes`. Frozen application acceptance remains distinct. |

The test and builder locks are candidate inputs and do not replace the active runtime lock. A clean layered environment must pass `pip check`; no CI or release success is implied by these static records.
