# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'lora_container.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QFrame, QGridLayout,
    QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QScrollArea, QSizePolicy, QWidget)

class Ui_lora_container(object):
    def setupUi(self, lora_container):
        if not lora_container.objectName():
            lora_container.setObjectName(u"lora_container")
        lora_container.resize(583, 831)
        self.gridLayout = QGridLayout(lora_container)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setHorizontalSpacing(0)
        self.gridLayout.setVerticalSpacing(10)
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.label = QLabel(lora_container)
        self.label.setObjectName(u"label")
        font = QFont()
        font.setBold(True)
        self.label.setFont(font)

        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setSpacing(10)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setContentsMargins(-1, -1, 10, -1)
        self.lineEdit = QLineEdit(lora_container)
        self.lineEdit.setObjectName(u"lineEdit")

        self.horizontalLayout.addWidget(self.lineEdit)

        self.toggleAllLora = QCheckBox(lora_container)
        self.toggleAllLora.setObjectName(u"toggleAllLora")
        font1 = QFont()
        font1.setPointSize(9)
        self.toggleAllLora.setFont(font1)
        self.toggleAllLora.setChecked(False)
        self.toggleAllLora.setTristate(False)

        self.horizontalLayout.addWidget(self.toggleAllLora)


        self.gridLayout.addLayout(self.horizontalLayout, 2, 0, 1, 1)

        self.pushButton = QPushButton(lora_container)
        self.pushButton.setObjectName(u"pushButton")

        self.gridLayout.addWidget(self.pushButton, 4, 0, 1, 1)

        self.lora_scroll_area = QScrollArea(lora_container)
        self.lora_scroll_area.setObjectName(u"lora_scroll_area")
        self.lora_scroll_area.setFont(font1)
        self.lora_scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.lora_scroll_area.setFrameShadow(QFrame.Shadow.Plain)
        self.lora_scroll_area.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 583, 719))
        self.gridLayout_2 = QGridLayout(self.scrollAreaWidgetContents)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.gridLayout_2.setHorizontalSpacing(0)
        self.gridLayout_2.setVerticalSpacing(10)
        self.gridLayout_2.setContentsMargins(0, 0, 10, 0)
        self.lora_scroll_area.setWidget(self.scrollAreaWidgetContents)

        self.gridLayout.addWidget(self.lora_scroll_area, 3, 0, 1, 1)

        self.line = QFrame(lora_container)
        self.line.setObjectName(u"line")
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout.addWidget(self.line, 1, 0, 1, 1)


        self.retranslateUi(lora_container)
        self.toggleAllLora.toggled.connect(lora_container.toggle_all)
        self.lineEdit.textEdited.connect(lora_container.search_text_changed)
        self.pushButton.clicked.connect(lora_container.scan_for_lora)

        QMetaObject.connectSlotsByName(lora_container)
    # setupUi

    def retranslateUi(self, lora_container):
        lora_container.setWindowTitle(QCoreApplication.translate("lora_container", u"Form", None))
        self.label.setText(QCoreApplication.translate("lora_container", u"Lora", None))
        self.lineEdit.setPlaceholderText(QCoreApplication.translate("lora_container", u"Search", None))
        self.toggleAllLora.setText(QCoreApplication.translate("lora_container", u"Toggle all", None))
        self.pushButton.setText(QCoreApplication.translate("lora_container", u"Scan for LoRA", None))
    # retranslateUi

