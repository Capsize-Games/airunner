# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'knowledge_base_panel.ui'
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
from PySide6.QtWidgets import (QApplication, QFormLayout, QGroupBox, QHBoxLayout,
    QLabel, QProgressBar, QPushButton, QSizePolicy,
    QSpacerItem, QVBoxLayout, QWidget)

class Ui_knowledge_base_panel(object):
    def setupUi(self, knowledge_base_panel):
        if not knowledge_base_panel.objectName():
            knowledge_base_panel.setObjectName(u"knowledge_base_panel")
        knowledge_base_panel.resize(400, 400)
        knowledge_base_panel.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
        self.verticalLayout = QVBoxLayout(knowledge_base_panel)
        self.verticalLayout.setSpacing(10)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.title_label = QLabel(knowledge_base_panel)
        self.title_label.setObjectName(u"title_label")
        self.title_label.setStyleSheet(u"font-size: 18px; font-weight: bold;")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignLeading|Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignVCenter)

        self.verticalLayout.addWidget(self.title_label)

        self.stats_group = QGroupBox(knowledge_base_panel)
        self.stats_group.setObjectName(u"stats_group")
        self.formLayout = QFormLayout(self.stats_group)
        self.formLayout.setObjectName(u"formLayout")
        self.total_label = QLabel(self.stats_group)
        self.total_label.setObjectName(u"total_label")

        self.formLayout.setWidget(0, QFormLayout.ItemRole.LabelRole, self.total_label)

        self.total_docs_value = QLabel(self.stats_group)
        self.total_docs_value.setObjectName(u"total_docs_value")
        self.total_docs_value.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.formLayout.setWidget(0, QFormLayout.ItemRole.FieldRole, self.total_docs_value)

        self.indexed_label = QLabel(self.stats_group)
        self.indexed_label.setObjectName(u"indexed_label")

        self.formLayout.setWidget(1, QFormLayout.ItemRole.LabelRole, self.indexed_label)

        self.indexed_docs_value = QLabel(self.stats_group)
        self.indexed_docs_value.setObjectName(u"indexed_docs_value")
        self.indexed_docs_value.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.formLayout.setWidget(1, QFormLayout.ItemRole.FieldRole, self.indexed_docs_value)

        self.unindexed_label = QLabel(self.stats_group)
        self.unindexed_label.setObjectName(u"unindexed_label")

        self.formLayout.setWidget(2, QFormLayout.ItemRole.LabelRole, self.unindexed_label)

        self.unindexed_docs_value = QLabel(self.stats_group)
        self.unindexed_docs_value.setObjectName(u"unindexed_docs_value")
        self.unindexed_docs_value.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.formLayout.setWidget(2, QFormLayout.ItemRole.FieldRole, self.unindexed_docs_value)


        self.verticalLayout.addWidget(self.stats_group)

        self.status_message = QLabel(knowledge_base_panel)
        self.status_message.setObjectName(u"status_message")
        self.status_message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_message.setWordWrap(True)

        self.verticalLayout.addWidget(self.status_message)

        self.progress_bar = QProgressBar(knowledge_base_panel)
        self.progress_bar.setObjectName(u"progress_bar")
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)

        self.verticalLayout.addWidget(self.progress_bar)

        self.progress_text = QLabel(knowledge_base_panel)
        self.progress_text.setObjectName(u"progress_text")
        self.progress_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress_text.setWordWrap(True)

        self.verticalLayout.addWidget(self.progress_text)

        self.button_layout = QHBoxLayout()
        self.button_layout.setObjectName(u"button_layout")
        self.index_button = QPushButton(knowledge_base_panel)
        self.index_button.setObjectName(u"index_button")
        self.index_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        self.button_layout.addWidget(self.index_button)

        self.cancel_button = QPushButton(knowledge_base_panel)
        self.cancel_button.setObjectName(u"cancel_button")
        self.cancel_button.setEnabled(False)

        self.button_layout.addWidget(self.cancel_button)


        self.verticalLayout.addLayout(self.button_layout)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout.addItem(self.verticalSpacer)


        self.retranslateUi(knowledge_base_panel)

        QMetaObject.connectSlotsByName(knowledge_base_panel)
    # setupUi

    def retranslateUi(self, knowledge_base_panel):
        knowledge_base_panel.setWindowTitle(QCoreApplication.translate("knowledge_base_panel", u"Form", None))
        self.title_label.setText(QCoreApplication.translate("knowledge_base_panel", u"Knowledge Base", None))
        self.stats_group.setTitle(QCoreApplication.translate("knowledge_base_panel", u"Document Statistics", None))
        self.total_label.setText(QCoreApplication.translate("knowledge_base_panel", u"Total Documents:", None))
        self.total_docs_value.setText(QCoreApplication.translate("knowledge_base_panel", u"0", None))
        self.indexed_label.setText(QCoreApplication.translate("knowledge_base_panel", u"Indexed:", None))
        self.indexed_docs_value.setText(QCoreApplication.translate("knowledge_base_panel", u"0", None))
        self.unindexed_label.setText(QCoreApplication.translate("knowledge_base_panel", u"Unindexed:", None))
        self.unindexed_docs_value.setText(QCoreApplication.translate("knowledge_base_panel", u"0", None))
        self.status_message.setText("")
        self.progress_bar.setFormat(QCoreApplication.translate("knowledge_base_panel", u"%p%", None))
        self.progress_text.setText("")
        self.index_button.setText(QCoreApplication.translate("knowledge_base_panel", u"Index All", None))
        self.cancel_button.setText(QCoreApplication.translate("knowledge_base_panel", u"Cancel", None))
    # retranslateUi

