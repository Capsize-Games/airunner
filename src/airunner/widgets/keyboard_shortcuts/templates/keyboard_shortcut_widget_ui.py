# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'keyboard_shortcut_widget.ui'
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
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QLabel, QLineEdit,
    QSizePolicy, QWidget)

class Ui_keyboard_shortcut_widget(object):
    def setupUi(self, keyboard_shortcut_widget):
        if not keyboard_shortcut_widget.objectName():
            keyboard_shortcut_widget.setObjectName(u"keyboard_shortcut_widget")
        keyboard_shortcut_widget.resize(400, 43)
        self.horizontalLayout = QHBoxLayout(keyboard_shortcut_widget)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.label = QLabel(keyboard_shortcut_widget)
        self.label.setObjectName(u"label")
        font = QFont()
        font.setPointSize(8)
        self.label.setFont(font)

        self.horizontalLayout.addWidget(self.label)

        self.line_edit = QLineEdit(keyboard_shortcut_widget)
        self.line_edit.setObjectName(u"line_edit")
        self.line_edit.setFont(font)
        self.line_edit.setReadOnly(True)

        self.horizontalLayout.addWidget(self.line_edit)


        self.retranslateUi(keyboard_shortcut_widget)

        QMetaObject.connectSlotsByName(keyboard_shortcut_widget)
    # setupUi

    def retranslateUi(self, keyboard_shortcut_widget):
        keyboard_shortcut_widget.setWindowTitle(QCoreApplication.translate("keyboard_shortcut_widget", u"Form", None))
        self.label.setText(QCoreApplication.translate("keyboard_shortcut_widget", u"TextLabel", None))
    # retranslateUi

