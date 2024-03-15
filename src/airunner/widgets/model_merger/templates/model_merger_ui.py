# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'model_merger.ui'
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
from PySide6.QtWidgets import (QApplication, QComboBox, QDialog, QGridLayout,
    QHBoxLayout, QLabel, QLineEdit, QProgressBar,
    QPushButton, QSizePolicy, QTabWidget, QWidget)

class Ui_model_merger(object):
    def setupUi(self, model_merger):
        if not model_merger.objectName():
            model_merger.setObjectName(u"model_merger")
        model_merger.resize(400, 630)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.MinimumExpanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(model_merger.sizePolicy().hasHeightForWidth())
        model_merger.setSizePolicy(sizePolicy)
        model_merger.setMinimumSize(QSize(1, 630))
        self.gridLayout = QGridLayout(model_merger)
        self.gridLayout.setObjectName(u"gridLayout")
        self.addModel_button = QPushButton(model_merger)
        self.addModel_button.setObjectName(u"addModel_button")

        self.gridLayout.addWidget(self.addModel_button, 7, 0, 1, 1)

        self.model_types = QComboBox(model_merger)
        self.model_types.setObjectName(u"model_types")

        self.gridLayout.addWidget(self.model_types, 1, 0, 1, 1)

        self.label_4 = QLabel(model_merger)
        self.label_4.setObjectName(u"label_4")
        font = QFont()
        font.setPointSize(10)
        self.label_4.setFont(font)

        self.gridLayout.addWidget(self.label_4, 9, 0, 1, 1)

        self.label_3 = QLabel(model_merger)
        self.label_3.setObjectName(u"label_3")
        font1 = QFont()
        font1.setBold(True)
        self.label_3.setFont(font1)

        self.gridLayout.addWidget(self.label_3, 2, 0, 1, 1)

        self.label_6 = QLabel(model_merger)
        self.label_6.setObjectName(u"label_6")
        self.label_6.setFont(font1)

        self.gridLayout.addWidget(self.label_6, 8, 0, 1, 1)

        self.base_models = QComboBox(model_merger)
        self.base_models.setObjectName(u"base_models")

        self.gridLayout.addWidget(self.base_models, 3, 0, 1, 1)

        self.label = QLabel(model_merger)
        self.label.setObjectName(u"label")
        self.label.setFont(font1)

        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)

        self.models = QTabWidget(model_merger)
        self.models.setObjectName(u"models")

        self.gridLayout.addWidget(self.models, 5, 0, 1, 1)

        self.model_name = QLineEdit(model_merger)
        self.model_name.setObjectName(u"model_name")

        self.gridLayout.addWidget(self.model_name, 10, 0, 1, 1)

        self.label_5 = QLabel(model_merger)
        self.label_5.setObjectName(u"label_5")
        self.label_5.setFont(font1)

        self.gridLayout.addWidget(self.label_5, 4, 0, 1, 1)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.merge_button = QPushButton(model_merger)
        self.merge_button.setObjectName(u"merge_button")

        self.horizontalLayout.addWidget(self.merge_button)

        self.progressBar = QProgressBar(model_merger)
        self.progressBar.setObjectName(u"progressBar")
        self.progressBar.setValue(0)

        self.horizontalLayout.addWidget(self.progressBar)


        self.gridLayout.addLayout(self.horizontalLayout, 11, 0, 1, 1)


        self.retranslateUi(model_merger)

        self.models.setCurrentIndex(-1)


        QMetaObject.connectSlotsByName(model_merger)
    # setupUi

    def retranslateUi(self, model_merger):
        model_merger.setWindowTitle(QCoreApplication.translate("model_merger", u"Model Merger", None))
        self.addModel_button.setText(QCoreApplication.translate("model_merger", u"Add model", None))
        self.label_4.setText(QCoreApplication.translate("model_merger", u"Save the merged model as this name", None))
        self.label_3.setText(QCoreApplication.translate("model_merger", u"Base model", None))
        self.label_6.setText(QCoreApplication.translate("model_merger", u"Model Name", None))
        self.label.setText(QCoreApplication.translate("model_merger", u"Model Type", None))
        self.label_5.setText(QCoreApplication.translate("model_merger", u"Models to merge into base model", None))
        self.merge_button.setText(QCoreApplication.translate("model_merger", u"Merge", None))
    # retranslateUi

