# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'huggingface_download_dialog.ui'
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
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QDialog, QHeaderView,
    QLabel, QProgressBar, QPushButton, QSizePolicy,
    QTableWidget, QTableWidgetItem, QTextEdit, QVBoxLayout,
    QWidget)

class Ui_HuggingFaceDownloadDialog(object):
    def setupUi(self, HuggingFaceDownloadDialog):
        if not HuggingFaceDownloadDialog.objectName():
            HuggingFaceDownloadDialog.setObjectName(u"HuggingFaceDownloadDialog")
        HuggingFaceDownloadDialog.resize(700, 600)
        HuggingFaceDownloadDialog.setModal(True)
        self.verticalLayout = QVBoxLayout(HuggingFaceDownloadDialog)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.title_label = QLabel(HuggingFaceDownloadDialog)
        self.title_label.setObjectName(u"title_label")

        self.verticalLayout.addWidget(self.title_label)

        self.path_label = QLabel(HuggingFaceDownloadDialog)
        self.path_label.setObjectName(u"path_label")
        self.path_label.setWordWrap(True)

        self.verticalLayout.addWidget(self.path_label)

        self.overall_label = QLabel(HuggingFaceDownloadDialog)
        self.overall_label.setObjectName(u"overall_label")

        self.verticalLayout.addWidget(self.overall_label)

        self.progress_bar = QProgressBar(HuggingFaceDownloadDialog)
        self.progress_bar.setObjectName(u"progress_bar")
        self.progress_bar.setMaximum(0)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)

        self.verticalLayout.addWidget(self.progress_bar)

        self.stats_label = QLabel(HuggingFaceDownloadDialog)
        self.stats_label.setObjectName(u"stats_label")

        self.verticalLayout.addWidget(self.stats_label)

        self.file_progress_label = QLabel(HuggingFaceDownloadDialog)
        self.file_progress_label.setObjectName(u"file_progress_label")

        self.verticalLayout.addWidget(self.file_progress_label)

        self.file_table = QTableWidget(HuggingFaceDownloadDialog)
        if (self.file_table.columnCount() < 2):
            self.file_table.setColumnCount(2)
        __qtablewidgetitem = QTableWidgetItem()
        self.file_table.setHorizontalHeaderItem(0, __qtablewidgetitem)
        __qtablewidgetitem1 = QTableWidgetItem()
        self.file_table.setHorizontalHeaderItem(1, __qtablewidgetitem1)
        self.file_table.setObjectName(u"file_table")
        self.file_table.setMinimumSize(QSize(0, 240))
        self.file_table.setAlternatingRowColors(True)
        self.file_table.setSelectionMode(QAbstractItemView.NoSelection)
        self.file_table.verticalHeader().setVisible(False)
        self.file_table.verticalHeader().setDefaultSectionSize(24)

        self.verticalLayout.addWidget(self.file_table)

        self.log_label = QLabel(HuggingFaceDownloadDialog)
        self.log_label.setObjectName(u"log_label")

        self.verticalLayout.addWidget(self.log_label)

        self.log_display = QTextEdit(HuggingFaceDownloadDialog)
        self.log_display.setObjectName(u"log_display")
        self.log_display.setMaximumSize(QSize(16777215, 150))
        self.log_display.setReadOnly(True)

        self.verticalLayout.addWidget(self.log_display)

        self.cancel_button = QPushButton(HuggingFaceDownloadDialog)
        self.cancel_button.setObjectName(u"cancel_button")

        self.verticalLayout.addWidget(self.cancel_button)


        self.retranslateUi(HuggingFaceDownloadDialog)

        QMetaObject.connectSlotsByName(HuggingFaceDownloadDialog)
    # setupUi

    def retranslateUi(self, HuggingFaceDownloadDialog):
        HuggingFaceDownloadDialog.setWindowTitle(QCoreApplication.translate("HuggingFaceDownloadDialog", u"Downloading Model", None))
        self.title_label.setText(QCoreApplication.translate("HuggingFaceDownloadDialog", u"Downloading Model", None))
        self.title_label.setStyleSheet(QCoreApplication.translate("HuggingFaceDownloadDialog", u"font-size: 14pt; font-weight: bold;", None))
        self.path_label.setText(QCoreApplication.translate("HuggingFaceDownloadDialog", u"Destination:", None))
        self.overall_label.setText(QCoreApplication.translate("HuggingFaceDownloadDialog", u"Overall Progress:", None))
        self.overall_label.setStyleSheet(QCoreApplication.translate("HuggingFaceDownloadDialog", u"font-weight: bold; margin-top: 10px;", None))
        self.progress_bar.setFormat(QCoreApplication.translate("HuggingFaceDownloadDialog", u"Initializing download...", None))
        self.stats_label.setText(QCoreApplication.translate("HuggingFaceDownloadDialog", u"Preparing to download...", None))
        self.stats_label.setStyleSheet(QCoreApplication.translate("HuggingFaceDownloadDialog", u"color: #888; font-size: 9pt;", None))
        self.file_progress_label.setText(QCoreApplication.translate("HuggingFaceDownloadDialog", u"File Progress:", None))
        self.file_progress_label.setStyleSheet(QCoreApplication.translate("HuggingFaceDownloadDialog", u"font-weight: bold; margin-top: 10px;", None))
        ___qtablewidgetitem = self.file_table.horizontalHeaderItem(0)
        ___qtablewidgetitem.setText(QCoreApplication.translate("HuggingFaceDownloadDialog", u"Filename", None));
        ___qtablewidgetitem1 = self.file_table.horizontalHeaderItem(1)
        ___qtablewidgetitem1.setText(QCoreApplication.translate("HuggingFaceDownloadDialog", u"Progress", None));
        self.log_label.setText(QCoreApplication.translate("HuggingFaceDownloadDialog", u"Download Log:", None))
        self.log_label.setStyleSheet(QCoreApplication.translate("HuggingFaceDownloadDialog", u"font-weight: bold; margin-top: 10px;", None))
        self.cancel_button.setText(QCoreApplication.translate("HuggingFaceDownloadDialog", u"Cancel", None))
    # retranslateUi

