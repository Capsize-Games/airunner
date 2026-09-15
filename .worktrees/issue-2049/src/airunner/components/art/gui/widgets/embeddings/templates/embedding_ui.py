# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'embedding.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QFrame, QGridLayout,
    QLineEdit, QPushButton, QSizePolicy, QVBoxLayout,
    QWidget)
import airunner.feather_rc

class Ui_embedding(object):
    def setupUi(self, embedding):
        if not embedding.objectName():
            embedding.setObjectName(u"embedding")
        embedding.resize(542, 83)
        self.gridLayout = QGridLayout(embedding)
        self.gridLayout.setSpacing(10)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.trigger_word_container = QVBoxLayout()
        self.trigger_word_container.setSpacing(10)
        self.trigger_word_container.setObjectName(u"trigger_word_container")

        self.gridLayout.addLayout(self.trigger_word_container, 3, 0, 1, 2)

        self.enabled_checkbox = QCheckBox(embedding)
        self.enabled_checkbox.setObjectName(u"enabled_checkbox")
        font = QFont()
        font.setPointSize(11)
        font.setBold(True)
        self.enabled_checkbox.setFont(font)

        self.gridLayout.addWidget(self.enabled_checkbox, 1, 0, 1, 2)

        self.delete_button = QPushButton(embedding)
        self.delete_button.setObjectName(u"delete_button")
        icon = QIcon()
        icon.addFile(u":/dark/icons/feather/dark/trash-2.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.delete_button.setIcon(icon)

        self.gridLayout.addWidget(self.delete_button, 2, 1, 1, 1)

        self.trigger_word_edit = QLineEdit(embedding)
        self.trigger_word_edit.setObjectName(u"trigger_word_edit")
        font1 = QFont()
        font1.setPointSize(9)
        self.trigger_word_edit.setFont(font1)

        self.gridLayout.addWidget(self.trigger_word_edit, 2, 0, 1, 1)

        self.line = QFrame(embedding)
        self.line.setObjectName(u"line")
        self.line.setMinimumSize(QSize(0, 0))
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout.addWidget(self.line, 0, 0, 1, 2)


        self.retranslateUi(embedding)
        self.trigger_word_edit.textChanged.connect(embedding.action_changed_trigger_word)

        QMetaObject.connectSlotsByName(embedding)
    # setupUi

    def retranslateUi(self, embedding):
        embedding.setWindowTitle(QCoreApplication.translate("embedding", u"Form", None))
        self.enabled_checkbox.setText(QCoreApplication.translate("embedding", u"enabledCheckbox", None))
        self.delete_button.setText("")
#if QT_CONFIG(tooltip)
        self.trigger_word_edit.setToolTip(QCoreApplication.translate("embedding", u"<html><head/><body><p>Some LoRA require a trigger word to activate.</p><p>Make a note here for your records.</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.trigger_word_edit.setPlaceholderText(QCoreApplication.translate("embedding", u"Trigger words (comma separated)", None))
    # retranslateUi

