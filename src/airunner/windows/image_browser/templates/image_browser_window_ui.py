# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'image_browser_window.ui'
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
from PySide6.QtWidgets import (QApplication, QDialog, QGridLayout, QSizePolicy,
    QWidget)

from airunner.widgets.image.image_panel_widget import ImagePanelWidget

class Ui_image_browser_window(object):
    def setupUi(self, image_browser_window):
        if not image_browser_window.objectName():
            image_browser_window.setObjectName(u"image_browser_window")
        image_browser_window.resize(400, 300)
        self.gridLayout = QGridLayout(image_browser_window)
        self.gridLayout.setObjectName(u"gridLayout")
        self.image_panel = ImagePanelWidget(image_browser_window)
        self.image_panel.setObjectName(u"image_panel")

        self.gridLayout.addWidget(self.image_panel, 0, 0, 1, 1)


        self.retranslateUi(image_browser_window)

        QMetaObject.connectSlotsByName(image_browser_window)
    # setupUi

    def retranslateUi(self, image_browser_window):
        image_browser_window.setWindowTitle(QCoreApplication.translate("image_browser_window", u"Dialog", None))
    # retranslateUi

