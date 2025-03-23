# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'prompt_container.ui'
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
from PySide6.QtWidgets import (QApplication, QGridLayout, QHBoxLayout, QPlainTextEdit,
    QPushButton, QSizePolicy, QSpacerItem, QWidget)

class Ui_prompt_container_widget(object):
    def setupUi(self, prompt_container_widget):
        if not prompt_container_widget.objectName():
            prompt_container_widget.setObjectName(u"prompt_container_widget")
        prompt_container_widget.resize(433, 316)
        self.gridLayout = QGridLayout(prompt_container_widget)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.prompt = QPlainTextEdit(prompt_container_widget)
        self.prompt.setObjectName(u"prompt")

        self.horizontalLayout.addWidget(self.prompt)

        self.secondary_prompt = QPlainTextEdit(prompt_container_widget)
        self.secondary_prompt.setObjectName(u"secondary_prompt")

        self.horizontalLayout.addWidget(self.secondary_prompt)


        self.gridLayout.addLayout(self.horizontalLayout, 0, 0, 1, 2)

        self.pushButton = QPushButton(prompt_container_widget)
        self.pushButton.setObjectName(u"pushButton")
        icon = QIcon(QIcon.fromTheme(u"user-trash"))
        self.pushButton.setIcon(icon)

        self.gridLayout.addWidget(self.pushButton, 1, 0, 1, 1)

        self.horizontalSpacer = QSpacerItem(396, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.gridLayout.addItem(self.horizontalSpacer, 1, 1, 1, 1)


        self.retranslateUi(prompt_container_widget)
        self.pushButton.clicked.connect(prompt_container_widget.handle_delete_prompt_clicked)

        QMetaObject.connectSlotsByName(prompt_container_widget)
    # setupUi

    def retranslateUi(self, prompt_container_widget):
        prompt_container_widget.setWindowTitle(QCoreApplication.translate("prompt_container_widget", u"Form", None))
        self.prompt.setPlaceholderText(QCoreApplication.translate("prompt_container_widget", u"Enter prompt", None))
        self.secondary_prompt.setPlaceholderText(QCoreApplication.translate("prompt_container_widget", u"Enter optional second prompt", None))
        self.pushButton.setText("")
    # retranslateUi

