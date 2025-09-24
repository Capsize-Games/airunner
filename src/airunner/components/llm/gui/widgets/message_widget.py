from PySide6.QtGui import QFontDatabase, QFont
from PySide6.QtWidgets import (
    QTextEdit,
    QApplication,
    QWidget,
    QVBoxLayout,
    QSizePolicy,
    QGraphicsOpacityEffect,
)
from PySide6.QtCore import Qt, QSize, Slot, QEvent, QTimer
from PySide6.QtCore import Signal, QPropertyAnimation, QEasingCurve

from airunner.components.llm.data.conversation import Conversation
from airunner.enums import SignalCode
from airunner.components.application.gui.widgets.base_widget import BaseWidget
from airunner.components.llm.gui.widgets.contentwidgets.latex_widget import LatexWidget
from airunner.components.llm.gui.widgets.contentwidgets.markdown_widget import (
    MarkdownWidget,
)
from airunner.components.llm.gui.widgets.contentwidgets.mixed_content_widget import (
    MixedContentWidget,
)
from airunner.components.llm.gui.widgets.contentwidgets.plain_text_widget import (
    PlainTextWidget,
)
from airunner.components.llm.gui.widgets.templates.message_ui import Ui_message
from airunner.utils.application import get_logger
from airunner.utils.text.formatter_extended import FormatterExtended


class AutoResizingTextEdit(QTextEdit):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.document().contentsChanged.connect(self.sizeChange)


def set_global_tooltip_style():
    app = QApplication.instance()
    if app is not None:
        app.setStyleSheet(
            app.styleSheet()
            + """
            QToolTip {
                color: #fff;
                background-color: #222;
                border: 1px solid #555;
                padding: 4px 8px;
                font-size: 13px;
                border-radius: 4px;
            }
            """
        )


