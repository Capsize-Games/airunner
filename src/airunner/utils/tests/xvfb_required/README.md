# Tests Requiring Xvfb or a Real Display

Some tests in this project require a real Qt display environment and **cannot** be run headlessly or with `pytest-qt` enabled. These are typically tests for background workers or GUI components that instantiate QApplication or use Qt signals/slots at a low level.

## How to Run

To run these tests locally or in CI (including on Wayland):

```bash
xvfb-run -a pytest src/airunner/utils/tests/xvfb_required/
```

Or, for a single test file:

```bash
xvfb-run -a pytest src/airunner/utils/tests/xvfb_required/test_background_worker.py
```

- The `-a` flag automatically picks a free display number.
- This works on most Linux systems, including those using Wayland.
- On CI, add `xvfb-run` to your test step.

## Why?

- These tests require a real Qt event loop and display context.
- Patching or mocking PySide6.QtCore is not safe due to deep C-extension dependencies.
- Running these tests headlessly or with `pytest-qt` will cause segfaults or import errors.

## When to Use
- Only run these tests when you want to verify low-level Qt worker or signal/slot logic.
- For most development and CI, you can skip this folder unless you are working on Qt threading or background worker code.

## Included Tests
- `test_background_worker.py`: Tests for BackgroundWorker threading and signals.
- `test_threaded_worker_mixin.py`: Tests for ThreadedWorkerMixin background task management (may cause core dumps if PySide6/QThread is not fully isolated).
