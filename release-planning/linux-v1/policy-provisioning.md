# Policy provisioning for trusted release CI (S06)

Owner-operated recipe. Production policy data and signing keys never
enter the public repository, public CI, issues, or logs. Public CI and
ordinary checkouts use the packaged empty set or synthetic fixtures
only.

## What the release does

On a published GitHub release, `.github/workflows/pypi-dispatch.yml`
runs the `provision-policy` job before the package build:

1. Check out the release tag (pinned action, no persisted
   credentials).
2. Download the already-compiled private artifact
   (`policy_terms.dat`) and its detached Ed25519 sidecar
   (`policy_terms.dat.sig`) from the owner-hosted URL in
   `POLICY_ARTIFACT_URL`, using `POLICY_ARTIFACT_TOKEN`. The sidecar
   is fetched from `<url>.sig`.
3. Run `scripts/build_policy_terms.py --stage-release`, which
   verifies, in order: the artifact is present and bounded; its
   SHA-256 matches `POLICY_ARTIFACT_SHA256`; it strictly parses to a
   non-empty `airunner-policy-data/1` digest set; and the sidecar
   verifies against the `POLICY_TRUST_STORE_JSON` public keys.
   Anything else -- absent, invalid, empty, unsigned, or signed
   outside the release trust store (synthetic-only) -- exits 2 and
   fails the release with a content-free error.
4. Upload the verified hashes plus sidecar as the
   `policy-bundle-fragment` job artifact (one-day retention), which
   the build job installs into
   `services/src/airunner_services/content_safety/data/` before
   `python -m build`, so the wheel carries production data.

A secret-free `provision-policy-fixture` job runs the S06 regression
suite (`services/tests/test_release_s06.py`) with throwaway keys and
synthetic data. It uses no environment and no secrets.

## Owner setup (one time, private)

1. Compile the artifact offline in the private controlled process
   with `scripts/build_policy_terms.py --input <private list>
   --output policy_terms.dat`. The plaintext list stays out of the
   repository.
2. Sign the exact artifact bytes with Ed25519 and publish the
   sidecar in the `airunner-policy-signature/1` format (schema in
   `services/src/airunner_services/content_safety/policy_signature.py`).
   Key generation and signing are owner-operated; private keys never
   leave the controlled process.
3. Host the two files at an authenticated URL and create the
   `release-policy` GitHub environment (protected: required
   reviewers, no bypass for test branches) with secrets:
   `POLICY_ARTIFACT_URL`, `POLICY_ARTIFACT_TOKEN`,
   `POLICY_ARTIFACT_SHA256` (hex of the exact bytes),
   `POLICY_TRUST_STORE_JSON` (`{"key-id": "<64 hex chars>"}`).
4. Rotate by publishing a new artifact/sidecar pair, updating the
   digest secret, and adding the new key ID to the trust-store
   secret before first use. Remove retired key IDs afterwards.

## Safety rules

- The workflow has no `pull_request` trigger, and the trusted job
  requires the `release` event plus the protected environment, so
  untrusted PR code never runs with release credentials.
- Steps never echo, list, or dump secrets: no `set -x`, no `env`
  output, no debug artifacts. Steps print counts and the signing key
  ID only.
- The source term list and private keys never enter the runner: only
  hashes, the detached signature, and public keys cross the trust
  boundary, and only the hashes plus signature land in the bundle.
- The fragment artifact is a release-bundle input, not a general
  download: one-day retention, installed only by the release build.
