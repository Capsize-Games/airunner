from PySide6.QtGui import QFontDatabase, QFont
from PySide6.QtWidgets import QTextEdit, QApplication, QWidget, QVBoxLayout
from PySide6.QtGui import QFontMetrics
from PySide6.QtCore import Qt, QSize, Slot, QEvent, QTimer, QThread, QObject
from PySide6.QtCore import Signal, QPropertyAnimation, QEasingCurve
import queue

from airunner.enums import SignalCode
from airunner.gui.widgets.base_widget import BaseWidget
from airunner.gui.widgets.llm.templates.message_ui import Ui_message
from airunner.data.models import Conversation
from airunner.data.session_manager import session_scope
from airunner.gui.widgets.llm.content_widgets import (
    PlainTextWidget,
    LatexWidget,
    MarkdownWidget,
    MixedContentWidget,
)
from airunner.utils.text.formatter_extended import FormatterExtended


class AutoResizingTextEdit(QTextEdit):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.document().contentsChanged.connect(self.sizeChange)


# Worker class for the resize operation
class ResizeWorker(QObject):
    finished = Signal()

    def __init__(self, message_queue):
        super().__init__()
        self.message_queue = message_queue
        self.running = True

    def process(self):
        while self.running:
            try:
                # Get the next message widget from the queue with a timeout
                message_widget = self.message_queue.get(timeout=0.1)
                message_widget.set_content_size()
                self.message_queue.task_done()
            except queue.Empty:
                # If the queue is empty, just continue and check again
                pass

    def stop(self):
        self.running = False


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
    icons = [
        ("copy", "copy_button"),
        ("x-circle", "delete_button"),
        ("play", "play_audio_button"),
    ]

    # Class-level thread and queue for all instances
    resize_queue = queue.Queue()
    resize_thread = None
    resize_worker = None

    @classmethod
    def initialize_resize_worker(cls):
        if cls.resize_thread is None:
            cls.resize_thread = QThread()
            cls.resize_worker = ResizeWorker(cls.resize_queue)
            cls.resize_worker.moveToThread(cls.resize_thread)

            # Connect signals and slots
            cls.resize_thread.started.connect(cls.resize_worker.process)

            # Start the thread
            cls.resize_thread.start()

    def __init__(self, *args, **kwargs):
        self.signal_handlers = {
            SignalCode.APPLICATION_SETTINGS_CHANGED_SIGNAL: self.on_application_settings_changed_signal,
            SignalCode.DELETE_MESSAGES_AFTER_ID: self.on_delete_messages_after_id,
        }
        self.name = kwargs.pop("name")
        self.message = kwargs.pop("message")
        self.message_id = kwargs.pop("message_id")
        self.conversation_id = kwargs.pop("conversation_id")
        self.is_bot = kwargs.pop("is_bot")
        super().__init__(*args, **kwargs)

        # Initialize the class-level worker if not already done
        self.__class__.initialize_resize_worker()

        self._deleted = False
        self.ui.user_name.setText(f"{self.name}")
        self.font_family = None
        self.font_size = None

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

        # Set size policies for better expansion
        from PySide6.QtWidgets import QSizePolicy

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.ui.content_container.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Minimum
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
        from PySide6.QtWidgets import QGraphicsOpacityEffect

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

    def set_message_content(self, message):
        """
        Set the message content in the widget, displaying the appropriate specialized widget
        based on content type.
        """
        # Clear any existing content widget
        if self.content_widget is not None:
            self.content_layout.removeWidget(self.content_widget)
            self.content_widget.deleteLater()
            self.content_widget = None

        # Use the extended formatter to get detailed content information
        result = FormatterExtended.format_content(message)

        # Create and configure the appropriate content widget based on content type
        if result["type"] == FormatterExtended.FORMAT_MIXED:
            self.content_widget = MixedContentWidget(self.ui.content_container)
            self.content_widget.setContent(result["parts"])
        elif result["type"] == FormatterExtended.FORMAT_LATEX:
            self.content_widget = LatexWidget(self.ui.content_container)
            self.content_widget.setContent(result["content"])
        elif result["type"] == FormatterExtended.FORMAT_MARKDOWN:
            self.content_widget = MarkdownWidget(self.ui.content_container)
            self.content_widget.setContent(result["content"])
        else:  # Plain text (default)
            self.content_widget = PlainTextWidget(self.ui.content_container)
            self.content_widget.setContent(result["content"])

        # Apply font settings to the content widget
        if self.font_family and self.font_size:
            font = QFont(self.font_family, self.font_size)
            self.content_widget.setFont(font)

        # Add the content widget to the container
        self.content_layout.addWidget(self.content_widget)

        # Connect size changed signal
        if hasattr(self.content_widget, "sizeChanged"):
            self.content_widget.sizeChanged.connect(self.content_size_changed)

    def content_size_changed(self):
        """Handle content widget size changes."""
        # Update our own size hints based on the content widget
        if self.content_widget:
            self.updateGeometry()

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
        # Let the content widget handle its own sizing
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
        # strip double spaces from self.message
        self.message = self.message.replace("  ", " ")

        # Update the content
        self.set_message_content(self.message)

    @Slot()
    def on_play_audio_button_clicked(self):
        self.api.tts.play_audio(self.message)

    @Slot()
    def delete(self):
        if not self._deleted:  # Check if the widget has already been deleted
            self._deleted = True
            with session_scope() as session:
                conversation = (
                    session.query(Conversation)
                    .filter(Conversation.id == self.conversation_id)
                    .first()
                )
                messages = conversation.value
                if self.message_id == 0:
                    conversation.value = []
                else:
                    conversation.value = messages[0 : self.message_id]
                session.add(conversation)
                session.commit()
            self.api.llm.delete_messages_after_id(self.message_id)
            self.setParent(None)
            QTimer.singleShot(0, self.deleteLater)

    @Slot()
    def copy(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.message)
