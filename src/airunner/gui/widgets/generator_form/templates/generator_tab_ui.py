# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'generator_tab.ui'
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
from PySide6.QtWidgets import (QApplication, QGridLayout, QSizePolicy, QTabWidget,
    QWidget)

from airunner.gui.widgets.generator_form.generator_form_widget import GeneratorForm

class Ui_generator_tab(object):
    def setupUi(self, generator_tab):
        if not generator_tab.objectName():
            generator_tab.setObjectName(u"generator_tab")
        generator_tab.resize(576, 1284)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(generator_tab.sizePolicy().hasHeightForWidth())
        generator_tab.setSizePolicy(sizePolicy)
        self.gridLayout_2 = QGridLayout(generator_tab)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.gridLayout_2.setContentsMargins(0, 0, 0, 0)
        self.generator_tabs = QTabWidget(generator_tab)
        self.generator_tabs.setObjectName(u"generator_tabs")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.generator_tabs.sizePolicy().hasHeightForWidth())
        self.generator_tabs.setSizePolicy(sizePolicy1)
        self.tab_stablediffusion = QWidget()
        self.tab_stablediffusion.setObjectName(u"tab_stablediffusion")
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.tab_stablediffusion.sizePolicy().hasHeightForWidth())
        self.tab_stablediffusion.setSizePolicy(sizePolicy2)
        self.gridLayout = QGridLayout(self.tab_stablediffusion)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.generator_form_stablediffusion = GeneratorForm(self.tab_stablediffusion)
        self.generator_form_stablediffusion.setObjectName(u"generator_form_stablediffusion")

        self.gridLayout.addWidget(self.generator_form_stablediffusion, 0, 0, 1, 1)

        self.generator_tabs.addTab(self.tab_stablediffusion, "")

        self.gridLayout_2.addWidget(self.generator_tabs, 0, 0, 1, 1)


        self.retranslateUi(generator_tab)
        self.generator_tabs.currentChanged.connect(generator_tab.handle_generator_tab_changed)

        self.generator_tabs.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(generator_tab)
    # setupUi

    def retranslateUi(self, generator_tab):
        generator_tab.setWindowTitle(QCoreApplication.translate("generator_tab", u"Form", None))
        self.generator_form_stablediffusion.setProperty("generator_section", QCoreApplication.translate("generator_tab", u"txt2img", None))
        self.generator_form_stablediffusion.setProperty("generator_name", QCoreApplication.translate("generator_tab", u"stablediffusion", None))
        self.generator_tabs.setTabText(self.generator_tabs.indexOf(self.tab_stablediffusion), QCoreApplication.translate("generator_tab", u"Stable Diffusion", None))
    # retranslateUi

