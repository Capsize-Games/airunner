# Linux release V6 input validation

V6 adds the reviewed pure `psycopg==3.3.7` wheel to the V5 runtime inputs.
The selected graph contains 244 distributions; its lock SHA-256 is
`350990b0cb1846a073991872a7147f588f4734aee1fa1bb79aa9044d8ed5d101`.
The other 243 selected wheel identities are unchanged from
[the V5 record](linux-release-v5-input-validation.md).

Validation completed on 2026-11-03 UTC:

- All 244 local wheel sizes and SHA-256 values matched the selected artifact
  manifest before installation. The new wheel is committed in the wheelhouse;
  the other wheels were reused from their previously verified intake paths.
- A fresh project environment installed the graph with `uv`, shared cache,
  hash enforcement, wheel-only inputs, no dependency resolution or builds,
  and kernel network denial. `uv pip check` passed for 244 packages.
- Installed metadata satisfied all 80 evaluated direct service base/profile
  requirements.
- The production notice collector and verifier passed for 244 distributions
  and 1,735 notice files.

[The PostgreSQL review](psycopg-3.3.7-pure-python-libpq.md) records the exact
source and wheel, excluded binary implementation, Ubuntu libpq requirement,
SASL plugin confinement, and remaining runtime checks. CORE remains SQLite-only.
No PostgreSQL DBAPI import, native libpq load, database connection, frozen
runtime acceptance, model execution, or release acceptance is established by
this input validation. Detailed commands and results remain in the private
service audit directory. Temporary Actions inputs still need durable release
mirrors before final publication.
