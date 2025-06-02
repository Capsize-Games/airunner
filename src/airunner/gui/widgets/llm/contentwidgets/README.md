# ConversationWidget module

## Refactored Conversation System (June 2025)

- The conversation display now uses a single HTML template (`conversation.jinja2.html`) for all message types.
- MathJax is used for rendering all mathematical and code content.
- All previous per-type widget templates (LaTeX, mixed, plain text) are obsolete and have been removed.
- The backend logic (`ConversationWidget`) is simplified and robust, with all content routed through MathJax.

## Usage
- Use `set_conversation(messages)` with a list of message dicts (see code for structure).
- For styling or template changes, edit `conversation.jinja2.html` and the associated CSS/JS files.

See the main project README for architecture and rationale.

## Testing
- See `tests/` for Pytest and pytest-qt based tests verifying scroll behavior and rendering.

## Customization
- To change styles, edit `conversation.jinja2.html` and the CSS in `content_widget.css`.

---

For design rationale, see `REFACTOR.md`.
