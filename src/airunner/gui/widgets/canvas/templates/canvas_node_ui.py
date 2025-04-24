# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'canvas_node.ui'
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
from PySide6.QtWidgets import (QApplication, QGridLayout, QSizePolicy, QWidget)

from airunner.gui.widgets.canvas.canvas_widget import CanvasWidget

class Ui_canvas_node(object):
    def setupUi(self, canvas_node):
        if not canvas_node.objectName():
            canvas_node.setObjectName(u"canvas_node")
        canvas_node.resize(400, 300)
        self.gridLayout = QGridLayout(canvas_node)
        self.gridLayout.setObjectName(u"gridLayout")
        self.widget = CanvasWidget(canvas_node)
        self.widget.setObjectName(u"widget")

        self.gridLayout.addWidget(self.widget, 0, 0, 1, 1)


        self.retranslateUi(canvas_node)

        QMetaObject.connectSlotsByName(canvas_node)
    # setupUi

    def retranslateUi(self, canvas_node):
        canvas_node.setWindowTitle(QCoreApplication.translate("canvas_node", u"Form", None))
    # retranslateUi

