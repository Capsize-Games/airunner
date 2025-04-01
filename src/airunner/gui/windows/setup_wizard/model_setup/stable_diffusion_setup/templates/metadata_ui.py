# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'metadata.ui'
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
from PySide6.QtWidgets import (QApplication, QFrame, QGridLayout, QLabel,
    QRadioButton, QSizePolicy, QSpacerItem, QWidget)

class Ui_metadata_setup(object):
    def setupUi(self, metadata_setup):
        if not metadata_setup.objectName():
            metadata_setup.setObjectName(u"metadata_setup")
        metadata_setup.resize(566, 375)
        self.gridLayout = QGridLayout(metadata_setup)
        self.gridLayout.setObjectName(u"gridLayout")
        self.radioButton = QRadioButton(metadata_setup)
        self.radioButton.setObjectName(u"radioButton")
        self.radioButton.setChecked(False)

        self.gridLayout.addWidget(self.radioButton, 4, 0, 1, 1)

        self.label = QLabel(metadata_setup)
        self.label.setObjectName(u"label")
        font = QFont()
        font.setPointSize(11)
        font.setBold(True)
        self.label.setFont(font)

        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)

        self.label_3 = QLabel(metadata_setup)
        self.label_3.setObjectName(u"label_3")

        self.gridLayout.addWidget(self.label_3, 3, 0, 1, 1)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout.addItem(self.verticalSpacer, 6, 0, 1, 1)

        self.line = QFrame(metadata_setup)
        self.line.setObjectName(u"line")
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout.addWidget(self.line, 2, 0, 1, 1)

        self.label_2 = QLabel(metadata_setup)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setWordWrap(True)

        self.gridLayout.addWidget(self.label_2, 1, 0, 1, 1)

        self.radioButton_2 = QRadioButton(metadata_setup)
        self.radioButton_2.setObjectName(u"radioButton_2")
        self.radioButton_2.setChecked(True)

        self.gridLayout.addWidget(self.radioButton_2, 5, 0, 1, 1)


        self.retranslateUi(metadata_setup)
        self.radioButton.toggled.connect(metadata_setup.yes_toggled)
        self.radioButton_2.toggled.connect(metadata_setup.no_toggled)

        QMetaObject.connectSlotsByName(metadata_setup)
    # setupUi

    def retranslateUi(self, metadata_setup):
        metadata_setup.setWindowTitle(QCoreApplication.translate("metadata_setup", u"Form", None))
        self.radioButton.setText(QCoreApplication.translate("metadata_setup", u"Yes", None))
        self.label.setText(QCoreApplication.translate("metadata_setup", u"Metadata Setup", None))
        self.label_3.setText(QCoreApplication.translate("metadata_setup", u"Would you like to enable metadata in images?", None))
        self.label_2.setText(QCoreApplication.translate("metadata_setup", u"Metadata is attached to PNGs in order to help facilitate the creation of similar images. You may adjust this setting in the preferences of the main application.", None))
        self.radioButton_2.setText(QCoreApplication.translate("metadata_setup", u"No", None))
    # retranslateUi

