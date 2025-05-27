# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'choose_model.ui'
##
## Created by: Qt User Interface Compiler version 6.9.0
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (
    QCoreApplication,
    QDate,
    QDateTime,
    QLocale,
    QMetaObject,
    QObject,
    QPoint,
    QRect,
    QSize,
    QTime,
    QUrl,
    Qt,
)
from PySide6.QtGui import (
    QBrush,
    QColor,
    QConicalGradient,
    QCursor,
    QFont,
    QFontDatabase,
    QGradient,
    QIcon,
    QImage,
    QKeySequence,
    QLinearGradient,
    QPainter,
    QPalette,
    QPixmap,
    QRadialGradient,
    QTransform,
)
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QRadioButton,
    QSizePolicy,
    QSpacerItem,
    QTabWidget,
    QWidget,
)


class Ui_choose_model(object):
    def setupUi(self, choose_model):
        if not choose_model.objectName():
            choose_model.setObjectName("choose_model")
        choose_model.resize(530, 341)
        self.gridLayout = QGridLayout(choose_model)
        self.gridLayout.setObjectName("gridLayout")
        self.label = QLabel(choose_model)
        self.label.setObjectName("label")
        font = QFont()
        font.setPointSize(11)
        font.setBold(True)
        self.label.setFont(font)

        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)

        self.tabWidget = QTabWidget(choose_model)
        self.tabWidget.setObjectName("tabWidget")
        self.tab = QWidget()
        self.tab.setObjectName("tab")
        self.gridLayout_6 = QGridLayout(self.tab)
        self.gridLayout_6.setObjectName("gridLayout_6")
        self.line_2 = QFrame(self.tab)
        self.line_2.setObjectName("line_2")
        self.line_2.setFrameShape(QFrame.Shape.HLine)
        self.line_2.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout_6.addWidget(self.line_2, 1, 0, 1, 1)

        self.groupBox = QGroupBox(self.tab)
        self.groupBox.setObjectName("groupBox")
        font1 = QFont()
        font1.setBold(True)
        self.groupBox.setFont(font1)
        self.gridLayout_3 = QGridLayout(self.groupBox)
        self.gridLayout_3.setObjectName("gridLayout_3")
        self.models = QComboBox(self.groupBox)
        self.models.setObjectName("models")

        self.gridLayout_3.addWidget(self.models, 0, 0, 1, 1)

        self.gridLayout_6.addWidget(self.groupBox, 2, 0, 1, 1)

        self.groupBox_3 = QGroupBox(self.tab)
        self.groupBox_3.setObjectName("groupBox_3")
        self.groupBox_3.setFont(font1)
        self.gridLayout_5 = QGridLayout(self.groupBox_3)
        self.gridLayout_5.setObjectName("gridLayout_5")
        self.versions = QComboBox(self.groupBox_3)
        self.versions.setObjectName("versions")

        self.gridLayout_5.addWidget(self.versions, 0, 0, 1, 1)

        self.gridLayout_6.addWidget(self.groupBox_3, 0, 0, 1, 1)

        self.tabWidget.addTab(self.tab, "")
        self.tab_2 = QWidget()
        self.tab_2.setObjectName("tab_2")
        self.gridLayout_2 = QGridLayout(self.tab_2)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.groupBox_2 = QGroupBox(self.tab_2)
        self.groupBox_2.setObjectName("groupBox_2")
        self.groupBox_2.setFont(font1)
        self.gridLayout_4 = QGridLayout(self.groupBox_2)
        self.gridLayout_4.setObjectName("gridLayout_4")
        self.custom_model = QLineEdit(self.groupBox_2)
        self.custom_model.setObjectName("custom_model")

        self.gridLayout_4.addWidget(self.custom_model, 0, 0, 1, 1)

        self.gridLayout_2.addWidget(self.groupBox_2, 0, 0, 1, 1)

        self.verticalSpacer_2 = QSpacerItem(
            20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding
        )

        self.gridLayout_2.addItem(self.verticalSpacer_2, 1, 0, 1, 1)

        self.tabWidget.addTab(self.tab_2, "")

        self.gridLayout.addWidget(self.tabWidget, 3, 0, 1, 1)

        self.verticalSpacer = QSpacerItem(
            20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding
        )

        self.gridLayout.addItem(self.verticalSpacer, 5, 0, 1, 1)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.default_radio_button = QRadioButton(choose_model)
        self.default_radio_button.setObjectName("default_radio_button")
        self.default_radio_button.setFont(font1)
        self.default_radio_button.setChecked(True)

        self.horizontalLayout.addWidget(self.default_radio_button)

        self.custom_radio_button = QRadioButton(choose_model)
        self.custom_radio_button.setObjectName("custom_radio_button")
        self.custom_radio_button.setFont(font1)

        self.horizontalLayout.addWidget(self.custom_radio_button)

        self.gridLayout.addLayout(self.horizontalLayout, 4, 0, 1, 1)

        self.line = QFrame(choose_model)
        self.line.setObjectName("line")
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout.addWidget(self.line, 2, 0, 1, 1)

        self.label_2 = QLabel(choose_model)
        self.label_2.setObjectName("label_2")
        self.label_2.setWordWrap(True)

        self.gridLayout.addWidget(self.label_2, 1, 0, 1, 1)

        self.retranslateUi(choose_model)
        self.versions.currentTextChanged.connect(choose_model.model_version_changed)
        self.models.currentTextChanged.connect(choose_model.model_changed)
        self.custom_model.textChanged.connect(choose_model.custom_model_changed)
        self.default_radio_button.toggled.connect(choose_model.model_type_toggled)
        self.custom_radio_button.toggled.connect(choose_model.custom_model_toggled)

        self.tabWidget.setCurrentIndex(0)

        QMetaObject.connectSlotsByName(choose_model)

    # setupUi

    def retranslateUi(self, choose_model):
        choose_model.setWindowTitle(
            QCoreApplication.translate("choose_model", "Form", None)
        )
        self.label.setText(
            QCoreApplication.translate(
                "choose_model", "Stable Diffusion Model Setup", None
            )
        )
        self.groupBox.setTitle(
            QCoreApplication.translate("choose_model", "Default Model", None)
        )
        self.groupBox_3.setTitle(
            QCoreApplication.translate("choose_model", "Default Model Version", None)
        )
        self.tabWidget.setTabText(
            self.tabWidget.indexOf(self.tab),
            QCoreApplication.translate("choose_model", "Tab 1", None),
        )
        self.groupBox_2.setTitle(
            QCoreApplication.translate("choose_model", "Custom model", None)
        )
        self.custom_model.setPlaceholderText(
            QCoreApplication.translate(
                "choose_model",
                "huggingface.co or civitai.com Stable Diffusion model URL",
                None,
            )
        )
        self.tabWidget.setTabText(
            self.tabWidget.indexOf(self.tab_2),
            QCoreApplication.translate("choose_model", "Tab 2", None),
        )
        self.default_radio_button.setText(
            QCoreApplication.translate(
                "choose_model", "Base Stable Diffusion models", None
            )
        )
        self.custom_radio_button.setText(
            QCoreApplication.translate("choose_model", "Custom", None)
        )
        self.label_2.setText(
            QCoreApplication.translate(
                "choose_model",
                "Choose your default model. You can download more models and customize this setting futher later in the preferences.",
                None,
            )
        )

    # retranslateUi
