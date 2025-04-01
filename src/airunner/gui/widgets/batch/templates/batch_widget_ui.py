# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'batch_widget.ui'
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
from PySide6.QtWidgets import (QApplication, QFrame, QGridLayout, QGroupBox,
    QLabel, QPushButton, QScrollArea, QSizePolicy,
    QSpacerItem, QSpinBox, QWidget)

class Ui_batch_widget(object):
    def setupUi(self, batch_widget):
        if not batch_widget.objectName():
            batch_widget.setObjectName(u"batch_widget")
        batch_widget.resize(322, 172)
        batch_widget.setMaximumSize(QSize(16777215, 16777215))
        font = QFont()
        font.setPointSize(8)
        batch_widget.setFont(font)
        self.gridLayout_4 = QGridLayout(batch_widget)
        self.gridLayout_4.setObjectName(u"gridLayout_4")
        self.scrollArea = QScrollArea(batch_widget)
        self.scrollArea.setObjectName(u"scrollArea")
        self.scrollArea.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 302, 152))
        self.gridLayout_2 = QGridLayout(self.scrollAreaWidgetContents)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.groupBox = QGroupBox(self.scrollAreaWidgetContents)
        self.groupBox.setObjectName(u"groupBox")
        font1 = QFont()
        font1.setPointSize(8)
        font1.setBold(True)
        self.groupBox.setFont(font1)
        self.gridLayout = QGridLayout(self.groupBox)
        self.gridLayout.setObjectName(u"gridLayout")
        self.images_per_batch = QSpinBox(self.groupBox)
        self.images_per_batch.setObjectName(u"images_per_batch")
        font2 = QFont()
        font2.setPointSize(8)
        font2.setBold(False)
        self.images_per_batch.setFont(font2)
        self.images_per_batch.setMinimum(1)
        self.images_per_batch.setMaximum(34)

        self.gridLayout.addWidget(self.images_per_batch, 0, 0, 1, 1)


        self.gridLayout_2.addWidget(self.groupBox, 2, 1, 1, 1)

        self.groupBox_2 = QGroupBox(self.scrollAreaWidgetContents)
        self.groupBox_2.setObjectName(u"groupBox_2")
        self.groupBox_2.setFont(font1)
        self.gridLayout_3 = QGridLayout(self.groupBox_2)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.total_batches = QSpinBox(self.groupBox_2)
        self.total_batches.setObjectName(u"total_batches")
        self.total_batches.setFont(font2)
        self.total_batches.setMinimum(1)
        self.total_batches.setMaximum(500)

        self.gridLayout_3.addWidget(self.total_batches, 0, 0, 1, 1)


        self.gridLayout_2.addWidget(self.groupBox_2, 2, 0, 1, 1)

        self.label = QLabel(self.scrollAreaWidgetContents)
        self.label.setObjectName(u"label")
        font3 = QFont()
        font3.setPointSize(10)
        font3.setBold(True)
        self.label.setFont(font3)

        self.gridLayout_2.addWidget(self.label, 0, 0, 1, 1)

        self.line = QFrame(self.scrollAreaWidgetContents)
        self.line.setObjectName(u"line")
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout_2.addWidget(self.line, 1, 0, 1, 2)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout_2.addItem(self.verticalSpacer, 4, 0, 1, 1)

        self.generate_batches_button = QPushButton(self.scrollAreaWidgetContents)
        self.generate_batches_button.setObjectName(u"generate_batches_button")
        self.generate_batches_button.setFont(font)

        self.gridLayout_2.addWidget(self.generate_batches_button, 3, 0, 1, 2)

        self.scrollArea.setWidget(self.scrollAreaWidgetContents)

        self.gridLayout_4.addWidget(self.scrollArea, 0, 0, 1, 1)


        self.retranslateUi(batch_widget)

        QMetaObject.connectSlotsByName(batch_widget)
    # setupUi

    def retranslateUi(self, batch_widget):
        batch_widget.setWindowTitle(QCoreApplication.translate("batch_widget", u"Form", None))
        self.groupBox.setTitle(QCoreApplication.translate("batch_widget", u"Images per batch", None))
        self.groupBox_2.setTitle(QCoreApplication.translate("batch_widget", u"Batches", None))
        self.label.setText(QCoreApplication.translate("batch_widget", u"Batch Generation", None))
        self.generate_batches_button.setText(QCoreApplication.translate("batch_widget", u"Generate batches", None))
    # retranslateUi

