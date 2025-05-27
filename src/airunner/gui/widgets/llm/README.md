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
