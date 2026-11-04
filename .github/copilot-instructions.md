# Repository instructions for coding assistants

This repository contains AI Runner's headless model service, runtime integration, and HTTP/WebSocket API. The retired Qt desktop application is outside this repository's active product scope.

## Scope and verification

- Follow the active task and repository-level instructions. Keep changes limited to the named behavior and files.
- Prefer focused, deterministic service tests. Do not launch a live service, load a real model, call paid APIs, change a live database, or deploy unless the task explicitly authorizes it.
- Do not create or modify tests unless the task or an applicable repository instruction authorizes test changes.
- Report exact checks and results. A skipped test, missing model, or unavailable GPU is not a pass for that behavior.
- For new Python environments on this machine, use `uv`. Do not install dependencies merely to make an audit appear complete; report missing tools or packages.

## Code and reports

- Follow PEP 8 and the conventions of the surrounding service module. Add clear types and docstrings to new public interfaces.
- Use `scripts/code_quality_report.py --path services/src/airunner_services` for the advisory AST report and `scripts/services_complexity_report.py` for Radon/Xenon output. These reports are not release gates. Xenon `unavailable` does not mean its check passed.
- Avoid broad formatting or refactoring work when a focused fix is sufficient.

## Security and data handling

- Keep prompts, generated content, transcriptions, credentials, and raw API payloads out of logs. Use the service log hygiene helpers in `services/src/airunner_services/utils/application/log_hygiene.py`.
- Route user-supplied remote URLs through `services/src/airunner_services/url_safety.py`.
- Validate user-controlled file paths with the service file policy in `services/src/airunner_services/runtimes/file_policy.py` and related document-access helpers.
- Keep app-managed data under the configured runtime/data layout. Preserve private permissions for sensitive local data.
- Preserve authentication on non-loopback API access, migration safety, offline behavior, and third-party notices. Do not weaken a check to make a test pass.

## License and claims

- Preserve the repository's GPL-3.0-only license and required upstream notices.
- Do not commit secrets, model weights, customer data, private policy source data, runtime logs, or generated build artifacts.
- Do not claim hardware, model, language, privacy, or safety support without implementation evidence and the corresponding validation result.

Use [CONTRIBUTING.md](../CONTRIBUTING.md) for contributor workflow and [SECURITY.md](../SECURITY.md) for vulnerability reporting.
