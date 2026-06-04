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

## Services Architecture

AI Runner uses a headless daemon architecture with a web-based GUI:

- **`services/`**: FastAPI-based daemon that orchestrates LLM, STT, TTS, and
  art workloads. Runs as `airunner-headless`.
- **`airunner_web_client/`**: React/TypeScript web GUI built with Vite. Serves
  as the user-facing client that connects to the daemon API.
- **`api/`**: Shared transport contracts between services and clients.

### Development Workflow

1. Start the daemon:
   ```bash
   ./scripts/dev/run_services.sh
   ```

2. Start the web client in a separate terminal:
   ```bash
   cd airunner_web_client
   npm install
   npm run dev
   ```

3. Open `http://localhost:5173` in your browser.

Or use the combined launcher:
```bash
./scripts/run_web.sh
```

---

## Web GUI Development (Airunner Web Client)

The web GUI is a React/TypeScript application located in `airunner_web_client/`.

- Built with [React](https://react.dev/), [TypeScript](https://www.typescriptlang.org/), and [Vite](https://vitejs.dev/)
- Communicates with the daemon API via REST endpoints
- Source files are under `airunner_web_client/src/`

### Building the Web Client

```bash
cd airunner_web_client
npm install
npm run build
```

### Running in Development

```bash
cd airunner_web_client
npm run dev
```

The dev server runs on `http://localhost:5173` and proxies API calls to the
daemon on port 8188.

---

## Services Development

### Running Tests

```bash
# Service unit tests
./venv/bin/python -m pytest services/tests/test_service_bootstrap.py -v

# Runtime smoke tests
./venv/bin/python scripts/run_tests.py --llm-runtime-smoke
./venv/bin/python scripts/run_tests.py --stt-runtime-smoke
./venv/bin/python scripts/run_tests.py --art-runtime-smoke
./venv/bin/python scripts/run_tests.py --tts-runtime-smoke
```

---

## Testing Guidelines
- Test files are located in `services/tests/` and `airunner_web_client/src/`
  for their respective packages.
- Run Python tests using:
  ```bash
  ./venv/bin/python -m pytest
  ```
- Write new tests for any new features or bug fixes. Follow the structure of existing tests.

---

## Documentation Contributions
- Documentation is stored in the `docs/` folder and as `README.md` files in
  relevant directories.
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
