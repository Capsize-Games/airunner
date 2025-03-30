# AI Runner Contribution Guide

Thank you for your interest in contributing to AI Runner. This guide provides an overview of our project's conventions and practices. Please ensure all commits are signed.

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
Widgets are stored under `src/airunner/widgets`. Each widget has a `templates` 
directory which contains template files for the widget (see below for more information).
- Widgets all extend from `BaseWidget`.
- Classes are named `ExampleWidget` where `Example` is the name of the widget and `Widget` is the suffix.
- See existing widgets for examples of how to extend `BaseWidget` and use the `widget_class_` attribute.

### Templates
- Templates are stored in a `templates` directory inside of each `widget` directory
- Use `pyside6-designer` to edit templates
- Build templates with `python bin/build_ui.py`
- See existing widgets for examples of how to use templates

### Icons
Icons are managed with resource files which are in turn managed with `pyside6-designer` 
and built with a custom script (see the following list).
- Use [svgrepo](https://www.svgrepo.com/) for icons
- Icons are stored in `src/airunner/icons/dark` and `src/airunner/icons/light` for dark and light themes respectively.
- Use `pyside6-designer` to add or edit icons
- Build resources with `python bin/build_ui.py`

---

## Testing Guidelines
- Test files are located in the `src/airunner/tests` directory.
- Run all tests using:
  ```bash
  python -m unittest discover -s src/airunner/tests
  ```
- To run a specific test, use:
  ```bash
  python -m unittest src/airunner/tests/test_example.py
  ```
- Write new tests for any new features or bug fixes. Follow the structure of existing tests.

---

## Documentation Contributions
- Documentation is stored in the `airunner.wiki` folder.
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
  feat: Add support for new image generation model

  Added support for SDXL Turbo model in the image generation pipeline.
  ```

---

## Environment Setup
- Install dependencies using:
  ```bash
  pip install -r requirements.txt
  ```
- Initialize the database:
  ```bash
  python src/airunner/setup_database.py
  ```
- Run the application:
  ```bash
  python src/airunner/main.py
  ```

---

## Code Review Process
- Submit a pull request (PR) with a clear title and description.
- Ensure your branch is up-to-date with the `main` branch.
- Address any feedback provided during the review process.
- PRs must pass all tests and meet coding standards before being merged.