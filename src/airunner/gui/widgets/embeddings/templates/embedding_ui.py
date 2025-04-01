# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'embedding.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QGridLayout, QLineEdit,
    QPushButton, QSizePolicy, QWidget)

class Ui_embedding(object):
    def setupUi(self, embedding):
        if not embedding.objectName():
            embedding.setObjectName(u"embedding")
        embedding.resize(542, 73)
        self.gridLayout = QGridLayout(embedding)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setHorizontalSpacing(10)
        self.gridLayout.setVerticalSpacing(0)
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.enabledCheckbox = QCheckBox(embedding)
        self.enabledCheckbox.setObjectName(u"enabledCheckbox")

        self.gridLayout.addWidget(self.enabledCheckbox, 0, 0, 1, 1)

        self.trigger_word_edit = QLineEdit(embedding)
        self.trigger_word_edit.setObjectName(u"trigger_word_edit")
        font = QFont()
        font.setPointSize(9)
        self.trigger_word_edit.setFont(font)

        self.gridLayout.addWidget(self.trigger_word_edit, 1, 0, 1, 1)

        self.delete_button = QPushButton(embedding)
        self.delete_button.setObjectName(u"delete_button")
        icon = QIcon(QIcon.fromTheme(u"user-trash"))
        self.delete_button.setIcon(icon)

        self.gridLayout.addWidget(self.delete_button, 1, 1, 1, 1)


        self.retranslateUi(embedding)
        self.delete_button.clicked.connect(embedding.action_clicked_button_deleted)
        self.trigger_word_edit.textChanged.connect(embedding.action_changed_trigger_word)
        self.enabledCheckbox.toggled.connect(embedding.action_toggled_embedding)

        QMetaObject.connectSlotsByName(embedding)
    # setupUi

    def retranslateUi(self, embedding):
        embedding.setWindowTitle(QCoreApplication.translate("embedding", u"Form", None))
        self.enabledCheckbox.setText(QCoreApplication.translate("embedding", u"enabledCheckbox", None))
#if QT_CONFIG(tooltip)
        self.trigger_word_edit.setToolTip(QCoreApplication.translate("embedding", u"<html><head/><body><p>Some LoRA require a trigger word to activate.</p><p>Make a note here for your records.</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.trigger_word_edit.setPlaceholderText(QCoreApplication.translate("embedding", u"Trigger words (comma separated)", None))
        self.delete_button.setText("")
    # retranslateUi

