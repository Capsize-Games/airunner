# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'generated_image.ui'
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
from PySide6.QtWidgets import (QApplication, QComboBox, QGridLayout, QHBoxLayout,
    QLabel, QPushButton, QSizePolicy, QSpacerItem,
    QWidget)

class Ui_Form(object):
    def setupUi(self, Form):
        if not Form.objectName():
            Form.setObjectName(u"Form")
        Form.resize(283, 328)
        self.gridLayout = QGridLayout(Form)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setHorizontalSpacing(0)
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalSpacer = QSpacerItem(17, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout.addItem(self.verticalSpacer, 5, 0, 1, 1)

        self.image_container = QLabel(Form)
        self.image_container.setObjectName(u"image_container")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Maximum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.image_container.sizePolicy().hasHeightForWidth())
        self.image_container.setSizePolicy(sizePolicy)
        self.image_container.setMinimumSize(QSize(256, 256))
        self.image_container.setMaximumSize(QSize(256, 256))

        self.gridLayout.addWidget(self.image_container, 0, 0, 1, 1)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.to_canvas_button = QPushButton(Form)
        self.to_canvas_button.setObjectName(u"to_canvas_button")

        self.horizontalLayout.addWidget(self.to_canvas_button)

        self.export_button = QPushButton(Form)
        self.export_button.setObjectName(u"export_button")

        self.horizontalLayout.addWidget(self.export_button)

        self.delete_button = QPushButton(Form)
        self.delete_button.setObjectName(u"delete_button")

        self.horizontalLayout.addWidget(self.delete_button)


        self.gridLayout.addLayout(self.horizontalLayout, 1, 0, 1, 1)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.slot_combobox = QComboBox(Form)
        self.slot_combobox.setObjectName(u"slot_combobox")

        self.horizontalLayout_2.addWidget(self.slot_combobox)

        self.to_slot_button = QPushButton(Form)
        self.to_slot_button.setObjectName(u"to_slot_button")

        self.horizontalLayout_2.addWidget(self.to_slot_button)


        self.gridLayout.addLayout(self.horizontalLayout_2, 3, 0, 1, 1)


        self.retranslateUi(Form)

        QMetaObject.connectSlotsByName(Form)
    # setupUi

    def retranslateUi(self, Form):
        Form.setWindowTitle(QCoreApplication.translate("Form", u"Form", None))
        self.image_container.setText("")
        self.to_canvas_button.setText(QCoreApplication.translate("Form", u"Send to canvas", None))
        self.export_button.setText(QCoreApplication.translate("Form", u"Export", None))
        self.delete_button.setText(QCoreApplication.translate("Form", u"Delete", None))
        self.to_slot_button.setText(QCoreApplication.translate("Form", u"Send to slot", None))
    # retranslateUi

