# AI Runner Contribution Guide

Thank you for your interest in contributing to AI Runner. This guide provides an overview of our project's conventions and practices.

---

## How to make changes and submit them

1. Fork or clone the `https://github.com/Capsize-Games/airunner` repo and checkout the `develop` branch.
2. Find an [issue from the project board](https://github.com/orgs/Capsize-Games/projects/23)
3. Create your own branch in the style of `[feature/bug/patch]/issue_number-description`.

Example

```bash
git checkout develop
git pull
git checkout -b bug/321-some-broken-feature-fix
```

4. Make your changes and commit them to your new branch
5. Push your branch to GitHub and open a pull request with `develop` as the base branch
## Pull request requirements
- Submit a pull request (PR) with a clear title and description.
- Address any feedback provided during the review process.
- PRs must pass all tests and meet coding standards before being merged.

---

## Development Environment Setup

Full install instructions live in the [README](README.md) (Advanced Python
Installation section). Two dev-environment notes that are easy to trip over:

- **NLTK import security guard:** `nltk 3.10.1+` refuses to load its data
  unless import-security is explicitly disabled in development. Set the
  environment variable in your dev shell (issue #2056):

  ```bash
  export NLTK_DISABLE_IMPORT_SECURITY=1
  ```

- **setuptools vs torch:** the pinned torch line (`2.13.0+cu129`) requires
  `setuptools>=77.0.3` and has **no** `setuptools<82` upper bound, so the
  latest setuptools is safe. If you use an older torch wheel that still
  declares `setuptools<82` (e.g. some 2.11.x builds), pin it in your venv
  before running `pip check` (issue #2057):

  ```bash
  pip install "setuptools<82"
  ```

  Verify the venv with `pip check` after installing.

---

## Coding Conventions
We follow the PEP 8 style guide for Python code. You can find the complete guide [here](https://pep8.org/). Additionally, refer to the [Style Guide](https://github.com/Capsize-Games/airunner/wiki/Style-guide) in the wiki for detailed coding standards specific to this project.

### Key Points from the Style Guide
- **Line Length:** Limit lines to 79 characters.
- **Indentation:** Use 4 spaces per indentation level, never tabs.
- **Naming Conventions:**
  - Variables and functions: `snake_case`
  - Classes: `PascalCase`
  - Constants: `UPPERCASE_WITH_UNDERSCORES`
- **Imports:**
  - Group imports into standard library, third-party, and local imports, separated by blank lines.
  - Use absolute imports whenever possible.
- **Comments and Docstrings:**
  - Use Google-style docstrings for all modules, classes, and functions.
  - Keep inline comments minimal and relevant.
- **Formatting**
  - Use [black](https://pypi.org/project/black/) for code formatting

---

## Logging Practices
- Use `self.logger` for logging within classes.
**Examples**:
- `self.logger.debug("...")`
- `self.logger.info("...")`
- `self.logger.warning("...")`
- `self.logger.error("...")`

---

## Signal and Slot Management
We utilize a `SignalMediator` class to manage signal-slot connections across different classes without direct imports.
**Example**:
In the `__init__` function of a class, connect a slot:
`self.register(SignalCode.SOME_CODE_SIGNAL, self.on_some_signal)`
Then, define the slot function:
```python
def on_some_signal(self, message):
    # Implement functionality here
    ...
```
To emit the signal (from any class):
`self.emit(SignalCode.SOME_CODE_SIGNAL, "Hello World!")`
Note: We use the `SignalCode` enum to define signal codes. The message parameter is optional and can be any object type.

---

## Inter-Class Function Calls
We employ a `ServiceLocator` class to call functions defined in one class from another class, avoiding direct imports.
**Example**:
Register a function:
`self.register_service(ServiceCode.SOME_CODE, self.some_function)`
Define the function:
```python
def some_function(self, message):
    # Implement functionality here
    ...
```
To call the function (from any class):
`self.get_service(ServiceCode.SOME_CODE)("Hello World!")`

---

## Widgets, Templates, and Resources (Icons)

### Widgets
Widgets are stored under `src/airunner/components/<feature>/gui/widgets` (for
example `src/airunner/components/chat/gui/widgets` or
`src/airunner/components/llm/gui/widgets`). Each widget has a `templates`
directory which contains template files for the widget (see below).
- Widgets extend `BaseWidget`, defined in
  `src/airunner/components/application/gui/widgets/base_widget.py`.
- Classes are named `ExampleWidget` where `Example` is the name of the widget and `Widget` is the suffix.
- See existing widgets for examples of how to extend `BaseWidget` and use the `widget_class_` attribute.

### Templates
- Templates are stored in a `templates` directory inside of each `widget` (or `windows`) directory.
- Use `pyside6-designer` to edit templates.
- Build templates with `python scripts/build_ui.py` (from the repo root).
- See existing widgets for examples of how to use templates.

### Icons
Icons are managed with Qt resource files which are in turn managed with
`pyside6-designer` and built with the same UI build script.
- Use [svgrepo](https://www.svgrepo.com/) for icons.
- Icon source sets live under `src/airunner/gui/resources/icons/` (for example
  `feather/` and `lucide/`), managed by the resource file
  `src/airunner/gui/resources/feather.qrc`.
- The icon manager lives in
  `src/airunner/components/icons/managers/icon_manager.py`.
- Use `pyside6-designer` to add or edit icons.
- Build resources with `python scripts/build_ui.py`.

---

## Testing Guidelines
- Repo-wide test discovery is configured in `pyproject.toml` with
  `testpaths = ["src", "services/tests"]`, so a plain `pytest` run collects
  both the in-repo GUI suite and the services-owned suite.
- Run the unit suite with the repo test runner:
  ```bash
  ./venv/bin/python scripts/run_tests.py --unit
  ```
- Run services-owned tests directly, for example:
  ```bash
  ./venv/bin/python -m pytest services/tests/test_service_bootstrap.py -v
  ```
- Run the agent eval suite:
  ```bash
  AIRUNNER_TEST_NO_GUI_LAUNCH=1 ./venv/bin/python -m pytest services/tests/eval --tb=short -ra
  ```
- Local dev helpers live in `scripts/dev/`: `run_services.sh` starts the
  daemon, `test_services.sh` health-checks it, `stop_services.sh` stops it,
  and `run_gui.sh` launches the desktop client. These scripts run the split
  packages from a checkout without reinstalling: they set `DEV_ENV=1` and a
  `PYTHONPATH` covering `services/src`, `src`, `native/src`, and `shared`
  inside the repo `venv` (override the venv with `AIRUNNER_DEV_VENV`).
- Write new tests for any new features or bug fixes. Follow the structure of
  existing tests in `services/tests/` and `src/airunner/components/*/tests/`.

---

## Documentation Contributions
- Documentation lives in the repo's `docs/` directory (for example
  `docs/architecture/`) and on the
  [Development Wiki](https://github.com/Capsize-Games/airunner/wiki/Development).
- Update or add relevant sections in the appropriate `.md` files.
- Ensure that all new features are documented.
- Use clear and concise language.

---

## Commit Message Standards
- Use descriptive commit messages that explain the purpose of the change.
- Follow this format:
  ```
  type: Short description

  Detailed explanation of the change (if necessary).
  ```
- Example:
  ```
  feat: Add support for Z-Image generation

  Added support for Z-Image models in the image generation pipeline.
  ```
