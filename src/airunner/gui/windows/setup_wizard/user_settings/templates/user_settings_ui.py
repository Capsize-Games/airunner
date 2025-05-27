# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'user_settings.ui'
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
    QLabel,
    QLineEdit,
    QSizePolicy,
    QSpacerItem,
    QWidget,
)


class Ui_Form(object):
    def setupUi(self, Form):
        if not Form.objectName():
            Form.setObjectName("Form")
        Form.resize(400, 700)
        self.gridLayout = QGridLayout(Form)
        self.gridLayout.setObjectName("gridLayout")
        self.verticalSpacer = QSpacerItem(
            20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding
        )

        self.gridLayout.addItem(self.verticalSpacer, 7, 0, 1, 1)

        self.label_4 = QLabel(Form)
        self.label_4.setObjectName("label_4")

        self.gridLayout.addWidget(self.label_4, 5, 0, 1, 1)

        self.label_2 = QLabel(Form)
        self.label_2.setObjectName("label_2")

        self.gridLayout.addWidget(self.label_2, 1, 0, 1, 1)

        self.comboBox = QComboBox(Form)
        self.comboBox.setObjectName("comboBox")

        self.gridLayout.addWidget(self.comboBox, 4, 0, 1, 1)

        self.lineEdit = QLineEdit(Form)
        self.lineEdit.setObjectName("lineEdit")

        self.gridLayout.addWidget(self.lineEdit, 2, 0, 1, 1)

        self.comboBox_2 = QComboBox(Form)
        self.comboBox_2.setObjectName("comboBox_2")

        self.gridLayout.addWidget(self.comboBox_2, 6, 0, 1, 1)

        self.label_3 = QLabel(Form)
        self.label_3.setObjectName("label_3")

        self.gridLayout.addWidget(self.label_3, 3, 0, 1, 1)

        self.label = QLabel(Form)
        self.label.setObjectName("label")
        font = QFont()
        font.setPointSize(11)
        font.setBold(True)
        self.label.setFont(font)

        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)

        self.retranslateUi(Form)

        QMetaObject.connectSlotsByName(Form)

    # setupUi

    def retranslateUi(self, Form):
        Form.setWindowTitle(QCoreApplication.translate("Form", "Form", None))
        self.label_4.setText(
            QCoreApplication.translate("Form", "Preferred language", None)
        )
        self.label_2.setText(QCoreApplication.translate("Form", "Your name", None))
        self.label_3.setText(QCoreApplication.translate("Form", "Gender", None))
        self.label.setText(QCoreApplication.translate("Form", "About you", None))

    # retranslateUi
