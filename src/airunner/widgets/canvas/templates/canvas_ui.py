# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'canvas.ui'
##
## Created by: Qt User Interface Compiler version 6.4.2
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
    QSizePolicy, QWidget)

class Ui_canvas(object):
    def setupUi(self, canvas):
        if not canvas.objectName():
            canvas.setObjectName(u"canvas")
        canvas.resize(218, 218)
        sizePolicy = QSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(canvas.sizePolicy().hasHeightForWidth())
        canvas.setSizePolicy(sizePolicy)
        canvas.setMinimumSize(QSize(66, 66))
        canvas.setStyleSheet(u"b")
        self.gridLayout = QGridLayout(canvas)
        self.gridLayout.setSpacing(0)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.central_widget = QWidget(canvas)
        self.central_widget.setObjectName(u"central_widget")
        sizePolicy.setHeightForWidth(self.central_widget.sizePolicy().hasHeightForWidth())
        self.central_widget.setSizePolicy(sizePolicy)
        self.central_widget.setMinimumSize(QSize(200, 200))
        self.central_widget.setStyleSheet(u"")
        self.gridLayout_2 = QGridLayout(self.central_widget)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.gridLayout_2.setHorizontalSpacing(0)
        self.gridLayout_2.setVerticalSpacing(3)
        self.gridLayout_2.setContentsMargins(0, 0, 0, 3)
        self.canvas_position = QLabel(self.central_widget)
        self.canvas_position.setObjectName(u"canvas_position")
        sizePolicy1 = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.canvas_position.sizePolicy().hasHeightForWidth())
        self.canvas_position.setSizePolicy(sizePolicy1)
        font = QFont()
        font.setPointSize(8)
        self.canvas_position.setFont(font)
        self.canvas_position.setAlignment(Qt.AlignRight|Qt.AlignTrailing|Qt.AlignVCenter)

        self.gridLayout_2.addWidget(self.canvas_position, 1, 0, 1, 1)

        self.canvas_container = QFrame(self.central_widget)
        self.canvas_container.setObjectName(u"canvas_container")
        self.canvas_container.setFrameShape(QFrame.NoFrame)
        self.canvas_container.setFrameShadow(QFrame.Plain)

        self.gridLayout_2.addWidget(self.canvas_container, 0, 0, 1, 1)


        self.gridLayout.addWidget(self.central_widget, 0, 0, 1, 1)


        self.retranslateUi(canvas)

        QMetaObject.connectSlotsByName(canvas)
    # setupUi

    def retranslateUi(self, canvas):
        canvas.setWindowTitle(QCoreApplication.translate("canvas", u"Form", None))
        self.canvas_position.setText(QCoreApplication.translate("canvas", u"TextLabel", None))
    # retranslateUi

