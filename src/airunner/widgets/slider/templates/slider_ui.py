# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'slider.ui'
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
from PySide6.QtWidgets import (QAbstractSpinBox, QApplication, QDoubleSpinBox, QGridLayout,
    QSizePolicy, QSlider, QWidget)

class Ui_slider_widget(object):
    def setupUi(self, slider_widget):
        if not slider_widget.objectName():
            slider_widget.setObjectName(u"slider_widget")
        slider_widget.resize(242, 93)
        slider_widget.setStyleSheet(u"")
        self.gridLayout = QGridLayout(slider_widget)
        self.gridLayout.setSpacing(0)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.slider = QSlider(slider_widget)
        self.slider.setObjectName(u"slider")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.slider.sizePolicy().hasHeightForWidth())
        self.slider.setSizePolicy(sizePolicy)
        self.slider.setAutoFillBackground(False)
        self.slider.setStyleSheet(u"")
        self.slider.setMaximum(100)
        self.slider.setPageStep(1)
        self.slider.setOrientation(Qt.Horizontal)

        self.gridLayout.addWidget(self.slider, 0, 0, 1, 1)

        self.slider_spinbox = QDoubleSpinBox(slider_widget)
        self.slider_spinbox.setObjectName(u"slider_spinbox")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.slider_spinbox.sizePolicy().hasHeightForWidth())
        self.slider_spinbox.setSizePolicy(sizePolicy1)
        self.slider_spinbox.setStyleSheet(u"")
        self.slider_spinbox.setWrapping(False)
        self.slider_spinbox.setFrame(False)
        self.slider_spinbox.setAlignment(Qt.AlignCenter)
        self.slider_spinbox.setButtonSymbols(QAbstractSpinBox.UpDownArrows)
        self.slider_spinbox.setProperty("showGroupSeparator", False)
        self.slider_spinbox.setMaximum(1.000000000000000)
        self.slider_spinbox.setSingleStep(0.010000000000000)

        self.gridLayout.addWidget(self.slider_spinbox, 0, 1, 1, 1)


        self.retranslateUi(slider_widget)
        self.slider_spinbox.valueChanged.connect(slider_widget.handle_spinbox_change)
        self.slider.valueChanged.connect(slider_widget.handle_slider_change)

        QMetaObject.connectSlotsByName(slider_widget)
    # setupUi

    def retranslateUi(self, slider_widget):
        slider_widget.setWindowTitle(QCoreApplication.translate("slider_widget", u"Form", None))
    # retranslateUi

