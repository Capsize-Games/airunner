# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'model_manager.ui'
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
from PySide6.QtWidgets import (QApplication, QGridLayout, QScrollArea, QSizePolicy,
    QTabWidget, QWidget)

from airunner.widgets.embeddings.embeddings_container_widget import EmbeddingsContainerWidget
from airunner.widgets.lora.lora_container_widget import LoraContainerWidget
from airunner.widgets.model_manager.custom_widget import CustomModelWidget
from airunner.widgets.model_manager.default_widget import DefaultModelWidget
from airunner.widgets.model_manager.import_widget import ImportWidget

class Ui_model_manager(object):
    def setupUi(self, model_manager):
        if not model_manager.objectName():
            model_manager.setObjectName(u"model_manager")
        model_manager.resize(472, 380)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(model_manager.sizePolicy().hasHeightForWidth())
        model_manager.setSizePolicy(sizePolicy)
        model_manager.setMinimumSize(QSize(0, 0))
        font = QFont()
        font.setPointSize(9)
        model_manager.setFont(font)
        self.gridLayout = QGridLayout(model_manager)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.tabs = QTabWidget(model_manager)
        self.tabs.setObjectName(u"tabs")
        sizePolicy.setHeightForWidth(self.tabs.sizePolicy().hasHeightForWidth())
        self.tabs.setSizePolicy(sizePolicy)
        self.tabs.setFont(font)
        self.tabs.setStyleSheet(u"")
        self.tabs.setTabsClosable(False)
        self.tabs.setTabBarAutoHide(False)
        self.default_tab = QWidget()
        self.default_tab.setObjectName(u"default_tab")
        self.gridLayout_2 = QGridLayout(self.default_tab)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.scrollArea = QScrollArea(self.default_tab)
        self.scrollArea.setObjectName(u"scrollArea")
        self.scrollArea.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 448, 333))
        self.gridLayout_5 = QGridLayout(self.scrollAreaWidgetContents)
        self.gridLayout_5.setObjectName(u"gridLayout_5")
        self.widget_2 = DefaultModelWidget(self.scrollAreaWidgetContents)
        self.widget_2.setObjectName(u"widget_2")

        self.gridLayout_5.addWidget(self.widget_2, 0, 0, 1, 1)

        self.scrollArea.setWidget(self.scrollAreaWidgetContents)

        self.gridLayout_2.addWidget(self.scrollArea, 0, 0, 1, 1)

        self.tabs.addTab(self.default_tab, "")
        self.custom_tab = QWidget()
        self.custom_tab.setObjectName(u"custom_tab")
        self.gridLayout_3 = QGridLayout(self.custom_tab)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.scrollArea_2 = QScrollArea(self.custom_tab)
        self.scrollArea_2.setObjectName(u"scrollArea_2")
        self.scrollArea_2.setWidgetResizable(True)
        self.scrollAreaWidgetContents_2 = QWidget()
        self.scrollAreaWidgetContents_2.setObjectName(u"scrollAreaWidgetContents_2")
        self.scrollAreaWidgetContents_2.setGeometry(QRect(0, 0, 448, 333))
        self.gridLayout_6 = QGridLayout(self.scrollAreaWidgetContents_2)
        self.gridLayout_6.setObjectName(u"gridLayout_6")
        self.widget = CustomModelWidget(self.scrollAreaWidgetContents_2)
        self.widget.setObjectName(u"widget")

        self.gridLayout_6.addWidget(self.widget, 0, 0, 1, 1)

        self.scrollArea_2.setWidget(self.scrollAreaWidgetContents_2)

        self.gridLayout_3.addWidget(self.scrollArea_2, 0, 0, 1, 1)

        self.tabs.addTab(self.custom_tab, "")
        self.lora_tab = QWidget()
        self.lora_tab.setObjectName(u"lora_tab")
        self.gridLayout_9 = QGridLayout(self.lora_tab)
        self.gridLayout_9.setObjectName(u"gridLayout_9")
        self.scrollArea_4 = QScrollArea(self.lora_tab)
        self.scrollArea_4.setObjectName(u"scrollArea_4")
        self.scrollArea_4.setWidgetResizable(True)
        self.scrollAreaWidgetContents_4 = QWidget()
        self.scrollAreaWidgetContents_4.setObjectName(u"scrollAreaWidgetContents_4")
        self.scrollAreaWidgetContents_4.setGeometry(QRect(0, 0, 448, 333))
        self.gridLayout_8 = QGridLayout(self.scrollAreaWidgetContents_4)
        self.gridLayout_8.setObjectName(u"gridLayout_8")
        self.lora_widget = LoraContainerWidget(self.scrollAreaWidgetContents_4)
        self.lora_widget.setObjectName(u"lora_widget")

        self.gridLayout_8.addWidget(self.lora_widget, 0, 0, 1, 1)

        self.scrollArea_4.setWidget(self.scrollAreaWidgetContents_4)

        self.gridLayout_9.addWidget(self.scrollArea_4, 0, 0, 1, 1)

        self.tabs.addTab(self.lora_tab, "")
        self.embeddings_tab = QWidget()
        self.embeddings_tab.setObjectName(u"embeddings_tab")
        self.gridLayout_11 = QGridLayout(self.embeddings_tab)
        self.gridLayout_11.setObjectName(u"gridLayout_11")
        self.scrollArea_5 = QScrollArea(self.embeddings_tab)
        self.scrollArea_5.setObjectName(u"scrollArea_5")
        self.scrollArea_5.setWidgetResizable(True)
        self.scrollAreaWidgetContents_5 = QWidget()
        self.scrollAreaWidgetContents_5.setObjectName(u"scrollAreaWidgetContents_5")
        self.scrollAreaWidgetContents_5.setGeometry(QRect(0, 0, 448, 333))
        self.gridLayout_10 = QGridLayout(self.scrollAreaWidgetContents_5)
        self.gridLayout_10.setObjectName(u"gridLayout_10")
        self.widget_4 = EmbeddingsContainerWidget(self.scrollAreaWidgetContents_5)
        self.widget_4.setObjectName(u"widget_4")

        self.gridLayout_10.addWidget(self.widget_4, 0, 0, 1, 1)

        self.scrollArea_5.setWidget(self.scrollAreaWidgetContents_5)

        self.gridLayout_11.addWidget(self.scrollArea_5, 0, 0, 1, 1)

        self.tabs.addTab(self.embeddings_tab, "")
        self.import_tab = QWidget()
        self.import_tab.setObjectName(u"import_tab")
        self.gridLayout_4 = QGridLayout(self.import_tab)
        self.gridLayout_4.setObjectName(u"gridLayout_4")
        self.scrollArea_3 = QScrollArea(self.import_tab)
        self.scrollArea_3.setObjectName(u"scrollArea_3")
        self.scrollArea_3.setWidgetResizable(True)
        self.scrollAreaWidgetContents_3 = QWidget()
        self.scrollAreaWidgetContents_3.setObjectName(u"scrollAreaWidgetContents_3")
        self.scrollAreaWidgetContents_3.setGeometry(QRect(0, 0, 448, 333))
        self.gridLayout_7 = QGridLayout(self.scrollAreaWidgetContents_3)
        self.gridLayout_7.setObjectName(u"gridLayout_7")
        self.widget_3 = ImportWidget(self.scrollAreaWidgetContents_3)
        self.widget_3.setObjectName(u"widget_3")

        self.gridLayout_7.addWidget(self.widget_3, 0, 0, 1, 1)

        self.scrollArea_3.setWidget(self.scrollAreaWidgetContents_3)

        self.gridLayout_4.addWidget(self.scrollArea_3, 0, 0, 1, 1)

        self.tabs.addTab(self.import_tab, "")

        self.gridLayout.addWidget(self.tabs, 0, 0, 1, 1)


        self.retranslateUi(model_manager)
        self.tabs.currentChanged.connect(model_manager.tab_changed)

        self.tabs.setCurrentIndex(4)


        QMetaObject.connectSlotsByName(model_manager)
    # setupUi

    def retranslateUi(self, model_manager):
        model_manager.setWindowTitle(QCoreApplication.translate("model_manager", u"Form", None))
        self.tabs.setTabText(self.tabs.indexOf(self.default_tab), QCoreApplication.translate("model_manager", u"Default", None))
        self.tabs.setTabText(self.tabs.indexOf(self.custom_tab), QCoreApplication.translate("model_manager", u"Imported", None))
        self.tabs.setTabText(self.tabs.indexOf(self.lora_tab), QCoreApplication.translate("model_manager", u"LoRA", None))
        self.tabs.setTabText(self.tabs.indexOf(self.embeddings_tab), QCoreApplication.translate("model_manager", u"Embeddings", None))
        self.tabs.setTabText(self.tabs.indexOf(self.import_tab), QCoreApplication.translate("model_manager", u"Import", None))
    # retranslateUi

