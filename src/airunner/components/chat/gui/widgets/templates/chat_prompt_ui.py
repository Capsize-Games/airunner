# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'chat_prompt.ui'
##
## Created by: Qt User Interface Compiler version 6.9.0
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QFrame,
    QGridLayout, QHBoxLayout, QLabel, QPlainTextEdit,
    QProgressBar, QPushButton, QScrollArea, QSizePolicy,
    QSpacerItem, QSplitter, QTabWidget, QWidget)

from airunner.components.chat.gui.widgets.conversation_widget import ConversationWidget
from airunner.components.llm.gui.widgets.llm_history_widget import LLMHistoryWidget
from airunner.components.llm.gui.widgets.llm_settings_widget import LLMSettingsWidget
import airunner.feather_rc

class Ui_chat_prompt(object):
    def setupUi(self, chat_prompt):
        if not chat_prompt.objectName():
            chat_prompt.setObjectName(u"chat_prompt")
        chat_prompt.resize(597, 691)
        self.gridLayout_2 = QGridLayout(chat_prompt)
        self.gridLayout_2.setSpacing(0)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.gridLayout_2.setContentsMargins(0, 0, 0, 0)
        self.chat_prompt_action_bar = QWidget(chat_prompt)
        self.chat_prompt_action_bar.setObjectName(u"chat_prompt_action_bar")
        self.horizontalLayout_3 = QHBoxLayout(self.chat_prompt_action_bar)
        self.horizontalLayout_3.setSpacing(0)
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.horizontalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.action_bar_container = QHBoxLayout()
        self.action_bar_container.setSpacing(5)
        self.action_bar_container.setObjectName(u"action_bar_container")
        self.action_bar_container.setContentsMargins(10, 10, 10, 10)
        self.clear_conversation_button = QPushButton(self.chat_prompt_action_bar)
        self.clear_conversation_button.setObjectName(u"clear_conversation_button")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Maximum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.clear_conversation_button.sizePolicy().hasHeightForWidth())
        self.clear_conversation_button.setSizePolicy(sizePolicy)
        self.clear_conversation_button.setMinimumSize(QSize(30, 30))
        self.clear_conversation_button.setMaximumSize(QSize(30, 30))
        icon = QIcon()
        icon.addFile(u":/light/icons/feather/light/plus.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.clear_conversation_button.setIcon(icon)

        self.action_bar_container.addWidget(self.clear_conversation_button)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.action_bar_container.addItem(self.horizontalSpacer)

        self.history_button = QPushButton(self.chat_prompt_action_bar)
        self.history_button.setObjectName(u"history_button")
        sizePolicy.setHeightForWidth(self.history_button.sizePolicy().hasHeightForWidth())
        self.history_button.setSizePolicy(sizePolicy)
        self.history_button.setMinimumSize(QSize(30, 30))
        self.history_button.setMaximumSize(QSize(30, 30))
        icon1 = QIcon()
        icon1.addFile(u":/light/icons/feather/light/clock.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.history_button.setIcon(icon1)
        self.history_button.setCheckable(True)

        self.action_bar_container.addWidget(self.history_button)

        self.settings_button = QPushButton(self.chat_prompt_action_bar)
        self.settings_button.setObjectName(u"settings_button")
        self.settings_button.setMinimumSize(QSize(30, 30))
        self.settings_button.setMaximumSize(QSize(30, 30))
        icon2 = QIcon()
        icon2.addFile(u":/light/icons/feather/light/settings.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.settings_button.setIcon(icon2)
        self.settings_button.setCheckable(True)

        self.action_bar_container.addWidget(self.settings_button)


        self.horizontalLayout_3.addLayout(self.action_bar_container)


        self.gridLayout_2.addWidget(self.chat_prompt_action_bar, 0, 0, 1, 1)

        self.chat_history_widget = LLMHistoryWidget(chat_prompt)
        self.chat_history_widget.setObjectName(u"chat_history_widget")

        self.gridLayout_2.addWidget(self.chat_history_widget, 1, 0, 1, 1)

        self.scrollArea = QScrollArea(chat_prompt)
        self.scrollArea.setObjectName(u"scrollArea")
        self.scrollArea.setWidgetResizable(True)
        self.scrollAreaWidgetContents_2 = QWidget()
        self.scrollAreaWidgetContents_2.setObjectName(u"scrollAreaWidgetContents_2")
        self.scrollAreaWidgetContents_2.setGeometry(QRect(0, 0, 595, 561))
        self.gridLayout_4 = QGridLayout(self.scrollAreaWidgetContents_2)
        self.gridLayout_4.setSpacing(0)
        self.gridLayout_4.setObjectName(u"gridLayout_4")
        self.gridLayout_4.setContentsMargins(0, 0, 0, 0)
        self.tabWidget = QTabWidget(self.scrollAreaWidgetContents_2)
        self.tabWidget.setObjectName(u"tabWidget")
        self.tab = QWidget()
        self.tab.setObjectName(u"tab")
        self.gridLayout_6 = QGridLayout(self.tab)
        self.gridLayout_6.setSpacing(0)
        self.gridLayout_6.setObjectName(u"gridLayout_6")
        self.gridLayout_6.setContentsMargins(0, 0, 0, 0)
        self.splitter = QSplitter(self.tab)
        self.splitter.setObjectName(u"splitter")
        self.splitter.setOrientation(Qt.Orientation.Vertical)
        self.conversation = ConversationWidget(self.splitter)
        self.conversation.setObjectName(u"conversation")
        self.splitter.addWidget(self.conversation)
        self.prompt_container = QWidget(self.splitter)
        self.prompt_container.setObjectName(u"prompt_container")
        self.gridLayout = QGridLayout(self.prompt_container)
        self.gridLayout.setSpacing(0)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setContentsMargins(10, 10, 10, 10)
        self.prompt_wrapper = QWidget(self.prompt_container)
        self.prompt_wrapper.setObjectName(u"prompt_wrapper")
        self.prompt_wrapper_layout = QGridLayout(self.prompt_wrapper)
        self.prompt_wrapper_layout.setSpacing(0)
        self.prompt_wrapper_layout.setObjectName(u"prompt_wrapper_layout")
        self.prompt_wrapper_layout.setContentsMargins(0, 0, 0, 0)

        self.gridLayout.addWidget(self.prompt_wrapper, 2, 0, 1, 1)

        self.chat_container = QWidget(self.prompt_container)
        self.chat_container.setObjectName(u"chat_container")
        self.gridLayout_7 = QGridLayout(self.chat_container)
        self.gridLayout_7.setObjectName(u"gridLayout_7")
        self.gridLayout_7.setContentsMargins(0, 0, 0, 0)
        self.attachments_scroll_area = QScrollArea(self.chat_container)
        self.attachments_scroll_area.setObjectName(u"attachments_scroll_area")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.attachments_scroll_area.sizePolicy().hasHeightForWidth())
        self.attachments_scroll_area.setSizePolicy(sizePolicy1)
        self.attachments_scroll_area.setMinimumSize(QSize(0, 0))
        self.attachments_scroll_area.setMaximumSize(QSize(16777215, 80))
        self.attachments_scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.attachments_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.attachments_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.attachments_scroll_area.setWidgetResizable(True)
        self.attachments_container = QWidget()
        self.attachments_container.setObjectName(u"attachments_container")
        self.attachments_container.setGeometry(QRect(0, 0, 0, 0))
        self.attachments_layout = QHBoxLayout(self.attachments_container)
        self.attachments_layout.setSpacing(8)
        self.attachments_layout.setObjectName(u"attachments_layout")
        self.attachments_layout.setContentsMargins(0, 4, 0, 4)
        self.attachments_scroll_area.setWidget(self.attachments_container)

        self.gridLayout_7.addWidget(self.attachments_scroll_area, 0, 0, 1, 2)

        self.token_count = QLabel(self.chat_container)
        self.token_count.setObjectName(u"token_count")
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.token_count.sizePolicy().hasHeightForWidth())
        self.token_count.setSizePolicy(sizePolicy2)
        self.token_count.setStyleSheet(u"")
        self.token_count.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout_7.addWidget(self.token_count, 1, 1, 1, 1)

        self.attach_button = QPushButton(self.chat_container)
        self.attach_button.setObjectName(u"attach_button")
        sizePolicy.setHeightForWidth(self.attach_button.sizePolicy().hasHeightForWidth())
        self.attach_button.setSizePolicy(sizePolicy)
        self.attach_button.setMinimumSize(QSize(30, 30))
        self.attach_button.setMaximumSize(QSize(30, 30))
        icon3 = QIcon()
        icon3.addFile(u":/light/icons/feather/light/paperclip.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.attach_button.setIcon(icon3)

        self.gridLayout_7.addWidget(self.attach_button, 2, 0, 1, 1)

        self.prompt = QPlainTextEdit(self.chat_container)
        self.prompt.setObjectName(u"prompt")
        sizePolicy3 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sizePolicy3.setHorizontalStretch(0)
        sizePolicy3.setVerticalStretch(0)
        sizePolicy3.setHeightForWidth(self.prompt.sizePolicy().hasHeightForWidth())
        self.prompt.setSizePolicy(sizePolicy3)
        self.prompt.setMinimumSize(QSize(0, 150))
        self.prompt.setMaximumSize(QSize(16777215, 16777215))

        self.gridLayout_7.addWidget(self.prompt, 2, 1, 1, 1)

        self.horizontalLayout_4 = QHBoxLayout()
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.last_message_tokens = QLabel(self.chat_container)
        self.last_message_tokens.setObjectName(u"last_message_tokens")
        sizePolicy2.setHeightForWidth(self.last_message_tokens.sizePolicy().hasHeightForWidth())
        self.last_message_tokens.setSizePolicy(sizePolicy2)
        self.last_message_tokens.setStyleSheet(u"")

        self.horizontalLayout_4.addWidget(self.last_message_tokens)

        self.total_tokens = QLabel(self.chat_container)
        self.total_tokens.setObjectName(u"total_tokens")
        sizePolicy2.setHeightForWidth(self.total_tokens.sizePolicy().hasHeightForWidth())
        self.total_tokens.setSizePolicy(sizePolicy2)
        self.total_tokens.setStyleSheet(u"")
        self.total_tokens.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.horizontalLayout_4.addWidget(self.total_tokens)


        self.gridLayout_7.addLayout(self.horizontalLayout_4, 3, 1, 1, 1)


        self.gridLayout.addWidget(self.chat_container, 0, 0, 1, 1)

        self.splitter.addWidget(self.prompt_container)

        self.gridLayout_6.addWidget(self.splitter, 0, 0, 1, 1)

        self.tabWidget.addTab(self.tab, "")
        self.tab_2 = QWidget()
        self.tab_2.setObjectName(u"tab_2")
        self.gridLayout_3 = QGridLayout(self.tab_2)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.gridLayout_3.setContentsMargins(0, 0, 0, 0)
        self.llm_settings = LLMSettingsWidget(self.tab_2)
        self.llm_settings.setObjectName(u"llm_settings")

        self.gridLayout_3.addWidget(self.llm_settings, 0, 0, 1, 1)

        self.tabWidget.addTab(self.tab_2, "")
        self.tab_3 = QWidget()
        self.tab_3.setObjectName(u"tab_3")
        self.gridLayout_5 = QGridLayout(self.tab_3)
        self.gridLayout_5.setObjectName(u"gridLayout_5")
        self.gridLayout_5.setContentsMargins(0, 0, 0, 0)
        self.widget = LLMHistoryWidget(self.tab_3)
        self.widget.setObjectName(u"widget")

        self.gridLayout_5.addWidget(self.widget, 0, 0, 1, 1)

        self.tabWidget.addTab(self.tab_3, "")

        self.gridLayout_4.addWidget(self.tabWidget, 0, 0, 1, 1)

        self.scrollArea.setWidget(self.scrollAreaWidgetContents_2)

        self.gridLayout_2.addWidget(self.scrollArea, 2, 0, 1, 1)

        self.chat_prompt_footer = QWidget(chat_prompt)
        self.chat_prompt_footer.setObjectName(u"chat_prompt_footer")
        self.horizontalLayout = QHBoxLayout(self.chat_prompt_footer)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.footer_container = QWidget(self.chat_prompt_footer)
        self.footer_container.setObjectName(u"footer_container")
        self.horizontalLayout_2 = QHBoxLayout(self.footer_container)
        self.horizontalLayout_2.setSpacing(5)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.horizontalLayout_2.setContentsMargins(10, 10, 10, 10)
        self.provider_dropdown = QComboBox(self.footer_container)
        self.provider_dropdown.setObjectName(u"provider_dropdown")
        sizePolicy4 = QSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        sizePolicy4.setHorizontalStretch(0)
        sizePolicy4.setVerticalStretch(0)
        sizePolicy4.setHeightForWidth(self.provider_dropdown.sizePolicy().hasHeightForWidth())
        self.provider_dropdown.setSizePolicy(sizePolicy4)
        self.provider_dropdown.setMinimumSize(QSize(110, 30))
        self.provider_dropdown.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)

        self.horizontalLayout_2.addWidget(self.provider_dropdown)

        self.model_dropdown = QComboBox(self.footer_container)
        self.model_dropdown.setObjectName(u"model_dropdown")
        sizePolicy5 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        sizePolicy5.setHorizontalStretch(0)
        sizePolicy5.setVerticalStretch(0)
        sizePolicy5.setHeightForWidth(self.model_dropdown.sizePolicy().hasHeightForWidth())
        self.model_dropdown.setSizePolicy(sizePolicy5)
        self.model_dropdown.setMinimumSize(QSize(150, 30))
        self.model_dropdown.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)

        self.horizontalLayout_2.addWidget(self.model_dropdown)

        self.thinking_checkbox = QCheckBox(self.footer_container)
        self.thinking_checkbox.setObjectName(u"thinking_checkbox")
        sizePolicy4.setHeightForWidth(self.thinking_checkbox.sizePolicy().hasHeightForWidth())
        self.thinking_checkbox.setSizePolicy(sizePolicy4)
        self.thinking_checkbox.setMinimumSize(QSize(0, 30))
        self.thinking_checkbox.setChecked(True)

        self.horizontalLayout_2.addWidget(self.thinking_checkbox)

        self.precision_dropdown = QComboBox(self.footer_container)
        self.precision_dropdown.setObjectName(u"precision_dropdown")
        sizePolicy4.setHeightForWidth(self.precision_dropdown.sizePolicy().hasHeightForWidth())
        self.precision_dropdown.setSizePolicy(sizePolicy4)
        self.precision_dropdown.setMinimumSize(QSize(80, 30))
        self.precision_dropdown.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)

        self.horizontalLayout_2.addWidget(self.precision_dropdown)

        self.footer_spacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_2.addItem(self.footer_spacer)

        self.send_button = QPushButton(self.footer_container)
        self.send_button.setObjectName(u"send_button")
        sizePolicy2.setHeightForWidth(self.send_button.sizePolicy().hasHeightForWidth())
        self.send_button.setSizePolicy(sizePolicy2)
        self.send_button.setMinimumSize(QSize(30, 30))
        self.send_button.setMaximumSize(QSize(30, 30))
        icon4 = QIcon()
        icon4.addFile(u":/light/icons/feather/light/chevron-up.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.send_button.setIcon(icon4)

        self.horizontalLayout_2.addWidget(self.send_button)

        self.stop_button = QPushButton(self.footer_container)
        self.stop_button.setObjectName(u"stop_button")
        sizePolicy2.setHeightForWidth(self.stop_button.sizePolicy().hasHeightForWidth())
        self.stop_button.setSizePolicy(sizePolicy2)
        self.stop_button.setMinimumSize(QSize(30, 30))
        self.stop_button.setMaximumSize(QSize(30, 30))
        icon5 = QIcon()
        icon5.addFile(u":/light/icons/feather/light/stop-circle.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.stop_button.setIcon(icon5)

        self.horizontalLayout_2.addWidget(self.stop_button)


        self.horizontalLayout.addWidget(self.footer_container)


        self.gridLayout_2.addWidget(self.chat_prompt_footer, 3, 0, 1, 1)

        self.progress_container = QWidget(chat_prompt)
        self.progress_container.setObjectName(u"progress_container")
        self.progress_layout = QHBoxLayout(self.progress_container)
        self.progress_layout.setSpacing(0)
        self.progress_layout.setObjectName(u"progress_layout")
        self.progress_layout.setContentsMargins(10, 0, 10, 10)
        self.progressBar = QProgressBar(self.progress_container)
        self.progressBar.setObjectName(u"progressBar")
        sizePolicy5.setHeightForWidth(self.progressBar.sizePolicy().hasHeightForWidth())
        self.progressBar.setSizePolicy(sizePolicy5)
        self.progressBar.setMinimumSize(QSize(0, 8))
        self.progressBar.setMaximumSize(QSize(16777215, 8))
        self.progressBar.setValue(0)
        self.progressBar.setTextVisible(False)

        self.progress_layout.addWidget(self.progressBar)


        self.gridLayout_2.addWidget(self.progress_container, 4, 0, 1, 1)


        self.retranslateUi(chat_prompt)
        self.provider_dropdown.currentIndexChanged.connect(chat_prompt.on_provider_changed)
        self.model_dropdown.currentIndexChanged.connect(chat_prompt.on_model_changed)
        self.prompt.textChanged.connect(chat_prompt.prompt_text_changed)
        self.thinking_checkbox.toggled.connect(chat_prompt.thinking_toggled)
        self.precision_dropdown.currentIndexChanged.connect(chat_prompt.on_precision_changed)

        self.tabWidget.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(chat_prompt)
    # setupUi

    def retranslateUi(self, chat_prompt):
        chat_prompt.setWindowTitle(QCoreApplication.translate("chat_prompt", u"Form", None))
#if QT_CONFIG(tooltip)
        self.clear_conversation_button.setToolTip(QCoreApplication.translate("chat_prompt", u"New converation", None))
#endif // QT_CONFIG(tooltip)
        self.clear_conversation_button.setText("")
#if QT_CONFIG(tooltip)
        self.history_button.setToolTip(QCoreApplication.translate("chat_prompt", u"Chat history", None))
#endif // QT_CONFIG(tooltip)
        self.history_button.setText("")
#if QT_CONFIG(tooltip)
        self.settings_button.setToolTip(QCoreApplication.translate("chat_prompt", u"Settings", None))
#endif // QT_CONFIG(tooltip)
        self.settings_button.setText("")
        self.token_count.setText(QCoreApplication.translate("chat_prompt", u"~0 tokens", None))
#if QT_CONFIG(tooltip)
        self.attach_button.setToolTip(QCoreApplication.translate("chat_prompt", u"Attach image (vision-capable models only)", None))
#endif // QT_CONFIG(tooltip)
        self.attach_button.setText("")
        self.last_message_tokens.setText("")
        self.total_tokens.setText("")
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab), QCoreApplication.translate("chat_prompt", u"Tab 1", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_2), QCoreApplication.translate("chat_prompt", u"Tab 2", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_3), QCoreApplication.translate("chat_prompt", u"Page", None))
#if QT_CONFIG(tooltip)
        self.provider_dropdown.setToolTip(QCoreApplication.translate("chat_prompt", u"Select LLM provider", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(tooltip)
        self.model_dropdown.setToolTip(QCoreApplication.translate("chat_prompt", u"Select LLM model", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(tooltip)
        self.thinking_checkbox.setToolTip(QCoreApplication.translate("chat_prompt", u"Enable thinking mode (Qwen3). When enabled, the model will reason step-by-step before responding. Slower but more thoughtful responses.", None))
#endif // QT_CONFIG(tooltip)
        self.thinking_checkbox.setText(QCoreApplication.translate("chat_prompt", u"Thinking", None))
#if QT_CONFIG(tooltip)
        self.precision_dropdown.setToolTip(QCoreApplication.translate("chat_prompt", u"Model precision/quantization. Lower precision uses less memory but may reduce quality.", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(tooltip)
        self.send_button.setToolTip(QCoreApplication.translate("chat_prompt", u"Send message", None))
#endif // QT_CONFIG(tooltip)
        self.send_button.setText("")
#if QT_CONFIG(tooltip)
        self.stop_button.setToolTip(QCoreApplication.translate("chat_prompt", u"Cancel message", None))
#endif // QT_CONFIG(tooltip)
        self.stop_button.setText("")
    # retranslateUi

