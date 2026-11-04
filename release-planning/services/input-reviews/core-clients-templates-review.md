# CORE HTTP clients and template packages

Static source and artifact review of eight exact CORE dependency pins, dated
2026-11-01. Versions were matched to the current CORE lock/inventory and the
captured official PyPI release records. Each sdist and listed wheel was
downloaded from the official file host and its SHA-256 matched the release
record. Canonical release tags and full commits are listed below. This review
does not activate packages or change the shared readiness inventory.

| Package and role | Release source | Sdist SHA-256 | Selected Linux wheel SHA-256 | License | Origin-policy disposition |
|---|---|---|---|---|---|
| certifi 2026.10.23 (direct runtime) | [tag](https://github.com/certifi/python-certifi/tree/2026.10.23), `b60466c9f2882d9cf088943c650b0faac06c080c` | `a9895e6e2758b371e0545e321a3a8fd1fcfd9829ada8824a936dfb16aaaf36cd` | `e9b54de76e530bb6cf0ccd036787103acb58fd42ba930ea8bf948ddbaa2f61d1` | MPL-2.0 | Reviewed; no concrete flag found |
| charset-normalizer 3.5.2 (transitive runtime) | [tag](https://github.com/jawah/charset_normalizer/tree/3.5.2), `935c29ad2d0d6e62fcf3a6e0617c55dc6e85db8f` | `39de2a259fc954455c57274dc94c79d5842774e1247a016aff30bc0efed0f4ef` | `7218e8f32b0956cfcd048fd42d9d5779809745ca1d86113ca56f66e7ae1549c4` | MIT | Covered by reviewed HTTP-dependencies decision |
| requests 2.34.2 (direct runtime) | [tag](https://github.com/psf/requests/tree/v2.34.2), `6e83187b8feb273ed4c6cdab5efd8d54901dfab3` | `f288924cae4e29463698d6d60bc6a4da69c89185ad1e0bcc4104f584e960b9ed` | `2a0d60c172f83ac6ab31e4554906c0f3b3588d37b5cb939b1c061f4907e278e0` | Apache-2.0 | Reviewed; no concrete flag found |
| urllib3 2.8.0 (transitive runtime) | [tag](https://github.com/urllib3/urllib3/tree/2.8.0), `b1d30ab61fe0db8f11092805e8c5ac43e091064a` | `63bf2ead4c879426ebf22ef2a781eeb4aa3b4ae798a0435506f8687fd5bb9b63` | `0cf3cae568d36aa9576b28dfb35f11328f1cb974ca7647d9475ebb86c75ac6e3` | MIT | Covered by reviewed HTTP-dependencies decision |
| click 8.5.0 (transitive runtime) | [tag](https://github.com/pallets/click/tree/8.5.0), `8b19813f2bfca99f1018a587a8cf54fc959f2e5d` | `ba0d2089de75ea0310e2dde03160e6ca10009947fb95a182f9b54021bb272e34` | `255bc9599cf7748b4b1a446ccc735421bd08a2ae529a8b88597d3de5664ee360` | BSD-3-Clause | Reviewed; no concrete flag found |
| Jinja2 3.1.6 (direct runtime) | [tag](https://github.com/pallets/jinja/tree/3.1.6), `15206881c006c79667fe5154fe80c01c65410679` | `0137fb05990d35f1275a587e9aee6d56da821fc83491a0fb838183be43f66d6d` | `85ece4451f492d0c13c5dd7c13a64681a86afae63a5f347908daf103ce6d2f67` | BSD-3-Clause | Reviewed; no concrete flag found |
| Mako 1.4.3 (transitive runtime) | [tag](https://github.com/sqlalchemy/mako/tree/rel_1_4_3), `6b833ae06fc8866b89ea7939e5d36dd71699cf05` | `cd6537fe88d5fec315c55c2f8529bc4ce7a9a352ad7db3eeaa6a66e2dd4ec37a` | `723296007c870bfd6b3f0c3230dba7198096e5269297ebf5e4eff9e7ffa39d4f` | MIT | Reviewed; no concrete flag found |
| MarkupSafe 3.0.4 (transitive runtime) | [tag](https://github.com/pallets/markupsafe/tree/3.0.4), `ece26078ec168ebac69f02877238e68d4b376c91` | `2e9ad7dd851bf45fab9f75cbff4cb493fee9979e8d8c7c9c3ee119022518edd6` | `434139499bb20b502ed3baa1f169e618f924a97e7a777fea1a49446d80106cf6` | BSD-3-Clause | Reviewed; no concrete flag found |

The selected wheel names are `certifi-2026.10.23-py3-none-any.whl`,
`charset_normalizer-3.5.2-cp313-cp313-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl`,
`requests-2.34.2-py3-none-any.whl`, `urllib3-2.8.0-py3-none-any.whl`,
`click-8.5.0-py3-none-any.whl`, `jinja2-3.1.6-py3-none-any.whl`,
`mako-1.4.3-py3-none-any.whl`, and
`markupsafe-3.0.4-cp313-cp313-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl`.
Charset-normalizer also has a pure-Python wheel, SHA-256
`b6b751274acb69d77b3323d6b7dbaa3c7fdfc1eb829b7eb61d262f32e1af9685`.
MarkupSafe has no universal wheel in this release.

## Source and packaging findings

All sdist members were checked for unsafe paths and special files before
extraction. Files shared with the exact tagged source were compared byte for
byte. No runtime Python source differences were found. Sdist-only changes are
generated metadata/version data; Mako's `pyproject.toml` and `setup.cfg`
contain generated packaging metadata differences only. PyPI records mark none
of these files yanked.

The checked wheel `RECORD` hashes and sizes all match. No wheel contains a
`.pth` file. The selected charset-normalizer wheel contains `cd` and `md`
CPython 3.13 native extensions, corresponding to the package's `cd.pyx` and
`md.pyx` sources; its pure-Python wheel contains no native payload. The
selected MarkupSafe wheel contains `_speedups.cpython-313-x86_64-linux-gnu.so`,
corresponding to `_speedups.c`. Other selected wheels contain no native
payload. Wheel license and notice files match the corresponding sdist files.

Build declarations inspected from package source: setuptools for certifi and
requests; a local PEP 517 backend wrapping setuptools for charset-normalizer;
Hatchling plus version plugins for urllib3; Flit Core for Click and Jinja2;
setuptools for Mako; and setuptools with a custom `build_ext` path for
MarkupSafe. The charset-normalizer backend reads its two documented build
environment switches and uses Cython only when explicitly enabled. MarkupSafe
attempts its optional C speedup on supported CPython builds and has a Python
fallback. These paths were read statically and not run. Build backend packages
were not independently installed or reviewed in this batch.

Requests and urllib3 implement HTTP client behavior when their request/pool
APIs are called. Requests also supports conventional proxy and CA-bundle
environment settings and `.netrc` authentication during request preparation.
These are expected, caller-triggered client behaviors, not import-time network
activity. Jinja2 and Mako provide template compilation/rendering; templates are
input code and callers must treat untrusted templates accordingly. Click's
environment-variable support is part of its explicit command-line API.
Certifi exposes its bundled CA certificate file. No hidden telemetry or
analytics path was identified in the inspected package source. No package
code, hook, or template was executed.

The captured PyPI release records had empty vulnerability arrays. An exact
version batch query to OSV on 2026-11-01 returned no records for these eight
versions. These sources are point-in-time advisory checks, not proof that no
vulnerability exists.

## Scope and status

Exact upstream source tags were retained in independent private maintenance
copies with GitHub Actions disabled. Static review included the release source,
sdist, selected wheel metadata and payload, build declarations, package
instructions, and primary maintainer/project profiles. Source builds, package
installation/import, tests, runtime API calls, and upstream workflows were not
run. The two concrete location flags found in primary profiles are covered by
the owner decision for reviewed HTTP dependencies; no location was inferred
from blank profiles. This review does not change the shared readiness
inventory, approve activation by itself, or establish successful CORE runtime
validation.
