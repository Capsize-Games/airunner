# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'model_form.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QFrame,
    QGridLayout, QHeaderView, QLabel, QLineEdit,
    QSizePolicy, QSpacerItem, QTableWidget, QTableWidgetItem,
    QWidget)

class Ui_model_form_widget(object):
    def setupUi(self, model_form_widget):
        if not model_form_widget.objectName():
            model_form_widget.setObjectName(u"model_form_widget")
        model_form_widget.resize(536, 514)
        self.gridLayout_3 = QGridLayout(model_form_widget)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.gridLayout_3.setContentsMargins(0, 0, 0, 0)
        self.line = QFrame(model_form_widget)
        self.line.setObjectName(u"line")
        self.line.setFrameShape(QFrame.HLine)
        self.line.setFrameShadow(QFrame.Sunken)

        self.gridLayout_3.addWidget(self.line, 1, 0, 1, 1)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout_3.addItem(self.verticalSpacer, 12, 0, 1, 1)

        self.model_data_table = QTableWidget(model_form_widget)
        if (self.model_data_table.columnCount() < 1):
            self.model_data_table.setColumnCount(1)
        __qtablewidgetitem = QTableWidgetItem()
        self.model_data_table.setHorizontalHeaderItem(0, __qtablewidgetitem)
        if (self.model_data_table.rowCount() < 6):
            self.model_data_table.setRowCount(6)
        __qtablewidgetitem1 = QTableWidgetItem()
        self.model_data_table.setVerticalHeaderItem(0, __qtablewidgetitem1)
        __qtablewidgetitem2 = QTableWidgetItem()
        self.model_data_table.setVerticalHeaderItem(1, __qtablewidgetitem2)
        __qtablewidgetitem3 = QTableWidgetItem()
        self.model_data_table.setVerticalHeaderItem(2, __qtablewidgetitem3)
        __qtablewidgetitem4 = QTableWidgetItem()
        self.model_data_table.setVerticalHeaderItem(3, __qtablewidgetitem4)
        __qtablewidgetitem5 = QTableWidgetItem()
        self.model_data_table.setVerticalHeaderItem(4, __qtablewidgetitem5)
        __qtablewidgetitem6 = QTableWidgetItem()
        self.model_data_table.setVerticalHeaderItem(5, __qtablewidgetitem6)
        self.model_data_table.setObjectName(u"model_data_table")
        self.model_data_table.horizontalHeader().setVisible(False)
        self.model_data_table.verticalHeader().setVisible(True)

        self.gridLayout_3.addWidget(self.model_data_table, 0, 0, 1, 1)

        self.label_6 = QLabel(model_form_widget)
        self.label_6.setObjectName(u"label_6")

        self.gridLayout_3.addWidget(self.label_6, 2, 0, 1, 1)

        self.frame = QFrame(model_form_widget)
        self.frame.setObjectName(u"frame")
        self.frame.setFrameShape(QFrame.Panel)
        self.frame.setFrameShadow(QFrame.Raised)
        self.gridLayout_4 = QGridLayout(self.frame)
        self.gridLayout_4.setObjectName(u"gridLayout_4")
        self.model_name = QLineEdit(self.frame)
        self.model_name.setObjectName(u"model_name")
        font = QFont()
        font.setPointSize(8)
        self.model_name.setFont(font)

        self.gridLayout_4.addWidget(self.model_name, 1, 0, 1, 1)

        self.branch_line_edit = QLineEdit(self.frame)
        self.branch_line_edit.setObjectName(u"branch_line_edit")
        self.branch_line_edit.setFont(font)

        self.gridLayout_4.addWidget(self.branch_line_edit, 5, 0, 1, 1)

        self.path_label = QLabel(self.frame)
        self.path_label.setObjectName(u"path_label")
        font1 = QFont()
        font1.setPointSize(8)
        font1.setBold(True)
        self.path_label.setFont(font1)

        self.gridLayout_4.addWidget(self.path_label, 2, 0, 1, 1)

        self.gridLayout_2 = QGridLayout()
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.label_7 = QLabel(self.frame)
        self.label_7.setObjectName(u"label_7")
        self.label_7.setFont(font1)

        self.gridLayout_2.addWidget(self.label_7, 0, 1, 1, 1)

        self.category = QComboBox(self.frame)
        self.category.setObjectName(u"category")
        self.category.setFont(font)

        self.gridLayout_2.addWidget(self.category, 1, 0, 1, 1)

        self.label = QLabel(self.frame)
        self.label.setObjectName(u"label")
        self.label.setFont(font1)

        self.gridLayout_2.addWidget(self.label, 0, 0, 1, 1)

        self.model_type = QComboBox(self.frame)
        self.model_type.setObjectName(u"model_type")

        self.gridLayout_2.addWidget(self.model_type, 1, 2, 1, 1)

        self.diffuser_model_version = QComboBox(self.frame)
        self.diffuser_model_version.setObjectName(u"diffuser_model_version")
        self.diffuser_model_version.setFont(font)

        self.gridLayout_2.addWidget(self.diffuser_model_version, 1, 1, 1, 1)

        self.label_4 = QLabel(self.frame)
        self.label_4.setObjectName(u"label_4")
        self.label_4.setFont(font1)

        self.gridLayout_2.addWidget(self.label_4, 0, 2, 1, 1)


        self.gridLayout_4.addLayout(self.gridLayout_2, 6, 0, 1, 1)

        self.path_line_edit = QLineEdit(self.frame)
        self.path_line_edit.setObjectName(u"path_line_edit")
        self.path_line_edit.setFont(font)

        self.gridLayout_4.addWidget(self.path_line_edit, 3, 0, 1, 1)

        self.gridLayout = QGridLayout()
        self.gridLayout.setObjectName(u"gridLayout")
        self.label_2 = QLabel(self.frame)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setFont(font1)

        self.gridLayout.addWidget(self.label_2, 0, 0, 1, 1)

        self.label_3 = QLabel(self.frame)
        self.label_3.setObjectName(u"label_3")
        self.label_3.setFont(font1)

        self.gridLayout.addWidget(self.label_3, 0, 1, 1, 1)

        self.pipeline_action = QComboBox(self.frame)
        self.pipeline_action.setObjectName(u"pipeline_action")
        self.pipeline_action.setFont(font)

        self.gridLayout.addWidget(self.pipeline_action, 1, 0, 1, 1)

        self.pipeline_class_line_edit = QLineEdit(self.frame)
        self.pipeline_class_line_edit.setObjectName(u"pipeline_class_line_edit")
        self.pipeline_class_line_edit.setFont(font)

        self.gridLayout.addWidget(self.pipeline_class_line_edit, 1, 1, 1, 1)


        self.gridLayout_4.addLayout(self.gridLayout, 7, 0, 1, 1)

        self.enabled = QCheckBox(self.frame)
        self.enabled.setObjectName(u"enabled")
        self.enabled.setFont(font)

        self.gridLayout_4.addWidget(self.enabled, 8, 0, 1, 1)

        self.branch_label = QLabel(self.frame)
        self.branch_label.setObjectName(u"branch_label")
        self.branch_label.setFont(font1)

        self.gridLayout_4.addWidget(self.branch_label, 4, 0, 1, 1)

        self.label_5 = QLabel(self.frame)
        self.label_5.setObjectName(u"label_5")
        self.label_5.setFont(font1)

        self.gridLayout_4.addWidget(self.label_5, 0, 0, 1, 1)


        self.gridLayout_3.addWidget(self.frame, 5, 0, 1, 1)


        self.retranslateUi(model_form_widget)

        QMetaObject.connectSlotsByName(model_form_widget)
    # setupUi

    def retranslateUi(self, model_form_widget):
        model_form_widget.setWindowTitle(QCoreApplication.translate("model_form_widget", u"Form", None))
        ___qtablewidgetitem = self.model_data_table.horizontalHeaderItem(0)
        ___qtablewidgetitem.setText(QCoreApplication.translate("model_form_widget", u"New Column", None));
        ___qtablewidgetitem1 = self.model_data_table.verticalHeaderItem(1)
        ___qtablewidgetitem1.setText(QCoreApplication.translate("model_form_widget", u"POI", None));
        ___qtablewidgetitem2 = self.model_data_table.verticalHeaderItem(2)
        ___qtablewidgetitem2.setText(QCoreApplication.translate("model_form_widget", u"Require Credit", None));
        ___qtablewidgetitem3 = self.model_data_table.verticalHeaderItem(3)
        ___qtablewidgetitem3.setText(QCoreApplication.translate("model_form_widget", u"Allow Commercial Use", None));
        ___qtablewidgetitem4 = self.model_data_table.verticalHeaderItem(4)
        ___qtablewidgetitem4.setText(QCoreApplication.translate("model_form_widget", u"Allow Derivatives", None));
        ___qtablewidgetitem5 = self.model_data_table.verticalHeaderItem(5)
        ___qtablewidgetitem5.setText(QCoreApplication.translate("model_form_widget", u"Allow Different License", None));
        self.label_6.setText(QCoreApplication.translate("model_form_widget", u"Save Data", None))
        self.model_name.setPlaceholderText(QCoreApplication.translate("model_form_widget", u"Name", None))
        self.branch_line_edit.setPlaceholderText(QCoreApplication.translate("model_form_widget", u"Branch", None))
        self.path_label.setText(QCoreApplication.translate("model_form_widget", u"Path", None))
        self.label_7.setText(QCoreApplication.translate("model_form_widget", u"Diffuser Model Version", None))
        self.label.setText(QCoreApplication.translate("model_form_widget", u"Category", None))
        self.label_4.setText(QCoreApplication.translate("model_form_widget", u"Model Type", None))
        self.path_line_edit.setPlaceholderText(QCoreApplication.translate("model_form_widget", u"Path", None))
        self.label_2.setText(QCoreApplication.translate("model_form_widget", u"Pipeline Action", None))
        self.label_3.setText(QCoreApplication.translate("model_form_widget", u"Pipeline Class", None))
        self.pipeline_class_line_edit.setPlaceholderText(QCoreApplication.translate("model_form_widget", u"Pipeline class", None))
        self.enabled.setText(QCoreApplication.translate("model_form_widget", u"Enabled", None))
        self.branch_label.setText(QCoreApplication.translate("model_form_widget", u"Branch", None))
        self.label_5.setText(QCoreApplication.translate("model_form_widget", u"Name", None))
    # retranslateUi

