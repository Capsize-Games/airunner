# Contributing

AI Runner in this repository is the headless model service and API. Contributions should target the service, its Python launcher, native sidecar integration, packaging, or documentation. The former Qt desktop code is not part of this repository's active product.

## Propose and submit a change

1. Check current issues and open pull requests for existing work.
2. Start from the repository's current default or protected branch. Do not assume the branch is named `develop`.
3. Make a focused change and update related documentation when behavior or commands change.
4. Run the relevant existing checks and report their exact results, including skips and unavailable resources.
5. Open a pull request against the current base branch and respond to review feedback.

Preserve the project's GPL-3.0-only license, upstream copyright notices, and third-party notices. Do not add generated artifacts, model weights, credentials, private policy data, customer data, or local runtime state to commits.

## Development environment

The package metadata requires Python 3.13.3 or newer. New Python environments on this machine use `uv`:

```bash
uv venv --python 3.13 .venv
uv pip install --python .venv/bin/python -e "./services[development]"
```

Dependency availability currently limits this clean install command. The services metadata requires `airunner-common~=6.1.7` and `facehuggershield==1.0.0`; the CI workflow checks out pinned source revisions because the corresponding PyPI releases are paused or yanked. The TTS extras require `airunner-tts-vendor`, whose PyPI availability is tracked in [issue #2413](https://github.com/Capsize-Games/airunner/issues/2413). Confirm the approved source for these dependencies before attempting package or model-profile installation. Do not treat an unresolved or skipped package-resolution check as a pass.

## Tests and reports

Run a focused service test after dependencies are available:

```bash
.venv/bin/python -m pytest services/tests/test_service_bootstrap.py -q
```

The repository also has smoke and functional suites under `services/tests/`. Some require native sidecars, model files, or GPU hardware. A skipped test or absent model does not verify that workload. Do not start a real model or service as part of a documentation-only or ordinary small code change.

Use the quality reports as advisory review tools:

```bash
.venv/bin/python scripts/code_quality_report.py --path services/src/airunner_services
.venv/bin/python scripts/services_complexity_report.py
```

The complexity report labels Xenon as unavailable if the executable is absent; that status is not a passing Xenon check. Review analyzer findings before changing code to satisfy a heuristic.

## Code and security practices

- Follow PEP 8, use type hints for new public interfaces, and keep functions focused.
- Keep user prompts, model output, credentials, and raw API payloads out of logs. The service log helpers are in `services/src/airunner_services/utils/application/log_hygiene.py`.
- Route user-supplied remote URLs through `services/src/airunner_services/url_safety.py`.
- Validate user-controlled filesystem paths with the service file-policy helpers under `services/src/airunner_services/runtimes/file_policy.py` and related document access code.
- Preserve authenticated non-loopback behavior, data boundaries, migration safety, and upstream license notices.
- Do not claim a model, hardware matrix, language, privacy property, or safety outcome is supported unless its implementation and verification evidence establish that claim.

Report vulnerabilities through [GitHub private security advisories](https://github.com/Capsize-Games/airunner/security/advisories/new), not the public issue tracker. See [SECURITY.md](SECURITY.md) for the project's reporting instructions.
