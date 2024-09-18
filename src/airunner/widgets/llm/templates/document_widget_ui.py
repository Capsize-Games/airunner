# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'document_widget.ui'
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
from PySide6.QtWidgets import (QApplication, QGridLayout, QLabel, QPushButton,
    QSizePolicy, QWidget)

class Ui_document_widget(object):
    def setupUi(self, document_widget):
        if not document_widget.objectName():
            document_widget.setObjectName(u"document_widget")
        document_widget.resize(440, 25)
        self.gridLayout = QGridLayout(document_widget)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setHorizontalSpacing(10)
        self.gridLayout.setVerticalSpacing(0)
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.pushButton = QPushButton(document_widget)
        self.pushButton.setObjectName(u"pushButton")
        self.pushButton.setMaximumSize(QSize(80, 16777215))
        icon = QIcon(QIcon.fromTheme(u"user-trash"))
        self.pushButton.setIcon(icon)

        self.gridLayout.addWidget(self.pushButton, 0, 0, 1, 1)

        self.label = QLabel(document_widget)
        self.label.setObjectName(u"label")

        self.gridLayout.addWidget(self.label, 0, 1, 1, 1)


        self.retranslateUi(document_widget)
        self.pushButton.clicked.connect(document_widget.on_delete)

        QMetaObject.connectSlotsByName(document_widget)
    # setupUi

    def retranslateUi(self, document_widget):
        document_widget.setWindowTitle(QCoreApplication.translate("document_widget", u"Form", None))
        self.pushButton.setText(QCoreApplication.translate("document_widget", u"Delete", None))
        self.label.setText(QCoreApplication.translate("document_widget", u"TextLabel", None))
    # retranslateUi

