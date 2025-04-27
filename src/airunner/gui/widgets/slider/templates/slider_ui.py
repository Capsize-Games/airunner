# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'slider.ui'
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
from PySide6.QtWidgets import (QAbstractSpinBox, QApplication, QDoubleSpinBox, QGridLayout,
    QGroupBox, QSizePolicy, QSlider, QWidget)

class Ui_slider_widget(object):
    def setupUi(self, slider_widget):
        if not slider_widget.objectName():
            slider_widget.setObjectName(u"slider_widget")
        slider_widget.resize(548, 50)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(slider_widget.sizePolicy().hasHeightForWidth())
        slider_widget.setSizePolicy(sizePolicy)
        slider_widget.setMinimumSize(QSize(0, 0))
        slider_widget.setMaximumSize(QSize(16777215, 16777215))
        slider_widget.setStyleSheet(u"")
        self.gridLayout = QGridLayout(slider_widget)
        self.gridLayout.setSpacing(0)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.groupBox = QGroupBox(slider_widget)
        self.groupBox.setObjectName(u"groupBox")
        sizePolicy.setHeightForWidth(self.groupBox.sizePolicy().hasHeightForWidth())
        self.groupBox.setSizePolicy(sizePolicy)
        self.groupBox.setMinimumSize(QSize(0, 0))
        self.groupBox.setMaximumSize(QSize(16777215, 16777215))
        font = QFont()
        font.setPointSize(9)
        self.groupBox.setFont(font)
        self.gridLayout_2 = QGridLayout(self.groupBox)
        self.gridLayout_2.setSpacing(0)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.gridLayout_2.setContentsMargins(5, 5, 5, 5)
        self.slider = QSlider(self.groupBox)
        self.slider.setObjectName(u"slider")
        sizePolicy.setHeightForWidth(self.slider.sizePolicy().hasHeightForWidth())
        self.slider.setSizePolicy(sizePolicy)
        self.slider.setMinimumSize(QSize(0, 0))
        self.slider.setAutoFillBackground(False)
        self.slider.setStyleSheet(u"")
        self.slider.setMaximum(100)
        self.slider.setPageStep(1)
        self.slider.setOrientation(Qt.Orientation.Horizontal)

        self.gridLayout_2.addWidget(self.slider, 0, 0, 1, 1)

        self.slider_spinbox = QDoubleSpinBox(self.groupBox)
        self.slider_spinbox.setObjectName(u"slider_spinbox")
        sizePolicy.setHeightForWidth(self.slider_spinbox.sizePolicy().hasHeightForWidth())
        self.slider_spinbox.setSizePolicy(sizePolicy)
        self.slider_spinbox.setMinimumSize(QSize(0, 0))
        self.slider_spinbox.setMaximumSize(QSize(16777215, 16777215))
        self.slider_spinbox.setStyleSheet(u"")
        self.slider_spinbox.setWrapping(False)
        self.slider_spinbox.setFrame(False)
        self.slider_spinbox.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.slider_spinbox.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.UpDownArrows)
        self.slider_spinbox.setKeyboardTracking(True)
        self.slider_spinbox.setProperty("showGroupSeparator", False)
        self.slider_spinbox.setMaximum(1.000000000000000)
        self.slider_spinbox.setSingleStep(0.010000000000000)

        self.gridLayout_2.addWidget(self.slider_spinbox, 0, 1, 1, 1)


        self.gridLayout.addWidget(self.groupBox, 0, 0, 1, 1)


        self.retranslateUi(slider_widget)
        self.slider.valueChanged.connect(slider_widget.handle_slider_valueChanged)
        self.slider_spinbox.valueChanged.connect(slider_widget.handle_spinbox_valueChanged)
        self.slider.sliderReleased.connect(slider_widget.on_slider_sliderReleased)

        QMetaObject.connectSlotsByName(slider_widget)
    # setupUi

    def retranslateUi(self, slider_widget):
        slider_widget.setWindowTitle(QCoreApplication.translate("slider_widget", u"Form", None))
        self.groupBox.setTitle(QCoreApplication.translate("slider_widget", u"GroupBox", None))
    # retranslateUi

