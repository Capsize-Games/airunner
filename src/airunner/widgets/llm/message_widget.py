from airunner.data.models.settings_models import Message
from airunner.enums import SignalCode
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.llm.templates.message_ui import Ui_message

from PySide6.QtGui import QFontDatabase, QFont
from PySide6.QtWidgets import QTextEdit, QApplication, QWidget
from PySide6.QtGui import QFontMetrics
from PySide6.QtCore import Qt, QSize, Slot, QEvent
from PySide6.QtCore import Signal


class AutoResizingTextEdit(QTextEdit):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.document().contentsChanged.connect(self.sizeChange)


class MessageWidget(BaseWidget):
    widget_class_ = Ui_message
    textChanged = Signal()

    def __init__(self, *args, **kwargs):
        self.name = kwargs.pop("name")
        self.message = kwargs.pop("message")
        self.conversation_id = kwargs.pop("conversation_id")
        self.message_id = kwargs.pop("message_id")
        if self.message_id is None:
            session = self.session
            message = session.query(Message).filter(Message.conversation_id == self.conversation_id).order_by(
                Message.id.desc()).first()
            if message is not None:
                self.message_id = message.id
        self.is_bot = kwargs.pop("is_bot")
        super().__init__(*args, **kwargs)
        self.ui.content.setReadOnly(True)
        self.ui.content.insertPlainText(self.message)
        self.ui.content.document().contentsChanged.connect(self.sizeChange)
        self.ui.user_name.setText(f"{self.name}")
        self.register(SignalCode.APPLICATION_SETTINGS_CHANGED_SIGNAL, self.on_application_settings_changed_signal)
        self.font_family = None
        self.font_size = None
        self.set_chat_font()

        if self.is_bot:
            self.ui.message_container.setProperty("class", "alternate")

        self.ui.copy_button.setVisible(False)
        self.ui.delete_button.setVisible(False)
        self.ui.message_container.installEventFilter(self)
        self.set_cursor(Qt.CursorShape.ArrowCursor)

    def set_cursor(self, cursor_type):
        self.ui.message_container.setCursor(cursor_type)
        for child in self.ui.message_container.findChildren(QWidget):
            child.setCursor(cursor_type)

    def eventFilter(self, obj, event):
        if obj == self.ui.message_container:
            if event.type() == QEvent.Type.Enter:
                self.ui.copy_button.setVisible(True)
                self.ui.delete_button.setVisible(True)
            elif event.type() == QEvent.Type.Leave:
                self.ui.copy_button.setVisible(False)
                self.ui.delete_button.setVisible(False)
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
                font = QFont("Ubuntu", self.font_size)  # Fallback to Ubuntu if Arial is not available
            font.setFamilies([
                font.family(),
                "Noto Color Emoji",
            ])
            self.ui.content.setFont(font)

    def set_content_size(self):
        doc_height = self.ui.content.document().size().height()
        doc_width = self.ui.content.document().size().width()
        self.setMinimumHeight(int(doc_height) + 45)
        self.setMinimumWidth(int(doc_width))

    def sizeChange(self):
        self.set_content_size()
        self.textChanged.emit()

    def resizeEvent(self, event):
        self.set_content_size()
        super().resizeEvent(event)

    def sizeHint(self):
        fm = QFontMetrics(self.font())
        h = fm.height() * (self.ui.content.document().lineCount() + 1)
        return QSize(self.width(), h)

    def minimumSizeHint(self):
        return self.sizeHint()

    def update_message(self, text):
        self.message += text

        # strip double spaces from self.message
        self.message = self.message.replace("  ", " ")

        self.ui.content.setPlainText(self.message)

    @Slot()
    def delete(self):
        session = self.session
        message = session.query(Message).filter(Message.id == self.message_id).first()
        session.delete(message)
        session.commit()
        self.setParent(None)
        self.deleteLater()

    @Slot()
    def copy(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.message)
