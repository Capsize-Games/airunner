# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'prompt_templates.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QGridLayout,
    QGroupBox, QHBoxLayout, QPlainTextEdit, QPushButton,
    QSizePolicy, QSpacerItem, QWidget)

class Ui_prompt_templates_widget(object):
    def setupUi(self, prompt_templates_widget):
        if not prompt_templates_widget.objectName():
            prompt_templates_widget.setObjectName(u"prompt_templates_widget")
        prompt_templates_widget.resize(582, 459)
        self.gridLayout = QGridLayout(prompt_templates_widget)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setHorizontalSpacing(0)
        self.gridLayout.setVerticalSpacing(10)
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.groupBox_2 = QGroupBox(prompt_templates_widget)
        self.groupBox_2.setObjectName(u"groupBox_2")
        self.gridLayout_3 = QGridLayout(self.groupBox_2)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.gridLayout_3.setHorizontalSpacing(0)
        self.gridLayout_3.setVerticalSpacing(10)
        self.gridLayout_3.setContentsMargins(10, 10, 10, 10)
        self.system_prompt = QPlainTextEdit(self.groupBox_2)
        self.system_prompt.setObjectName(u"system_prompt")

        self.gridLayout_3.addWidget(self.system_prompt, 0, 0, 1, 1)

        self.pushButton_2 = QPushButton(self.groupBox_2)
        self.pushButton_2.setObjectName(u"pushButton_2")

        self.gridLayout_3.addWidget(self.pushButton_2, 1, 0, 1, 1)


        self.gridLayout.addWidget(self.groupBox_2, 1, 0, 1, 1)

        self.groupBox = QGroupBox(prompt_templates_widget)
        self.groupBox.setObjectName(u"groupBox")
        self.gridLayout_2 = QGridLayout(self.groupBox)
        self.gridLayout_2.setSpacing(0)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.gridLayout_2.setContentsMargins(10, 10, 10, 10)
        self.template_name = QComboBox(self.groupBox)
        self.template_name.setObjectName(u"template_name")

        self.gridLayout_2.addWidget(self.template_name, 0, 0, 1, 1)


        self.gridLayout.addWidget(self.groupBox, 0, 0, 1, 1)

        self.groupBox_3 = QGroupBox(prompt_templates_widget)
        self.groupBox_3.setObjectName(u"groupBox_3")
        self.gridLayout_4 = QGridLayout(self.groupBox_3)
        self.gridLayout_4.setObjectName(u"gridLayout_4")
        self.gridLayout_4.setHorizontalSpacing(0)
        self.gridLayout_4.setVerticalSpacing(10)
        self.gridLayout_4.setContentsMargins(10, 10, 10, 10)
        self.guardrails_prompt = QPlainTextEdit(self.groupBox_3)
        self.guardrails_prompt.setObjectName(u"guardrails_prompt")

        self.gridLayout_4.addWidget(self.guardrails_prompt, 0, 0, 1, 1)

        self.pushButton = QPushButton(self.groupBox_3)
        self.pushButton.setObjectName(u"pushButton")

        self.gridLayout_4.addWidget(self.pushButton, 1, 0, 1, 1)


        self.gridLayout.addWidget(self.groupBox_3, 2, 0, 1, 1)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer)

        self.use_guardrails = QCheckBox(prompt_templates_widget)
        self.use_guardrails.setObjectName(u"use_guardrails")

        self.horizontalLayout.addWidget(self.use_guardrails)

        self.use_datetime = QCheckBox(prompt_templates_widget)
        self.use_datetime.setObjectName(u"use_datetime")

        self.horizontalLayout.addWidget(self.use_datetime)


        self.gridLayout.addLayout(self.horizontalLayout, 3, 0, 1, 1)


        self.retranslateUi(prompt_templates_widget)
        self.system_prompt.textChanged.connect(prompt_templates_widget.system_prompt_changed)
        self.guardrails_prompt.textChanged.connect(prompt_templates_widget.guardrails_prompt_changed)
        self.use_guardrails.toggled.connect(prompt_templates_widget.toggle_use_guardrails)
        self.use_datetime.toggled.connect(prompt_templates_widget.toggle_use_datetime)
        self.template_name.currentIndexChanged.connect(prompt_templates_widget.template_changed)
        self.pushButton_2.clicked.connect(prompt_templates_widget.reset_system_prompt)
        self.pushButton.clicked.connect(prompt_templates_widget.reset_guardrails_prompt)

        QMetaObject.connectSlotsByName(prompt_templates_widget)
    # setupUi

    def retranslateUi(self, prompt_templates_widget):
        prompt_templates_widget.setWindowTitle(QCoreApplication.translate("prompt_templates_widget", u"Form", None))
        self.groupBox_2.setTitle(QCoreApplication.translate("prompt_templates_widget", u"System Prompt", None))
        self.pushButton_2.setText(QCoreApplication.translate("prompt_templates_widget", u"Reset to Default", None))
        self.groupBox.setTitle(QCoreApplication.translate("prompt_templates_widget", u"Template", None))
        self.groupBox_3.setTitle(QCoreApplication.translate("prompt_templates_widget", u"Guardrails Prompt", None))
        self.pushButton.setText(QCoreApplication.translate("prompt_templates_widget", u"Reset to Default", None))
        self.use_guardrails.setText(QCoreApplication.translate("prompt_templates_widget", u"Use guardrails", None))
        self.use_datetime.setText(QCoreApplication.translate("prompt_templates_widget", u"Use datetime", None))
    # retranslateUi

