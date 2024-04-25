# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'nullscream.ui'
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
from PySide6.QtWidgets import (QApplication, QFrame, QGridLayout, QGroupBox,
    QLabel, QLineEdit, QSizePolicy, QSplitter,
    QTextEdit, QWidget)

class Ui_nullscream(object):
    def setupUi(self, nullscream):
        if not nullscream.objectName():
            nullscream.setObjectName(u"nullscream")
        nullscream.resize(459, 644)
        self.gridLayout_3 = QGridLayout(nullscream)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.label = QLabel(nullscream)
        self.label.setObjectName(u"label")
        font = QFont()
        font.setBold(True)
        self.label.setFont(font)

        self.gridLayout_3.addWidget(self.label, 0, 0, 1, 1)

        self.line = QFrame(nullscream)
        self.line.setObjectName(u"line")
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout_3.addWidget(self.line, 1, 0, 1, 1)

        self.splitter = QSplitter(nullscream)
        self.splitter.setObjectName(u"splitter")
        self.splitter.setOrientation(Qt.Orientation.Vertical)
        self.groupBox = QGroupBox(self.splitter)
        self.groupBox.setObjectName(u"groupBox")
        self.gridLayout = QGridLayout(self.groupBox)
        self.gridLayout.setObjectName(u"gridLayout")
        self.blocked = QTextEdit(self.groupBox)
        self.blocked.setObjectName(u"blocked")

        self.gridLayout.addWidget(self.blocked, 1, 0, 1, 1)

        self.lineEdit_2 = QLineEdit(self.groupBox)
        self.lineEdit_2.setObjectName(u"lineEdit_2")

        self.gridLayout.addWidget(self.lineEdit_2, 0, 0, 1, 1)

        self.splitter.addWidget(self.groupBox)
        self.groupBox_2 = QGroupBox(self.splitter)
        self.groupBox_2.setObjectName(u"groupBox_2")
        self.gridLayout_2 = QGridLayout(self.groupBox_2)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.allowed = QTextEdit(self.groupBox_2)
        self.allowed.setObjectName(u"allowed")

        self.gridLayout_2.addWidget(self.allowed, 1, 0, 1, 1)

        self.lineEdit = QLineEdit(self.groupBox_2)
        self.lineEdit.setObjectName(u"lineEdit")

        self.gridLayout_2.addWidget(self.lineEdit, 0, 0, 1, 1)

        self.splitter.addWidget(self.groupBox_2)

        self.gridLayout_3.addWidget(self.splitter, 2, 0, 1, 1)


        self.retranslateUi(nullscream)
        self.lineEdit_2.textEdited.connect(nullscream.filter_blocked)
        self.lineEdit.textChanged.connect(nullscream.filter_allowed)

        QMetaObject.connectSlotsByName(nullscream)
    # setupUi

    def retranslateUi(self, nullscream):
        nullscream.setWindowTitle(QCoreApplication.translate("nullscream", u"Form", None))
        self.label.setText(QCoreApplication.translate("nullscream", u"NULLSCREAM", None))
        self.groupBox.setTitle(QCoreApplication.translate("nullscream", u"Blocked", None))
        self.groupBox_2.setTitle(QCoreApplication.translate("nullscream", u"Allowed", None))
    # retranslateUi

