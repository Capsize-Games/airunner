# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'embedding.ui'
##
## Created by: Qt User Interface Compiler version 6.6.2
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
from PySide6.QtWidgets import (QApplication, QGridLayout, QGroupBox, QLineEdit,
    QSizePolicy, QWidget)

class Ui_embedding(object):
    def setupUi(self, embedding):
        if not embedding.objectName():
            embedding.setObjectName(u"embedding")
        embedding.resize(400, 168)
        self.gridLayout_2 = QGridLayout(embedding)
        self.gridLayout_2.setSpacing(0)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.gridLayout_2.setContentsMargins(0, 0, 0, 0)
        self.enabledCheckbox = QGroupBox(embedding)
        self.enabledCheckbox.setObjectName(u"enabledCheckbox")
        self.enabledCheckbox.setCheckable(True)
        self.enabledCheckbox.setChecked(False)
        self.gridLayout = QGridLayout(self.enabledCheckbox)
        self.gridLayout.setObjectName(u"gridLayout")
        self.trigger_word_edit = QLineEdit(self.enabledCheckbox)
        self.trigger_word_edit.setObjectName(u"trigger_word_edit")
        font = QFont()
        font.setPointSize(9)
        self.trigger_word_edit.setFont(font)

        self.gridLayout.addWidget(self.trigger_word_edit, 2, 0, 1, 1)


        self.gridLayout_2.addWidget(self.enabledCheckbox, 0, 0, 1, 2)


        self.retranslateUi(embedding)
        self.enabledCheckbox.toggled.connect(embedding.action_toggled_embedding)
        self.trigger_word_edit.textChanged.connect(embedding.action_changed_trigger_word)

        QMetaObject.connectSlotsByName(embedding)
    # setupUi

    def retranslateUi(self, embedding):
        embedding.setWindowTitle(QCoreApplication.translate("embedding", u"Form", None))
        self.enabledCheckbox.setTitle(QCoreApplication.translate("embedding", u"Embedding name here", None))
#if QT_CONFIG(tooltip)
        self.trigger_word_edit.setToolTip(QCoreApplication.translate("embedding", u"<html><head/><body><p>Some LoRA require a trigger word to activate.</p><p>Make a note here for your records.</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.trigger_word_edit.setPlaceholderText(QCoreApplication.translate("embedding", u"Trigger words (comma separated)", None))
    # retranslateUi

