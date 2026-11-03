# Psycopg 3.3.7 and Ubuntu libpq runtime review

Status: reviewed candidate staged for the full `linux-release` profile. No
Psycopg import or PostgreSQL connection was performed as part of this change.
CORE remains SQLite-only.

## Exact Python artifact

- Distribution: `psycopg==3.3.7`, pure wheel `psycopg-3.3.7-py3-none-any.whl`.
- SHA256: `d592e88a077e01ff57f22d59f16e828b92f2b2d9f439b6679d582b48d74cf306`.
- Wheel size: 216207 bytes; wheel tag: `py3-none-any`.
- Upstream source tag: `3.3.7`, tag object `025a611fcd5e07dc7aef0f99e5f09a9b8907b51e`, commit `4daf632fae52ad7493c76fdea11d3a65856df114`.
- Matching source archive SHA256: `6574f23fd79bf129ee0616b49f6e358faf7ae1bf3a362d2ad599cf8f9c3d4935`.
- Wheel metadata declares `LGPL-3.0-only`, Python `>=3.10`, and no unconditional requirements. Its Python modules match the reviewed source archive; the license file is included in the wheel.
- Source and wheel review evidence, including the private upstream clone, is retained in the ignored service audit tree at `pyinstaller-analysis-only-20261103/attempt4/`. Public links: [PyPI artifact page](https://pypi.org/project/psycopg/3.3.7/), [signed upstream tag object](https://api.github.com/repos/psycopg/psycopg/git/tags/025a611fcd5e07dc7aef0f99e5f09a9b8907b51e).

The selected runtime sets `PSYCOPG_IMPL=python`; the reviewed `psycopg.pq` source then loads `pq_ctypes` and skips the separately distributed C and binary implementations. No `psycopg-c`, `psycopg-binary`, pool extra, or source build is selected. The binary wheel's stale bundled libpq/TLS/Kerberos/LDAP closure and its build inputs remain excluded.

## Native runtime

The full Linux image declares the Ubuntu `libpq5` runtime package. The reviewed Noble amd64 package identity is `16.15-0ubuntu0.24.04.1`, SHA256
`3f96dd36bcd7841172c1ead4965da20a193bb9ccf9a93a3f5a3ac7f56369dbb1`.
Its verified package closure retains TLS, LDAP, and GSSAPI/Kerberos dependencies;
PostgreSQL Common's reviewed build helper enables OpenSSL, LDAP, and GSSAPI.
The 24-package/18-source input ledgers, license evidence, changelog/advisory
review, and ELF closure are in the ignored audit tree's
`NOBLE-LIBPQ-CLOSURE-REVIEW.md`, `noble-libpq-runtime-closure.json`, and
`noble-libpq-source-inputs.json`.

The standard platform loader, libc, libm, pthread, dl, and rt remain platform
requirements (Ubuntu 24.04 or newer), not bundled overlay files. Psycopg uses
`ctypes` and does not add an ELF `DT_NEEDED` edge, so the OS package must be
installed and the target loader cache updated through the distribution's
package mechanism. The local Debian 13 PyInstaller Analysis is not evidence of
Ubuntu 24.04 frozen SONAME compatibility; the full frozen runtime must validate
that closure on Ubuntu 24.04.

## SASL plugin-path confinement

Before any PostgreSQL DBAPI load, the service helper creates an application
private `postgresql-runtime/sasl-empty` directory and sets `SASL_PATH` to exactly that path,
replacing inherited values. It rejects setuid/setgid execution, non-applicable
owners, symlinks, path-list delimiters, writable root-owned paths, and any
plugin directory that is not empty. Service-owned directories are private;
root-owned packaged paths may be root-owned. This confines Cyrus SASL plugin
search without removing libpq's LDAP-simple, GSSAPI, or TLS support. Runtime
acceptance still needs to verify the environment and loaded-library map on the
actual Ubuntu 24.04 service process, followed by supported authentication-mode
checks where test endpoints exist.

## Optional freeze warnings

The selected wheel provides `psycopg`; the full bundle explicitly collects it.
The missing `psycopg2` warning is scoped to SQLAlchemy's optional legacy dialect
and top-level probe. `psycopg_c`/`psycopg_binary` warnings are scoped to
`psycopg.pq`, where the explicit `PSYCOPG_IMPL=python` selection bypasses them.
PyTorch's optional `einops` warnings are scoped to the inspected Dynamo and FX
callers; the selected ZImage path has no compile requirement, and generic SD
compile is opt-in. These are importer-specific dispositions, not broad
allowances for other callers or model families.

## Not exercised

No Psycopg import, libpq load from the service, PostgreSQL
server, DBAPI connection, migration, LDAP authentication, GSSAPI authentication,
TLS connection, or final Ubuntu 24.04 frozen bundle was run. This record and
staged lock describe reviewed inputs; they do not claim runtime acceptance.

## Isolated OS installation follow-up

The exact runtime closure and two matching glibc development packages were
installed offline in the pinned CUDA 12.9.2 Ubuntu 24.04 image. Installing the
runtime closure alone would remove CUDA development packages because its newer
libc6 conflicts with the base image's older libc6-dev. The separate build
supplement resolves that exact dependency without removals or downgrades.
All 26 locked versions and the five checked CUDA/build package identities were
present after installation; `dpkg --audit` was clean. The retained install-log
SHA-256 is `389e81289ccbd21ccdaed89798331df17e8d16f1dfe02be4b579ad54045b5cba`.
The container was disposable, used runc, had no network or GPU access, and ran
under CPU/RAM limits. Runtime package scripts and triggers ran only there; the
two supplemental archives contain no maintainer scripts.

The production Docker recipe verifies staged archives before package installs,
constructs local apt metadata from the verified control records, disables
network/downloads/removals for the locked install, and checks the exact package
versions after subsequent system installs. Full Docker execution is still
required. The frozen candidate currently depends on target-host libpq; carrying
and validating that external prerequisite remains separate work under #2446.
