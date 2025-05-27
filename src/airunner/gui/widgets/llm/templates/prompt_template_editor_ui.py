# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'prompt_template_editor.ui'
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
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QWidget,
)


class Ui_Form(object):
    def setupUi(self, Form):
        if not Form.objectName():
            Form.setObjectName("Form")
        Form.resize(364, 447)
        self.gridLayout = QGridLayout(Form)
        self.gridLayout.setObjectName("gridLayout")
        self.groupBox_3 = QGroupBox(Form)
        self.groupBox_3.setObjectName("groupBox_3")
        self.gridLayout_4 = QGridLayout(self.groupBox_3)
        self.gridLayout_4.setObjectName("gridLayout_4")
        self.system_instructions = QPlainTextEdit(self.groupBox_3)
        self.system_instructions.setObjectName("system_instructions")

        self.gridLayout_4.addWidget(self.system_instructions, 1, 0, 1, 1)

        self.label = QLabel(self.groupBox_3)
        self.label.setObjectName("label")

        self.gridLayout_4.addWidget(self.label, 0, 0, 1, 1)

        self.gridLayout.addWidget(self.groupBox_3, 2, 0, 1, 1)

        self.groupBox = QGroupBox(Form)
        self.groupBox.setObjectName("groupBox")
        self.gridLayout_2 = QGridLayout(self.groupBox)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.llm_category = QComboBox(self.groupBox)
        self.llm_category.setObjectName("llm_category")

        self.gridLayout_2.addWidget(self.llm_category, 0, 0, 1, 1)

        self.gridLayout.addWidget(self.groupBox, 0, 0, 1, 1)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.template_name = QComboBox(Form)
        self.template_name.setObjectName("template_name")

        self.horizontalLayout.addWidget(self.template_name)

        self.pushButton_2 = QPushButton(Form)
        self.pushButton_2.setObjectName("pushButton_2")

        self.horizontalLayout.addWidget(self.pushButton_2)

        self.pushButton_3 = QPushButton(Form)
        self.pushButton_3.setObjectName("pushButton_3")

        self.horizontalLayout.addWidget(self.pushButton_3)

        self.pushButton = QPushButton(Form)
        self.pushButton.setObjectName("pushButton")

        self.horizontalLayout.addWidget(self.pushButton)

        self.gridLayout.addLayout(self.horizontalLayout, 4, 0, 1, 1)

        self.groupBox_2 = QGroupBox(Form)
        self.groupBox_2.setObjectName("groupBox_2")
        self.gridLayout_3 = QGridLayout(self.groupBox_2)
        self.gridLayout_3.setObjectName("gridLayout_3")
        self.template_format = QComboBox(self.groupBox_2)
        self.template_format.setObjectName("template_format")

        self.gridLayout_3.addWidget(self.template_format, 0, 0, 1, 1)

        self.gridLayout.addWidget(self.groupBox_2, 1, 0, 1, 1)

        self.retranslateUi(Form)
        self.llm_category.currentTextChanged.connect(Form.llm_category_changed)
        self.template_format.currentTextChanged.connect(Form.model_changed)
        self.system_instructions.textChanged.connect(Form.system_instructions_changed)
        self.template_name.currentTextChanged.connect(Form.template_name_changed)
        self.pushButton_2.clicked.connect(Form.save_clicked)
        self.pushButton_3.clicked.connect(Form.delete_clicked)
        self.pushButton.clicked.connect(Form.new_clicked)

        QMetaObject.connectSlotsByName(Form)

    # setupUi

    def retranslateUi(self, Form):
        Form.setWindowTitle(QCoreApplication.translate("Form", "Form", None))
        self.groupBox_3.setTitle(
            QCoreApplication.translate("Form", "System Instructions", None)
        )
        self.system_instructions.setPlaceholderText(
            QCoreApplication.translate(
                "Form",
                "EXAMPLE: You are {{ botname }}. You are having a conversation with {{ username }}. {{ username }} is the user and you are the assistant. You should stay in character and respond as {{ botname }}.",
                None,
            )
        )
        self.label.setText(
            QCoreApplication.translate(
                "Form", "Keep the instructions brief, but be descriptive.", None
            )
        )
        self.groupBox.setTitle(QCoreApplication.translate("Form", "LLM Category", None))
        self.pushButton_2.setText(QCoreApplication.translate("Form", "Save", None))
        self.pushButton_3.setText(QCoreApplication.translate("Form", "Delete", None))
        self.pushButton.setText(QCoreApplication.translate("Form", "New", None))
        self.groupBox_2.setTitle(QCoreApplication.translate("Form", "Model", None))

    # retranslateUi
