import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional

from PySide6.QtCore import QTimer, Slot, Qt
from PySide6.QtWidgets import QApplication, QLabel
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineWidgets import QWebEngineView
from llama_cloud import MessageRole

from airunner.components.conversations.conversation_history_manager import (
    ConversationHistoryManager,
)
from airunner.components.llm.gui.widgets.loading_widget import LoadingWidget
from airunner.enums import SignalCode, TemplateName
from airunner.components.llm.gui.widgets.contentwidgets import (
    ChatBridge,
    ConversationWebEnginePage,
)
from airunner.components.chat.gui.widgets.templates.conversation_ui import (
    Ui_conversation,
)

from airunner.components.application.gui.widgets.base_widget import BaseWidget
from airunner.components.llm.utils import strip_names_from_message
from airunner.utils.application.log_hygiene import summarize_mapping_keys
from airunner.utils.text.formatter_extended import FormatterExtended


_LOG_CONVERSATION_WEBVIEW_PROGRESS = (
    os.environ.get("AIRUNNER_LOG_CONVERSATION_WEBVIEW_PROGRESS", "0")
    == "1"
)


def get_conversation_asset_version() -> str:
    """Return a cache-busting version for live conversation assets."""
    static_dir = Path(__file__).resolve().parent.parent / "static"
    asset_paths = (
        static_dir / "css" / "conversation.css",
        static_dir / "js" / "conversation.js",
    )
    latest_mtime = max(
        (path.stat().st_mtime_ns for path in asset_paths if path.exists()),
        default=0,
    )
    return str(latest_mtime)


