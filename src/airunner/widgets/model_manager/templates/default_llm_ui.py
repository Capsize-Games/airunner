# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'default_llm.ui'
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
    QHBoxLayout, QLineEdit, QScrollArea, QSizePolicy,
    QVBoxLayout, QWidget)

class Ui_default_llm_model_widget(object):
    def setupUi(self, default_llm_model_widget):
        if not default_llm_model_widget.objectName():
            default_llm_model_widget.setObjectName(u"default_llm_model_widget")
        default_llm_model_widget.resize(496, 434)
        self.gridLayout = QGridLayout(default_llm_model_widget)
        self.gridLayout.setObjectName(u"gridLayout")
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.comboBox = QComboBox(default_llm_model_widget)
        self.comboBox.setObjectName(u"comboBox")

        self.horizontalLayout.addWidget(self.comboBox)

        self.toggle_all = QCheckBox(default_llm_model_widget)
        self.toggle_all.setObjectName(u"toggle_all")
        font = QFont()
        font.setPointSize(8)
        self.toggle_all.setFont(font)
        self.toggle_all.setTristate(True)

        self.horizontalLayout.addWidget(self.toggle_all)


        self.gridLayout.addLayout(self.horizontalLayout, 0, 0, 1, 1)

        self.default_scroll_area = QScrollArea(default_llm_model_widget)
        self.default_scroll_area.setObjectName(u"default_scroll_area")
        self.default_scroll_area.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 476, 350))
        self.verticalLayout = QVBoxLayout(self.scrollAreaWidgetContents)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.default_scroll_area.setWidget(self.scrollAreaWidgetContents)

        self.gridLayout.addWidget(self.default_scroll_area, 2, 0, 1, 1)

        self.lineEdit = QLineEdit(default_llm_model_widget)
        self.lineEdit.setObjectName(u"lineEdit")

        self.gridLayout.addWidget(self.lineEdit, 1, 0, 1, 1)


        self.retranslateUi(default_llm_model_widget)
        self.comboBox.currentTextChanged.connect(default_llm_model_widget.mode_type_changed)
        self.lineEdit.textEdited.connect(default_llm_model_widget.search_text_changed)
        self.toggle_all.stateChanged.connect(default_llm_model_widget.toggle_all_state_change)

        QMetaObject.connectSlotsByName(default_llm_model_widget)
    # setupUi

    def retranslateUi(self, default_llm_model_widget):
        default_llm_model_widget.setWindowTitle(QCoreApplication.translate("default_llm_model_widget", u"Form", None))
        self.toggle_all.setText(QCoreApplication.translate("default_llm_model_widget", u"Toggle all", None))
        self.lineEdit.setPlaceholderText(QCoreApplication.translate("default_llm_model_widget", u"Search models", None))
    # retranslateUi

