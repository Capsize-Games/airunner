# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'import.ui'
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
from PySide6.QtWidgets import (QApplication, QComboBox, QFrame, QGridLayout,
    QHBoxLayout, QLabel, QLineEdit, QProgressBar,
    QPushButton, QSizePolicy, QSpacerItem, QVBoxLayout,
    QWidget)

from airunner.widgets.model_manager.model_form_widget import ModelFormWidget

class Ui_import_model_widget(object):
    def setupUi(self, import_model_widget):
        if not import_model_widget.objectName():
            import_model_widget.setObjectName(u"import_model_widget")
        import_model_widget.resize(426, 400)
        self.gridLayout_4 = QGridLayout(import_model_widget)
        self.gridLayout_4.setObjectName(u"gridLayout_4")
        self.import_form = QFrame(import_model_widget)
        self.import_form.setObjectName(u"import_form")
        self.import_form.setFrameShape(QFrame.StyledPanel)
        self.import_form.setFrameShadow(QFrame.Raised)
        self.gridLayout_2 = QGridLayout(self.import_form)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.import_url = QLineEdit(self.import_form)
        self.import_url.setObjectName(u"import_url")
        font = QFont()
        font.setPointSize(8)
        self.import_url.setFont(font)

        self.gridLayout_2.addWidget(self.import_url, 2, 0, 1, 1)

        self.import_button = QPushButton(self.import_form)
        self.import_button.setObjectName(u"import_button")
        self.import_button.setFont(font)

        self.gridLayout_2.addWidget(self.import_button, 2, 1, 1, 1)

        self.url_label = QLabel(self.import_form)
        self.url_label.setObjectName(u"url_label")
        font1 = QFont()
        font1.setPointSize(8)
        font1.setBold(True)
        self.url_label.setFont(font1)

        self.gridLayout_2.addWidget(self.url_label, 1, 0, 1, 1)


        self.gridLayout_4.addWidget(self.import_form, 3, 0, 1, 1)

        self.download_form = QFrame(import_model_widget)
        self.download_form.setObjectName(u"download_form")
        self.download_form.setFrameShape(QFrame.StyledPanel)
        self.download_form.setFrameShadow(QFrame.Raised)
        self.gridLayout = QGridLayout(self.download_form)
        self.gridLayout.setObjectName(u"gridLayout")
        self.download_progress_bar = QProgressBar(self.download_form)
        self.download_progress_bar.setObjectName(u"download_progress_bar")
        self.download_progress_bar.setFont(font)
        self.download_progress_bar.setValue(0)

        self.gridLayout.addWidget(self.download_progress_bar, 2, 0, 1, 1)

        self.downloading_label = QLabel(self.download_form)
        self.downloading_label.setObjectName(u"downloading_label")
        self.downloading_label.setFont(font)

        self.gridLayout.addWidget(self.downloading_label, 0, 0, 1, 1)

        self.cancel_download_button = QPushButton(self.download_form)
        self.cancel_download_button.setObjectName(u"cancel_download_button")
        self.cancel_download_button.setFont(font)

        self.gridLayout.addWidget(self.cancel_download_button, 3, 0, 1, 1)


        self.gridLayout_4.addWidget(self.download_form, 5, 0, 1, 1)

        self.model_select_form = QFrame(import_model_widget)
        self.model_select_form.setObjectName(u"model_select_form")
        self.model_select_form.setFrameShape(QFrame.StyledPanel)
        self.model_select_form.setFrameShadow(QFrame.Raised)
        self.gridLayout_3 = QGridLayout(self.model_select_form)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.download_button = QPushButton(self.model_select_form)
        self.download_button.setObjectName(u"download_button")
        self.download_button.setFont(font)

        self.gridLayout_3.addWidget(self.download_button, 3, 0, 1, 1)

        self.cancel_download_save_button = QPushButton(self.model_select_form)
        self.cancel_download_save_button.setObjectName(u"cancel_download_save_button")
        self.cancel_download_save_button.setFont(font)

        self.gridLayout_3.addWidget(self.cancel_download_save_button, 3, 1, 1, 1)

        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.model_version_label = QLabel(self.model_select_form)
        self.model_version_label.setObjectName(u"model_version_label")
        self.model_version_label.setFont(font1)

        self.verticalLayout.addWidget(self.model_version_label)

        self.model_choices = QComboBox(self.model_select_form)
        self.model_choices.setObjectName(u"model_choices")
        self.model_choices.setFont(font)

        self.verticalLayout.addWidget(self.model_choices)


        self.gridLayout_3.addLayout(self.verticalLayout, 1, 0, 1, 2)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.name = QLabel(self.model_select_form)
        self.name.setObjectName(u"name")
        font2 = QFont()
        font2.setPointSize(14)
        font2.setBold(True)
        self.name.setFont(font2)
        self.name.setAlignment(Qt.AlignBottom|Qt.AlignLeading|Qt.AlignLeft)
        self.name.setWordWrap(True)

        self.horizontalLayout.addWidget(self.name)

        self.creator = QLabel(self.model_select_form)
        self.creator.setObjectName(u"creator")
        self.creator.setAlignment(Qt.AlignBottom|Qt.AlignLeading|Qt.AlignLeft)

        self.horizontalLayout.addWidget(self.creator)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer)

        self.nsfw_label = QLabel(self.model_select_form)
        self.nsfw_label.setObjectName(u"nsfw_label")
        font3 = QFont()
        font3.setPointSize(10)
        font3.setBold(True)
        font3.setItalic(False)
        self.nsfw_label.setFont(font3)
        self.nsfw_label.setAlignment(Qt.AlignBottom|Qt.AlignRight|Qt.AlignTrailing)

        self.horizontalLayout.addWidget(self.nsfw_label)


        self.gridLayout_3.addLayout(self.horizontalLayout, 0, 0, 1, 2)

        self.gridLayout_5 = QGridLayout()
        self.gridLayout_5.setObjectName(u"gridLayout_5")
        self.model_form = ModelFormWidget(self.model_select_form)
        self.model_form.setObjectName(u"model_form")

        self.gridLayout_5.addWidget(self.model_form, 0, 0, 1, 1)


        self.gridLayout_3.addLayout(self.gridLayout_5, 2, 0, 1, 2)


        self.gridLayout_4.addWidget(self.model_select_form, 4, 0, 1, 1)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout_4.addItem(self.verticalSpacer, 8, 0, 1, 1)

        self.download_complete_form = QWidget(import_model_widget)
        self.download_complete_form.setObjectName(u"download_complete_form")
        self.download_complete = QGridLayout(self.download_complete_form)
        self.download_complete.setObjectName(u"download_complete")
        self.label = QLabel(self.download_complete_form)
        self.label.setObjectName(u"label")
        font4 = QFont()
        font4.setBold(True)
        self.label.setFont(font4)

        self.download_complete.addWidget(self.label, 0, 0, 1, 1)

        self.pushButton = QPushButton(self.download_complete_form)
        self.pushButton.setObjectName(u"pushButton")
        self.pushButton.setFont(font)

        self.download_complete.addWidget(self.pushButton, 1, 0, 1, 1)


        self.gridLayout_4.addWidget(self.download_complete_form, 7, 0, 1, 1)


        self.retranslateUi(import_model_widget)
        self.download_button.clicked.connect(import_model_widget.action_clicked_button_download)
        self.cancel_download_save_button.clicked.connect(import_model_widget.action_clicked_button_cancel)
        self.cancel_download_button.clicked.connect(import_model_widget.action_clicked_button_cancel)
        self.import_button.clicked.connect(import_model_widget.action_clicked_button_import)
        self.pushButton.clicked.connect(import_model_widget.action_download_complete_continue)

        QMetaObject.connectSlotsByName(import_model_widget)
    # setupUi

    def retranslateUi(self, import_model_widget):
        import_model_widget.setWindowTitle(QCoreApplication.translate("import_model_widget", u"Form", None))
        self.import_url.setPlaceholderText(QCoreApplication.translate("import_model_widget", u"URL", None))
        self.import_button.setText(QCoreApplication.translate("import_model_widget", u"Import", None))
        self.url_label.setText(QCoreApplication.translate("import_model_widget", u"CivitAI.com URL", None))
        self.downloading_label.setText(QCoreApplication.translate("import_model_widget", u"Downloading model name here", None))
        self.cancel_download_button.setText(QCoreApplication.translate("import_model_widget", u"Cancel", None))
        self.download_button.setText(QCoreApplication.translate("import_model_widget", u"Download and Save", None))
        self.cancel_download_save_button.setText(QCoreApplication.translate("import_model_widget", u"Cancel", None))
        self.model_version_label.setText(QCoreApplication.translate("import_model_widget", u"Model Version", None))
        self.name.setText(QCoreApplication.translate("import_model_widget", u"TextLabel", None))
        self.creator.setText(QCoreApplication.translate("import_model_widget", u"TextLabel", None))
        self.nsfw_label.setText(QCoreApplication.translate("import_model_widget", u"NSFW", None))
        self.label.setText(QCoreApplication.translate("import_model_widget", u"Download complete", None))
        self.pushButton.setText(QCoreApplication.translate("import_model_widget", u"OK", None))
    # retranslateUi

