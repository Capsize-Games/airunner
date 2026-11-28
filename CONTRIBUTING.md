# Contributing

AI Runner in this repository is the headless model service and API. Contributions should target the service, its Python launcher, native sidecar integration, packaging, or documentation. The former Qt desktop code is not part of this repository's active product.

## Propose and submit a change

1. Check current issues and open pull requests for existing work.
2. Start from the repository's current default or protected branch. Do not assume the branch is named `develop`.
3. Make a focused change and update related documentation when behavior or commands change.
4. Run the relevant existing checks and report their exact results, including skips and unavailable resources.
5. Open a pull request against the current base branch and respond to review feedback.

Preserve the project's Apache-2.0 license, upstream copyright notices, and third-party notices. Commit generated release inputs only when the packaging workflow needs them, with exact hashes, source provenance, and required license material. Keep model weights, credentials, private policy data, customer data, and local runtime state out of commits.

## First contribution in 30 minutes

For a documentation, test, or small code fix, no GPU or model files are needed:

1. Fork `Capsize-Games/airunner`, clone your fork, and branch from current `master`.
2. Create the environment: `uv venv --python 3.13.5 .venv`, then `uv pip install --python .venv/bin/python -e "./services[development]" -e ./native`. The base metadata requires `airunner-common~=6.1.8`; its reviewed wheel is in the [common v6.1.8 release](https://github.com/Capsize-Games/airunner-common/releases/tag/v6.1.8), while PyPI publication remains paused (see [#2413](https://github.com/Capsize-Games/airunner/issues/2413)). Do not start with the `headless`, `desktop`, or `tts-python` extras; they are not the contributor path.
3. Verify the setup: `.venv/bin/python -m pytest services/tests/test_service_bootstrap.py -q` must pass. A skip is not a pass; quote the exact output.
4. Pick a [`good first issue`](https://github.com/Capsize-Games/airunner/issues?q=label%3A%22good+first+issue%22+state%3Aopen), make one focused change, and run the single related test file. Useful fast subsets are documented under [Tests and reports](#tests-and-reports).
5. Open a pull request against `master` describing what changed, why, and the exact test output. First-time fork pull requests need a maintainer to approve CI ("Approve and run workflows") before checks run; a red check may be pre-existing, so describe what you observed rather than force-pushing around it.

No CLA, DCO, or sign-off is required. Keep the Apache-2.0 license notices intact.

## Development environment

The package metadata requires Python 3.13.3 or newer; Linux candidate CI uses 3.13.5. New Python environments on this machine use `uv`:

```bash
uv venv --python 3.13.5 .venv
uv pip install --python .venv/bin/python -e "./services[development]"
```

The editable development command is not a verified full-profile installation. The base metadata requires `airunner-common~=6.1.8`; its reviewed wheel is available in the [common v6.1.8 release](https://github.com/Capsize-Games/airunner-common/releases/tag/v6.1.8), while PyPI publication remains paused. The [CORE constraints](package/constraints-linux-core.txt) bind its exact release wheel and the other reviewed CORE inputs. FacehuggerShield is optional through `legacy-shield`. OpenVoice/Melo vendor inputs are deferred from `linux-release`; the retained Linux TTS profile uses eSpeak. The full ML release lock remains pending, so the CORE installation checks do not establish that the development or ML extras resolve. See the [CORE candidate workflow](.github/workflows/core-debian-candidate.yml) and [service architecture](release-planning/services/ARCHITECTURE.md) for their separate checks and exclusions.

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
