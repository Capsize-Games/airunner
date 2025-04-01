# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'paths.ui'
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
from PySide6.QtWidgets import (QApplication, QGridLayout, QPushButton, QSizePolicy,
    QSpacerItem, QWidget)

from airunner.gui.widgets.paths.path_widget import PathWidget

class Ui_paths_form(object):
    def setupUi(self, paths_form):
        if not paths_form.objectName():
            paths_form.setObjectName(u"paths_form")
        paths_form.resize(498, 1113)
        self.gridLayout = QGridLayout(paths_form)
        self.gridLayout.setObjectName(u"gridLayout")
        self.ebook_path_widget = PathWidget(paths_form)
        self.ebook_path_widget.setObjectName(u"ebook_path_widget")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.ebook_path_widget.sizePolicy().hasHeightForWidth())
        self.ebook_path_widget.setSizePolicy(sizePolicy)
        self.ebook_path_widget.setMinimumSize(QSize(0, 0))

        self.gridLayout.addWidget(self.ebook_path_widget, 3, 0, 1, 1)

        self.image_path_widget = PathWidget(paths_form)
        self.image_path_widget.setObjectName(u"image_path_widget")
        sizePolicy.setHeightForWidth(self.image_path_widget.sizePolicy().hasHeightForWidth())
        self.image_path_widget.setSizePolicy(sizePolicy)
        self.image_path_widget.setMinimumSize(QSize(0, 0))

        self.gridLayout.addWidget(self.image_path_widget, 2, 0, 1, 1)

        self.llama_index_path_widget = PathWidget(paths_form)
        self.llama_index_path_widget.setObjectName(u"llama_index_path_widget")
        sizePolicy.setHeightForWidth(self.llama_index_path_widget.sizePolicy().hasHeightForWidth())
        self.llama_index_path_widget.setSizePolicy(sizePolicy)
        self.llama_index_path_widget.setMinimumSize(QSize(0, 0))

        self.gridLayout.addWidget(self.llama_index_path_widget, 5, 0, 1, 1)

        self.base_path_widget = PathWidget(paths_form)
        self.base_path_widget.setObjectName(u"base_path_widget")
        sizePolicy.setHeightForWidth(self.base_path_widget.sizePolicy().hasHeightForWidth())
        self.base_path_widget.setSizePolicy(sizePolicy)
        self.base_path_widget.setMinimumSize(QSize(0, 0))

        self.gridLayout.addWidget(self.base_path_widget, 1, 0, 1, 1)

        self.documents_path_widget = PathWidget(paths_form)
        self.documents_path_widget.setObjectName(u"documents_path_widget")
        sizePolicy.setHeightForWidth(self.documents_path_widget.sizePolicy().hasHeightForWidth())
        self.documents_path_widget.setSizePolicy(sizePolicy)
        self.documents_path_widget.setMinimumSize(QSize(0, 0))

        self.gridLayout.addWidget(self.documents_path_widget, 4, 0, 1, 1)

        self.auto_button = QPushButton(paths_form)
        self.auto_button.setObjectName(u"auto_button")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Preferred)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.auto_button.sizePolicy().hasHeightForWidth())
        self.auto_button.setSizePolicy(sizePolicy1)
        self.auto_button.setMinimumSize(QSize(0, 0))

        self.gridLayout.addWidget(self.auto_button, 0, 0, 1, 1)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout.addItem(self.verticalSpacer, 6, 0, 1, 1)


        self.retranslateUi(paths_form)
        self.auto_button.clicked.connect(paths_form.action_button_clicked_reset)

        QMetaObject.connectSlotsByName(paths_form)
    # setupUi

    def retranslateUi(self, paths_form):
        paths_form.setWindowTitle(QCoreApplication.translate("paths_form", u"Form", None))
        self.ebook_path_widget.setProperty("title", QCoreApplication.translate("paths_form", u"Ebook Path", None))
        self.ebook_path_widget.setProperty("description", QCoreApplication.translate("paths_form", u"Absolute path to directory containing ebooks (epub)", None))
        self.ebook_path_widget.setProperty("path_name", QCoreApplication.translate("paths_form", u"ebook_path", None))
        self.image_path_widget.setProperty("title", QCoreApplication.translate("paths_form", u"Image Path", None))
        self.image_path_widget.setProperty("description", QCoreApplication.translate("paths_form", u"Absolute path to the directory which will contain generated images", None))
        self.image_path_widget.setProperty("path_name", QCoreApplication.translate("paths_form", u"image_path", None))
        self.llama_index_path_widget.setProperty("title", QCoreApplication.translate("paths_form", u"LLama Index Path", None))
        self.llama_index_path_widget.setProperty("description", QCoreApplication.translate("paths_form", u"Absolute path to directory which will store files for LLama Index", None))
        self.llama_index_path_widget.setProperty("path_name", QCoreApplication.translate("paths_form", u"llama_index_path", None))
        self.base_path_widget.setProperty("title", QCoreApplication.translate("paths_form", u"Base Path", None))
        self.base_path_widget.setProperty("description", QCoreApplication.translate("paths_form", u"Absolute path to the directory which will hold all model directories", None))
        self.base_path_widget.setProperty("path_name", QCoreApplication.translate("paths_form", u"base_path", None))
        self.documents_path_widget.setProperty("title", QCoreApplication.translate("paths_form", u"Documents Path", None))
        self.documents_path_widget.setProperty("description", QCoreApplication.translate("paths_form", u"Absolute path to directory containing documnets (txt, PDF)", None))
        self.documents_path_widget.setProperty("path_name", QCoreApplication.translate("paths_form", u"documents_path", None))
        self.auto_button.setText(QCoreApplication.translate("paths_form", u"Reset Paths to Default Values", None))
    # retranslateUi

