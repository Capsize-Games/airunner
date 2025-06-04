# LLM Chat Prompt Widget & Mood/Summary System

## Overview

This module provides the chat prompt widget for the AI Runner LLM interface, including:
- The main chat input and message display area
- Visual feedback for LLM operations (e.g., loading, mood/summary updates)
- Integration with the bot mood and conversation summary system

## Mood & Summary System

- The chat prompt widget now displays a visual loading indicator (spinner and message) when the LLM is updating the bot's mood or summarizing the conversation.
- The loading indicator message is now fully customizable: when the LLM agent triggers a mood or summary update, it emits a signal with an arbitrary message (see `show_loading_message` in the API). The chat prompt widget displays this message in the loading spinner.
- The indicator is automatically hidden as soon as a new chat message arrives.
- The mood/summary system is always enabled by default for all chatbots. No manual activation is required.
- See `test_chat_prompt_widget.py` for tests verifying custom loading messages.

## Key Components

- `chat_prompt_widget.py`: Main widget logic, including status indicator and message handling.
- `loading_widget.py`: Spinner widget for visual feedback.
- `message_widget.py`: Displays individual chat messages, including mood/emoji.
- `templates/`: Qt Designer `.ui` files for all widgets.
- `tests/`: Pytest-based tests for widget logic and UI behavior.

## Refactor: Single Conversation Widget

- As of 2025-05-31, the chat prompt now uses a single ConversationWidget (HTML-based, QWebEngineView) for all message display.
- The old per-message MessageWidget logic is deprecated and will be removed.
- See `user/conversation_widget.py` for implementation details.
- All conversation rendering is now handled by Jinja2 HTML templates for performance and maintainability.

## Local Network Access (LNA) Support

### Overview
This module's local HTTP server (`local_http_server.py`) is LNA-compliant for Chromium-based clients (e.g., QWebEngineView in PySide6). It automatically responds to preflight OPTIONS requests and all actual requests with the required headers for Local Network Access (LNA) and CORS.

### LNA/CORS Headers
- `Access-Control-Allow-Private-Network: true`
- `Access-Control-Allow-Origin: *` (or specific origin if needed)
- `Access-Control-Allow-Methods: GET, POST, OPTIONS, PUT, DELETE`
- `Access-Control-Allow-Headers: Content-Type, Authorization, X-Requested-With`

### Diagnostics & Debugging
- The PySide6 application enables QWebEngineView diagnostics:
  - Remote debugging via `QTWEBENGINE_REMOTE_DEBUGGING=9223`.
  - JavaScript console messages are captured and printed to stdout.
  - Developer tools are enabled in all QWebEngineView widgets.
- To inspect LNA/CORS issues, check the application logs for `JSCONSOLE:::` messages and use the remote debugging port if needed.

### Security Notes
- The server is strict about directory traversal and dangerous file types.
- LNA headers are always sent for both preflight and actual requests.
- For production, consider restricting `Access-Control-Allow-Origin` to a specific origin.

### Testing LNA
- Use the PySide6 app's QWebEngineView to load local network resources.
- Automated tests should verify that OPTIONS and actual requests receive the correct headers and are not blocked by Chromium's LNA enforcement.

## Security Hardening: Local Network Access (LNA) and CORS

### Hardened Production Mode
- The local HTTP server is now locked down for production:
  - **No LNA:** Never sends `Access-Control-Allow-Private-Network`.
  - **No permissive CORS:** Does not send `Access-Control-Allow-Origin` except for trusted origins (commented out by default).
  - **OPTIONS requests:** All preflight (OPTIONS) requests are blocked with 403 Forbidden.
  - **Unsafe HTTP methods:** POST, PUT, DELETE, OPTIONS are all blocked with 405/403.
  - **Directory traversal:** Strict checks, all attempts are logged and blocked.
  - **Dangerous file types:** Never served.
  - **Directory listing:** Always forbidden.
  - **Strict MIME enforcement:** Only whitelisted types are served.
  - **Security headers:** HSTS, X-Content-Type-Options, X-Frame-Options, Referrer-Policy, X-XSS-Protection always set.

### Security Notes
- This configuration is designed to be as close to unhackable as possible for a local HTTP server.
- No website (even if loaded in QWebEngineView or Chromium) can access this server via LNA or CORS.
- If you need to allow access for a specific trusted origin, uncomment and set the `Access-Control-Allow-Origin` header in `_send_lna_cors_headers`.

## Usage

- The mood/summary system is always enabled by default. No user action is required.
- To test or extend the indicator logic, see `test_chat_prompt_widget.py`.

## Testing

- All UI and logic changes are covered by tests in the `tests/` subdirectory.
- Use `pytest` and `pytest-qt` to run tests:
  ```bash
  pytest src/airunner/gui/widgets/llm/tests/
  ```

## Development Notes

- Do not edit `*_ui.py` files directly. Edit `.ui` files and run `airunner-build-ui` to regenerate.
- For more details, see the main project [README](../../../README.md).
