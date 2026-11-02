# Debian release publisher

The release workflow builds the services-only Debian package after
the candidate gate and wheel artifact check pass. A dispatch on the annotated
version tag creates or resumes a draft after all artifacts pass their gates,
attaches the complete verified asset set, and publishes an immutable release.
Published-release events only verify existing assets. The Debian
manifest records the repository, annotated tag, source commit, workflow run,
package version, filename, size, and SHA-256 digest.

The host publisher polls the public release API. It accepts a package only
when the exact `pypi-dispatch.yml` dispatch run and its `publish-release-assets`
job completed successfully for that tag and commit, the annotated tag points to
the recorded commit, the release is stable and immutable, and GitHub's release
asset digest matches the manifest. It stages a copy of the current repository,
adds the package with the existing signing key, verifies the staged signature,
and performs a clean Ubuntu install and daemon health check before promotion.
It then recreates only the configured apt web container, waits for matching
signed public metadata, and repeats the clean install and health check. A
failed check restores the previous repository tree and recreates the same
container with that tree.

The host configuration is supplied separately and must be root-owned with
mode `0600`. It contains these fields:

- `apt_base_url`, `suite`, and `container_name`
- `repo_root`, `gnupg_home`, `publish_script`, `compose_file`, and
  `compose_project_dir`
- `work_dir`, `state_dir`, and `public_key_file`
- `verification_image`, pinned as an OCI SHA-256 digest
- `timeout_seconds` and `retry_interval_seconds`

The configuration, target-specific paths, and signing material are not stored
in this repository. Run `deployment/apt/install-publisher.sh
--config-source <root-only-config>` from a trusted source checkout on the
existing apt host. The installer preserves an existing publisher script beside
the replacement and enables the polling timer. It does not publish a package.

## Debian runtime profile

The Debian package is architecture-specific and carries the frozen CORE
services runtime built from `packaging/linux/services-core-bundle-spec.toml`
and `package/constraints-linux-core.txt`. This keeps the daemon's pinned Python
dependencies with the application instead of asking `dh_python3` to map them
to distribution packages whose versions do not match the service pins. The
CORE profile excludes ML model runtimes, GPU libraries, and model files; those
remain separately provisioned. The full ML P05 bundle retains its separate
dependency and acceptance profile.

`package/core-input-readiness.json` records the current 51-distribution graph
and records incomplete dependency review. The reviewed packaging-tool origin
exceptions are recorded; remaining exact-pin reviews still block activation.
CI checks the record before installing dependencies. While it is pending,
the CORE build does not start. The
frozen artifact and clean Ubuntu install have not yet passed acceptance.

The release candidate must pass the Ubuntu 26.04 clean install and daemon
health check in the publisher before the apt repository is promoted. A Debian
build or GitHub release asset alone does not establish that install check.
