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
| llama.cpp native sidecar | b10000; `47a39665e7081dc482feec169961acc09750a5c4` | Origin accepted; hosted CPU build passed; final platform artifact acceptance in progress |
| whisper.cpp native sidecar | v1.9.5; `d1be6fde11ac6e0407606b4e42fe72d34add8037` | Origin accepted; hosted CPU build passed; final platform artifact acceptance in progress |
| llama-cpp-python | 0.3.21; wrapper `d2bcbac46605f11d382426dd88d67e8b5c124cd7`, vendored llama.cpp `f53577432541bb9edc1588c4ef45c66bf07e4468` | Reviewed clean source; hosted CUDA wheel build has not passed |
| scikit-build-core | 1.1.1; `67040d09985ea5683038943676f31550b5f4faf5` | Reviewed backend input; target build remains unverified |
| pathspec | 1.1.1 | Reviewed backend input |
| pip bootstrap wheel | 26.2.2; SHA-256 `fd7f4dfa8190e014013b9f08f3e973f4e4c26ffd179a204895533a7254813a70` | Reviewed source and wheel; hosted offline Python bootstrap passed |
| Kitware CMake | 3.31.6; source `859ca5c4d7396a011a462878179bc173e1283731` | Pinned official archive; hosted isolated version check passed |
| NVIDIA CUDA image | 12.9.2 devel Ubuntu 24.04; index `16656a1ef115bca9e1f820c6349876f1486d2b3c9a0e615773799fe402960dc5` | Supported image inventory passed; target wheel/inference pending |

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

The full ML release lock remains unfinished. Its eventual selected inputs will be added here as their reviews are completed. Excluded OpenVoice/Melo and legacy Shield components remain outside the enabled release profile.
