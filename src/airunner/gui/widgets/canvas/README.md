# Canvas Widgets for AI Runner

## Purpose
This module contains custom PySide6 widgets and scenes for image input, editing, and mask creation in the AI Runner application. It provides the core UI and business logic for user-supplied images, including drawing, linking, locking, and image import/delete operations.

### Key Components
- `InputImage`: Main widget for displaying and editing input images, supporting linking to grid images, locking, and mask mode.
- `InputImageScene`: Custom QGraphicsScene for drawing and image manipulation.
- `BrushScene`: Fallback/utility scene for brush-based drawing.
- `canvas_widget.py`: Base widget for canvas-related UI.

## Testing Strategy
- **Unit tests**: All business logic (signal connection, link/lock, image update, etc.) is covered by headless unit tests in `test_input_image.py`.
- **Functional tests**: GUI/interaction tests are in `tests/functional/test_input_image_functional.py`.
- **Test Skipping**: All tests that invoke GUI dialogs (e.g., `QFileDialog.getOpenFileName`) are skipped in CI/headless environments due to persistent PySide6/Qt segfaults. See code for `pytestmark` and skip reasons.

## Limitations & Known Issues
- **Segfaults in Headless/CI**: Any test that triggers a native file dialog (even monkeypatched) can cause a segfault in headless/CI environments. This is a known PySide6/Qt limitation. See `PySide6_GUI_Tests.md` in the docs for details and workarounds.
- **Resource Management**: All widgets/scenes implement robust teardown in `closeEvent` to avoid segfaults and leaks. Manual widget closure is required in functional tests.

## Usage
Import and use `InputImage` in your PySide6 application as a drop-in widget for image input, editing, and mask creation. See code and tests for API details.

---

*Last updated: 2025-05-26*
