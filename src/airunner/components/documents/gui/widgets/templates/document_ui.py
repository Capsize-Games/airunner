# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'document.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QGridLayout, QPushButton,
    QSizePolicy, QWidget)
import airunner.feather_rc

class Ui_document_widget(object):
    def setupUi(self, document_widget):
        if not document_widget.objectName():
            document_widget.setObjectName(u"document_widget")
        document_widget.resize(400, 83)
        self.gridLayout = QGridLayout(document_widget)
        self.gridLayout.setObjectName(u"gridLayout")
        self.checkBox = QCheckBox(document_widget)
        self.checkBox.setObjectName(u"checkBox")

        self.gridLayout.addWidget(self.checkBox, 0, 0, 1, 1)

        self.delete_button = QPushButton(document_widget)
        self.delete_button.setObjectName(u"delete_button")
        self.delete_button.setMinimumSize(QSize(30, 30))
        self.delete_button.setMaximumSize(QSize(30, 30))
        icon = QIcon()
        icon.addFile(u":/dark/icons/feather/dark/trash-2.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.delete_button.setIcon(icon)

        self.gridLayout.addWidget(self.delete_button, 0, 1, 1, 1)


        self.retranslateUi(document_widget)

        QMetaObject.connectSlotsByName(document_widget)
    # setupUi

    def retranslateUi(self, document_widget):
        document_widget.setWindowTitle(QCoreApplication.translate("document_widget", u"Form", None))
        self.checkBox.setText(QCoreApplication.translate("document_widget", u"CheckBox", None))
        self.delete_button.setText("")
    # retranslateUi

