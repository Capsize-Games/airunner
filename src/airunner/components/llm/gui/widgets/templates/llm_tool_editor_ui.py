# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'llm_tool_editor.ui'
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
from PySide6.QtWidgets import (QAbstractButton, QApplication, QCheckBox, QDialog,
    QDialogButtonBox, QFormLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QSizePolicy, QSpacerItem,
    QTextEdit, QVBoxLayout, QWidget)

class Ui_llm_tool_editor(object):
    def setupUi(self, llm_tool_editor):
        if not llm_tool_editor.objectName():
            llm_tool_editor.setObjectName(u"llm_tool_editor")
        llm_tool_editor.resize(900, 700)
        self.verticalLayout = QVBoxLayout(llm_tool_editor)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.title_label = QLabel(llm_tool_editor)
        self.title_label.setObjectName(u"title_label")

        self.verticalLayout.addWidget(self.title_label)

        self.formLayout = QFormLayout()
        self.formLayout.setObjectName(u"formLayout")
        self.name_label = QLabel(llm_tool_editor)
        self.name_label.setObjectName(u"name_label")

        self.formLayout.setWidget(0, QFormLayout.ItemRole.LabelRole, self.name_label)

        self.name_input = QLineEdit(llm_tool_editor)
        self.name_input.setObjectName(u"name_input")

        self.formLayout.setWidget(0, QFormLayout.ItemRole.FieldRole, self.name_input)

        self.display_name_label = QLabel(llm_tool_editor)
        self.display_name_label.setObjectName(u"display_name_label")

        self.formLayout.setWidget(1, QFormLayout.ItemRole.LabelRole, self.display_name_label)

        self.display_name_input = QLineEdit(llm_tool_editor)
        self.display_name_input.setObjectName(u"display_name_input")

        self.formLayout.setWidget(1, QFormLayout.ItemRole.FieldRole, self.display_name_input)

        self.description_label = QLabel(llm_tool_editor)
        self.description_label.setObjectName(u"description_label")

        self.formLayout.setWidget(2, QFormLayout.ItemRole.LabelRole, self.description_label)

        self.description_input = QTextEdit(llm_tool_editor)
        self.description_input.setObjectName(u"description_input")
        self.description_input.setMaximumSize(QSize(16777215, 80))

        self.formLayout.setWidget(2, QFormLayout.ItemRole.FieldRole, self.description_input)

        self.code_label = QLabel(llm_tool_editor)
        self.code_label.setObjectName(u"code_label")

        self.formLayout.setWidget(3, QFormLayout.ItemRole.LabelRole, self.code_label)

        self.code_input = QTextEdit(llm_tool_editor)
        self.code_input.setObjectName(u"code_input")
        font = QFont()
        font.setFamilies([u"Monospace"])
        self.code_input.setFont(font)

        self.formLayout.setWidget(3, QFormLayout.ItemRole.FieldRole, self.code_input)

        self.enabled_checkbox = QCheckBox(llm_tool_editor)
        self.enabled_checkbox.setObjectName(u"enabled_checkbox")
        self.enabled_checkbox.setChecked(True)

        self.formLayout.setWidget(4, QFormLayout.ItemRole.FieldRole, self.enabled_checkbox)


        self.verticalLayout.addLayout(self.formLayout)

        self.info_layout = QHBoxLayout()
        self.info_layout.setObjectName(u"info_layout")
        self.safety_label = QLabel(llm_tool_editor)
        self.safety_label.setObjectName(u"safety_label")

        self.info_layout.addWidget(self.safety_label)

        self.horizontalSpacer = QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.info_layout.addItem(self.horizontalSpacer)

        self.validate_button = QPushButton(llm_tool_editor)
        self.validate_button.setObjectName(u"validate_button")

        self.info_layout.addWidget(self.validate_button)


        self.verticalLayout.addLayout(self.info_layout)

        self.buttonBox = QDialogButtonBox(llm_tool_editor)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setStandardButtons(QDialogButtonBox.Cancel|QDialogButtonBox.Save)

        self.verticalLayout.addWidget(self.buttonBox)


        self.retranslateUi(llm_tool_editor)
        self.buttonBox.accepted.connect(llm_tool_editor.accept)
        self.buttonBox.rejected.connect(llm_tool_editor.reject)
        self.validate_button.clicked.connect(llm_tool_editor.on_validate_clicked)

        QMetaObject.connectSlotsByName(llm_tool_editor)
    # setupUi

    def retranslateUi(self, llm_tool_editor):
        llm_tool_editor.setWindowTitle(QCoreApplication.translate("llm_tool_editor", u"LLM Tool Editor", None))
        self.title_label.setText(QCoreApplication.translate("llm_tool_editor", u"Tool Editor", None))
        self.title_label.setStyleSheet(QCoreApplication.translate("llm_tool_editor", u"font-size: 16px; font-weight: bold;", None))
        self.name_label.setText(QCoreApplication.translate("llm_tool_editor", u"Tool Name:", None))
        self.name_input.setPlaceholderText(QCoreApplication.translate("llm_tool_editor", u"e.g., calculate_fibonacci", None))
        self.display_name_label.setText(QCoreApplication.translate("llm_tool_editor", u"Display Name:", None))
        self.display_name_input.setPlaceholderText(QCoreApplication.translate("llm_tool_editor", u"e.g., Calculate Fibonacci", None))
        self.description_label.setText(QCoreApplication.translate("llm_tool_editor", u"Description:", None))
        self.description_input.setPlaceholderText(QCoreApplication.translate("llm_tool_editor", u"What does this tool do? Be clear and concise.", None))
        self.code_label.setText(QCoreApplication.translate("llm_tool_editor", u"Python Code:", None))
        self.code_input.setPlaceholderText(QCoreApplication.translate("llm_tool_editor", u"@tool\n"
"def my_tool(param: str) -> str:\n"
"    \"\"\"Tool description.\"\"\"\n"
"    # Your code here\n"
"    return result", None))
        self.enabled_checkbox.setText(QCoreApplication.translate("llm_tool_editor", u"Enabled", None))
        self.safety_label.setText(QCoreApplication.translate("llm_tool_editor", u"\u26a0\ufe0f Safety Check: Not Run", None))
        self.validate_button.setText(QCoreApplication.translate("llm_tool_editor", u"Validate Code", None))
    # retranslateUi

