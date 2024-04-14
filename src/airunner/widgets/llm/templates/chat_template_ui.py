# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'chat_template.ui'
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
from PySide6.QtWidgets import (QApplication, QComboBox, QGridLayout, QGroupBox,
    QHBoxLayout, QLineEdit, QPlainTextEdit, QPushButton,
    QSizePolicy, QWidget)

class Ui_Form(object):
    def setupUi(self, Form):
        if not Form.objectName():
            Form.setObjectName(u"Form")
        Form.resize(574, 640)
        self.gridLayout_3 = QGridLayout(Form)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.groupBox = QGroupBox(Form)
        self.groupBox.setObjectName(u"groupBox")
        self.gridLayout_2 = QGridLayout(self.groupBox)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.user_name = QLineEdit(self.groupBox)
        self.user_name.setObjectName(u"user_name")

        self.gridLayout_2.addWidget(self.user_name, 0, 0, 1, 1)


        self.gridLayout_3.addWidget(self.groupBox, 5, 0, 1, 1)

        self.groupBox_5 = QGroupBox(Form)
        self.groupBox_5.setObjectName(u"groupBox_5")
        self.gridLayout_6 = QGridLayout(self.groupBox_5)
        self.gridLayout_6.setObjectName(u"gridLayout_6")
        self.template_name = QLineEdit(self.groupBox_5)
        self.template_name.setObjectName(u"template_name")

        self.gridLayout_6.addWidget(self.template_name, 0, 0, 1, 1)


        self.gridLayout_3.addWidget(self.groupBox_5, 4, 0, 1, 1)

        self.groupBox_4 = QGroupBox(Form)
        self.groupBox_4.setObjectName(u"groupBox_4")
        self.gridLayout_5 = QGridLayout(self.groupBox_4)
        self.gridLayout_5.setObjectName(u"gridLayout_5")
        self.bot_name = QLineEdit(self.groupBox_4)
        self.bot_name.setObjectName(u"bot_name")

        self.gridLayout_5.addWidget(self.bot_name, 0, 0, 1, 1)


        self.gridLayout_3.addWidget(self.groupBox_4, 6, 0, 1, 1)

        self.groupBox_3 = QGroupBox(Form)
        self.groupBox_3.setObjectName(u"groupBox_3")
        self.groupBox_3.setCheckable(True)
        self.gridLayout_4 = QGridLayout(self.groupBox_3)
        self.gridLayout_4.setObjectName(u"gridLayout_4")
        self.guardrails = QPlainTextEdit(self.groupBox_3)
        self.guardrails.setObjectName(u"guardrails")

        self.gridLayout_4.addWidget(self.guardrails, 0, 0, 1, 1)


        self.gridLayout_3.addWidget(self.groupBox_3, 7, 0, 1, 1)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.template_names = QComboBox(Form)
        self.template_names.setObjectName(u"template_names")

        self.horizontalLayout.addWidget(self.template_names)

        self.add_template_button = QPushButton(Form)
        self.add_template_button.setObjectName(u"add_template_button")
        icon = QIcon(QIcon.fromTheme(u"list-add"))
        self.add_template_button.setIcon(icon)

        self.horizontalLayout.addWidget(self.add_template_button)


        self.gridLayout_3.addLayout(self.horizontalLayout, 0, 0, 1, 1)

        self.groupBox_2 = QGroupBox(Form)
        self.groupBox_2.setObjectName(u"groupBox_2")
        self.gridLayout = QGridLayout(self.groupBox_2)
        self.gridLayout.setObjectName(u"gridLayout")
        self.instructions = QPlainTextEdit(self.groupBox_2)
        self.instructions.setObjectName(u"instructions")

        self.gridLayout.addWidget(self.instructions, 0, 0, 1, 1)


        self.gridLayout_3.addWidget(self.groupBox_2, 8, 0, 1, 1)


        self.retranslateUi(Form)
        self.add_template_button.clicked.connect(Form.add_template)
        self.template_name.textChanged.connect(Form.template_name_changed)
        self.user_name.textChanged.connect(Form.user_name_changed)
        self.bot_name.textChanged.connect(Form.bot_name_changed)
        self.guardrails.textChanged.connect(Form.guardrails_changed)
        self.instructions.textChanged.connect(Form.instructions_changed)

        QMetaObject.connectSlotsByName(Form)
    # setupUi

    def retranslateUi(self, Form):
        Form.setWindowTitle(QCoreApplication.translate("Form", u"Form", None))
        self.groupBox.setTitle(QCoreApplication.translate("Form", u"User name", None))
        self.groupBox_5.setTitle(QCoreApplication.translate("Form", u"Template name", None))
        self.groupBox_4.setTitle(QCoreApplication.translate("Form", u"Bot name", None))
#if QT_CONFIG(tooltip)
        self.groupBox_3.setToolTip(QCoreApplication.translate("Form", u"Toggle guardrails", None))
#endif // QT_CONFIG(tooltip)
        self.groupBox_3.setTitle(QCoreApplication.translate("Form", u"Guardrails", None))
        self.add_template_button.setText("")
        self.groupBox_2.setTitle(QCoreApplication.translate("Form", u"Instructions", None))
    # retranslateUi

