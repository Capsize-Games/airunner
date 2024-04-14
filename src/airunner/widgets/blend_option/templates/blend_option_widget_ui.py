# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'blend_option_widget.ui'
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
from PySide6.QtWidgets import (QApplication, QComboBox, QDoubleSpinBox, QFormLayout,
    QFrame, QGridLayout, QHBoxLayout, QLabel,
    QPlainTextEdit, QPushButton, QSizePolicy, QSlider,
    QSpacerItem, QVBoxLayout, QWidget)

class Ui_Form(object):
    def setupUi(self, Form):
        if not Form.objectName():
            Form.setObjectName(u"Form")
        Form.resize(290, 940)
        self.verticalLayout_2 = QVBoxLayout(Form)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.gridLayout_2 = QGridLayout()
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.weight_slider = QSlider(Form)
        self.weight_slider.setObjectName(u"weight_slider")
        self.weight_slider.setMaximum(100)
        self.weight_slider.setSliderPosition(100)
        self.weight_slider.setOrientation(Qt.Horizontal)

        self.horizontalLayout.addWidget(self.weight_slider)

        self.line = QFrame(Form)
        self.line.setObjectName(u"line")
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFrameShadow(QFrame.Shadow.Sunken)

        self.horizontalLayout.addWidget(self.line)

        self.weight_spinbox = QDoubleSpinBox(Form)
        self.weight_spinbox.setObjectName(u"weight_spinbox")
        self.weight_spinbox.setMaximum(1.000000000000000)
        self.weight_spinbox.setSingleStep(0.010000000000000)
        self.weight_spinbox.setValue(1.000000000000000)

        self.horizontalLayout.addWidget(self.weight_spinbox)


        self.gridLayout_2.addLayout(self.horizontalLayout, 3, 0, 1, 2)

        self.plainTextEdit = QPlainTextEdit(Form)
        self.plainTextEdit.setObjectName(u"plainTextEdit")

        self.gridLayout_2.addWidget(self.plainTextEdit, 1, 0, 1, 2)

        self.image_form = QFormLayout()
        self.image_form.setObjectName(u"image_form")
        self.image_form.setFormAlignment(Qt.AlignLeading|Qt.AlignLeft|Qt.AlignTop)
        self.image_container = QLabel(Form)
        self.image_container.setObjectName(u"image_container")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.image_container.sizePolicy().hasHeightForWidth())
        self.image_container.setSizePolicy(sizePolicy)
        self.image_container.setMinimumSize(QSize(128, 128))
        self.image_container.setMaximumSize(QSize(128, 128))
        self.image_container.setStyleSheet(u"border: 1px solid black")

        self.image_form.setWidget(0, QFormLayout.LabelRole, self.image_container)

        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.layer_combobox = QComboBox(Form)
        self.layer_combobox.setObjectName(u"layer_combobox")

        self.verticalLayout.addWidget(self.layer_combobox)

        self.import_image_button = QPushButton(Form)
        self.import_image_button.setObjectName(u"import_image_button")

        self.verticalLayout.addWidget(self.import_image_button)

        self.image_spacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout.addItem(self.image_spacer)


        self.image_form.setLayout(0, QFormLayout.FieldRole, self.verticalLayout)


        self.gridLayout_2.addLayout(self.image_form, 2, 0, 1, 2)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout_2.addItem(self.verticalSpacer, 5, 1, 1, 1)

        self.image_or_text_combobox = QComboBox(Form)
        self.image_or_text_combobox.addItem("")
        self.image_or_text_combobox.addItem("")
        self.image_or_text_combobox.setObjectName(u"image_or_text_combobox")

        self.gridLayout_2.addWidget(self.image_or_text_combobox, 0, 0, 1, 2)

        self.delete_button = QPushButton(Form)
        self.delete_button.setObjectName(u"delete_button")

        self.gridLayout_2.addWidget(self.delete_button, 4, 0, 1, 2)


        self.verticalLayout_2.addLayout(self.gridLayout_2)

        self.verticalSpacer_2 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_2.addItem(self.verticalSpacer_2)


        self.retranslateUi(Form)

        QMetaObject.connectSlotsByName(Form)
    # setupUi

    def retranslateUi(self, Form):
        Form.setWindowTitle(QCoreApplication.translate("Form", u"Form", None))
        self.image_container.setText("")
        self.import_image_button.setText(QCoreApplication.translate("Form", u"Import new image", None))
        self.image_or_text_combobox.setItemText(0, QCoreApplication.translate("Form", u"Image", None))
        self.image_or_text_combobox.setItemText(1, QCoreApplication.translate("Form", u"Text", None))

        self.delete_button.setText(QCoreApplication.translate("Form", u"Delete", None))
    # retranslateUi