class MessageWidget(BaseWidget):
    widget_class_ = Ui_message
    textChanged = Signal()
    messageResized = Signal()
    icons = [
        ("copy", "copy_button"),
        ("x-circle", "delete_button"),
        ("play", "play_audio_button"),
    ]

    def __init__(self, *args, **kwargs):
        self._current_content_type = None
        self.signal_handlers = {
            SignalCode.APPLICATION_SETTINGS_CHANGED_SIGNAL: self.on_application_settings_changed_signal,
            SignalCode.DELETE_MESSAGES_AFTER_ID: self.on_delete_messages_after_id,
        }
        self.name = kwargs.pop("name")
        self.message = kwargs.pop("message")
        self.message_id = kwargs.pop("message_id")
        self.conversation_id = kwargs.pop("conversation_id")
        self.is_bot = kwargs.pop("is_bot")
        # Accept both 'bot_mood' and 'mood' for compatibility
        self.mood = kwargs.pop("bot_mood", None)
        self.mood_emoji = kwargs.pop("bot_mood_emoji", None)
        self.user_mood = kwargs.pop("user_mood", None)
        # If 'mood' or 'mood_emoji' are provided, use them (test compatibility)
        mood_override = kwargs.pop("mood", None)
        mood_emoji_override = kwargs.pop("mood_emoji", None)
        if mood_override is not None:
            self.mood = mood_override
        if mood_emoji_override is not None:
            self.mood_emoji = mood_emoji_override
        self.font_family = None
        self.font_size = None
        self.content_widget = None
        # Remove any stray custom keys that might be passed
        for k in ["mood", "mood_emoji"]:
            kwargs.pop(k, None)
        super().__init__(*args, **kwargs)

        self._deleted = False
        self.ui.user_name.setText(f"{self.name}")
        # Set mood emoji for bot messages only if both mood and emoji are present
        if self.is_bot and self.mood_emoji and self.mood:
            self.ui.mood_emoji.setText(self.mood_emoji)
            self.ui.mood_emoji.setToolTip(self.mood)
            self.ui.mood_emoji.setVisible(True)
        else:
            self.ui.mood_emoji.setVisible(False)

        # Set up content container layout
        self.content_layout = QVBoxLayout(self.ui.content_container)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)

        # Initialize content widget to None
        self.content_widget = None

        # Set the chat font
        self.set_chat_font()

        if self.is_bot:
            self.ui.message_container.setProperty("class", "alternate")

        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        self.ui.content_container.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )

        # Always keep buttons in the layout but make them transparent when not visible
        # This prevents layout shifts when hovering
        self.ui.copy_button.setVisible(True)
        self.ui.delete_button.setVisible(True)
        self.ui.play_audio_button.setVisible(True)

        # Set opacity to make them invisible but keep their layout space
        self.ui.copy_button.setStyleSheet(
            "background: transparent; border: none;"
        )
        self.ui.delete_button.setStyleSheet(
            "background: transparent; border: none;"
        )
        self.ui.play_audio_button.setStyleSheet(
            "background: transparent; border: none;"
        )

        # Create opacity effects for smooth transitions
        # Create opacity effects for each button
        self.copy_opacity = QGraphicsOpacityEffect()
        self.delete_opacity = QGraphicsOpacityEffect()
        self.play_opacity = QGraphicsOpacityEffect()

        # Set initial opacity to 0.05 (almost invisible but still clickable)
        self.copy_opacity.setOpacity(0.05)
        self.delete_opacity.setOpacity(0.05)
        self.play_opacity.setOpacity(0.05)

        # Apply effects to buttons
        self.ui.copy_button.setGraphicsEffect(self.copy_opacity)
        self.ui.delete_button.setGraphicsEffect(self.delete_opacity)
        self.ui.play_audio_button.setGraphicsEffect(self.play_opacity)

        # Create animations
        self.copy_anim = QPropertyAnimation(self.copy_opacity, b"opacity")
        self.delete_anim = QPropertyAnimation(self.delete_opacity, b"opacity")
        self.play_anim = QPropertyAnimation(self.play_opacity, b"opacity")

        # Configure animations
        for anim in [self.copy_anim, self.delete_anim, self.play_anim]:
            anim.setDuration(150)  # 150ms duration for smooth transition
            anim.setEasingCurve(QEasingCurve.Type.InOutQuad)

        self.ui.message_container.installEventFilter(self)
        self.set_cursor(Qt.CursorShape.ArrowCursor)

        # Add a stylesheet for action buttons for hover/pressed feedback
        button_style = """
        QPushButton {
            background: transparent;
            border: none;
            border-radius: 3px;
        }
        QPushButton:hover {
            background: #333;
            border: 1px solid #666;
        }
        QPushButton:pressed {
            background: #444;
            border: 1px solid #888;
        }
        """
        self.ui.copy_button.setStyleSheet(button_style)
        self.ui.delete_button.setStyleSheet(button_style)
        self.ui.play_audio_button.setStyleSheet(button_style)

        # Set the cursor to pointing hand for action buttons
        self.ui.copy_button.setCursor(Qt.PointingHandCursor)
        self.ui.delete_button.setCursor(Qt.PointingHandCursor)
        self.ui.play_audio_button.setCursor(Qt.PointingHandCursor)

        # Remove tooltips from action buttons
        self.ui.copy_button.setToolTip("")
        self.ui.delete_button.setToolTip("")
        self.ui.play_audio_button.setToolTip("")

        # Hide image_content by default
        self.ui.image_content.setVisible(False)

        # Set message content
        self.set_message_content(self.message)

    def update_mood_emoji(self, mood: str, emoji: str):
        """Update the mood/emoji display for this message widget."""
        self.mood = mood
        self.mood_emoji = emoji
        if self.mood:
            self.ui.mood_emoji.setText(self.mood_emoji)
            self.ui.mood_emoji.setToolTip(self.mood)
            self.ui.mood_emoji.setVisible(True)
            font = self.ui.mood_emoji.font()
            font.setFamilies([font.family(), "Noto Color Emoji"])
            font.setPointSize(24)
            self.ui.mood_emoji.setFont(font)
            self.ui.mood_emoji.setStyleSheet("")  # Remove debug styling
        else:
            self.ui.mood_emoji.setVisible(False)

    def set_message_content(self, message):
        """
        Set the message content in the widget, displaying the appropriate specialized widget
        based on content type. Enhanced with safety checks and robust streaming support.
        """
        if self._deleted:
            return

        try:
            # Use the extended formatter to get detailed content information
            result = FormatterExtended.format_content(message)
            new_type = result["type"]

            # Track the current content type to avoid unnecessary widget replacement
            current_type = getattr(self, "_current_content_type", None)

            # Only replace the widget if the type has changed
            if self.content_widget is None or current_type != new_type:
                # Remove and delete the old widget if present
                if self.content_widget is not None:
                    self.content_layout.removeWidget(self.content_widget)
                    self.content_widget.deleteLater()
                    self.content_widget = None

                # Create and configure the appropriate content widget based on content type
                if new_type == FormatterExtended.FORMAT_MIXED:
                    self.content_widget = MixedContentWidget(
                        self.ui.content_container
                    )
                    self.content_widget.setContent(result["parts"])
                    self.content_layout.addWidget(self.content_widget)
                elif new_type == FormatterExtended.FORMAT_LATEX:
                    self.content_widget = LatexWidget(
                        self.ui.content_container
                    )
                    self.content_widget.setContent(result["content"])
                    self.content_layout.addWidget(self.content_widget)
                elif new_type == FormatterExtended.FORMAT_MARKDOWN:
                    self.content_widget = MarkdownWidget(
                        self.ui.content_container
                    )
                    self.content_widget.setContent(result["content"])
                    self.content_layout.addWidget(self.content_widget)
                else:  # Plain text (default)
                    self.content_widget = PlainTextWidget(
                        self.ui.content_container
                    )
                    self.content_widget.setContent(result["content"])
                    self.content_layout.addWidget(self.content_widget)

                # Apply font settings to the content widget
                if self.font_family and self.font_size:
                    font = QFont(self.font_family, self.font_size)
                    self.content_widget.setFont(font)

                # Add the content widget to the container
                self.content_layout.addWidget(self.content_widget)

                # Connect size changed signal
                if hasattr(self.content_widget, "sizeChanged"):
                    self.content_widget.sizeChanged.connect(
                        self.content_size_changed
                    )

                # Update the current content type
                self._current_content_type = new_type
            else:
                # If the widget type is the same, just update the content
                if new_type == FormatterExtended.FORMAT_MIXED:
                    self.content_widget.setContent(result["parts"])
                elif new_type == FormatterExtended.FORMAT_LATEX:
                    self.content_widget.setContent(result["content"])
                elif new_type == FormatterExtended.FORMAT_MARKDOWN:
                    self.content_widget.setContent(result["content"])
                else:
                    self.content_widget.setContent(result["content"])
        except Exception as e:
            # Log error but don't crash
            if hasattr(self, "logger"):
                self.logger.error(f"Error setting message content: {e}")
            # Fallback to plain text widget
            try:
                if self.content_widget is not None:
                    self.content_layout.removeWidget(self.content_widget)
                    self.content_widget.deleteLater()
                    self.content_widget = None
                self.content_widget = PlainTextWidget(
                    self.ui.content_container
                )
                self.content_widget.setContent(message)
                self.content_layout.addWidget(self.content_widget)
                self._current_content_type = "plain"
            except Exception as fallback_error:
                if hasattr(self, "logger"):
                    self.logger.error(f"Fallback error: {fallback_error}")

    def content_size_changed(self):
        """Handle content widget size changes safely in the main thread."""
        if self.content_widget:
            # Use QTimer.singleShot to ensure this runs in the main thread
            QTimer.singleShot(0, self._update_size_deferred)

    def _update_size_deferred(self):
        """Deferred size update that runs in the main thread."""
        if self.content_widget and not self._deleted:
            try:
                self.adjustSize()
                self.updateGeometry()
                parent = self.parentWidget()
                while parent is not None:
                    parent.updateGeometry()
                    parent = parent.parentWidget()
                self.messageResized.emit()
            except RuntimeError:
                # Widget may have been deleted
                pass

    def on_delete_messages_after_id(self, data):
        message_id = data.get("message_id", None)
        if self.message_id > message_id:
            if (
                not self._deleted
            ):  # Check if the widget has already been deleted
                try:
                    if (
                        self.parentWidget()
                    ):  # Check if the widget still has a parent
                        self.deleteLater()
                except RuntimeError:
                    pass

    def set_cursor(self, cursor_type):
        self.ui.message_container.setCursor(cursor_type)
        for child in self.ui.message_container.findChildren(QWidget):
            child.setCursor(cursor_type)

    def eventFilter(self, obj, event):
        if obj == self.ui.message_container:
            if event.type() == QEvent.Type.Enter:
                # Show buttons with smooth animation
                for anim in [self.copy_anim, self.delete_anim, self.play_anim]:
                    anim.stop()
                    anim.setStartValue(
                        anim.currentValue()
                        if anim.state() == QPropertyAnimation.State.Running
                        else 0.05
                    )
                    anim.setEndValue(1.0)
                    anim.start()
            elif event.type() == QEvent.Type.Leave:
                # Hide buttons with smooth animation (to 0.05, not 0)
                for anim in [self.copy_anim, self.delete_anim, self.play_anim]:
                    anim.stop()
                    anim.setStartValue(
                        anim.currentValue()
                        if anim.state() == QPropertyAnimation.State.Running
                        else 1.0
                    )
                    anim.setEndValue(0.05)
                    anim.start()
        return super().eventFilter(obj, event)

    def on_application_settings_changed_signal(self):
        self.set_chat_font()

    def set_chat_font(self):
        font_setting = self.get_font_setting_by_name("chat")
        font_family = font_setting.font_family
        font_size = font_setting.font_size
        if self.font_family != font_family or self.font_size != font_size:
            self.font_family = font_family
            self.font_size = font_size
            # Check if the font family is available
            available_families = QFontDatabase().families()
            if self.font_family in available_families:
                font = QFont(self.font_family, self.font_size)
            else:
                font = QFont(
                    "Ubuntu", self.font_size
                )  # Fallback to Ubuntu if Arial is not available
            font.setFamilies(
                [
                    font.family(),
                    "Noto Color Emoji",
                ]
            )

            # Apply the font to the content widget if it exists
            if self.content_widget:
                self.content_widget.setFont(font)

    def set_content_size(self):
        """
        Set the content size of the widget based on the content widget's size hint.
        This method is now safe to call from any thread via QTimer.singleShot.
        """
        QTimer.singleShot(0, self._set_content_size_safe)

    def _set_content_size_safe(self):
        """Safe content size setting that runs in the main thread."""
        if self.content_widget and not self._deleted:
            try:
                self.content_widget.adjustSize()
                self.adjustSize()
                self.updateGeometry()
                parent = self.parentWidget()
                if parent:
                    parent.updateGeometry()
            except RuntimeError:
                # Widget may have been deleted
                pass

    def sizeChange(self):
        # Notify that the text has changed
        self.textChanged.emit()

    def resizeEvent(self, event):
        super().resizeEvent(event)

    def sizeHint(self):
        # Use the content widget's size hint if available
        if self.content_widget:
            content_size = self.content_widget.sizeHint()
            return QSize(
                content_size.width(), content_size.height() + 60
            )  # Add space for header

        # Fallback sizing logic
        lines = self.message.count("\n") + 1
        chars_per_line = (
            max(len(line) for line in self.message.split("\n") if line)
            if self.message
            else 30
        )

        # Estimate size based on content
        width = min(max(chars_per_line * 10, 300), 1000)  # Reasonable width
        height = max(100, min(lines * 24, 800))  # Reasonable height per line

        return QSize(width, height + 50)  # Add space for header

    def minimumSizeHint(self):
        # Use the content widget's minimum size hint if available
        if self.content_widget:
            content_min_size = self.content_widget.minimumSizeHint()
            return QSize(
                content_min_size.width(), content_min_size.height() + 60
            )  # Add space for header

        # Reasonable minimum size
        return QSize(300, 100)

    def update_message(self, text):
        self.message += text
        self.message = self.message.replace("  ", " ")
        # Optimize streaming: if current widget is PlainTextWidget, append text directly
        if (
            self.content_widget is not None
            and isinstance(self.content_widget, PlainTextWidget)
            and getattr(self, "_current_content_type", None) == "plain"
        ):
            self.content_widget.appendText(text)
        else:
            # Always update the content for all types (Markdown, Mixed, LaTeX, PlainText)
            self.set_message_content(self.message)

    @Slot()
    def on_play_audio_button_clicked(self):
        self.api.tts.play_audio(self.message)

    @Slot()
    def delete(self):
        if not self._deleted:  # Check if the widget has already been deleted
            self._deleted = True
            try:
                conversation = Conversation.objects.filter_by(current=True)[0]
            except IndexError:
                get_logger(__name__).warning(
                    "No current conversation found for deletion."
                )
                return
            messages = conversation.value
            if self.message_id == 0:
                updated_messages = []
            else:
                updated_messages = messages[0 : self.message_id]
            Conversation.objects.update(
                conversation.id, value=updated_messages
            )
            self.api.llm.delete_messages_after_id(self.message_id)
            self.setParent(None)
            QTimer.singleShot(0, self.deleteLater)

    @Slot()
    def copy(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.message)
