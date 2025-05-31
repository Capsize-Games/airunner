# ConversationWidget module

ConversationWidget provides a modern, single-view chat display for AI Runner using QWebEngineView and Jinja2 HTML templates.

## Features
- Renders the entire conversation as HTML for performance and flexibility.
- Modern, responsive styles with no horizontal scrollbar (vertical scroll only).
- Smooth auto-scroll to bottom when new messages are added, including during streaming updates.
- Supports multiple content types (plain text, markdown, LaTeX, mixed) via per-message widget templates.

## Usage
- Instantiate `ConversationWidget` and call `set_conversation(messages)` with a list of message dicts.
- Each message dict should include at least: `sender`, `text` (or `content`), and `is_bot` (True for assistant, False for user).

## Testing
- See `tests/` for Pytest and pytest-qt based tests verifying scroll behavior and rendering.

## Customization
- To change styles, edit `conversation.html` and the CSS in `content_widget.css`.
- For new content types, add a new widget template and update the mapping in `ConversationWidget`.

---

For design rationale, see `REFACTOR.md`.
