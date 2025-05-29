# Markdown/Code Editor Widget for AIRunner

## Purpose
A modular widget for AIRunner that provides a rich markdown/code editing environment with syntax highlighting, MathJax rendering, and seamless integration with the LLM agent. The widget is displayed as a tab in the main GUI, following the architectural and UI patterns of the `nodegraph` widget.

## Key Features
- **Markdown and Code Editing:**
  - Supports editing markdown and code with syntax highlighting for multiple languages.
  - Renders mathematical/scientific notation using MathJax.
- **Language Selection:**
  - Dropdown menu to select the programming language for syntax highlighting.
- **Standard Editor Features:**
  - Typing, deleting, selecting text, copy, paste, undo, redo, and navigation.
- **LLM Agent Integration:**
  - Bi-directional communication with AIRunner’s LLM agent for content updates and code execution.
- **Tab Integration:**
  - Displayed as a tab in the main window, mirroring the `nodegraph` widget’s integration.

## Architecture
- **Widget Structure:**
  - Subclass of `BaseWidget`.
  - UI defined in a `.ui` file (e.g., `editor_widget.ui`).
  - Uses a code editor component (e.g., QPlainTextEdit or QScintilla, with syntax highlighting support).
  - MathJax rendering via embedded web view or custom widget.
  - Language dropdown (QComboBox).
- **Integration Points:**
  - Registered as a tab in the main window.
  - Communicates with the LLM agent via signals/slots and API hooks.
  - Exposes methods for the LLM agent to update content and trigger code execution.

## Component List
- `editor_widget.ui`: UI layout for the editor widget.
- `editor_widget.py`: Widget logic, subclassing `BaseWidget`.
- `syntax_highlighter.py`: Syntax highlighting logic for multiple languages.
- `mathjax_viewer.py`: MathJax rendering component (if not using a web view directly).
- Tests in `tests/` subdirectory.
- `README.md` (this file).

## High-Level Test Cases
- Widget instantiates and displays as a tab.
- User can type, edit, and format code/markdown.
- Language dropdown changes syntax highlighting.
- MathJax renders equations correctly.
- LLM agent can send/receive content and trigger code execution.
- Undo/redo, copy/paste, and navigation work as expected.

## Usage
- Add the widget as a tab in the main window.
- Use the language dropdown to select syntax highlighting.
- Interact with the LLM agent for collaborative editing and code execution.

---
For implementation details, see the source files in this directory.
