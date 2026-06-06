## Testing Boundary

- Do not run or launch the AI Runner application as part of normal task execution.
- The user will always test runtime behavior manually.
- Limit validation to static analysis, targeted unit tests, linting, compilation, and read-only inspection unless the user explicitly asks for a specific command.
- When a change would normally be verified by launching the app, state that the user should verify it instead of starting the application.

## Code Style and Quality

- Write clean Python code that is idiomatic and easy to read.
- Keep line lengths to no more than 80 characters.
- Keep classes at 200 lines of code or less and files under 250 lines of code.
- Keep functions at 20 lines of code or less
- Use meaningful names, clear structure, and maintainable formatting.
- Follow the PEP 8 style guide for Python code.
- Use type hints to improve code readability and maintainability.
- Include docstrings for all functions and classes to explain their purpose and usage.
- When you need to check code quality, use the `src/airunner/bin/code_quality_report.py` script
- When you need to check code coverage use the `src/airunner/bin/coverage_report.py` script
- Always run automated tests to ensure that your code changes do not break existing functionality. Use the `src/airunner/bin/run_tests.py` script to run tests.
- Avoid multiple classes in a single file - we prefer one class per file for better organization and readability. Subdirectories are a good way to group related classes together while keeping each file focused and manageable.

## Generated UI Files

- Never edit generated `*_ui.py` files directly.
- Always edit the corresponding `.ui` template file instead.
- Regenerate generated UI Python files with `src/airunner/bin/build_ui.py` after changing a `.ui` template.
- Treat any direct `*_ui.py` edit as invalid because `src/airunner/bin/build_ui.py` will overwrite it.

## Security and Privacy Standards

- Treat log hygiene as a product requirement, not a cleanup pass. Do not add logs that expose prompts, conversation bodies, transcriptions, raw tool payloads, API responses, filesystem paths, tokens, secrets, or other user content unless the user explicitly asks for that level of logging.
- Prefer structured summaries in logs over raw values. Log counts, sizes, IDs, hashes, timing, and state transitions instead of full content.
- Reuse the existing log-hygiene utilities in `src/airunner/utils/application/log_hygiene.py` and keep sanitization active for both headless/root logging and wrapped GUI loggers.
- Do not introduce fallback logging to shared temp locations such as `/tmp`. If file logging is unavailable, disable it cleanly instead of redirecting sensitive output to a broader filesystem scope.
- Route any new remote fetch path through the existing URL safety layer in `src/airunner/components/tools/url_safety.py`. Do not add direct `requests` or similar network fetches for user-supplied URLs without the shared validation path.
- Validate and normalize every user-controlled local path through the shared helpers in `src/airunner/utils/path_policy.py` before reading, persisting, or executing against it.
- Keep persistent caches, logs, and other app-managed files inside `AIRUNNER_BASE_PATH` rather than package directories or generic temp directories.
- Prefer least-privilege filesystem behavior for application data. When creating sensitive data directories, preserve private permissions where practical.

## Python environment

We use virtualenv for python. Our environment is at `venv/bin/python`

## Do not read these files

These are binary files, don't try to read them:

- ./build/airunner-launcher/airunner
- ./venv/bin/airunner

## Database

- never modify the database with sql commands - we must always generate alembic migrations in order to modify the database
- never write loose-sql in the code or hacks or fallbacks for the database
- never run alembic migrations yourself, these should automatically be run when we start the API

## Committing

We have very strict code rules that are enforced with a pre-commit hook. NEVER use skip unless explicitly instructed to do so by the user. All code MUST comply with our strict rules. Even if your new changes aren't the cause of the code violations found by the pre-commit, you must NEVER skip the pre-commit hook - you MUST address any issues found in the pre-commit hook.