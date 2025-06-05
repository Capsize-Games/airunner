# Document Editor Component

This module provides a code editor widget for the AI Runner application, featuring line numbers and syntax highlighting.

## Features
- **Code Editing:** QPlainTextEdit-based editor for code and text.
- **Line Numbers:** Continuously updated line number area for easy code navigation.
- **Syntax Highlighting:** Basic Python syntax highlighting using QSyntaxHighlighter. Easily extensible for other languages.

## Usage
- The main widget class is `DocumentEditorWidget`, which can be embedded in any PySide6 UI.
- The widget is designed to be modular and follows the AI Runner component conventions.

## Extensibility
- To add support for more languages, extend or modify the `PythonSyntaxHighlighter` class.
- The editor uses a monospaced font and disables line wrapping by default for code clarity.

## Integration
- The widget is auto-wired to the UI via the `document_editor.ui` template.
- Do not edit `*_ui.py` files directly. For UI changes, edit the `.ui` file and run `airunner-build-ui`.

## File Structure
- `document_editor_widget.py`: Main implementation.
- `templates/document_editor.ui`: UI template (edit here for layout changes).

## Example
```python
from airunner.components.document_editor.gui.widgets.document_editor_widget import DocumentEditorWidget
editor = DocumentEditorWidget()
```

## License
See project root for license information.
