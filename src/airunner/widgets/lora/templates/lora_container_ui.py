# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'lora_container.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QFrame, QGridLayout,
    QHBoxLayout, QLineEdit, QScrollArea, QSizePolicy,
    QWidget)

class Ui_lora_container(object):
    def setupUi(self, lora_container):
        if not lora_container.objectName():
            lora_container.setObjectName(u"lora_container")
        lora_container.resize(583, 775)
        self.gridLayout = QGridLayout(lora_container)
        self.gridLayout.setObjectName(u"gridLayout")
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.lineEdit = QLineEdit(lora_container)
        self.lineEdit.setObjectName(u"lineEdit")

        self.horizontalLayout.addWidget(self.lineEdit)

        self.toggleAllLora = QCheckBox(lora_container)
        self.toggleAllLora.setObjectName(u"toggleAllLora")
        font = QFont()
        font.setPointSize(9)
        self.toggleAllLora.setFont(font)
        self.toggleAllLora.setChecked(False)
        self.toggleAllLora.setTristate(False)

        self.horizontalLayout.addWidget(self.toggleAllLora)


        self.gridLayout.addLayout(self.horizontalLayout, 0, 0, 1, 1)

        self.lora_scroll_area = QScrollArea(lora_container)
        self.lora_scroll_area.setObjectName(u"lora_scroll_area")
        self.lora_scroll_area.setFont(font)
        self.lora_scroll_area.setFrameShape(QFrame.NoFrame)
        self.lora_scroll_area.setFrameShadow(QFrame.Plain)
        self.lora_scroll_area.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 565, 724))
        self.gridLayout_2 = QGridLayout(self.scrollAreaWidgetContents)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.lora_scroll_area.setWidget(self.scrollAreaWidgetContents)

        self.gridLayout.addWidget(self.lora_scroll_area, 1, 0, 1, 1)


        self.retranslateUi(lora_container)
        self.toggleAllLora.toggled.connect(lora_container.toggle_all)
        self.lineEdit.textEdited.connect(lora_container.search_text_changed)

        QMetaObject.connectSlotsByName(lora_container)
    # setupUi

    def retranslateUi(self, lora_container):
        lora_container.setWindowTitle(QCoreApplication.translate("lora_container", u"Form", None))
        self.lineEdit.setPlaceholderText(QCoreApplication.translate("lora_container", u"Search", None))
        self.toggleAllLora.setText(QCoreApplication.translate("lora_container", u"Toggle all", None))
    # retranslateUi

