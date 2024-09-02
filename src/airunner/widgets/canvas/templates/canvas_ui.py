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
from PySide6.QtWidgets import (QApplication, QGridLayout, QSizePolicy, QSplitter,
    QWidget)

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
        self.gridLayout_2 = QGridLayout(self.central_widget)
        self.gridLayout_2.setSpacing(0)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.gridLayout_2.setContentsMargins(0, 0, 0, 0)
        self.canvas_splitter = QSplitter(self.central_widget)
        self.canvas_splitter.setObjectName(u"canvas_splitter")
        self.canvas_splitter.setOrientation(Qt.Orientation.Horizontal)
        self.drawing_pad_groupbox = QWidget(self.canvas_splitter)
        self.drawing_pad_groupbox.setObjectName(u"drawing_pad_groupbox")
        self.gridLayout_3 = QGridLayout(self.drawing_pad_groupbox)
        self.gridLayout_3.setSpacing(0)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.gridLayout_3.setContentsMargins(0, 0, 0, 0)
        self.drawing_pad = CustomGraphicsView(self.drawing_pad_groupbox)
        self.drawing_pad.setObjectName(u"drawing_pad")
        self.drawing_pad.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.drawing_pad.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.gridLayout_3.addWidget(self.drawing_pad, 4, 0, 1, 1)

        self.canvas_splitter.addWidget(self.drawing_pad_groupbox)
        self.widget = QWidget(self.canvas_splitter)
        self.widget.setObjectName(u"widget")
        self.gridLayout_4 = QGridLayout(self.widget)
        self.gridLayout_4.setSpacing(0)
        self.gridLayout_4.setObjectName(u"gridLayout_4")
        self.gridLayout_4.setContentsMargins(0, 0, 0, 0)
        self.canvas_container = CustomGraphicsView(self.widget)
        self.canvas_container.setObjectName(u"canvas_container")
        self.canvas_container.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.canvas_container.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.gridLayout_4.addWidget(self.canvas_container, 0, 0, 1, 1)

        self.canvas_splitter.addWidget(self.widget)

        self.gridLayout_2.addWidget(self.canvas_splitter, 0, 0, 1, 1)


        self.gridLayout.addWidget(self.central_widget, 0, 0, 1, 1)


        self.retranslateUi(canvas)

        QMetaObject.connectSlotsByName(canvas)
    # setupUi

    def retranslateUi(self, canvas):
        canvas.setWindowTitle(QCoreApplication.translate("canvas", u"Form", None))
        self.drawing_pad.setProperty("canvas_type", QCoreApplication.translate("canvas", u"brush", None))
        self.canvas_container.setProperty("canvas_type", QCoreApplication.translate("canvas", u"image", None))
    # retranslateUi

