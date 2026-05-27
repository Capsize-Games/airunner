# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'civitai_browser_dialog.ui'
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
from PySide6.QtWidgets import (QAbstractButton, QApplication, QComboBox, QDialogButtonBox,
    QFormLayout, QFrame, QHBoxLayout, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QPushButton,
    QSizePolicy, QSplitter, QTextBrowser, QVBoxLayout,
    QWidget)

class Ui_CivitaiBrowserDialog(object):
    def setupUi(self, CivitaiBrowserDialog):
        if not CivitaiBrowserDialog.objectName():
            CivitaiBrowserDialog.setObjectName(u"CivitaiBrowserDialog")
        CivitaiBrowserDialog.resize(1080, 720)
        self.verticalLayout = QVBoxLayout(CivitaiBrowserDialog)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.filterLayout = QHBoxLayout()
        self.filterLayout.setObjectName(u"filterLayout")
        self.search_line_edit = QLineEdit(CivitaiBrowserDialog)
        self.search_line_edit.setObjectName(u"search_line_edit")

        self.filterLayout.addWidget(self.search_line_edit)

        self.base_model_combo = QComboBox(CivitaiBrowserDialog)
        self.base_model_combo.setObjectName(u"base_model_combo")

        self.filterLayout.addWidget(self.base_model_combo)

        self.type_combo = QComboBox(CivitaiBrowserDialog)
        self.type_combo.setObjectName(u"type_combo")

        self.filterLayout.addWidget(self.type_combo)

        self.search_button = QPushButton(CivitaiBrowserDialog)
        self.search_button.setObjectName(u"search_button")

        self.filterLayout.addWidget(self.search_button)

        self.load_more_button = QPushButton(CivitaiBrowserDialog)
        self.load_more_button.setObjectName(u"load_more_button")

        self.filterLayout.addWidget(self.load_more_button)


        self.verticalLayout.addLayout(self.filterLayout)

        self.status_label = QLabel(CivitaiBrowserDialog)
        self.status_label.setObjectName(u"status_label")

        self.verticalLayout.addWidget(self.status_label)

        self.browser_splitter = QSplitter(CivitaiBrowserDialog)
        self.browser_splitter.setObjectName(u"browser_splitter")
        self.browser_splitter.setOrientation(Qt.Horizontal)
        self.results_panel = QWidget(self.browser_splitter)
        self.results_panel.setObjectName(u"results_panel")
        self.resultsLayout = QVBoxLayout(self.results_panel)
        self.resultsLayout.setObjectName(u"resultsLayout")
        self.resultsLayout.setContentsMargins(0, 0, 0, 0)
        self.results_list = QListWidget(self.results_panel)
        self.results_list.setObjectName(u"results_list")

        self.resultsLayout.addWidget(self.results_list)

        self.browser_splitter.addWidget(self.results_panel)
        self.details_panel = QWidget(self.browser_splitter)
        self.details_panel.setObjectName(u"details_panel")
        self.detailsLayout = QVBoxLayout(self.details_panel)
        self.detailsLayout.setObjectName(u"detailsLayout")
        self.detailsLayout.setContentsMargins(0, 0, 0, 0)
        self.selected_model_label = QLabel(self.details_panel)
        self.selected_model_label.setObjectName(u"selected_model_label")

        self.detailsLayout.addWidget(self.selected_model_label)

        self.selected_model_meta_label = QLabel(self.details_panel)
        self.selected_model_meta_label.setObjectName(u"selected_model_meta_label")
        self.selected_model_meta_label.setWordWrap(True)

        self.detailsLayout.addWidget(self.selected_model_meta_label)

        self.preview_label = QLabel(self.details_panel)
        self.preview_label.setObjectName(u"preview_label")
        self.preview_label.setMinimumSize(QSize(320, 220))
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setFrameShape(QFrame.StyledPanel)

        self.detailsLayout.addWidget(self.preview_label)

        self.sample_images_list = QListWidget(self.details_panel)
        self.sample_images_list.setObjectName(u"sample_images_list")

        self.detailsLayout.addWidget(self.sample_images_list)

        self.description_browser = QTextBrowser(self.details_panel)
        self.description_browser.setObjectName(u"description_browser")

        self.detailsLayout.addWidget(self.description_browser)

        self.selectionLayout = QFormLayout()
        self.selectionLayout.setObjectName(u"selectionLayout")
        self.version_label = QLabel(self.details_panel)
        self.version_label.setObjectName(u"version_label")

        self.selectionLayout.setWidget(0, QFormLayout.ItemRole.LabelRole, self.version_label)

        self.version_combo = QComboBox(self.details_panel)
        self.version_combo.setObjectName(u"version_combo")

        self.selectionLayout.setWidget(0, QFormLayout.ItemRole.FieldRole, self.version_combo)

        self.file_label = QLabel(self.details_panel)
        self.file_label.setObjectName(u"file_label")

        self.selectionLayout.setWidget(1, QFormLayout.ItemRole.LabelRole, self.file_label)

        self.file_combo = QComboBox(self.details_panel)
        self.file_combo.setObjectName(u"file_combo")

        self.selectionLayout.setWidget(1, QFormLayout.ItemRole.FieldRole, self.file_combo)


        self.detailsLayout.addLayout(self.selectionLayout)

        self.actionLayout = QHBoxLayout()
        self.actionLayout.setObjectName(u"actionLayout")
        self.open_model_button = QPushButton(self.details_panel)
        self.open_model_button.setObjectName(u"open_model_button")

        self.actionLayout.addWidget(self.open_model_button)

        self.download_button = QPushButton(self.details_panel)
        self.download_button.setObjectName(u"download_button")

        self.actionLayout.addWidget(self.download_button)


        self.detailsLayout.addLayout(self.actionLayout)

        self.browser_splitter.addWidget(self.details_panel)

        self.verticalLayout.addWidget(self.browser_splitter)

        self.button_box = QDialogButtonBox(CivitaiBrowserDialog)
        self.button_box.setObjectName(u"button_box")
        self.button_box.setStandardButtons(QDialogButtonBox.Close)

        self.verticalLayout.addWidget(self.button_box)


        self.retranslateUi(CivitaiBrowserDialog)

        QMetaObject.connectSlotsByName(CivitaiBrowserDialog)
    # setupUi

    def retranslateUi(self, CivitaiBrowserDialog):
        CivitaiBrowserDialog.setWindowTitle(QCoreApplication.translate("CivitaiBrowserDialog", u"CivitAI Browser", None))
        self.search_line_edit.setPlaceholderText(QCoreApplication.translate("CivitaiBrowserDialog", u"Search checkpoints, LoRAs, and embeddings", None))
        self.search_button.setText(QCoreApplication.translate("CivitaiBrowserDialog", u"Search", None))
        self.load_more_button.setText(QCoreApplication.translate("CivitaiBrowserDialog", u"Load More", None))
        self.status_label.setText(QCoreApplication.translate("CivitaiBrowserDialog", u"Loading models\u2026", None))
        self.selected_model_label.setText(QCoreApplication.translate("CivitaiBrowserDialog", u"Select a model", None))
        self.selected_model_meta_label.setText("")
        self.preview_label.setText(QCoreApplication.translate("CivitaiBrowserDialog", u"No preview selected", None))
        self.version_label.setText(QCoreApplication.translate("CivitaiBrowserDialog", u"Version", None))
        self.file_label.setText(QCoreApplication.translate("CivitaiBrowserDialog", u"File", None))
        self.open_model_button.setText(QCoreApplication.translate("CivitaiBrowserDialog", u"Open on CivitAI", None))
        self.download_button.setText(QCoreApplication.translate("CivitaiBrowserDialog", u"Download Selected File", None))
    # retranslateUi

