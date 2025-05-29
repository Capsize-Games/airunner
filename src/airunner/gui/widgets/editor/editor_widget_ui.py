# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'editor_widget.ui'
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
from PySide6.QtWidgets import (QApplication, QComboBox, QHBoxLayout, QPlainTextEdit,
    QSizePolicy, QVBoxLayout, QWidget)

class Ui_EditorWidget(object):
    def setupUi(self, EditorWidget):
        if not EditorWidget.objectName():
            EditorWidget.setObjectName(u"EditorWidget")
        EditorWidget.resize(800, 600)
        self.verticalLayout = QVBoxLayout(EditorWidget)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.topBarLayout = QHBoxLayout()
        self.topBarLayout.setObjectName(u"topBarLayout")
        self.languageComboBox = QComboBox(EditorWidget)
        self.languageComboBox.setObjectName(u"languageComboBox")

        self.topBarLayout.addWidget(self.languageComboBox)


        self.verticalLayout.addLayout(self.topBarLayout)

        self.editorTextEdit = QPlainTextEdit(EditorWidget)
        self.editorTextEdit.setObjectName(u"editorTextEdit")
        self.editorTextEdit.setTabChangesFocus(False)

        self.verticalLayout.addWidget(self.editorTextEdit)

        self.mathjaxWidget = QWidget(EditorWidget)
        self.mathjaxWidget.setObjectName(u"mathjaxWidget")
        self.mathjaxWidget.setMinimumHeight(60)

        self.verticalLayout.addWidget(self.mathjaxWidget)


        self.retranslateUi(EditorWidget)

        QMetaObject.connectSlotsByName(EditorWidget)
    # setupUi

    def retranslateUi(self, EditorWidget):
        self.languageComboBox.setObjectName(QCoreApplication.translate("EditorWidget", u"languageComboBox", None))
        self.editorTextEdit.setObjectName(QCoreApplication.translate("EditorWidget", u"editorTextEdit", None))
        pass
    # retranslateUi

