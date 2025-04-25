# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'rag_settings.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QGridLayout,
    QGroupBox, QLineEdit, QSizePolicy, QSpacerItem,
    QWidget)

class Ui_rag_settings(object):
    def setupUi(self, rag_settings):
        if not rag_settings.objectName():
            rag_settings.setObjectName(u"rag_settings")
        rag_settings.resize(400, 300)
        self.gridLayout_2 = QGridLayout(rag_settings)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.enabled = QCheckBox(rag_settings)
        self.enabled.setObjectName(u"enabled")

        self.gridLayout_2.addWidget(self.enabled, 0, 0, 1, 1)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout_2.addItem(self.verticalSpacer, 3, 0, 1, 1)

        self.model_path_container = QGroupBox(rag_settings)
        self.model_path_container.setObjectName(u"model_path_container")
        self.gridLayout = QGridLayout(self.model_path_container)
        self.gridLayout.setObjectName(u"gridLayout")
        self.model_path = QLineEdit(self.model_path_container)
        self.model_path.setObjectName(u"model_path")

        self.gridLayout.addWidget(self.model_path, 0, 0, 1, 1)


        self.gridLayout_2.addWidget(self.model_path_container, 2, 0, 1, 1)

        self.groupBox_2 = QGroupBox(rag_settings)
        self.groupBox_2.setObjectName(u"groupBox_2")
        self.gridLayout_3 = QGridLayout(self.groupBox_2)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.service = QComboBox(self.groupBox_2)
        self.service.setObjectName(u"service")

        self.gridLayout_3.addWidget(self.service, 0, 0, 1, 1)


        self.gridLayout_2.addWidget(self.groupBox_2, 1, 0, 1, 1)


        self.retranslateUi(rag_settings)
        self.enabled.toggled.connect(rag_settings.on_enabled_toggled)
        self.service.currentTextChanged.connect(rag_settings.on_service_currentTextChanged)
        self.model_path.textChanged.connect(rag_settings.on_model_path_textChanged)

        QMetaObject.connectSlotsByName(rag_settings)
    # setupUi

    def retranslateUi(self, rag_settings):
        rag_settings.setWindowTitle(QCoreApplication.translate("rag_settings", u"Form", None))
        self.enabled.setText(QCoreApplication.translate("rag_settings", u"Enable RAG", None))
        self.model_path_container.setTitle(QCoreApplication.translate("rag_settings", u"Model Path", None))
        self.groupBox_2.setTitle(QCoreApplication.translate("rag_settings", u"Service", None))
    # retranslateUi

