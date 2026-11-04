# Docker release workflow action review

Review date: 2026-11-02

This is a bounded source review for the actions directly used by
`.github/workflows/docker-release.yml`. No action JavaScript, npm/Yarn install,
build hook, Docker build, or container was executed during this review.

## Adopted action revisions and private copies

| Workflow action | Selected upstream tag and commit | Owner-controlled private copy | License |
|---|---|---|---|
| `actions/checkout` | Existing shared release-action pin `11d5960a326750d5838078e36cf38b85af677262` (`v4`) | Existing shared review; not re-reviewed in this task | Existing review record |
| `docker/login-action` | `v3.7.0`, `c94ce9fb468520275223c153574b00df6fe4bcc9` | `Capsize-Games/docker-login-action-maintenance` (Actions disabled; tag preserved) | Apache-2.0 |
| `docker/build-push-action` | `v6.19.2`, `10e90e3645eae34f1e60eeb005ba3a3d33f178e8` | `Capsize-Games/docker-build-push-action-maintenance` (Actions disabled; tag preserved) | Apache-2.0 |
| `@docker/actions-toolkit` used by the selected action revisions | `v0.62.1`, `88d39b6b65b7ae11fe64205b66b5a7debaf2a1b7` for build-push; `v0.63.0`, `76f06a5079322247f64dbfd3a64ac7ac64b0167b` for the other actions | `Capsize-Games/docker-actions-toolkit-maintenance` (Actions disabled; both tags preserved) | Apache-2.0 |

The workflow pins the checkout action and both retained Docker action entry
points to full commit SHAs. It no longer invokes `docker/setup-buildx-action`:
the job checks the hosted runner's Docker and Buildx tools and uses its
existing builder. This avoids that setup action's ability to resolve and
download a mutable Buildx release or create a separate builder. The private
copies retain upstream history and selected tags; they are independent
private repositories with Actions disabled and no automatic upstream
synchronization.

## Reviewed behavior

- The workflow runs `docker version` and `docker buildx version` before the
  build. Those runner-supplied binary versions are not pinned by this workflow.
- Login reads the registry, username, and password inputs. For GHCR, it sends
  the password through Docker login stdin, masks secret values, and logs out in
  its post step. The workflow only provides GitHub's actor and token to this
  step. Login is skipped for manual candidate runs unless publication is
  explicitly requested from an allowed ref.
- Build-push receives a local repository context and the staged reviewed input
  context. The workflow supplies no build secrets, SSH mounts, or Git auth
  token. Source inspection found that build summary generation may use the
  `dockereng/export-build:latest` container through a legacy path when Buildx
  is older than 0.23 or legacy export is forced. The build step sets both
  `DOCKER_BUILD_SUMMARY=false` and `DOCKER_BUILD_RECORD_UPLOAD=false`,
  disabling summary/export and record upload while preserving image build,
  smoke-test, and publication behavior.
- The smoke step starts the real daemon on Docker's private `none` network. It
  has no host ports, host mounts, or GPU, disables model modalities and
  preload, and creates a temporary API key inside the workflow. It checks
  unauthenticated health, requires HTTP 401 for `/api/version` without a key,
  requires HTTP 200 with the key, then stops the daemon and checks for a clean
  exit. The key is masked and is not printed.
- Manual dispatch defaults to build and smoke test only. GHCR login and push
  run for manual dispatch only when `publish_image` is true and the ref is
  `master` or a version tag matching `vMAJOR.MINOR.PATCH` with an optional
  prerelease/build suffix. The job validates that ref before login. Existing
  successful `workflow_run` and published-release publication paths remain.

## Scope and remaining limitation

The review covered each selected action's metadata and relevant entry-point
source paths, plus toolkit paths for setup, login, build summary, and
build-record handling. It did not audit every source file or every transitive
npm dependency for all repositories. Docker and Buildx versions supplied by
the hosted runner are not pinned by this workflow. No Docker image build or
hosted workflow run has been claimed from this review.
