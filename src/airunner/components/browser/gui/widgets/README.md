# Browser Widget Module

This module implements the browser widget for AI Runner, providing a full-featured, privacy-focused web browser UI with multi-tab support.

## Purpose
- Provides a browser interface with tabs, history, bookmarks, and privacy controls.
- Each tab is a full browser UI, instantiated from the same Qt Designer `.ui` template for consistency and isolation.
- Ensures privacy by using off-the-record profiles and strict security defaults.

## Key Components
- `BrowserWidget`: Main class managing the browser UI, tab management, and all browser features.
- `Ui_browser`: Auto-generated UI class from `browser.ui` (do not edit `*_ui.py` directly).
- Tab management: Each tab is a QWidget with its own `Ui_browser` instance, signals, and state.
- Privacy: Uses `QWebEngineProfile` for OTR/private browsing, disables risky features, and provides session clearing.

## Usage
- Do not edit `*_ui.py` files directly. Use Qt Designer to modify `browser.ui` and run `airunner-build-ui` to regenerate.
- To add a new tab, the widget duplicates the full browser UI, clears its state, and connects all signals for independent operation.
- All browser data (history, bookmarks, cache) is managed per tab and can be cleared for privacy.

## Development Notes
- Follow the AI Runner coding guidelines: DRY, type hints, Google-style docstrings, and no direct edits to generated UI files.
- See `browser_widget.py` for implementation details and extension points.
