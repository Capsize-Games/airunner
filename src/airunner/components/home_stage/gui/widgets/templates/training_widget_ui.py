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
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QCheckBox, QComboBox,
    QFrame, QGroupBox, QHBoxLayout, QHeaderView,
    QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QProgressBar, QPushButton, QScrollArea, QSizePolicy,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from airunner.components.application.gui.widgets.slider.slider_widget import SliderWidget

class Ui_training_widget(object):
    def setupUi(self, training_widget):
        if not training_widget.objectName():
            training_widget.setObjectName(u"training_widget")
        training_widget.resize(521, 612)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(training_widget.sizePolicy().hasHeightForWidth())
        training_widget.setSizePolicy(sizePolicy)
        self.verticalLayout = QVBoxLayout(training_widget)
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.scrollArea = QScrollArea(training_widget)
        self.scrollArea.setObjectName(u"scrollArea")
        self.scrollArea.setFrameShape(QFrame.Shape.NoFrame)
        self.scrollArea.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaLayout = QVBoxLayout(self.scrollAreaWidgetContents)
        self.scrollAreaLayout.setObjectName(u"scrollAreaLayout")
        self.files_group = QGroupBox(self.scrollAreaWidgetContents)
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


        self.scrollAreaLayout.addWidget(self.files_group)

        self.settings_group = QWidget(self.scrollAreaWidgetContents)
        self.settings_group.setObjectName(u"settings_group")
        self.settings_layout = QVBoxLayout(self.settings_group)
        self.settings_layout.setSpacing(10)
        self.settings_layout.setObjectName(u"settings_layout")
        self.settings_layout.setContentsMargins(0, 0, 0, 0)
        self.adapter_group = QGroupBox(self.settings_group)
        self.adapter_group.setObjectName(u"adapter_group")
        self.adapter_layout = QVBoxLayout(self.adapter_group)
        self.adapter_layout.setObjectName(u"adapter_layout")
        self.model_name_layout = QHBoxLayout()
        self.model_name_layout.setObjectName(u"model_name_layout")
        self.model_name_label = QLabel(self.adapter_group)
        self.model_name_label.setObjectName(u"model_name_label")

        self.model_name_layout.addWidget(self.model_name_label)

        self.model_name_input = QLineEdit(self.adapter_group)
        self.model_name_input.setObjectName(u"model_name_input")

        self.model_name_layout.addWidget(self.model_name_input)


        self.adapter_layout.addLayout(self.model_name_layout)

        self.manage_adapters_button = QPushButton(self.adapter_group)
        self.manage_adapters_button.setObjectName(u"manage_adapters_button")

        self.adapter_layout.addWidget(self.manage_adapters_button)


        self.settings_layout.addWidget(self.adapter_group)

        self.scenario_group = QGroupBox(self.settings_group)
        self.scenario_group.setObjectName(u"scenario_group")
        self.scenario_layout = QVBoxLayout(self.scenario_group)
        self.scenario_layout.setObjectName(u"scenario_layout")
        self.scenario_combo = QComboBox(self.scenario_group)
        self.scenario_combo.setObjectName(u"scenario_combo")

        self.scenario_layout.addWidget(self.scenario_combo)

        self.scenario_description = QLabel(self.scenario_group)
        self.scenario_description.setObjectName(u"scenario_description")
        self.scenario_description.setWordWrap(True)

        self.scenario_layout.addWidget(self.scenario_description)


        self.settings_layout.addWidget(self.scenario_group)

        self.advanced_group = QGroupBox(self.settings_group)
        self.advanced_group.setObjectName(u"advanced_group")
        self.advanced_group.setCheckable(True)
        self.advanced_group.setChecked(False)
        self.advanced_layout = QVBoxLayout(self.advanced_group)
        self.advanced_layout.setObjectName(u"advanced_layout")
        self.learning_rate_slider = SliderWidget(self.advanced_group)
        self.learning_rate_slider.setObjectName(u"learning_rate_slider")
        self.learning_rate_slider.setProperty(u"current_value", 0.000200000000000)
        self.learning_rate_slider.setProperty(u"slider_minimum", 0.000010000000000)
        self.learning_rate_slider.setProperty(u"slider_maximum", 0.000500000000000)
        self.learning_rate_slider.setProperty(u"spinbox_minimum", 0.000010000000000)
        self.learning_rate_slider.setProperty(u"spinbox_maximum", 0.000500000000000)
        self.learning_rate_slider.setProperty(u"spinbox_single_step", 0.000010000000000)
        self.learning_rate_slider.setProperty(u"display_as_float", True)

        self.advanced_layout.addWidget(self.learning_rate_slider)

        self.epochs_slider = SliderWidget(self.advanced_group)
        self.epochs_slider.setObjectName(u"epochs_slider")
        self.epochs_slider.setProperty(u"current_value", 1)
        self.epochs_slider.setProperty(u"slider_minimum", 1)
        self.epochs_slider.setProperty(u"slider_maximum", 10)
        self.epochs_slider.setProperty(u"spinbox_minimum", 1)
        self.epochs_slider.setProperty(u"spinbox_maximum", 10)
        self.epochs_slider.setProperty(u"spinbox_single_step", 1)
        self.epochs_slider.setProperty(u"display_as_float", False)

        self.advanced_layout.addWidget(self.epochs_slider)

        self.batch_size_slider = SliderWidget(self.advanced_group)
        self.batch_size_slider.setObjectName(u"batch_size_slider")
        self.batch_size_slider.setProperty(u"current_value", 1)
        self.batch_size_slider.setProperty(u"slider_minimum", 1)
        self.batch_size_slider.setProperty(u"slider_maximum", 8)
        self.batch_size_slider.setProperty(u"spinbox_minimum", 1)
        self.batch_size_slider.setProperty(u"spinbox_maximum", 8)
        self.batch_size_slider.setProperty(u"spinbox_single_step", 1)
        self.batch_size_slider.setProperty(u"display_as_float", False)

        self.advanced_layout.addWidget(self.batch_size_slider)

        self.gradient_accumulation_slider = SliderWidget(self.advanced_group)
        self.gradient_accumulation_slider.setObjectName(u"gradient_accumulation_slider")
        self.gradient_accumulation_slider.setProperty(u"current_value", 1)
        self.gradient_accumulation_slider.setProperty(u"slider_minimum", 1)
        self.gradient_accumulation_slider.setProperty(u"slider_maximum", 8)
        self.gradient_accumulation_slider.setProperty(u"spinbox_minimum", 1)
        self.gradient_accumulation_slider.setProperty(u"spinbox_maximum", 8)
        self.gradient_accumulation_slider.setProperty(u"spinbox_single_step", 1)
        self.gradient_accumulation_slider.setProperty(u"display_as_float", False)

        self.advanced_layout.addWidget(self.gradient_accumulation_slider)

        self.warmup_steps_slider = SliderWidget(self.advanced_group)
        self.warmup_steps_slider.setObjectName(u"warmup_steps_slider")
        self.warmup_steps_slider.setProperty(u"current_value", 0)
        self.warmup_steps_slider.setProperty(u"slider_minimum", 0)
        self.warmup_steps_slider.setProperty(u"slider_maximum", 100)
        self.warmup_steps_slider.setProperty(u"spinbox_minimum", 0)
        self.warmup_steps_slider.setProperty(u"spinbox_maximum", 100)
        self.warmup_steps_slider.setProperty(u"spinbox_single_step", 5)
        self.warmup_steps_slider.setProperty(u"display_as_float", False)

        self.advanced_layout.addWidget(self.warmup_steps_slider)

        self.gradient_checkpointing_checkbox = QCheckBox(self.advanced_group)
        self.gradient_checkpointing_checkbox.setObjectName(u"gradient_checkpointing_checkbox")

        self.advanced_layout.addWidget(self.gradient_checkpointing_checkbox)


        self.settings_layout.addWidget(self.advanced_group)

        self.preview_group = QGroupBox(self.settings_group)
        self.preview_group.setObjectName(u"preview_group")
        self.preview_layout = QVBoxLayout(self.preview_group)
        self.preview_layout.setObjectName(u"preview_layout")
        self.preview_table = QTableWidget(self.preview_group)
        if (self.preview_table.columnCount() < 3):
            self.preview_table.setColumnCount(3)
        __qtablewidgetitem = QTableWidgetItem()
        self.preview_table.setHorizontalHeaderItem(0, __qtablewidgetitem)
        __qtablewidgetitem1 = QTableWidgetItem()
        self.preview_table.setHorizontalHeaderItem(1, __qtablewidgetitem1)
        __qtablewidgetitem2 = QTableWidgetItem()
        self.preview_table.setHorizontalHeaderItem(2, __qtablewidgetitem2)
        self.preview_table.setObjectName(u"preview_table")
        self.preview_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.preview_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.preview_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        self.preview_layout.addWidget(self.preview_table)

        self.preview_button = QPushButton(self.preview_group)
        self.preview_button.setObjectName(u"preview_button")

        self.preview_layout.addWidget(self.preview_button)


        self.settings_layout.addWidget(self.preview_group)

        self.manage_models_button = QPushButton(self.settings_group)
        self.manage_models_button.setObjectName(u"manage_models_button")

        self.settings_layout.addWidget(self.manage_models_button)


        self.scrollAreaLayout.addWidget(self.settings_group)

        self.control_layout = QHBoxLayout()
        self.control_layout.setObjectName(u"control_layout")
        self.start_button = QPushButton(self.scrollAreaWidgetContents)
        self.start_button.setObjectName(u"start_button")

        self.control_layout.addWidget(self.start_button)

        self.cancel_button = QPushButton(self.scrollAreaWidgetContents)
        self.cancel_button.setObjectName(u"cancel_button")
        self.cancel_button.setEnabled(False)

        self.control_layout.addWidget(self.cancel_button)


        self.scrollAreaLayout.addLayout(self.control_layout)

        self.progress_bar = QProgressBar(self.scrollAreaWidgetContents)
        self.progress_bar.setObjectName(u"progress_bar")
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)

        self.scrollAreaLayout.addWidget(self.progress_bar)

        self.status_message = QLabel(self.scrollAreaWidgetContents)
        self.status_message.setObjectName(u"status_message")

        self.scrollAreaLayout.addWidget(self.status_message)

        self.scrollArea.setWidget(self.scrollAreaWidgetContents)

        self.verticalLayout.addWidget(self.scrollArea)


        self.retranslateUi(training_widget)

        QMetaObject.connectSlotsByName(training_widget)
    # setupUi

    def retranslateUi(self, training_widget):
        self.files_group.setTitle(QCoreApplication.translate("training_widget", u"Training Files", None))
        self.add_button.setText(QCoreApplication.translate("training_widget", u"Add", None))
        self.remove_button.setText(QCoreApplication.translate("training_widget", u"Remove", None))
        self.adapter_group.setTitle(QCoreApplication.translate("training_widget", u"Adapter Configuration", None))
        self.model_name_label.setText(QCoreApplication.translate("training_widget", u"Model Name:", None))
        self.model_name_input.setPlaceholderText(QCoreApplication.translate("training_widget", u"Enter model/adapter name (reuse name to continue training)", None))
        self.manage_adapters_button.setText(QCoreApplication.translate("training_widget", u"Manage Adapters", None))
        self.scenario_group.setTitle(QCoreApplication.translate("training_widget", u"Training Scenario", None))
        self.scenario_description.setText("")
        self.advanced_group.setTitle(QCoreApplication.translate("training_widget", u"Advanced Settings", None))
        self.learning_rate_slider.setProperty(u"label_text", QCoreApplication.translate("training_widget", u"Learning Rate", None))
        self.epochs_slider.setProperty(u"label_text", QCoreApplication.translate("training_widget", u"Epochs", None))
        self.batch_size_slider.setProperty(u"label_text", QCoreApplication.translate("training_widget", u"Batch Size", None))
        self.gradient_accumulation_slider.setProperty(u"label_text", QCoreApplication.translate("training_widget", u"Gradient Accumulation Steps", None))
        self.warmup_steps_slider.setProperty(u"label_text", QCoreApplication.translate("training_widget", u"Warmup Steps", None))
        self.gradient_checkpointing_checkbox.setText(QCoreApplication.translate("training_widget", u"Enable Gradient Checkpointing", None))
        self.preview_group.setTitle(QCoreApplication.translate("training_widget", u"Content to Fine-tune", None))
        ___qtablewidgetitem = self.preview_table.horizontalHeaderItem(0)
        ___qtablewidgetitem.setText(QCoreApplication.translate("training_widget", u"#", None));
        ___qtablewidgetitem1 = self.preview_table.horizontalHeaderItem(1)
        ___qtablewidgetitem1.setText(QCoreApplication.translate("training_widget", u"Title", None));
        ___qtablewidgetitem2 = self.preview_table.horizontalHeaderItem(2)
        ___qtablewidgetitem2.setText(QCoreApplication.translate("training_widget", u"Preview", None));
        self.preview_button.setText(QCoreApplication.translate("training_widget", u"Choose Training Sections", None))
        self.manage_models_button.setText(QCoreApplication.translate("training_widget", u"Manage Models", None))
        self.start_button.setText(QCoreApplication.translate("training_widget", u"Start Fine-tune", None))
        self.cancel_button.setText(QCoreApplication.translate("training_widget", u"Cancel", None))
        self.progress_bar.setFormat(QCoreApplication.translate("training_widget", u"%p%", None))
        self.status_message.setText(QCoreApplication.translate("training_widget", u"TextLabel", None))
        pass
    # retranslateUi

