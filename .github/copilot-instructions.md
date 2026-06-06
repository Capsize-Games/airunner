# Copilot Instructions

## Testing Boundary

- Do not run or launch the AI Runner application as part of normal task execution unless you are instructed to do so by the user.
- The user will always test runtime behavior manually.
- Do not create or modify automated tests unless the user explicitly asks for test changes.
- When a change would normally be verified by launching the app, state that the user should verify it instead of starting the application.

## Code Style and Quality

- Write clean Python code that is idiomatic and easy to read.
- Keep line lengths to no more than 80 characters.
- Keep classes restricted to 300 lines of code
- Keep files restricted to 300 lines of code.
- Keep functions at 20 lines of code or less
- Use meaningful names, clear structure, and maintainable formatting.
- Follow the PEP 8 style guide for Python code.
- Use type hints to improve code readability and maintainability.
- Include docstrings for all functions and classes to explain their purpose and usage.
- When you need to check code quality, use the `src/airunner/bin/code_quality_report.py` script
- When you need to check code coverage use the `src/airunner/bin/coverage_report.py` script
- Avoid multiple classes in a single file - we prefer one class per file for better organization and readability. Subdirectories are a good way to group related classes together while keeping each file focused and manageable.
- Do not use inline import statements. All imports should be at the top of the file, grouped by standard library imports, third-party imports, and local application imports, in that order.

## Testing

- Only create functional automated tests. Avoid granular unit tests that require extensive mocking. Focus on testing the overall behavior and functionality of application features rather than isolated units of code unless the user authorizes you to create unit tests for a given session.
- Do not create tests for edge cases that are unlikely to occur in real-world usage. Instead, prioritize testing common use cases and scenarios that users are likely to encounter.
- Avoid writing tests for src/airunner gui code unless the user explicitly requests it.

## Generated UI Files

- Never edit generated `*_ui.py` files directly.
- Always edit the corresponding `.ui` template file instead.
- Regenerate generated UI Python files with `src/airunner/bin/build_ui.py` after changing a `.ui` template.
- Treat any direct `*_ui.py` edit as invalid because `src/airunner/bin/build_ui.py` will overwrite it.

## Security and Privacy Standards

- Treat log hygiene as a product requirement, not a cleanup pass. Do not add logs that expose prompts, conversation bodies, transcriptions, raw tool payloads, API responses, filesystem paths, tokens, secrets, or other user content unless the user explicitly asks for that level of logging.
- Prefer structured summaries in logs over raw values. Log counts, sizes, IDs, hashes, timing, and state transitions instead of full content.
- Reuse the existing log-hygiene utilities in `src/airunner/utils/application/log_hygiene.py` and keep sanitization active for both daemon/root logging and wrapped GUI loggers.
- Do not introduce fallback logging to shared temp locations such as `/tmp`. If file logging is unavailable, disable it cleanly instead of redirecting sensitive output to a broader filesystem scope.
- Route any new remote fetch path through the existing URL safety layer in `src/airunner/components/tools/url_safety.py`. Do not add direct `requests` or similar network fetches for user-supplied URLs without the shared validation path.
- Validate and normalize every user-controlled local path through the shared helpers in `src/airunner/utils/path_policy.py` before reading, persisting, or executing against it.
- Keep persistent caches, logs, and other app-managed files inside `AIRUNNER_BASE_PATH` rather than package directories or generic temp directories.
- Prefer least-privilege filesystem behavior for application data. When creating sensitive data directories, preserve private permissions where practical.