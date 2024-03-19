# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'prompt_browser_prompt_widget.ui'
##
## Created by: Qt User Interface Compiler version 6.6.2
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
    QPlainTextEdit, QPushButton, QSizePolicy, QVBoxLayout,
    QWidget)

class Ui_prompt_widget(object):
    def setupUi(self, prompt_widget):
        if not prompt_widget.objectName():
            prompt_widget.setObjectName(u"prompt_widget")
        prompt_widget.resize(616, 257)
        self.gridLayout = QGridLayout(prompt_widget)
        self.gridLayout.setObjectName(u"gridLayout")
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.load_button = QPushButton(prompt_widget)
        self.load_button.setObjectName(u"load_button")
        font = QFont()
        font.setPointSize(9)
        self.load_button.setFont(font)

        self.horizontalLayout.addWidget(self.load_button)

        self.delete_button = QPushButton(prompt_widget)
        self.delete_button.setObjectName(u"delete_button")
        self.delete_button.setFont(font)

        self.horizontalLayout.addWidget(self.delete_button)


        self.gridLayout.addLayout(self.horizontalLayout, 1, 0, 1, 2)

        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.label = QLabel(prompt_widget)
        self.label.setObjectName(u"label")
        font1 = QFont()
        font1.setPointSize(9)
        font1.setBold(True)
        self.label.setFont(font1)

        self.verticalLayout.addWidget(self.label)

        self.prompt = QPlainTextEdit(prompt_widget)
        self.prompt.setObjectName(u"prompt")
        self.prompt.setFont(font)

        self.verticalLayout.addWidget(self.prompt)

        self.verticalLayout_2 = QVBoxLayout()
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.label_3 = QLabel(prompt_widget)
        self.label_3.setObjectName(u"label_3")
        self.label_3.setFont(font1)

        self.verticalLayout_2.addWidget(self.label_3)

        self.negative_prompt = QPlainTextEdit(prompt_widget)
        self.negative_prompt.setObjectName(u"negative_prompt")
        self.negative_prompt.setFont(font)

        self.verticalLayout_2.addWidget(self.negative_prompt)


        self.verticalLayout.addLayout(self.verticalLayout_2)


        self.gridLayout.addLayout(self.verticalLayout, 0, 0, 1, 2)


        self.retranslateUi(prompt_widget)
        self.load_button.clicked.connect(prompt_widget.action_clicked_button_load)
        self.delete_button.clicked.connect(prompt_widget.action_clicked_button_delete)
        self.prompt.textChanged.connect(prompt_widget.action_text_changed_prompt)
        self.negative_prompt.textChanged.connect(prompt_widget.action_text_changed_negative_prompt)

        QMetaObject.connectSlotsByName(prompt_widget)
    # setupUi

    def retranslateUi(self, prompt_widget):
        prompt_widget.setWindowTitle(QCoreApplication.translate("prompt_widget", u"Form", None))
        self.load_button.setText(QCoreApplication.translate("prompt_widget", u"Load", None))
        self.delete_button.setText(QCoreApplication.translate("prompt_widget", u"Delete", None))
        self.label.setText(QCoreApplication.translate("prompt_widget", u"Prompt", None))
        self.label_3.setText(QCoreApplication.translate("prompt_widget", u"Negative Prompt", None))
    # retranslateUi

