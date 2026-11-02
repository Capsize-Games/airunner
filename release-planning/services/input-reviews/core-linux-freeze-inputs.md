# Linux CORE freeze input review

Date: 2026-11-01

## Candidate and status

This record describes the Linux `services-core` dependency graph candidate. It
is not approval to install or execute the freeze tools. Activation remains
pending; CI must stop before installing builder dependencies while
`package/core-input-readiness.json` has a pending status.

The metadata-only resolution used CPython 3.13.5, Linux x86_64, and binary-only
selection. It contains 51 distributions. The requirements input SHA-256 is
`e05b93209931f945ee66686d33ac76173279dcdc8ca3f9c8ade83e55d494cc66`; the
hash-pinned lock SHA-256 is
`1ec91599b40ab9dccd826aeed33928a20eeb0319b90f4f57a6b4bff33d2b16cf`.
`airunner-common==6.1.8` is included from its reviewed release wheel with
the [upstream release asset](https://github.com/Capsize-Games/airunner-common/releases/download/v6.1.8/airunner_common-6.1.8-py3-none-any.whl),
SHA-256
`ac2110ecbcd965c9a773405494bcecb3d1c6c5f127d22fde81d37478b94088fd`.

The graph selects PyInstaller 6.12.0 and pyinstaller-hooks-contrib 2026.9,
with builder pins setuptools 84.2.1, wheel 0.48.0, and packaging 26.3. The
lock includes hashes for the resolved distribution artifacts. The exact-pin
inventory at
[`core-linux-dependency-inventory.json`](core-linux-dependency-inventory.json)
binds every package/version to this lock digest and records source review
separately from origin-policy state. Current evidence covers source review for
7 of 51 locked distributions; the other 44 need exact-pin source review. Origin
review is complete for two inputs, pending for 47 inputs, and the two
freeze-tool exceptions remain pending. See
[`core-linux-reviewed-inputs.md`](core-linux-reviewed-inputs.md) for reviewed
scope and next source intakes.

The readiness checker requires the inventory package set and pins to match
the complete lock before any input can become ready. Reviewed freeze-tool
sources or recorded origin exceptions cannot substitute for the remaining
package reviews. The current candidate remains non-activatable.

## Reviewed builder sources

PyInstaller 6.12.0:

- Upstream tag: [v6.12.0](https://github.com/pyinstaller/pyinstaller/tree/v6.12.0)
- Release metadata: [PyPI](https://pypi.org/project/pyinstaller/6.12.0/)
- Peeled commit: `31dbe9ff477716e4790aa317bc9da68766d20659`
- Source archive SHA-256: `1834797be48ce1b26015af68bdeb3c61a6c7500136f04e0fc65e468115dec777`
- License metadata: GPL-2.0-or-later with a bootloader distribution exception.

pyinstaller-hooks-contrib 2026.9:

- Upstream tag: [v2026.9](https://github.com/pyinstaller/pyinstaller-hooks-contrib/tree/v2026.9)
- Release metadata: [PyPI](https://pypi.org/project/pyinstaller-hooks-contrib/2026.9/)
- Peeled commit: `222e37fea0d8300595af3601a4f42d2fcf634a37`
- Source archive SHA-256: `2748767901acb5cecd1304652b6c7add5bffcff1d71d01207fe24a5d42942a56`
- License metadata: GPL-2.0-or-later; the setup metadata also lists Apache Software License.

The static review covered the exact source release metadata, setup and project
configuration, license files, archive hashes, and Linux hooks matched to the
resolved graph. The matched hook set included built-in hooks for NumPy,
packaging, pandas, Pygments, setuptools, and SQLAlchemy; contributed hooks for
AnyIO, certifi, charset-normalizer, cloudpickle, Jinja2, Mako, Markdown, NLTK,
pandas-flavor, psutil, Pydantic, regex, setuptools-scm, tzdata, urllib3,
uvicorn, uvloop, and websockets. In this matched set, reviewed hooks perform
module or local file/data collection; no direct network or credential access
was found. This does not cover every hook in the contributed hooks project.

PyInstaller's source setup command can invoke Waf to build a bootloader from
source. The candidate is binary-only, so a source build is not part of the
selected resolution. The NLTK hook reads existing directories in
`nltk.data.path`; any future builder must use an isolated HOME and
`NLTK_DATA`, with no user corpus or model directories exposed.

## Security and evidence limits

The official [PyInstaller advisory GHSA-9fxf-4qw3-ghmr](https://github.com/pyinstaller/pyinstaller/security/advisories/GHSA-9fxf-4qw3-ghmr)
covers versions from 6.10 up to, but not including, 6.22.1 for `onefile`
environment-variable handling. Its report says the `onedir` path was refactored
in 6.8. The CORE spec selects `onedir`; keep the advisory in scope if that
mode changes. The advisory endpoint for pyinstaller-hooks-contrib was
unavailable during review, which is not evidence that the project has no
advisories. PyPI listed no provenance metadata for either reviewed release.

Static review did not install or import either tool, run setup hooks, invoke
PyInstaller, freeze an executable, download models, or use a GPU. The exact
source inputs were inspected, but activation remains pending the outstanding dependency source
reviews and concrete source-policy flags. No frozen startup or clean-install acceptance result
is available.
