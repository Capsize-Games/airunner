# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'lora_trigger_word.ui'
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
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QLabel, QPushButton,
    QSizePolicy, QWidget)

class Ui_lora_trigger_word(object):
    def setupUi(self, lora_trigger_word):
        if not lora_trigger_word.objectName():
            lora_trigger_word.setObjectName(u"lora_trigger_word")
        lora_trigger_word.resize(345, 43)
        self.horizontalLayout = QHBoxLayout(lora_trigger_word)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.trigger_word = QLabel(lora_trigger_word)
        self.trigger_word.setObjectName(u"trigger_word")

        self.horizontalLayout.addWidget(self.trigger_word)

        self.button_to_prompt = QPushButton(lora_trigger_word)
        self.button_to_prompt.setObjectName(u"button_to_prompt")
        self.button_to_prompt.setCursor(QCursor(Qt.PointingHandCursor))
        icon = QIcon()
        iconThemeName = u"edit-paste"
        if QIcon.hasThemeIcon(iconThemeName):
            icon = QIcon.fromTheme(iconThemeName)
        else:
            icon.addFile(u".", QSize(), QIcon.Normal, QIcon.Off)

        self.button_to_prompt.setIcon(icon)

        self.horizontalLayout.addWidget(self.button_to_prompt)

        self.button_to_negative_prompt = QPushButton(lora_trigger_word)
        self.button_to_negative_prompt.setObjectName(u"button_to_negative_prompt")
        self.button_to_negative_prompt.setCursor(QCursor(Qt.PointingHandCursor))
        self.button_to_negative_prompt.setIcon(icon)

        self.horizontalLayout.addWidget(self.button_to_negative_prompt)

        self.button_copy = QPushButton(lora_trigger_word)
        self.button_copy.setObjectName(u"button_copy")
        self.button_copy.setCursor(QCursor(Qt.PointingHandCursor))
        icon1 = QIcon(QIcon.fromTheme(u"edit-copy"))
        self.button_copy.setIcon(icon1)

        self.horizontalLayout.addWidget(self.button_copy)


        self.retranslateUi(lora_trigger_word)
        self.button_to_prompt.clicked["bool"].connect(lora_trigger_word.action_click_button_to_prompt)
        self.button_to_negative_prompt.clicked.connect(lora_trigger_word.action_click_button_to_negative_prompt)
        self.button_copy.clicked.connect(lora_trigger_word.action_click_button_copy)

        QMetaObject.connectSlotsByName(lora_trigger_word)
    # setupUi

    def retranslateUi(self, lora_trigger_word):
        lora_trigger_word.setWindowTitle(QCoreApplication.translate("lora_trigger_word", u"Form", None))
        self.trigger_word.setText(QCoreApplication.translate("lora_trigger_word", u"Trigger Word", None))
#if QT_CONFIG(tooltip)
        self.button_to_prompt.setToolTip(QCoreApplication.translate("lora_trigger_word", u"Send trigger word to prompt", None))
#endif // QT_CONFIG(tooltip)
        self.button_to_prompt.setText(QCoreApplication.translate("lora_trigger_word", u"Prompt", None))
#if QT_CONFIG(tooltip)
        self.button_to_negative_prompt.setToolTip(QCoreApplication.translate("lora_trigger_word", u"Send trigger word to negative prompt", None))
#endif // QT_CONFIG(tooltip)
        self.button_to_negative_prompt.setText(QCoreApplication.translate("lora_trigger_word", u"Negative", None))
#if QT_CONFIG(tooltip)
        self.button_copy.setToolTip(QCoreApplication.translate("lora_trigger_word", u"Copy trigger word to clipboard", None))
#endif // QT_CONFIG(tooltip)
        self.button_copy.setText("")
    # retranslateUi

