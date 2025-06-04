# Chat GUI Widgets

This module contains widgets for the chat UI, including the main chat prompt and conversation display, and manages frontend-backend communication via QWebChannel.

## Components

- `chat_prompt_widget.py`: Parent chat prompt widget. Handles user input, send/clear/history actions, and delegates all conversation state management to `ConversationWidget`.
- `conversation_widget.py`: The single source of truth for conversation state. Manages loading, updating, deleting, and displaying messages. Ensures all messages have unique, consecutive integer IDs and correct roles. Handles all message deletion, addition, and UI/database synchronization.

## Architecture & Workflow

- **State Management:**
  - All conversation state (messages, IDs, roles) is managed exclusively in `ConversationWidget`.
  - The parent widget (`ChatPromptWidget`) only calls `load_conversation` and `clear_conversation` on the child; it does not manipulate conversation state directly.
- **Message Deletion:**
  - Message deletion is robust: messages can be deleted immediately after being sent, IDs are always correct, and the UI/database remain in sync.
  - After any add/delete, all messages are re-indexed to have consecutive IDs, preventing UI or JS errors.
- **Frontend Integration:**
  - QWebChannel is used for communication between the Python backend and the JavaScript frontend.
  - The frontend triggers actions (e.g., deleteMessage), but all persistent state changes are handled in Python for security and consistency.

## Usage

- To add or delete messages, always use the provided methods on `ConversationWidget`.
- Do not expose slots directly on QWidget subclasses; use QObject bridges for frontend-callable slots if needed.
- For UI changes, edit the `.ui` files and run `airunner-build-ui`.

## Safety & Best Practices

- All message and history logic is handled in Python.
- The frontend only triggers actions; it does not manipulate persistent state directly.
- All code follows DRY, KISS, and type-hinting guidelines.

---

For more details, see the main project README and architecture documentation.
