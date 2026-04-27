# Copilot Instructions

## Testing Boundary

- Do not run or launch the AI Runner application as part of normal task execution.
- The user will always test runtime behavior manually.
- Limit validation to static analysis, targeted unit tests, linting, compilation, and read-only inspection unless the user explicitly asks for a specific command.
- When a change would normally be verified by launching the app, state that the user should verify it instead of starting the application.

## Code Style and Quality

- Write clean Python code that is idiomatic and easy to read.
- Keep line lengths to no more than 80 characters.
- Keep classes at 500 lines of code or less and files under 550 lines of code.
- Keep functions at 20 lines of code or less
- Use meaningful names, clear structure, and maintainable formatting.
- Follow the PEP 8 style guide for Python code.
- Use type hints to improve code readability and maintainability.
- Include docstrings for all functions and classes to explain their purpose and usage.
- When you need to check code quality, use the `src/airunner/bin/code_quality_report.py` script
- When you need to check code coverage use the `src/airunner/bin/coverage_report.py` script
- Always run automated tests to ensure that your code changes do not break existing functionality. Use the `src/airunner/bin/run_tests.py` script to run tests.