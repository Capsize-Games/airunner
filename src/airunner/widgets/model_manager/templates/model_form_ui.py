# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'model_form.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QFrame,
    QGridLayout, QHBoxLayout, QLabel, QLineEdit,
    QSizePolicy, QSpacerItem, QWidget)

class Ui_model_form_widget(object):
    def setupUi(self, model_form_widget):
        if not model_form_widget.objectName():
            model_form_widget.setObjectName(u"model_form_widget")
        model_form_widget.resize(536, 688)
        self.gridLayout_5 = QGridLayout(model_form_widget)
        self.gridLayout_5.setObjectName(u"gridLayout_5")
        self.model_data = QGridLayout()
        self.model_data.setObjectName(u"model_data")
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.label_3 = QLabel(model_form_widget)
        self.label_3.setObjectName(u"label_3")
        font = QFont()
        font.setBold(True)
        self.label_3.setFont(font)

        self.horizontalLayout.addWidget(self.label_3)

        self.poi = QLabel(model_form_widget)
        self.poi.setObjectName(u"poi")

        self.horizontalLayout.addWidget(self.poi)


        self.model_data.addLayout(self.horizontalLayout, 0, 0, 1, 1)

        self.line_2 = QFrame(model_form_widget)
        self.line_2.setObjectName(u"line_2")
        self.line_2.setFrameShape(QFrame.Shape.HLine)
        self.line_2.setFrameShadow(QFrame.Shadow.Sunken)

        self.model_data.addWidget(self.line_2, 1, 0, 1, 1)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.label_9 = QLabel(model_form_widget)
        self.label_9.setObjectName(u"label_9")
        self.label_9.setFont(font)

        self.horizontalLayout_2.addWidget(self.label_9)

        self.require_credit = QLabel(model_form_widget)
        self.require_credit.setObjectName(u"require_credit")

        self.horizontalLayout_2.addWidget(self.require_credit)


        self.model_data.addLayout(self.horizontalLayout_2, 2, 0, 1, 1)

        self.line_3 = QFrame(model_form_widget)
        self.line_3.setObjectName(u"line_3")
        self.line_3.setFrameShape(QFrame.Shape.HLine)
        self.line_3.setFrameShadow(QFrame.Shadow.Sunken)

        self.model_data.addWidget(self.line_3, 3, 0, 1, 1)

        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.label_11 = QLabel(model_form_widget)
        self.label_11.setObjectName(u"label_11")
        self.label_11.setFont(font)

        self.horizontalLayout_3.addWidget(self.label_11)

        self.allow_commercial_use = QLabel(model_form_widget)
        self.allow_commercial_use.setObjectName(u"allow_commercial_use")

        self.horizontalLayout_3.addWidget(self.allow_commercial_use)


        self.model_data.addLayout(self.horizontalLayout_3, 4, 0, 1, 1)

        self.line_4 = QFrame(model_form_widget)
        self.line_4.setObjectName(u"line_4")
        self.line_4.setFrameShape(QFrame.Shape.HLine)
        self.line_4.setFrameShadow(QFrame.Shadow.Sunken)

        self.model_data.addWidget(self.line_4, 5, 0, 1, 1)

        self.horizontalLayout_4 = QHBoxLayout()
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.label_14 = QLabel(model_form_widget)
        self.label_14.setObjectName(u"label_14")
        self.label_14.setFont(font)

        self.horizontalLayout_4.addWidget(self.label_14)

        self.allow_derivatives = QLabel(model_form_widget)
        self.allow_derivatives.setObjectName(u"allow_derivatives")

        self.horizontalLayout_4.addWidget(self.allow_derivatives)


        self.model_data.addLayout(self.horizontalLayout_4, 6, 0, 1, 1)

        self.line_5 = QFrame(model_form_widget)
        self.line_5.setObjectName(u"line_5")
        self.line_5.setFrameShape(QFrame.Shape.HLine)
        self.line_5.setFrameShadow(QFrame.Shadow.Sunken)

        self.model_data.addWidget(self.line_5, 7, 0, 1, 1)

        self.horizontalLayout_5 = QHBoxLayout()
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")
        self.label_16 = QLabel(model_form_widget)
        self.label_16.setObjectName(u"label_16")
        self.label_16.setFont(font)

        self.horizontalLayout_5.addWidget(self.label_16)

        self.allow_different_license = QLabel(model_form_widget)
        self.allow_different_license.setObjectName(u"allow_different_license")

        self.horizontalLayout_5.addWidget(self.allow_different_license)


        self.model_data.addLayout(self.horizontalLayout_5, 8, 0, 1, 1)


        self.gridLayout_5.addLayout(self.model_data, 0, 0, 1, 2)

        self.line = QFrame(model_form_widget)
        self.line.setObjectName(u"line")
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout_5.addWidget(self.line, 1, 0, 1, 2)

        self.label_6 = QLabel(model_form_widget)
        self.label_6.setObjectName(u"label_6")
        self.label_6.setFont(font)

        self.gridLayout_5.addWidget(self.label_6, 2, 0, 1, 1)

        self.frame = QFrame(model_form_widget)
        self.frame.setObjectName(u"frame")
        self.frame.setFrameShape(QFrame.Panel)
        self.frame.setFrameShadow(QFrame.Raised)
        self.gridLayout_4 = QGridLayout(self.frame)
        self.gridLayout_4.setObjectName(u"gridLayout_4")
        self.model_name = QLineEdit(self.frame)
        self.model_name.setObjectName(u"model_name")
        font1 = QFont()
        font1.setPointSize(8)
        self.model_name.setFont(font1)

        self.gridLayout_4.addWidget(self.model_name, 1, 0, 1, 1)

        self.branch_line_edit = QLineEdit(self.frame)
        self.branch_line_edit.setObjectName(u"branch_line_edit")
        self.branch_line_edit.setFont(font1)

        self.gridLayout_4.addWidget(self.branch_line_edit, 5, 0, 1, 1)

        self.path_label = QLabel(self.frame)
        self.path_label.setObjectName(u"path_label")
        font2 = QFont()
        font2.setPointSize(8)
        font2.setBold(True)
        self.path_label.setFont(font2)

        self.gridLayout_4.addWidget(self.path_label, 2, 0, 1, 1)

        self.gridLayout_2 = QGridLayout()
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.label_7 = QLabel(self.frame)
        self.label_7.setObjectName(u"label_7")
        self.label_7.setFont(font2)

        self.gridLayout_2.addWidget(self.label_7, 0, 1, 1, 1)

        self.category = QComboBox(self.frame)
        self.category.setObjectName(u"category")
        self.category.setFont(font1)

        self.gridLayout_2.addWidget(self.category, 1, 0, 1, 1)

        self.label = QLabel(self.frame)
        self.label.setObjectName(u"label")
        self.label.setFont(font2)

        self.gridLayout_2.addWidget(self.label, 0, 0, 1, 1)

        self.model_type = QComboBox(self.frame)
        self.model_type.setObjectName(u"model_type")

        self.gridLayout_2.addWidget(self.model_type, 1, 2, 1, 1)

        self.diffuser_model_version = QComboBox(self.frame)
        self.diffuser_model_version.setObjectName(u"diffuser_model_version")
        self.diffuser_model_version.setFont(font1)

        self.gridLayout_2.addWidget(self.diffuser_model_version, 1, 1, 1, 1)

        self.label_4 = QLabel(self.frame)
        self.label_4.setObjectName(u"label_4")
        self.label_4.setFont(font2)

        self.gridLayout_2.addWidget(self.label_4, 0, 2, 1, 1)


        self.gridLayout_4.addLayout(self.gridLayout_2, 6, 0, 1, 1)

        self.path_line_edit = QLineEdit(self.frame)
        self.path_line_edit.setObjectName(u"path_line_edit")
        self.path_line_edit.setFont(font1)

        self.gridLayout_4.addWidget(self.path_line_edit, 3, 0, 1, 1)

        self.gridLayout = QGridLayout()
        self.gridLayout.setObjectName(u"gridLayout")
        self.label_2 = QLabel(self.frame)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setFont(font2)

        self.gridLayout.addWidget(self.label_2, 0, 0, 1, 1)

        self.pipeline_action = QComboBox(self.frame)
        self.pipeline_action.setObjectName(u"pipeline_action")
        self.pipeline_action.setFont(font1)

        self.gridLayout.addWidget(self.pipeline_action, 1, 0, 1, 1)


        self.gridLayout_4.addLayout(self.gridLayout, 7, 0, 1, 1)

        self.enabled = QCheckBox(self.frame)
        self.enabled.setObjectName(u"enabled")
        self.enabled.setFont(font1)

        self.gridLayout_4.addWidget(self.enabled, 8, 0, 1, 1)

        self.branch_label = QLabel(self.frame)
        self.branch_label.setObjectName(u"branch_label")
        self.branch_label.setFont(font2)

        self.gridLayout_4.addWidget(self.branch_label, 4, 0, 1, 1)

        self.label_5 = QLabel(self.frame)
        self.label_5.setObjectName(u"label_5")
        self.label_5.setFont(font2)

        self.gridLayout_4.addWidget(self.label_5, 0, 0, 1, 1)


        self.gridLayout_5.addWidget(self.frame, 3, 0, 1, 2)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout_5.addItem(self.verticalSpacer, 4, 1, 1, 1)


        self.retranslateUi(model_form_widget)

        QMetaObject.connectSlotsByName(model_form_widget)
    # setupUi

    def retranslateUi(self, model_form_widget):
        model_form_widget.setWindowTitle(QCoreApplication.translate("model_form_widget", u"Form", None))
        self.label_3.setText(QCoreApplication.translate("model_form_widget", u"POI", None))
        self.poi.setText(QCoreApplication.translate("model_form_widget", u"POI Value", None))
        self.label_9.setText(QCoreApplication.translate("model_form_widget", u"Require Credit", None))
        self.require_credit.setText(QCoreApplication.translate("model_form_widget", u"Require credit value", None))
        self.label_11.setText(QCoreApplication.translate("model_form_widget", u"Allow Commercial Use", None))
        self.allow_commercial_use.setText(QCoreApplication.translate("model_form_widget", u"Allow commercial use value", None))
        self.label_14.setText(QCoreApplication.translate("model_form_widget", u"Allow derivatives value", None))
        self.allow_derivatives.setText(QCoreApplication.translate("model_form_widget", u"Allow Derivatives", None))
        self.label_16.setText(QCoreApplication.translate("model_form_widget", u"Allow different license value", None))
        self.allow_different_license.setText(QCoreApplication.translate("model_form_widget", u"Allow Different License", None))
        self.label_6.setText(QCoreApplication.translate("model_form_widget", u"Save Data", None))
        self.model_name.setPlaceholderText(QCoreApplication.translate("model_form_widget", u"Name", None))
        self.branch_line_edit.setPlaceholderText(QCoreApplication.translate("model_form_widget", u"Branch", None))
        self.path_label.setText(QCoreApplication.translate("model_form_widget", u"Path", None))
        self.label_7.setText(QCoreApplication.translate("model_form_widget", u"Diffuser Model Version", None))
        self.label.setText(QCoreApplication.translate("model_form_widget", u"Category", None))
        self.label_4.setText(QCoreApplication.translate("model_form_widget", u"Model Type", None))
        self.path_line_edit.setPlaceholderText(QCoreApplication.translate("model_form_widget", u"Path", None))
        self.label_2.setText(QCoreApplication.translate("model_form_widget", u"Pipeline Action", None))
        self.enabled.setText(QCoreApplication.translate("model_form_widget", u"Enabled", None))
        self.branch_label.setText(QCoreApplication.translate("model_form_widget", u"Branch", None))
        self.label_5.setText(QCoreApplication.translate("model_form_widget", u"Name", None))
    # retranslateUi

