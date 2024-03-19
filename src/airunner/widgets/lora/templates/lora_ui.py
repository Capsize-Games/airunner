# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'lora.ui'
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

class Ui_lora(object):
    def setupUi(self, lora):
        if not lora.objectName():
            lora.setObjectName(u"lora")
        lora.resize(437, 121)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(lora.sizePolicy().hasHeightForWidth())
        lora.setSizePolicy(sizePolicy)
        lora.setMaximumSize(QSize(16777215, 16777215))
        font = QFont()
        font.setPointSize(9)
        lora.setFont(font)
        self.gridLayout_2 = QGridLayout(lora)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.gridLayout_2.setContentsMargins(0, 0, 0, 0)
        self.gridLayout = QGridLayout()
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setHorizontalSpacing(0)
        self.enabledCheckbox = QGroupBox(lora)
        self.enabledCheckbox.setObjectName(u"enabledCheckbox")
        self.enabledCheckbox.setCheckable(True)
        self.gridLayout_3 = QGridLayout(self.enabledCheckbox)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.trigger_word_edit = QLineEdit(self.enabledCheckbox)
        self.trigger_word_edit.setObjectName(u"trigger_word_edit")

        self.gridLayout_3.addWidget(self.trigger_word_edit, 0, 0, 1, 1)


        self.gridLayout.addWidget(self.enabledCheckbox, 0, 0, 2, 1)


        self.gridLayout_2.addLayout(self.gridLayout, 0, 0, 1, 1)


        self.retranslateUi(lora)
        self.trigger_word_edit.textChanged.connect(lora.action_changed_trigger_words)
        self.enabledCheckbox.toggled.connect(lora.action_toggled_lora_enabled)
        self.trigger_word_edit.textEdited.connect(lora.action_text_changed_trigger_word)

        QMetaObject.connectSlotsByName(lora)
    # setupUi

    def retranslateUi(self, lora):
        lora.setWindowTitle(QCoreApplication.translate("lora", u"Form", None))
        self.enabledCheckbox.setTitle(QCoreApplication.translate("lora", u"LoRA name here", None))
#if QT_CONFIG(tooltip)
        self.trigger_word_edit.setToolTip(QCoreApplication.translate("lora", u"<html><head/><body><p>Some LoRA require a trigger word to activate.</p><p>Make a note here for your records.</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.trigger_word_edit.setPlaceholderText(QCoreApplication.translate("lora", u"Trigger words (comma separated)", None))
    # retranslateUi

