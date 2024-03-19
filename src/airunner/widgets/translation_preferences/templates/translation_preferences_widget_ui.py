# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'translation_preferences_widget.ui'
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
from PySide6.QtWidgets import (QApplication, QComboBox, QFormLayout, QFrame,
    QGridLayout, QGroupBox, QLabel, QRadioButton,
    QSizePolicy, QSpacerItem, QWidget)

class Ui_translation_preferences(object):
    def setupUi(self, translation_preferences):
        if not translation_preferences.objectName():
            translation_preferences.setObjectName(u"translation_preferences")
        translation_preferences.resize(390, 379)
        self.gridLayout = QGridLayout(translation_preferences)
        self.gridLayout.setObjectName(u"gridLayout")
        self.translate_groupbox = QGroupBox(translation_preferences)
        self.translate_groupbox.setObjectName(u"translate_groupbox")
        self.translate_groupbox.setCheckable(True)
        self.gridLayout_3 = QGridLayout(self.translate_groupbox)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.label_5 = QLabel(self.translate_groupbox)
        self.label_5.setObjectName(u"label_5")

        self.gridLayout_3.addWidget(self.label_5, 13, 0, 1, 1)

        self.line = QFrame(self.translate_groupbox)
        self.line.setObjectName(u"line")
        self.line.setFrameShape(QFrame.HLine)
        self.line.setFrameShadow(QFrame.Sunken)

        self.gridLayout_3.addWidget(self.line, 3, 0, 1, 1)

        self.label_4 = QLabel(self.translate_groupbox)
        self.label_4.setObjectName(u"label_4")
        font = QFont()
        font.setPointSize(9)
        self.label_4.setFont(font)

        self.gridLayout_3.addWidget(self.label_4, 1, 0, 1, 1)

        self.label_6 = QLabel(self.translate_groupbox)
        self.label_6.setObjectName(u"label_6")
        self.label_6.setFont(font)

        self.gridLayout_3.addWidget(self.label_6, 14, 0, 1, 1)

        self.label = QLabel(self.translate_groupbox)
        self.label.setObjectName(u"label")
        self.label.setFont(font)

        self.gridLayout_3.addWidget(self.label, 5, 0, 1, 1)

        self.line_2 = QFrame(self.translate_groupbox)
        self.line_2.setObjectName(u"line_2")
        self.line_2.setFrameShape(QFrame.HLine)
        self.line_2.setFrameShadow(QFrame.Sunken)

        self.gridLayout_3.addWidget(self.line_2, 12, 0, 1, 1)

        self.language_combobox = QComboBox(self.translate_groupbox)
        self.language_combobox.setObjectName(u"language_combobox")

        self.gridLayout_3.addWidget(self.language_combobox, 2, 0, 1, 1)

        self.label_3 = QLabel(self.translate_groupbox)
        self.label_3.setObjectName(u"label_3")

        self.gridLayout_3.addWidget(self.label_3, 0, 0, 1, 1)

        self.label_2 = QLabel(self.translate_groupbox)
        self.label_2.setObjectName(u"label_2")

        self.gridLayout_3.addWidget(self.label_2, 4, 0, 1, 1)

        self.translation_model_combobox = QComboBox(self.translate_groupbox)
        self.translation_model_combobox.setObjectName(u"translation_model_combobox")

        self.gridLayout_3.addWidget(self.translation_model_combobox, 15, 0, 1, 1)

        self.voice_combobox = QComboBox(self.translate_groupbox)
        self.voice_combobox.setObjectName(u"voice_combobox")

        self.gridLayout_3.addWidget(self.voice_combobox, 6, 0, 1, 1)

        self.horizontalWidget = QWidget(self.translate_groupbox)
        self.horizontalWidget.setObjectName(u"horizontalWidget")
        self.formLayout = QFormLayout(self.horizontalWidget)
        self.formLayout.setObjectName(u"formLayout")
        self.female_radio_button = QRadioButton(self.horizontalWidget)
        self.female_radio_button.setObjectName(u"female_radio_button")

        self.formLayout.setWidget(0, QFormLayout.LabelRole, self.female_radio_button)

        self.male_radio_button = QRadioButton(self.horizontalWidget)
        self.male_radio_button.setObjectName(u"male_radio_button")

        self.formLayout.setWidget(0, QFormLayout.FieldRole, self.male_radio_button)


        self.gridLayout_3.addWidget(self.horizontalWidget, 8, 0, 1, 1)


        self.gridLayout.addWidget(self.translate_groupbox, 0, 0, 1, 1)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout.addItem(self.verticalSpacer, 2, 0, 1, 1)


        self.retranslateUi(translation_preferences)
        self.language_combobox.currentTextChanged.connect(translation_preferences.language_text_changed)
        self.translate_groupbox.toggled.connect(translation_preferences.toggle_translation)
        self.translation_model_combobox.currentTextChanged.connect(translation_preferences.translation_model_changed)
        self.female_radio_button.clicked.connect(translation_preferences.female_clicked)
        self.male_radio_button.clicked.connect(translation_preferences.male_clicked)
        self.voice_combobox.currentTextChanged.connect(translation_preferences.voice_text_changed)

        QMetaObject.connectSlotsByName(translation_preferences)
    # setupUi

    def retranslateUi(self, translation_preferences):
        translation_preferences.setWindowTitle(QCoreApplication.translate("translation_preferences", u"Form", None))
        self.translate_groupbox.setTitle(QCoreApplication.translate("translation_preferences", u"Translate", None))
        self.label_5.setText(QCoreApplication.translate("translation_preferences", u"Translation model", None))
        self.label_4.setText(QCoreApplication.translate("translation_preferences", u"Your preferred language", None))
        self.label_6.setText(QCoreApplication.translate("translation_preferences", u"This model will be used to translate", None))
        self.label.setText(QCoreApplication.translate("translation_preferences", u"Override TTS voice model", None))
        self.label_3.setText(QCoreApplication.translate("translation_preferences", u"Language", None))
        self.label_2.setText(QCoreApplication.translate("translation_preferences", u"Voice", None))
        self.female_radio_button.setText(QCoreApplication.translate("translation_preferences", u"Female", None))
        self.male_radio_button.setText(QCoreApplication.translate("translation_preferences", u"Male", None))
    # retranslateUi

