# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'message.ui'
##
## Created by: Qt User Interface Compiler version 6.9.0
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (
    QCoreApplication,
    QDate,
    QDateTime,
    QLocale,
    QMetaObject,
    QObject,
    QPoint,
    QRect,
    QSize,
    QTime,
    QUrl,
    Qt,
)
from PySide6.QtGui import (
    QBrush,
    QColor,
    QConicalGradient,
    QCursor,
    QFont,
    QFontDatabase,
    QGradient,
    QIcon,
    QImage,
    QKeySequence,
    QLinearGradient,
    QPainter,
    QPalette,
    QPixmap,
    QRadialGradient,
    QTransform,
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QWidget,
)
import airunner.feather_rc


class Ui_message(object):
    def setupUi(self, message):
        if not message.objectName():
            message.setObjectName("message")
        message.resize(497, 456)
        sizePolicy = QSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(message.sizePolicy().hasHeightForWidth())
        message.setSizePolicy(sizePolicy)
        message.setMinimumSize(QSize(0, 0))
        message.setStyleSheet("")
        self.gridLayout_2 = QGridLayout(message)
        self.gridLayout_2.setSpacing(0)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.gridLayout_2.setContentsMargins(0, 0, 0, 0)
        self.message_container = QWidget(message)
        self.message_container.setObjectName("message_container")
        self.gridLayout = QGridLayout(self.message_container)
        self.gridLayout.setSpacing(0)
        self.gridLayout.setObjectName("gridLayout")
        self.gridLayout.setContentsMargins(10, 10, 10, 10)
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setSpacing(2)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.user_name = QLabel(self.message_container)
        self.user_name.setObjectName("user_name")
        self.user_name.setMinimumSize(QSize(0, 25))

        self.horizontalLayout.addWidget(self.user_name)

        self.horizontalSpacer = QSpacerItem(
            40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )

        self.horizontalLayout.addItem(self.horizontalSpacer)

        self.play_audio_button = QPushButton(self.message_container)
        self.play_audio_button.setObjectName("play_audio_button")
        icon = QIcon()
        icon.addFile(
            ":/light/icons/feather/light/play.svg",
            QSize(),
            QIcon.Mode.Normal,
            QIcon.State.Off,
        )
        self.play_audio_button.setIcon(icon)

        self.horizontalLayout.addWidget(self.play_audio_button)

        self.copy_button = QPushButton(self.message_container)
        self.copy_button.setObjectName("copy_button")
        icon1 = QIcon()
        icon1.addFile(
            ":/light/icons/feather/light/copy.svg",
            QSize(),
            QIcon.Mode.Normal,
            QIcon.State.Off,
        )
        self.copy_button.setIcon(icon1)

        self.horizontalLayout.addWidget(self.copy_button)

        self.delete_button = QPushButton(self.message_container)
        self.delete_button.setObjectName("delete_button")
        icon2 = QIcon()
        icon2.addFile(
            ":/light/icons/feather/light/x-circle.svg",
            QSize(),
            QIcon.Mode.Normal,
            QIcon.State.Off,
        )
        self.delete_button.setIcon(icon2)

        self.horizontalLayout.addWidget(self.delete_button)

        self.gridLayout.addLayout(self.horizontalLayout, 0, 0, 1, 1)

        self.content_container = QFrame(self.message_container)
        self.content_container.setObjectName("content_container")
        sizePolicy1 = QSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(
            self.content_container.sizePolicy().hasHeightForWidth()
        )
        self.content_container.setSizePolicy(sizePolicy1)
        self.content_container.setFrameShape(QFrame.StyledPanel)
        self.content_container.setFrameShadow(QFrame.Raised)

        self.gridLayout.addWidget(self.content_container, 1, 0, 1, 1)

        self.image_content = QLabel(self.message_container)
        self.image_content.setObjectName("image_content")
        self.image_content.setVisible(False)
        self.image_content.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.gridLayout.addWidget(self.image_content, 2, 0, 1, 1)

        self.gridLayout_2.addWidget(self.message_container, 0, 0, 1, 1)

        self.retranslateUi(message)
        self.delete_button.clicked.connect(message.delete)
        self.copy_button.clicked.connect(message.copy)

        QMetaObject.connectSlotsByName(message)

    # setupUi

    def retranslateUi(self, message):
        message.setWindowTitle(QCoreApplication.translate("message", "Form", None))
        # if QT_CONFIG(tooltip)
        message.setToolTip(
            QCoreApplication.translate("message", "Copy message text", None)
        )
        # endif // QT_CONFIG(tooltip)
        self.user_name.setText(QCoreApplication.translate("message", "TextLabel", None))
        # if QT_CONFIG(tooltip)
        self.play_audio_button.setToolTip(
            QCoreApplication.translate("message", "Play message audio", None)
        )
        # endif // QT_CONFIG(tooltip)
        self.play_audio_button.setText("")
        # if QT_CONFIG(tooltip)
        self.copy_button.setToolTip(
            QCoreApplication.translate("message", "Copy message", None)
        )
        # endif // QT_CONFIG(tooltip)
        self.copy_button.setText("")
        # if QT_CONFIG(tooltip)
        self.delete_button.setToolTip(
            QCoreApplication.translate("message", "Delete message", None)
        )
        # endif // QT_CONFIG(tooltip)
        self.delete_button.setText("")

    # retranslateUi
