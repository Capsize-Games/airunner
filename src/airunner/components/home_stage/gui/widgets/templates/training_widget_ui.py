# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'training_widget.ui'
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
from PySide6.QtWidgets import (QApplication, QComboBox, QGridLayout, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QProgressBar, QPushButton, QSizePolicy,
    QTextEdit, QVBoxLayout, QWidget)

class Ui_training_widget(object):
    def setupUi(self, training_widget):
        if not training_widget.objectName():
            training_widget.setObjectName(u"training_widget")
        training_widget.resize(521, 612)
        self.verticalLayout = QVBoxLayout(training_widget)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.files_group = QGroupBox(training_widget)
        self.files_group.setObjectName(u"files_group")
        self.files_layout = QVBoxLayout(self.files_group)
        self.files_layout.setObjectName(u"files_layout")
        self.files_list = QListWidget(self.files_group)
        self.files_list.setObjectName(u"files_list")

        self.files_layout.addWidget(self.files_list)

        self.files_buttons = QHBoxLayout()
        self.files_buttons.setObjectName(u"files_buttons")
        self.add_button = QPushButton(self.files_group)
        self.add_button.setObjectName(u"add_button")

        self.files_buttons.addWidget(self.add_button)

        self.remove_button = QPushButton(self.files_group)
        self.remove_button.setObjectName(u"remove_button")

        self.files_buttons.addWidget(self.remove_button)


        self.files_layout.addLayout(self.files_buttons)


        self.verticalLayout.addWidget(self.files_group)

        self.settings_group = QWidget(training_widget)
        self.settings_group.setObjectName(u"settings_group")
        self.gridLayout_3 = QGridLayout(self.settings_group)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.gridLayout_3.setVerticalSpacing(10)
        self.gridLayout_3.setContentsMargins(0, 0, 0, 0)
        self.groupBox = QGroupBox(self.settings_group)
        self.groupBox.setObjectName(u"groupBox")
        self.gridLayout = QGridLayout(self.groupBox)
        self.gridLayout.setObjectName(u"gridLayout")
        self.model_name_input = QLineEdit(self.groupBox)
        self.model_name_input.setObjectName(u"model_name_input")

        self.gridLayout.addWidget(self.model_name_input, 0, 0, 1, 1)


        self.gridLayout_3.addWidget(self.groupBox, 0, 0, 1, 1)

        self.groupBox_2 = QGroupBox(self.settings_group)
        self.groupBox_2.setObjectName(u"groupBox_2")
        self.gridLayout_2 = QGridLayout(self.groupBox_2)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.format_combo = QComboBox(self.groupBox_2)
        self.format_combo.setObjectName(u"format_combo")

        self.gridLayout_2.addWidget(self.format_combo, 0, 0, 1, 1)


        self.gridLayout_3.addWidget(self.groupBox_2, 1, 0, 1, 1)

        self.groupBox_3 = QGroupBox(self.settings_group)
        self.groupBox_3.setObjectName(u"groupBox_3")
        self.gridLayout_4 = QGridLayout(self.groupBox_3)
        self.gridLayout_4.setObjectName(u"gridLayout_4")
        self.preview_area = QTextEdit(self.groupBox_3)
        self.preview_area.setObjectName(u"preview_area")

        self.gridLayout_4.addWidget(self.preview_area, 0, 0, 1, 1)

        self.preview_button = QPushButton(self.groupBox_3)
        self.preview_button.setObjectName(u"preview_button")

        self.gridLayout_4.addWidget(self.preview_button, 1, 0, 1, 1)


        self.gridLayout_3.addWidget(self.groupBox_3, 3, 0, 1, 1)

        self.manage_models_button = QPushButton(self.settings_group)
        self.manage_models_button.setObjectName(u"manage_models_button")

        self.gridLayout_3.addWidget(self.manage_models_button, 4, 0, 1, 1)


        self.verticalLayout.addWidget(self.settings_group)

        self.control_layout = QHBoxLayout()
        self.control_layout.setObjectName(u"control_layout")
        self.start_button = QPushButton(training_widget)
        self.start_button.setObjectName(u"start_button")

        self.control_layout.addWidget(self.start_button)

        self.cancel_button = QPushButton(training_widget)
        self.cancel_button.setObjectName(u"cancel_button")
        self.cancel_button.setEnabled(False)

        self.control_layout.addWidget(self.cancel_button)


        self.verticalLayout.addLayout(self.control_layout)

        self.progress_bar = QProgressBar(training_widget)
        self.progress_bar.setObjectName(u"progress_bar")
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)

        self.verticalLayout.addWidget(self.progress_bar)

        self.status_message = QLabel(training_widget)
        self.status_message.setObjectName(u"status_message")

        self.verticalLayout.addWidget(self.status_message)


        self.retranslateUi(training_widget)

        QMetaObject.connectSlotsByName(training_widget)
    # setupUi

    def retranslateUi(self, training_widget):
        self.files_group.setTitle(QCoreApplication.translate("training_widget", u"Training Files", None))
        self.add_button.setText(QCoreApplication.translate("training_widget", u"Add", None))
        self.remove_button.setText(QCoreApplication.translate("training_widget", u"Remove", None))
        self.groupBox.setTitle(QCoreApplication.translate("training_widget", u"Model Name", None))
        self.groupBox_2.setTitle(QCoreApplication.translate("training_widget", u"Formatting", None))
        self.groupBox_3.setTitle(QCoreApplication.translate("training_widget", u"Content to fine-tune", None))
        self.preview_button.setText(QCoreApplication.translate("training_widget", u"Choose training sections", None))
        self.manage_models_button.setText(QCoreApplication.translate("training_widget", u"Manage Models", None))
        self.start_button.setText(QCoreApplication.translate("training_widget", u"Start Fine-tune", None))
        self.cancel_button.setText(QCoreApplication.translate("training_widget", u"Cancel", None))
        self.progress_bar.setFormat(QCoreApplication.translate("training_widget", u"%p%", None))
        self.status_message.setText(QCoreApplication.translate("training_widget", u"TextLabel", None))
        pass
    # retranslateUi

