# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'custom.ui'
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
    QHBoxLayout, QLineEdit, QPushButton, QScrollArea,
    QSizePolicy, QVBoxLayout, QWidget)

class Ui_custom_model_widget(object):
    def setupUi(self, custom_model_widget):
        if not custom_model_widget.objectName():
            custom_model_widget.setObjectName(u"custom_model_widget")
        custom_model_widget.resize(503, 300)
        self.gridLayout = QGridLayout(custom_model_widget)
        self.gridLayout.setObjectName(u"gridLayout")
        self.scan_for_models_button = QPushButton(custom_model_widget)
        self.scan_for_models_button.setObjectName(u"scan_for_models_button")
        font = QFont()
        font.setPointSize(8)
        self.scan_for_models_button.setFont(font)

        self.gridLayout.addWidget(self.scan_for_models_button, 4, 0, 1, 1)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.comboBox = QComboBox(custom_model_widget)
        self.comboBox.setObjectName(u"comboBox")

        self.horizontalLayout.addWidget(self.comboBox)

        self.toggle_all = QCheckBox(custom_model_widget)
        self.toggle_all.setObjectName(u"toggle_all")
        self.toggle_all.setFont(font)

        self.horizontalLayout.addWidget(self.toggle_all)


        self.gridLayout.addLayout(self.horizontalLayout, 1, 0, 1, 1)

        self.custom_scroll_area = QScrollArea(custom_model_widget)
        self.custom_scroll_area.setObjectName(u"custom_scroll_area")
        self.custom_scroll_area.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 483, 187))
        self.verticalLayout_2 = QVBoxLayout(self.scrollAreaWidgetContents)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.custom_scroll_area.setWidget(self.scrollAreaWidgetContents)

        self.gridLayout.addWidget(self.custom_scroll_area, 3, 0, 1, 1)

        self.lineEdit = QLineEdit(custom_model_widget)
        self.lineEdit.setObjectName(u"lineEdit")

        self.gridLayout.addWidget(self.lineEdit, 2, 0, 1, 1)


        self.retranslateUi(custom_model_widget)
        self.scan_for_models_button.clicked.connect(custom_model_widget.action_button_clicked_scan_for_models)
        self.comboBox.currentTextChanged.connect(custom_model_widget.mode_type_changed)
        self.toggle_all.toggled.connect(custom_model_widget.toggle_all_toggled)
        self.lineEdit.textEdited.connect(custom_model_widget.search_text_edited)

        QMetaObject.connectSlotsByName(custom_model_widget)
    # setupUi

    def retranslateUi(self, custom_model_widget):
        custom_model_widget.setWindowTitle(QCoreApplication.translate("custom_model_widget", u"Form", None))
        self.scan_for_models_button.setText(QCoreApplication.translate("custom_model_widget", u"Scan for models", None))
        self.toggle_all.setText(QCoreApplication.translate("custom_model_widget", u"Toggle all", None))
        self.lineEdit.setPlaceholderText(QCoreApplication.translate("custom_model_widget", u"Search models", None))
    # retranslateUi

