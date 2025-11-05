# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'knowledge_editor.ui'
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
from PySide6.QtWidgets import (QAbstractButton, QApplication, QCheckBox, QComboBox,
    QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout,
    QLabel, QLineEdit, QSizePolicy, QSlider,
    QTextEdit, QVBoxLayout, QWidget)

class Ui_knowledge_editor(object):
    def setupUi(self, knowledge_editor):
        if not knowledge_editor.objectName():
            knowledge_editor.setObjectName(u"knowledge_editor")
        knowledge_editor.resize(600, 500)
        self.verticalLayout = QVBoxLayout(knowledge_editor)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.title_label = QLabel(knowledge_editor)
        self.title_label.setObjectName(u"title_label")

        self.verticalLayout.addWidget(self.title_label)

        self.formLayout = QFormLayout()
        self.formLayout.setObjectName(u"formLayout")
        self.text_label = QLabel(knowledge_editor)
        self.text_label.setObjectName(u"text_label")

        self.formLayout.setWidget(0, QFormLayout.ItemRole.LabelRole, self.text_label)

        self.text_input = QTextEdit(knowledge_editor)
        self.text_input.setObjectName(u"text_input")
        self.text_input.setMaximumSize(QSize(16777215, 100))

        self.formLayout.setWidget(0, QFormLayout.ItemRole.FieldRole, self.text_input)

        self.category_label = QLabel(knowledge_editor)
        self.category_label.setObjectName(u"category_label")

        self.formLayout.setWidget(1, QFormLayout.ItemRole.LabelRole, self.category_label)

        self.category_input = QComboBox(knowledge_editor)
        self.category_input.setObjectName(u"category_input")
        self.category_input.setEditable(True)

        self.formLayout.setWidget(1, QFormLayout.ItemRole.FieldRole, self.category_input)

        self.tags_label = QLabel(knowledge_editor)
        self.tags_label.setObjectName(u"tags_label")

        self.formLayout.setWidget(2, QFormLayout.ItemRole.LabelRole, self.tags_label)

        self.tags_input = QLineEdit(knowledge_editor)
        self.tags_input.setObjectName(u"tags_input")

        self.formLayout.setWidget(2, QFormLayout.ItemRole.FieldRole, self.tags_input)

        self.confidence_label = QLabel(knowledge_editor)
        self.confidence_label.setObjectName(u"confidence_label")

        self.formLayout.setWidget(3, QFormLayout.ItemRole.LabelRole, self.confidence_label)

        self.confidence_layout = QHBoxLayout()
        self.confidence_layout.setObjectName(u"confidence_layout")
        self.confidence_slider = QSlider(knowledge_editor)
        self.confidence_slider.setObjectName(u"confidence_slider")
        self.confidence_slider.setMinimum(0)
        self.confidence_slider.setMaximum(100)
        self.confidence_slider.setValue(80)
        self.confidence_slider.setOrientation(Qt.Horizontal)

        self.confidence_layout.addWidget(self.confidence_slider)

        self.confidence_value_label = QLabel(knowledge_editor)
        self.confidence_value_label.setObjectName(u"confidence_value_label")
        self.confidence_value_label.setMinimumSize(QSize(50, 0))

        self.confidence_layout.addWidget(self.confidence_value_label)


        self.formLayout.setLayout(3, QFormLayout.ItemRole.FieldRole, self.confidence_layout)

        self.source_label = QLabel(knowledge_editor)
        self.source_label.setObjectName(u"source_label")

        self.formLayout.setWidget(4, QFormLayout.ItemRole.LabelRole, self.source_label)

        self.source_input = QLineEdit(knowledge_editor)
        self.source_input.setObjectName(u"source_input")

        self.formLayout.setWidget(4, QFormLayout.ItemRole.FieldRole, self.source_input)

        self.checkboxes_layout = QHBoxLayout()
        self.checkboxes_layout.setObjectName(u"checkboxes_layout")
        self.verified_checkbox = QCheckBox(knowledge_editor)
        self.verified_checkbox.setObjectName(u"verified_checkbox")

        self.checkboxes_layout.addWidget(self.verified_checkbox)

        self.enabled_checkbox = QCheckBox(knowledge_editor)
        self.enabled_checkbox.setObjectName(u"enabled_checkbox")
        self.enabled_checkbox.setChecked(True)

        self.checkboxes_layout.addWidget(self.enabled_checkbox)


        self.formLayout.setLayout(5, QFormLayout.ItemRole.FieldRole, self.checkboxes_layout)


        self.verticalLayout.addLayout(self.formLayout)

        self.buttonBox = QDialogButtonBox(knowledge_editor)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setStandardButtons(QDialogButtonBox.Cancel|QDialogButtonBox.Save)

        self.verticalLayout.addWidget(self.buttonBox)


        self.retranslateUi(knowledge_editor)
        self.buttonBox.accepted.connect(knowledge_editor.accept)
        self.buttonBox.rejected.connect(knowledge_editor.reject)
        self.confidence_slider.valueChanged.connect(knowledge_editor.on_confidence_changed)

        QMetaObject.connectSlotsByName(knowledge_editor)
    # setupUi

    def retranslateUi(self, knowledge_editor):
        knowledge_editor.setWindowTitle(QCoreApplication.translate("knowledge_editor", u"Knowledge Editor", None))
        self.title_label.setText(QCoreApplication.translate("knowledge_editor", u"Knowledge Fact Editor", None))
        self.title_label.setStyleSheet(QCoreApplication.translate("knowledge_editor", u"font-size: 16px; font-weight: bold;", None))
        self.text_label.setText(QCoreApplication.translate("knowledge_editor", u"Fact Text:", None))
        self.text_input.setPlaceholderText(QCoreApplication.translate("knowledge_editor", u"Enter the factual information...", None))
        self.category_label.setText(QCoreApplication.translate("knowledge_editor", u"Category:", None))
        self.tags_label.setText(QCoreApplication.translate("knowledge_editor", u"Tags:", None))
        self.tags_input.setPlaceholderText(QCoreApplication.translate("knowledge_editor", u"Comma-separated tags (e.g., preference, important)", None))
        self.confidence_label.setText(QCoreApplication.translate("knowledge_editor", u"Confidence:", None))
        self.confidence_value_label.setText(QCoreApplication.translate("knowledge_editor", u"0.80", None))
        self.source_label.setText(QCoreApplication.translate("knowledge_editor", u"Source:", None))
        self.source_input.setPlaceholderText(QCoreApplication.translate("knowledge_editor", u"Where did this fact come from?", None))
        self.verified_checkbox.setText(QCoreApplication.translate("knowledge_editor", u"Verified", None))
        self.enabled_checkbox.setText(QCoreApplication.translate("knowledge_editor", u"Enabled", None))
    # retranslateUi

