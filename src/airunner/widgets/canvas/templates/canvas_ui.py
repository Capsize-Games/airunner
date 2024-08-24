# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'canvas.ui'
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
from PySide6.QtWidgets import (QApplication, QGridLayout, QGroupBox, QSizePolicy,
    QSplitter, QWidget)

from airunner.widgets.canvas.custom_view import CustomGraphicsView

class Ui_canvas(object):
    def setupUi(self, canvas):
        if not canvas.objectName():
            canvas.setObjectName(u"canvas")
        canvas.resize(788, 708)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(canvas.sizePolicy().hasHeightForWidth())
        canvas.setSizePolicy(sizePolicy)
        canvas.setMinimumSize(QSize(0, 0))
        canvas.setStyleSheet(u"b")
        self.gridLayout = QGridLayout(canvas)
        self.gridLayout.setSpacing(0)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.central_widget = QWidget(canvas)
        self.central_widget.setObjectName(u"central_widget")
        sizePolicy.setHeightForWidth(self.central_widget.sizePolicy().hasHeightForWidth())
        self.central_widget.setSizePolicy(sizePolicy)
        self.central_widget.setMinimumSize(QSize(0, 0))
        self.central_widget.setStyleSheet(u"")
        self.gridLayout_6 = QGridLayout(self.central_widget)
        self.gridLayout_6.setObjectName(u"gridLayout_6")
        self.gridLayout_6.setContentsMargins(0, 0, 0, 0)
        self.canvas_splitter = QSplitter(self.central_widget)
        self.canvas_splitter.setObjectName(u"canvas_splitter")
        self.canvas_splitter.setOrientation(Qt.Orientation.Horizontal)
        self.canvas_side_splitter = QSplitter(self.canvas_splitter)
        self.canvas_side_splitter.setObjectName(u"canvas_side_splitter")
        self.canvas_side_splitter.setOrientation(Qt.Orientation.Vertical)
        self.drawing_pad_groupbox = QGroupBox(self.canvas_side_splitter)
        self.drawing_pad_groupbox.setObjectName(u"drawing_pad_groupbox")
        self.drawing_pad_groupbox.setCheckable(True)
        self.gridLayout_3 = QGridLayout(self.drawing_pad_groupbox)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.gridLayout_3.setContentsMargins(0, 0, 0, 0)
        self.drawing_pad = CustomGraphicsView(self.drawing_pad_groupbox)
        self.drawing_pad.setObjectName(u"drawing_pad")
        self.drawing_pad.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.drawing_pad.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.gridLayout_3.addWidget(self.drawing_pad, 4, 0, 1, 1)

        self.canvas_side_splitter.addWidget(self.drawing_pad_groupbox)
        self.controlnet_groupbox = QGroupBox(self.canvas_side_splitter)
        self.controlnet_groupbox.setObjectName(u"controlnet_groupbox")
        self.controlnet_groupbox.setCheckable(True)
        self.gridLayout_2 = QGridLayout(self.controlnet_groupbox)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.gridLayout_2.setContentsMargins(0, 0, 0, 0)
        self.controlnet = CustomGraphicsView(self.controlnet_groupbox)
        self.controlnet.setObjectName(u"controlnet")
        self.controlnet.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.controlnet.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.gridLayout_2.addWidget(self.controlnet, 0, 0, 1, 1)

        self.canvas_side_splitter.addWidget(self.controlnet_groupbox)
        self.canvas_splitter.addWidget(self.canvas_side_splitter)
        self.canvas_side_splitter_2 = QSplitter(self.canvas_splitter)
        self.canvas_side_splitter_2.setObjectName(u"canvas_side_splitter_2")
        self.canvas_side_splitter_2.setOrientation(Qt.Orientation.Vertical)
        self.groupBox = QGroupBox(self.canvas_side_splitter_2)
        self.groupBox.setObjectName(u"groupBox")
        self.gridLayout_4 = QGridLayout(self.groupBox)
        self.gridLayout_4.setObjectName(u"gridLayout_4")
        self.gridLayout_4.setContentsMargins(0, 0, 0, 0)
        self.canvas_container = CustomGraphicsView(self.groupBox)
        self.canvas_container.setObjectName(u"canvas_container")
        self.canvas_container.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.canvas_container.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.gridLayout_4.addWidget(self.canvas_container, 0, 0, 1, 1)

        self.canvas_side_splitter_2.addWidget(self.groupBox)
        self.groupBox_2 = QGroupBox(self.canvas_side_splitter_2)
        self.groupBox_2.setObjectName(u"groupBox_2")
        self.groupBox_2.setCheckable(True)
        self.gridLayout_5 = QGridLayout(self.groupBox_2)
        self.gridLayout_5.setObjectName(u"gridLayout_5")
        self.gridLayout_5.setContentsMargins(0, 0, 0, 0)
        self.controlnet_2 = CustomGraphicsView(self.groupBox_2)
        self.controlnet_2.setObjectName(u"controlnet_2")
        self.controlnet_2.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.controlnet_2.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.gridLayout_5.addWidget(self.controlnet_2, 0, 0, 1, 1)

        self.canvas_side_splitter_2.addWidget(self.groupBox_2)
        self.canvas_splitter.addWidget(self.canvas_side_splitter_2)

        self.gridLayout_6.addWidget(self.canvas_splitter, 0, 0, 1, 1)


        self.gridLayout.addWidget(self.central_widget, 0, 0, 1, 1)


        self.retranslateUi(canvas)
        self.controlnet_groupbox.toggled.connect(canvas.toggle_controlnet)
        self.drawing_pad_groupbox.clicked.connect(canvas.toggle_drawing_pad)
        self.groupBox_2.toggled.connect(canvas.toggle_outpaint)

        QMetaObject.connectSlotsByName(canvas)
    # setupUi

    def retranslateUi(self, canvas):
        canvas.setWindowTitle(QCoreApplication.translate("canvas", u"Form", None))
        self.drawing_pad_groupbox.setTitle(QCoreApplication.translate("canvas", u"Drawing pad", None))
        self.drawing_pad.setProperty("canvas_type", QCoreApplication.translate("canvas", u"brush", None))
        self.controlnet_groupbox.setTitle(QCoreApplication.translate("canvas", u"Controlnet", None))
        self.controlnet.setProperty("canvas_type", QCoreApplication.translate("canvas", u"controlnet", None))
        self.groupBox.setTitle(QCoreApplication.translate("canvas", u"Main", None))
        self.canvas_container.setProperty("canvas_type", QCoreApplication.translate("canvas", u"image", None))
        self.groupBox_2.setTitle(QCoreApplication.translate("canvas", u"Outpaint", None))
        self.controlnet_2.setProperty("canvas_type", QCoreApplication.translate("canvas", u"outpaint", None))
    # retranslateUi

