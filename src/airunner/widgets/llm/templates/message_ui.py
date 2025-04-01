# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'message.ui'
##
## Created by: Qt User Interface Compiler version 6.7.0
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
from PySide6.QtWidgets import (QApplication, QGridLayout, QHBoxLayout, QLabel,
    QPushButton, QSizePolicy, QSpacerItem, QTextEdit,
    QWidget)
import airunner.feather_rc

class Ui_message(object):
    def setupUi(self, message):
        if not message.objectName():
            message.setObjectName(u"message")
        message.resize(497, 456)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(message.sizePolicy().hasHeightForWidth())
        message.setSizePolicy(sizePolicy)
        message.setMinimumSize(QSize(0, 0))
        message.setStyleSheet(u"")
        self.gridLayout_2 = QGridLayout(message)
        self.gridLayout_2.setSpacing(0)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.gridLayout_2.setContentsMargins(0, 0, 0, 0)
        self.message_container = QWidget(message)
        self.message_container.setObjectName(u"message_container")
        self.gridLayout = QGridLayout(self.message_container)
        self.gridLayout.setSpacing(0)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setContentsMargins(10, 10, 10, 10)
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setSpacing(5)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.user_name = QLabel(self.message_container)
        self.user_name.setObjectName(u"user_name")
        self.user_name.setMinimumSize(QSize(0, 25))

        self.horizontalLayout.addWidget(self.user_name)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer)

        self.copy_button = QPushButton(self.message_container)
        self.copy_button.setObjectName(u"copy_button")
        icon = QIcon()
        icon.addFile(u":/light/icons/feather/light/copy.svg", QSize(), QIcon.Normal, QIcon.Off)
        self.copy_button.setIcon(icon)

        self.horizontalLayout.addWidget(self.copy_button)

        self.delete_button = QPushButton(self.message_container)
        self.delete_button.setObjectName(u"delete_button")
        icon1 = QIcon()
        icon1.addFile(u":/light/icons/feather/light/x-circle.svg", QSize(), QIcon.Normal, QIcon.Off)
        self.delete_button.setIcon(icon1)

        self.horizontalLayout.addWidget(self.delete_button)


        self.gridLayout.addLayout(self.horizontalLayout, 0, 0, 1, 1)

        self.content = QTextEdit(self.message_container)
        self.content.setObjectName(u"content")
        self.content.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.content.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.gridLayout.addWidget(self.content, 1, 0, 1, 1)


        self.gridLayout_2.addWidget(self.message_container, 0, 0, 1, 1)


        self.retranslateUi(message)
        self.delete_button.clicked.connect(message.delete)
        self.copy_button.clicked.connect(message.copy)

        QMetaObject.connectSlotsByName(message)
    # setupUi

    def retranslateUi(self, message):
        message.setWindowTitle(QCoreApplication.translate("message", u"Form", None))
        self.user_name.setText(QCoreApplication.translate("message", u"TextLabel", None))
#if QT_CONFIG(tooltip)
        self.copy_button.setToolTip(QCoreApplication.translate("message", u"Copy message", None))
#endif // QT_CONFIG(tooltip)
        self.copy_button.setText("")
#if QT_CONFIG(tooltip)
        self.delete_button.setToolTip(QCoreApplication.translate("message", u"Delete message", None))
#endif // QT_CONFIG(tooltip)
        self.delete_button.setText("")
    # retranslateUi