class ConversationWidget(BaseWidget):
    ui: Ui_conversation  # type: ignore[assignment]
    """Widget that displays a conversation using a single QWebEngineView and HTML template.

    Args:
        parent (QWidget, optional): Parent widget.
    """

    widget_class_ = Ui_conversation

    @staticmethod
    def _use_placeholder_conversation_view() -> bool:
        """Return whether one lightweight placeholder should replace QWebEngine."""
        return os.environ.get("AIRUNNER_TEST_NO_GUI_LAUNCH", "0") == "1" or (
            os.environ.get("QT_QPA_PLATFORM", "").lower() == "offscreen"
        )

    def __init__(self, *args, **kwargs):
        self.registered: bool = False
        self.signal_handlers = {
            SignalCode.QUEUE_LOAD_CONVERSATION: self.on_queue_load_conversation,
            SignalCode.LLM_TEXT_STREAMED_SIGNAL: self.on_add_bot_message_to_conversation,
            SignalCode.CONVERSATION_DELETED: self.on_delete_conversation,
            SignalCode.LLM_CLEAR_HISTORY_SIGNAL: self.on_clear_conversation,
            SignalCode.APPLICATION_MAIN_WINDOW_LOADED_SIGNAL: self.on_main_window_loaded_signal,
            SignalCode.MOOD_SUMMARY_UPDATE_STARTED: self._handle_mood_summary_update_started,
            SignalCode.BOT_MOOD_UPDATED: self.on_bot_mood_updated_signal,
            SignalCode.CHATBOT_CHANGED: self.on_chatbot_changed,
            SignalCode.LLM_TEXT_GENERATE_REQUEST_SIGNAL: self.on_llm_request_text_generate_signal,
            SignalCode.LLM_TOOL_STATUS_SIGNAL: self.on_tool_status_update,
            SignalCode.LLM_THINKING_SIGNAL: self.on_thinking_update,
        }
        self.ui_update_timer = QTimer(self)
        self.ui_update_timer.setInterval(50)
        self.ui_update_timer.timeout.connect(self.flush_token_buffer)
        self.ui_update_timer.start()
        self._conversation_history_manager = None
        self._conversation: Optional[Any] = None
        self._conversation_id: Optional[int] = None
        self.conversation_history = []
        self._streamed_messages = []
        self.loading_widget = LoadingWidget(self)
        self.loading_widget.hide()
        self._page_ready = False  # Flag to prevent early template rendering
        self._template_rendered = False
        self._template_render_scheduled = False
        self._interactive_template_loaded = False
        self._startup_placeholder: Optional[QLabel] = None
        self._main_window_loaded = False
        self._shutdown_started = False
        super().__init__()
        self._conversation_history_manager = ConversationHistoryManager(
            getattr(self.api, "daemon_client", None)
        )

        self.token_buffer = []
        # Add a streaming buffer to ensure proper token ordering
        self._current_stream_tokens = []
        self._stream_started = False
        self._orphaned_tokens = (
            []
        )  # Collect tokens that arrive before is_first_message
        # Add sequence-based buffering to handle out-of-order signals
        self._sequence_buffer = {}  # Dict[int, LLMResponse]
        self._expected_sequence = 1  # Next expected sequence number
        # Track which message index is currently being streamed to avoid overwriting
        self._active_stream_message_index = None
        self._rendered_request_ids = set()
        self._js_ready = self._use_placeholder_conversation_view()
        self._chat_bridge_flush_pending = False
        self._pending_chat_bridge_calls = []
        self._web_channel: Optional[QWebChannel] = None
        self._chat_bridge = ChatBridge()
        self._chat_bridge.scrollRequested.connect(self._handle_scroll_request)

        self._chat_bridge.deleteMessageRequested.connect(self.deleteMessage)
        self._chat_bridge.copyMessageRequested.connect(
            self._handle_copy_message
        )
        self._chat_bridge.copyTextRequested.connect(self._handle_copy_text)

    def _get_view(self) -> Optional[QWebEngineView]:
        """Return the live conversation web view when it exists."""
        stage = self.ui.stage if self.ui and hasattr(self.ui, "stage") else None
        return stage if isinstance(stage, QWebEngineView) else None

    def _initialize_web_engine_view(self, view: QWebEngineView) -> None:
        """Attach the custom page and chat bridge once per web view."""
        if getattr(view, "_airunner_initialized", False):
            self._page_ready = True
            return

        custom_page = ConversationWebEnginePage(view, self)
        view.setPage(custom_page)
        if _LOG_CONVERSATION_WEBVIEW_PROGRESS:
            view.loadStarted.connect(
                lambda: self.logger.debug(
                    "[ConversationWidget] Load started"
                )
            )
            view.loadFinished.connect(
                lambda ok: self.logger.debug(
                    f"[ConversationWidget] Load finished: {ok}"
                )
            )
            view.loadProgress.connect(
                lambda progress: self.logger.debug(
                    f"[ConversationWidget] Load progress: {progress}%"
                )
            )
        view.setContextMenuPolicy(Qt.ContextMenuPolicy.PreventContextMenu)
        self._web_channel = QWebChannel(view.page())
        self._web_channel.registerObject("chatBridge", self._chat_bridge)
        view.page().setWebChannel(self._web_channel)
        setattr(view, "_airunner_initialized", True)
        self._page_ready = True

    def _ensure_web_engine_view(self) -> Optional[QWebEngineView]:
        """Create the conversation web view only when interactive HTML is needed."""
        if self._use_placeholder_conversation_view():
            return None

        view = self._get_view()
        if view is not None:
            self._initialize_web_engine_view(view)
            return view

        if not self.ui or not hasattr(self.ui, "stage"):
            return None

        placeholder = self.ui.stage
        layout = getattr(self.ui, "gridLayout", None)
        min_size = placeholder.minimumSize()
        object_name = placeholder.objectName() or "stage"
        row = 0
        column = 0
        row_span = 1
        column_span = 1
        if layout is not None:
            index = layout.indexOf(placeholder)
            if index != -1:
                row, column, row_span, column_span = (
                    layout.getItemPosition(index)
                )
                layout.removeWidget(placeholder)

        parent = placeholder.parentWidget() or self
        placeholder.hide()
        placeholder.deleteLater()

        view = QWebEngineView(parent)
        view.setObjectName(object_name)
        view.setMinimumSize(min_size)
        if layout is not None:
            layout.addWidget(view, row, column, row_span, column_span)
        self.ui.stage = view
        self._initialize_web_engine_view(view)
        return view

    def navigate(self, url: str):
        """Open a URL in the system's default browser."""
        import webbrowser
        webbrowser.open(url)

    @property
    def conversation(self) -> Optional[Any]:
        return self._conversation

    @conversation.setter
    def conversation(self, val: Optional[Any]):
        self._conversation = val
        self._conversation_id = val.id if val else None

    @property
    def conversation_id(self) -> Optional[int]:
        return self._conversation_id

    @conversation_id.setter
    def conversation_id(self, val: Optional[int]):
        self._conversation_id = val

    @property
    def web_engine_view(self) -> Optional[object]:
        # Return None during initialization until custom page is set
        if not getattr(self, "_page_ready", False):
            return None
        return self._get_view()

    @property
    def template(self) -> Optional[str]:
        return "conversation.jinja2.html"

    @property
    def template_context(self) -> Dict:
        context = super().template_context
        context["asset_version"] = get_conversation_asset_version()
        context["messages"] = []
        return context

    def on_delete_conversation(self, data):
        if self.conversation_id == data["conversation_id"]:
            self._clear_conversation_widgets()
            self.conversation = None

    def showEvent(self, event):
        super().showEvent(event)
        if self._main_window_loaded:
            self._schedule_initial_template_render()
        if not self.registered:
            self.registered = True

    def resizeEvent(self, event):
        super().resizeEvent(event)

    def on_main_window_loaded_signal(self, _data=None) -> None:
        """Render the initial conversation template after app startup."""
        self._main_window_loaded = True
        self._schedule_initial_template_render()

    def _schedule_initial_template_render(self) -> None:
        """Schedule the initial HTML template render once."""
        if self._template_rendered or self._template_render_scheduled:
            return
        self._template_render_scheduled = True
        QTimer.singleShot(0, self._render_initial_template)

    def _render_initial_template(self) -> None:
        """Render the conversation template after the widget is shown."""
        if self._template_rendered:
            return
        self._template_rendered = True
        if self._streamed_messages:
            self._ensure_interactive_template()
            return
        self.logger.debug(
            "[ConversationWidget] Deferring empty startup render"
        )
        return

    def _ensure_interactive_template(self) -> None:
        """Load the full conversation webview only when chat content is needed."""
        if self._interactive_template_loaded:
            return
        if self._use_placeholder_conversation_view():
            return
        view = self._ensure_web_engine_view()
        if view is None:
            return
        self._interactive_template_loaded = True
        if self._startup_placeholder is not None:
            self._startup_placeholder.hide()
        self.logger.debug(
            "[ConversationWidget] Rendering interactive conversation template"
        )
        self.render_template()
        self._schedule_chat_bridge_flush()

    def _setup_startup_placeholder(self) -> None:
        """Create one overlay placeholder for the empty startup state."""
        if self._startup_placeholder is not None:
            return
        self.logger.debug(
            "[ConversationWidget] Creating startup placeholder"
        )
        placeholder = QLabel(self)
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder.setObjectName("conversation_startup_placeholder")
        placeholder.hide()
        self._startup_placeholder = placeholder
        self._sync_startup_placeholder_geometry()
        self.logger.debug(
            "[ConversationWidget] Startup placeholder created"
        )

    def _sync_startup_placeholder_geometry(self) -> None:
        """Keep the empty-state overlay aligned with the hidden webview."""
        if self._startup_placeholder is None or not hasattr(self.ui, "stage"):
            return
        self.logger.debug(
            "[ConversationWidget] Syncing startup placeholder geometry"
        )
        self._startup_placeholder.setGeometry(self.ui.stage.geometry())
        self._startup_placeholder.raise_()
        self.logger.debug(
            "[ConversationWidget] Startup placeholder geometry synced"
        )

    def _render_startup_placeholder(self) -> None:
        """Show a lightweight empty-state shell to avoid blocking startup."""
        if self._startup_placeholder is None:
            self._setup_startup_placeholder()
        self.logger.debug(
            "[ConversationWidget] Preparing startup placeholder theme"
        )
        theme = self.template_context.get("theme", "dark")
        is_dark = theme.startswith("dark")
        background = "#161616" if is_dark else "#f5f5f5"
        foreground = "#d2d2d2" if is_dark else "#4d4d4d"
        border = "#2f2f2f" if is_dark else "#d8d8d8"
        self.logger.debug(
            "[ConversationWidget] Applying startup placeholder text"
        )
        self._startup_placeholder.setText("Start a conversation.")
        self.logger.debug(
            "[ConversationWidget] Applying startup placeholder stylesheet"
        )
        self._startup_placeholder.setStyleSheet(
            "QLabel#conversation_startup_placeholder {"
            f"background: {background};"
            f"color: {foreground};"
            f"border: 1px solid {border};"
            "border-radius: 10px;"
            "padding: 18px 20px;"
            "font-size: 13px;"
            "}"
        )
        self.logger.debug(
            "[ConversationWidget] Syncing startup placeholder before show"
        )
        self._sync_startup_placeholder_geometry()
        self.logger.debug(
            "[ConversationWidget] Showing startup placeholder"
        )
        self._startup_placeholder.show()
        self.logger.debug(
            "[ConversationWidget] Startup placeholder shown"
        )

    def on_chatbot_changed(self):
        self.api.llm.clear_history()
        self._clear_conversation()

    def on_queue_load_conversation(self, data):
        conversation_id = data.get("index")
        self.load_conversation(conversation_id=conversation_id)

    def load_conversation(self, conversation_id: Optional[int] = None) -> None:
        """Load a conversation by ID, update state and UI."""
        session = self._conversation_history_manager.get_conversation_session(
            conversation_id=conversation_id,
            max_messages=50,
        )
        conversation = session.get("conversation")
        if conversation is None:
            self.clear_conversation()
            return
        self._conversation = conversation
        self._conversation_id = conversation.id
        self._rendered_request_ids.clear()
        messages = session.get("messages", [])
        self.set_conversation_widgets(messages, skip_scroll=True)
        # Tool statuses are now attached to messages as tool_usage and rendered by JS
        # No need to restore separately - this was causing duplicate widgets

    def clear_conversation(self) -> None:
        """Clear all conversation state and UI."""
        self._conversation = None
        self._conversation_id = None
        self.conversation_history = []
        self._streamed_messages = []
        self._rendered_request_ids.clear()
        self._pending_chat_bridge_calls = []
        # Use explicit clear signal instead of set_conversation([])
        self._chat_bridge.clear_messages()
        self._clear_conversation_widgets()

    def handle_close(self):
        """Release webview resources before the application exits."""
        self._stop_ui_update_timer()
        self._shutdown_web_view()

    def _stop_ui_update_timer(self) -> None:
        """Stop recurring UI work during shutdown."""
        if self.ui_update_timer.isActive():
            self.ui_update_timer.stop()

    def _shutdown_web_view(self) -> None:
        """Tear down the conversation webview synchronously."""
        if self._shutdown_started:
            return
        self._shutdown_started = True
        view = self._get_view()
        if view is None:
            return

        try:
            page = view.page()
        except RuntimeError:
            page = None

        if page is not None:
            try:
                page.setWebChannel(None)
            except Exception:
                pass

        try:
            view.stop()
            view.close()
        except Exception:
            pass

        self._delete_qt_object("_web_channel")
        self._delete_qt_object("_chat_bridge")

        if page is not None:
            try:
                page.deleteLater()
            except Exception:
                pass

        try:
            view.deleteLater()
            QApplication.processEvents()
        except Exception:
            pass

    def _delete_qt_object(self, attr_name: str) -> None:
        """Delete a Qt object attribute if it exists."""
        qt_object = getattr(self, attr_name, None)
        if qt_object is None:
            return
        try:
            qt_object.deleteLater()
        except Exception:
            pass
        setattr(self, attr_name, None)

    def on_add_bot_message_to_conversation(self, data: Dict):
        self.hide_status_indicator()
        llm_response = data.get("response", None)
        if not llm_response:
            raise ValueError("No LLMResponse object found in data")

        if llm_response.node_id is not None:
            return

        # Skip empty end-of-stream signals, but reset state
        if llm_response.is_end_of_message:
            # Allow inclusion of any final token content then finalize after processing
            if not llm_response.message:
                self._finalize_stream_state()
                return
            # If final token carries content we'll process it then finalize in _process_sequential_tokens

        # Always use the sequence-based handler
        self._handle_sequenced_token(llm_response)

    def hide_status_indicator(self):
        """Hide the loading spinner."""
        self.loading_widget.hide()
        QApplication.processEvents()

    def wait_for_js_ready(self, callback, max_attempts=50):
        """Wait for the JS QWebChannel to be ready before calling setMessages.

        Args:
            callback: Function to call when JS is ready
            max_attempts: Maximum number of retry attempts (default 50 = ~2.5 seconds)
        """
        if self._use_placeholder_conversation_view():
            callback()
            return

        self._ensure_interactive_template()
        attempt_count = 0

        def check_ready():
            nonlocal attempt_count
            attempt_count += 1

            try:
                view = self._get_view()
                if not view or not view.page():
                    self.logger.debug(
                        "ConversationWidget: Widget or page no longer available for JS ready check"
                    )
                    return

                view_page = view.page()
                view_page.runJavaScript(
                    "window.isChatReady === true",
                    lambda ready: handle_result(ready),
                )
            except RuntimeError as e:
                self.logger.debug(
                    f"ConversationWidget: JavaScript ready check failed (widget deleted?): {e}"
                )
                callback()

        def handle_result(ready):
            if ready:
                self._js_ready = True
                callback()
            elif attempt_count < max_attempts:
                QTimer.singleShot(50, check_ready)
            else:
                callback()

        check_ready()

    def _dispatch_chat_bridge_call(
        self,
        method_name: str,
        *args,
    ) -> None:
        """Send one bridge event now or queue it until JS is ready."""
        if self._js_ready:
            getattr(self._chat_bridge, method_name)(*args)
            return
        self._pending_chat_bridge_calls.append((method_name, args))
        self._schedule_chat_bridge_flush()

    def _schedule_chat_bridge_flush(self) -> None:
        """Wait for JS once before flushing queued bridge events."""
        if self._js_ready:
            self._flush_pending_chat_bridge_calls()
            return
        if self._chat_bridge_flush_pending:
            return
        self._chat_bridge_flush_pending = True
        self.wait_for_js_ready(self._flush_pending_chat_bridge_calls)

    def _flush_pending_chat_bridge_calls(self) -> None:
        """Flush queued bridge events after the web view comes online."""
        self._chat_bridge_flush_pending = False
        if not self._js_ready:
            return
        pending_calls = self._pending_chat_bridge_calls
        self._pending_chat_bridge_calls = []
        for method_name, args in pending_calls:
            getattr(self._chat_bridge, method_name)(*args)

    def _format_message_for_webview(
        self,
        *,
        content: str,
        message_id: int,
        name: str,
        is_bot: bool,
        timestamp: str = "",
        request_id: str = "",
    ) -> Dict[str, Any]:
        """Return one formatted message payload for the conversation view."""
        fmt = FormatterExtended.format_content(content)
        return {
            "content": fmt["content"],
            "content_type": fmt["type"],
            "id": message_id,
            "timestamp": timestamp,
            "name": name,
            "is_bot": is_bot,
            "request_id": request_id,
        }

    def wait_for_dom_ready(self, callback, max_attempts=50):
        """Wait for the DOM to be ready before executing callback.

        Args:
            callback: Function to call when DOM is ready
            max_attempts: Maximum number of retry attempts (default 50 = ~2.5 seconds)
        """
        if self._use_placeholder_conversation_view():
            callback()
            return

        self._ensure_interactive_template()
        attempt_count = 0

        def check_dom_ready():
            nonlocal attempt_count
            attempt_count += 1

            try:
                view = self._get_view()
                if not view or not view.page():
                    self.logger.debug(
                        "ConversationWidget: Widget or page no longer available for DOM ready check"
                    )
                    return

                view_page = view.page()
                view_page.runJavaScript(
                    "document.readyState === 'complete' && !!document.getElementById('conversation-container')",
                    lambda ready: handle_dom_result(ready),
                )
            except RuntimeError as e:
                self.logger.debug(
                    f"ConversationWidget: DOM ready check failed (widget deleted?): {e}"
                )
                callback()

        def handle_dom_result(ready):
            if ready:
                callback()
            elif attempt_count < max_attempts:
                QTimer.singleShot(50, check_dom_ready)
            else:
                self.logger.warning(
                    f"ConversationWidget: DOM ready timeout after {max_attempts} attempts"
                )
                callback()

        check_dom_ready()

    def set_conversation(self, messages: List[Dict[str, Any]]) -> None:
        """Update the conversation display using MathJax for all content types.

        Args:
            messages (List[Dict[str, Any]]): List of message dicts (sender, text, timestamp, etc).
        """
        # If empty list, use clear_messages signal instead
        if not messages:
            self._clear_conversation_widgets()
            return

        simplified_messages = []
        for msg in messages:
            content = msg.get("text") or msg.get("content") or ""
            # Format content for MathJax compatibility
            fmt = FormatterExtended.format_content(content)

            # Build the message dict preserving important fields
            simplified_msg = {
                "content": fmt["content"],  # MathJax will handle all formatting
                "content_type": fmt["type"],  # Keep for debugging/logging
                "id": msg.get("id", len(simplified_messages)),
                "timestamp": msg.get("timestamp", ""),
                "name": msg.get("name")
                or msg.get("sender")
                or ("Assistant" if msg.get("is_bot") else "User"),
                "is_bot": msg.get("is_bot", False),
                "request_id": msg.get("request_id", ""),
            }
            
            # Preserve thinking and tool usage fields for assistant messages
            if msg.get("thinking_content"):
                simplified_msg["thinking_content"] = msg["thinking_content"]
            if msg.get("thinking_metadata"):
                simplified_msg["thinking_metadata"] = msg[
                    "thinking_metadata"
                ]
            if msg.get("pre_tool_thinking"):
                simplified_msg["pre_tool_thinking"] = msg["pre_tool_thinking"]
            if msg.get("tool_usage"):
                simplified_msg["tool_usage"] = msg["tool_usage"]
            
            # Debug logging
            self.logger.info(
                f"[SET_CONVERSATION] Message {simplified_msg['id']}: "
                f"is_bot={simplified_msg['is_bot']}, "
                f"has_pre_tool_thinking={bool(simplified_msg.get('pre_tool_thinking'))}, "
                f"has_thinking_content={bool(simplified_msg.get('thinking_content'))}, "
                f"has_thinking_metadata={bool(simplified_msg.get('thinking_metadata'))}, "
                f"has_tool_usage={bool(simplified_msg.get('tool_usage'))}"
            )
            
            simplified_messages.append(simplified_msg)

        # Ensure _conversation_id is set if possible
        if self._conversation_id is None and self._conversation is not None:
            self._conversation_id = getattr(self._conversation, "id", None)

        def send():
            self._pending_chat_bridge_calls = []
            self._chat_bridge.set_messages(simplified_messages)

        self.wait_for_js_ready(send)

    def _restore_tool_statuses(self):
        """Restore tool statuses from conversation metadata."""
        if not self._conversation:
            return

        user_data = self._conversation.user_data or {}
        tool_statuses = user_data.get("tool_statuses", [])

        self.logger.debug(
            f"[TOOL STATUS] Restoring {len(tool_statuses)} tool statuses from database"
        )

        # Send each tool status to JavaScript for rendering
        # Only send completed statuses (starting statuses are transient)
        for tool_status in tool_statuses:
            status = tool_status.get("status", "")
            if status == "completed":
                self.logger.debug(
                    f"[TOOL STATUS] Restoring completed status: {tool_status.get('tool_id')}"
                )
                self._chat_bridge.updateToolStatus(
                    tool_status.get("request_id", ""),
                    tool_status.get("tool_id", ""),
                    tool_status.get("tool_name", ""),
                    tool_status.get("query", ""),
                    status,
                    tool_status.get("details", "") or "",
                    json.dumps(tool_status.get("metadata"))
                    if tool_status.get("metadata")
                    else "",
                )

    def _handle_scroll_request(self) -> None:
        """Handle scroll request from JavaScript and delegate to parent scroll area."""
        try:
            # Scroll outer QScrollArea to bottom
            scroll_area = getattr(self.ui, "messages", None)
            if scroll_area is not None:
                vsb = scroll_area.verticalScrollBar()
                vsb.setValue(vsb.maximum())
            else:
                # Log that outer scroll area was not found so we can determine which scrollbar is active
                self.logger.debug(
                    "_handle_scroll_request: no outer scroll area found on UI (messages attribute missing)"
                )
        except Exception:
            self.logger.debug("_handle_scroll_request failed", exc_info=True)

    def _handle_copy_message(self, message_id) -> None:
        """Handle copy requests from the webview by copying message text to the system clipboard."""
        try:
            # normalize id
            try:
                mid = int(message_id)
            except Exception:
                mid = message_id

            self.logger.info(f"_handle_copy_message: looking for message id {mid}")

            # find message text in streamed messages or conversation
            text = None
            # check streamed buffer first
            streamed_msgs = getattr(self, "_streamed_messages", []) or []
            self.logger.info(f"_handle_copy_message: searching {len(streamed_msgs)} streamed messages")
            for m in streamed_msgs:
                msg_id = m.get("id", -1)
                try:
                    if int(msg_id) == int(mid):
                        text = m.get("content") or m.get("text") or ""
                        self.logger.info(f"_handle_copy_message: found in streamed messages, content length={len(text)}")
                        break
                except (ValueError, TypeError):
                    continue
                    
            # fallback to conversation stored value
            if (
                text is None
                and self._conversation
                and hasattr(self._conversation, "value")
            ):
                conv_msgs = self._conversation.value or []
                self.logger.info(f"_handle_copy_message: searching {len(conv_msgs)} conversation messages")
                for m in conv_msgs:
                    msg_id = m.get("id", -1)
                    try:
                        if int(msg_id) == int(mid):
                            text = m.get("content") or m.get("text") or ""
                            self.logger.info(f"_handle_copy_message: found in conversation, content length={len(text)}")
                            break
                    except (ValueError, TypeError):
                        continue

            if text is None:
                self.logger.warning(
                    f"_handle_copy_message: message id {message_id} not found in {len(streamed_msgs)} streamed or conversation messages"
                )
                return

            self._copy_text_to_clipboard(
                str(text),
                source=f"message id {message_id}",
            )
        except Exception as e:
            self.logger.warning(f"_handle_copy_message failed: {e}", exc_info=True)

    def _handle_copy_text(self, text: str) -> None:
        """Handle raw text copy requests from the webview."""
        normalized = str(text or "")
        if not normalized:
            self.logger.info("_handle_copy_text: ignoring empty copy request")
            return
        self._copy_text_to_clipboard(normalized, source="status widget")

    def _copy_text_to_clipboard(self, text: str, *, source: str) -> None:
        """Copy one text payload to the system clipboard."""
        try:
            clipboard = QApplication.clipboard()
            clipboard.setText(str(text))
            self.logger.info(
                f"_copy_text_to_clipboard: copied {len(text)} chars from {source}"
            )
        except Exception as e:
            self.logger.warning(
                f"_copy_text_to_clipboard: failed for {source}: {e}",
                exc_info=True,
            )

    def scroll_to_bottom(self) -> None:
        """Scroll the conversation to the bottom by triggering the parent QScrollArea."""

        def trigger_scroll():
            try:
                view = self._get_view()
                if not view or not view.page():
                    self.logger.debug(
                        "ConversationWidget: Widget or page no longer available for scroll"
                    )
                    return

                view_page = view.page()
                view_page.runJavaScript(
                    """
                    if (window.chatBridge && window.chatBridge.request_scroll) {
                        window.chatBridge.request_scroll();
                        console.log('[ConversationWidget] Scroll request sent to Qt');
                    } else {
                        console.warn('[ConversationWidget] chatBridge.request_scroll not available');
                    }
                    """,
                    lambda result: self.logger.debug(
                        f"ConversationWidget: Scroll request result: {result}"
                    ),
                )
            except RuntimeError as e:
                self.logger.debug(
                    f"ConversationWidget: JavaScript call failed (widget deleted?): {e}"
                )

        trigger_scroll()
        QTimer.singleShot(50, trigger_scroll)
        QTimer.singleShot(200, trigger_scroll)

    def _assign_message_ids(self, messages: list[dict]) -> list[dict]:
        """Assign unique, consecutive integer 'id' to every message."""
        for idx, msg in enumerate(messages):
            msg["id"] = idx
        return messages

    def set_conversation_widgets(self, messages, skip_scroll: bool = False):
        """Replace per-message widgets with a single HTML conversation view."""
        del skip_scroll
        # Ensure every message has a unique integer 'id' and correct role/is_bot
        messages = self._assign_message_ids(messages)
        for msg in messages:
            if "role" not in msg:
                msg["role"] = "assistant" if msg.get("is_bot") else "user"
            if "is_bot" not in msg:
                msg["is_bot"] = msg.get("role") == "assistant"
        self._streamed_messages = list(messages)
        if self._conversation is not None:
            self._conversation.value = self._streamed_messages
        self.set_conversation(self._streamed_messages)

    def _clear_conversation(self, skip_update: bool = False):
        self.logger.debug(
            "[CONVERSATION] _clear_conversation called "
            f"(skip_update={skip_update})"
        )
        self.conversation = None
        self.conversation_history = []
        self._streamed_messages = []
        self._rendered_request_ids.clear()
        # Use explicit clear signal instead of set_conversation([])
        if not skip_update and self._interactive_template_loaded:
            self._chat_bridge.clear_messages()
        self._clear_conversation_widgets(skip_update=skip_update)

    def append_user_message_for_request(
        self,
        prompt: str,
        request_id: Optional[str] = None,
    ) -> None:
        """Append one user message unless it was already rendered."""
        if not prompt:
            return
        if request_id and request_id in self._rendered_request_ids:
            return
        if request_id:
            self._rendered_request_ids.add(request_id)

        username = getattr(getattr(self, "user", None), "username", "User")
        self._streamed_messages.append(
            {
                "name": username,
                "content": prompt,
                "role": "user",
                "is_bot": False,
                "request_id": request_id,
            }
        )
        self._streamed_messages = self._assign_message_ids(
            self._streamed_messages
        )
        if self._conversation is not None:
            self._conversation.value = self._streamed_messages
        self._dispatch_chat_bridge_call(
            "append_message",
            self._format_message_for_webview(
                content=prompt,
                message_id=self._streamed_messages[-1]["id"],
                name=username,
                is_bot=False,
                request_id=request_id or "",
            ),
        )

    def _clear_conversation_widgets(self, skip_update: bool = False):
        """Clear the HTML conversation view."""
        if not skip_update and self._interactive_template_loaded:
            self._chat_bridge.clear_messages()

    def on_clear_conversation(self):
        self._clear_conversation()

    def add_message_to_conversation(
        self,
        name: str,
        message: str,
        is_bot: bool,
        first_message: bool = True,
        _message_id: Optional[int] = None,
        _profile_widget: bool = False,
        mood: str = None,
        mood_emoji: str = None,
        user_mood: str = None,
    ):
        del first_message
        message = strip_names_from_message(
            message,
            self.user.username,
            self.chatbot.botname,
        )
        widget = None
        if message != "":
            message_id = None
            if _message_id is not None:
                message_id = _message_id
            if message_id is None and (
                self.conversation
                and hasattr(self.conversation, "value")
                and isinstance(self.conversation.value, list)
            ):
                message_id = len(self.conversation.value)
            elif message_id is None:
                message_id = 0
            kwargs = dict(
                name=name,
                message=message,
                is_bot=is_bot,
                message_id=message_id,
                conversation_id=self.conversation_id,
            )
            if is_bot:
                kwargs["bot_mood"] = mood
                kwargs["bot_mood_emoji"] = mood_emoji
                kwargs["user_mood"] = user_mood
            else:
                kwargs["user_mood"] = user_mood

        else:
            self.logger.warning(
                f"ChatPromptWidget.add_message_to_conversation: Message is empty, not creating widget"
            )

        return widget

    def show_status_indicator(
        self, message: str = "Updating bot mood / summarizing..."
    ):
        """Show the loading spinner with a status message."""
        self.loading_widget.ui.label.setText(message)
        self.loading_widget.show()
        self.loading_widget.raise_()
        QApplication.processEvents()

    def on_mood_summary_update_started(self):
        self.show_status_indicator("Updating bot mood / summarizing...")

    def _handle_mood_summary_update_started(self, data):
        """Handle mood/summary update signal and show loading message."""
        message = data.get("message", "Updating bot mood / summarizing...")
        self.show_status_indicator(message)

    def on_bot_mood_updated_signal(self, data):
        """Handle live mood/emoji update for a message widget."""
        print("TODO: BOT MOOD UPDATED")

    def flush_token_buffer(self):
        """
        Flush the token buffer and update the UI.
        """
        combined_message = "".join(self.token_buffer)
        self.token_buffer.clear()

        if combined_message != "":
            if (
                self._streamed_messages
                and self._streamed_messages[-1]["is_bot"]
            ):
                self._streamed_messages[-1]["content"] += combined_message
            else:
                self._streamed_messages.append(
                    {
                        "name": self.chatbot.botname,
                        "content": combined_message,
                        "role": MessageRole.ASSISTANT.value,
                        "is_bot": True,
                    }
                )
            self._streamed_messages = self._assign_message_ids(
                self._streamed_messages
            )
            self.set_conversation(self._streamed_messages)

    def on_llm_request_text_generate_signal(self, data):
        """
        Handle the LLM request text generation signal.
        """
        request_data = data.get("request_data", {})
        prompt = request_data.get("prompt", "")
        request_id = data.get("request_id") or request_data.get(
            "request_id"
        )
        self.append_user_message_for_request(
            prompt,
            request_id=request_id,
        )

    def on_tool_status_update(self, data: Dict[str, Any]):
        """Handle tool status updates and display them in the UI.

        Args:
            data: Tool status data containing:
                - tool_id: Unique identifier for the tool call
                - tool_name: Name of the tool (e.g., "search_web")
                - query: Query being executed
                - status: "starting" or "completed"
                - details: Optional details (e.g., domain names for web search)
                - conversation_id: ID of the conversation
                - timestamp: When the status changed
        """
        self.logger.debug(
            "[TOOL STATUS] Received signal (%s)",
            summarize_mapping_keys(data, label="data"),
        )

        tool_id = data.get("tool_id")
        tool_name = data.get("tool_name")
        query = data.get("query")
        status = data.get("status")
        details = data.get("details", "")
        conversation_id = data.get("conversation_id")
        request_id = data.get("request_id", "")
        metadata = data.get("metadata")
        timestamp = data.get("timestamp")

        if not all([tool_id, tool_name, query, status]):
            self.logger.warning(
                f"[TOOL STATUS] Missing required fields in data: {data}"
            )
            return

        # Only process if this is for the current conversation
        if (
            conversation_id
            and self.conversation
            and conversation_id != self.conversation.id
        ):
            self.logger.debug(
                f"[TOOL STATUS] Ignoring status for different conversation"
            )
            return

        self.logger.info(
            f"[TOOL STATUS] Processing {status} status for {tool_name}: {query}"
        )

        # Save to database (conversation.user_data)
        if self.conversation:
            user_data = self.conversation.user_data or {}
            tool_statuses = user_data.get("tool_statuses", [])

            # Check if this tool_id already exists (update instead of append)
            existing_idx = None
            for idx, ts in enumerate(tool_statuses):
                if ts.get("tool_id") == tool_id:
                    existing_idx = idx
                    break

            tool_status_entry = {
                "tool_id": tool_id,
                "tool_name": tool_name,
                "query": query,
                "status": status,
                "details": details,
                "request_id": request_id,
                "metadata": metadata,
                "timestamp": timestamp,
            }

            if existing_idx is not None:
                # Update existing entry
                tool_statuses[existing_idx] = tool_status_entry
                self.logger.debug(
                    f"[TOOL STATUS] Updated existing entry at index {existing_idx}"
                )
            else:
                # Append new entry
                tool_statuses.append(tool_status_entry)
                self.logger.debug(f"[TOOL STATUS] Appended new entry")

            user_data["tool_statuses"] = tool_statuses
            self.conversation.user_data = user_data
            self._conversation_history_manager.update_conversation_user_data(
                self.conversation.id,
                user_data,
            )
            self.logger.debug(
                f"[TOOL STATUS] Saved to database: {len(tool_statuses)} total statuses"
            )

        # Send to JavaScript for rendering
        self.logger.debug(
            f"[TOOL STATUS] Calling _chat_bridge.updateToolStatus"
        )
        self._chat_bridge.updateToolStatus(
            request_id or "",
            tool_id,
            tool_name,
            query,
            status,
            details or "",  # Ensure empty string instead of None
            json.dumps(metadata) if metadata else "",
        )

    def on_thinking_update(self, data: Dict[str, Any]):
        """Handle thinking status updates from Qwen3 <think> blocks.

        Args:
            data: Thinking status data containing:
                - status: "started", "streaming", or "completed"
                - content: The thinking text content
        """
        request_id = data.get("request_id", "")
        status = data.get("status", "")
        content = data.get("content", "")
        metadata = data.get("metadata")
        metadata_json = json.dumps(metadata) if metadata else ""

        # Send to JavaScript for rendering
        self._dispatch_chat_bridge_call(
            "updateThinkingStatus",
            request_id,
            status,
            content,
            metadata_json,
        )

    def show_model_loading_status(
        self,
        request_id: str,
        message: str = "Loading model",
    ) -> None:
        """Show one request-scoped model loading status in the web view."""
        self._dispatch_chat_bridge_call(
            "updateModelLoadStatus",
            request_id,
            "started",
            message,
        )

    def clear_model_loading_status(self, request_id: str) -> None:
        """Remove one request-scoped model loading status from the web view."""
        self._dispatch_chat_bridge_call(
            "updateModelLoadStatus",
            request_id,
            "completed",
            "",
        )

    def _get_view(self):
        """Return the QWebEngineView used for rendering the conversation."""
        stage = self.ui.stage if self.ui and hasattr(self.ui, "stage") else None
        return stage if isinstance(stage, QWebEngineView) else None

    @property
    def _view(self):
        """Compat property for tests expecting a _view attribute (QWebEngineView)."""
        return self._get_view()

    @Slot(int)
    @Slot(str)
    def deleteMessage(self, message_id):
        """Delete a message and all subsequent messages from the conversation."""
        conversation = self._conversation
        if not conversation or not hasattr(conversation, "value"):
            return
        try:
            message_id = int(message_id)
        except Exception:
            return
        messages = conversation.value or []
        idx = next(
            (
                i
                for i, m in enumerate(messages)
                if int(m.get("id", -1)) == message_id
            ),
            None,
        )
        if idx is None:
            return
        new_messages = messages[:idx]
        new_messages = self._assign_message_ids(new_messages)
        updated = self._conversation_history_manager.update_conversation_messages(
            conversation.id,
            new_messages,
        )
        if not updated:
            return
        self._conversation.value = new_messages
        self.set_conversation_widgets(new_messages)

    def _handle_sequenced_token(self, llm_response):
        """
        Handle tokens with sequence numbers to ensure proper ordering.

        Args:
            llm_response: LLMResponse object with sequence_number field
        """
        sequence_num = llm_response.sequence_number

        # Initialize / restart sequence tracking on first message boundary
        if llm_response.is_first_message:
            if not self._stream_started:
                existing_keys = list(self._sequence_buffer.keys())
                self._expected_sequence = sequence_num
                self._current_stream_tokens = []
                self._stream_started = True
                self._active_stream_message_index = (
                    None  # Force creation of a new message when processed
                )
            else:
                # New stream while another is active -> finalize previous WITHOUT deleting its content
                self._finalize_stream_state(
                    partial=True
                )  # Keep sequence buffer for possible early tokens
                self._expected_sequence = sequence_num
                self._current_stream_tokens = []
                self._stream_started = True
                self._active_stream_message_index = None

        # Store token in sequence buffer
        self._sequence_buffer[sequence_num] = llm_response

        # Process any tokens that are now in sequence immediately
        self._process_sequential_tokens()

    def _process_sequential_tokens(self):
        """Process buffered tokens that are in the correct sequence."""

        processed_any = False
        last_token_was_end = False
        while self._expected_sequence in self._sequence_buffer:
            token_response = self._sequence_buffer.pop(self._expected_sequence)

            # Add to stream buffer
            if token_response.message:
                self._current_stream_tokens.append(token_response.message)
            if getattr(token_response, "is_end_of_message", False):
                last_token_was_end = True

            self._expected_sequence += 1
            processed_any = True

        # Update the conversation display only once after processing all available tokens
        if processed_any:
            combined_content = "".join(self._current_stream_tokens)

            if not self._streamed_messages:
                self._streamed_messages = []

            # Update or create bot message
            if self._active_stream_message_index is None:
                # Always create a new message for a new stream to avoid overwriting prior answers
                # Calculate the ID before creating the message
                new_message_id = len(self._streamed_messages)
                new_message = {
                    "id": new_message_id,  # Store ID in the message for copy lookup
                    "name": self.chatbot.botname,
                    "content": combined_content,
                    "role": MessageRole.ASSISTANT.value,
                    "is_bot": True,
                    "request_id": getattr(
                        token_response,
                        "request_id",
                        "",
                    ),
                }
                self._streamed_messages.append(new_message)
                self._active_stream_message_index = (
                    len(self._streamed_messages) - 1
                )
                # Use appendMessage instead of set_conversation to avoid clearing
                self._dispatch_chat_bridge_call(
                    "append_message",
                    self._format_message_for_webview(
                        content=combined_content,
                        message_id=new_message_id,
                        name=self.chatbot.botname,
                        is_bot=True,
                            request_id=getattr(
                                token_response,
                                "request_id",
                                "",
                            ),
                    ),
                )
            else:
                # Just update the existing message content during streaming
                self._streamed_messages[self._active_stream_message_index][
                    "content"
                ] = combined_content
                # Use incremental update instead of rebuilding entire conversation
                # Format the content before sending
                fmt = FormatterExtended.format_content(combined_content)
                self._dispatch_chat_bridge_call(
                    "update_last_message_content",
                    self._streamed_messages[
                        self._active_stream_message_index
                    ].get("request_id", ""),
                    fmt["content"],
                    fmt["type"],
                )

        if last_token_was_end:
            self._finalize_stream_state()
            if self._streamed_messages:
                self._streamed_messages = self._assign_message_ids(
                    self._streamed_messages
                )
                if self._conversation is not None:
                    self._conversation.value = self._streamed_messages

    def _finalize_stream_state(self, partial: bool = False):
        """Reset streaming state after a message completes.

        Args:
            partial: If True, keeps existing sequence buffer (used when a new first token arrives mid-stream).
        """
        self._stream_started = False
        self._current_stream_tokens = []
        self._active_stream_message_index = None
        self._expected_sequence = 1 if not partial else self._expected_sequence
        if not partial:
            self._sequence_buffer = {}

    def on_theme_changed_signal(self, data: Dict):
        """
        Set the theme for the home widget by updating the CSS in the webEngineView.
        This will call the setTheme JS function in the loaded HTML.
        """
        view = self._get_view()
        if view is not None and view.page():
            theme_name = data.get(
                "template", TemplateName.SYSTEM_DEFAULT
            ).value.lower()
            # Set window.currentTheme before calling setTheme
            js = f"window.currentTheme = '{theme_name}'; window.setTheme && window.setTheme('{theme_name}');"
            view.page().runJavaScript(js)
        super().on_theme_changed_signal(data)
