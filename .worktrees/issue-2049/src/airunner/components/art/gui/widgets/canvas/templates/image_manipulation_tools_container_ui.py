# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'image_manipulation_tools_container.ui'
##
## Created by: Qt User Interface Compiler version 6.9.0
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
from PySide6.QtWidgets import (QApplication, QGridLayout, QSizePolicy, QTabWidget,
    QWidget)

from airunner.components.art.gui.widgets.canvas.input_image_container import InputImageContainer

class Ui_image_manipulation_tools_container(object):
    def setupUi(self, image_manipulation_tools_container):
        if not image_manipulation_tools_container.objectName():
            image_manipulation_tools_container.setObjectName(u"image_manipulation_tools_container")
        image_manipulation_tools_container.resize(400, 300)
        self.gridLayout = QGridLayout(image_manipulation_tools_container)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.image_manipulation_tools_tab_container = QTabWidget(image_manipulation_tools_container)
        self.image_manipulation_tools_tab_container.setObjectName(u"image_manipulation_tools_tab_container")
        self.image_manipulation_tools_tab_container.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
        self.tab = QWidget()
        self.tab.setObjectName(u"tab")
        self.gridLayout_2 = QGridLayout(self.tab)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.gridLayout_2.setContentsMargins(0, 0, 0, 0)
        self.image_to_image = InputImageContainer(self.tab)
        self.image_to_image.setObjectName(u"image_to_image")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.image_to_image.sizePolicy().hasHeightForWidth())
        self.image_to_image.setSizePolicy(sizePolicy)

        self.gridLayout_2.addWidget(self.image_to_image, 0, 0, 1, 1)

        self.image_manipulation_tools_tab_container.addTab(self.tab, "")
        self.tab_2 = QWidget()
        self.tab_2.setObjectName(u"tab_2")
        self.gridLayout_3 = QGridLayout(self.tab_2)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.gridLayout_3.setContentsMargins(0, 0, 0, 0)
        self.controlnet_image = InputImageContainer(self.tab_2)
        self.controlnet_image.setObjectName(u"controlnet_image")
        sizePolicy.setHeightForWidth(self.controlnet_image.sizePolicy().hasHeightForWidth())
        self.controlnet_image.setSizePolicy(sizePolicy)

        self.gridLayout_3.addWidget(self.controlnet_image, 0, 0, 1, 1)

        self.image_manipulation_tools_tab_container.addTab(self.tab_2, "")
        self.tab_3 = QWidget()
        self.tab_3.setObjectName(u"tab_3")
        self.gridLayout_4 = QGridLayout(self.tab_3)
        self.gridLayout_4.setObjectName(u"gridLayout_4")
        self.gridLayout_4.setContentsMargins(0, 0, 0, 0)
        self.widget_2 = InputImageContainer(self.tab_3)
        self.widget_2.setObjectName(u"widget_2")

        self.gridLayout_4.addWidget(self.widget_2, 0, 0, 1, 1)

        self.image_manipulation_tools_tab_container.addTab(self.tab_3, "")

        self.gridLayout.addWidget(self.image_manipulation_tools_tab_container, 0, 0, 1, 1)


        self.retranslateUi(image_manipulation_tools_container)

        self.image_manipulation_tools_tab_container.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(image_manipulation_tools_container)
    # setupUi

    def retranslateUi(self, image_manipulation_tools_container):
        image_manipulation_tools_container.setWindowTitle(QCoreApplication.translate("image_manipulation_tools_container", u"Form", None))
        self.image_to_image.setProperty(u"settings_key", QCoreApplication.translate("image_manipulation_tools_container", u"image_to_image_settings", None))
        self.image_manipulation_tools_tab_container.setTabText(self.image_manipulation_tools_tab_container.indexOf(self.tab), QCoreApplication.translate("image_manipulation_tools_container", u"Image-to-Image", None))
        self.controlnet_image.setProperty(u"settings_key", QCoreApplication.translate("image_manipulation_tools_container", u"controlnet_settings", None))
        self.image_manipulation_tools_tab_container.setTabText(self.image_manipulation_tools_tab_container.indexOf(self.tab_2), QCoreApplication.translate("image_manipulation_tools_container", u"Controlnet", None))
        self.widget_2.setProperty(u"settings_key", QCoreApplication.translate("image_manipulation_tools_container", u"outpaint_settings", None))
        self.image_manipulation_tools_tab_container.setTabText(self.image_manipulation_tools_tab_container.indexOf(self.tab_3), QCoreApplication.translate("image_manipulation_tools_container", u"Inpaint", None))
    # retranslateUi

