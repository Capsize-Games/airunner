# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'open_voice_preferences.ui'
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
from PySide6.QtWidgets import (QApplication, QComboBox, QGridLayout, QGroupBox,
    QHBoxLayout, QLineEdit, QPushButton, QSizePolicy,
    QSpacerItem, QVBoxLayout, QWidget)

from airunner.components.application.gui.widgets.slider.slider_widget import SliderWidget

class Ui_open_voice_preferences(object):
    def setupUi(self, open_voice_preferences):
        if not open_voice_preferences.objectName():
            open_voice_preferences.setObjectName(u"open_voice_preferences")
        open_voice_preferences.resize(400, 300)
        self.verticalLayout = QVBoxLayout(open_voice_preferences)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.groupBox_2 = QGroupBox(open_voice_preferences)
        self.groupBox_2.setObjectName(u"groupBox_2")
        self.horizontalLayout_2 = QHBoxLayout(self.groupBox_2)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.voice_sample_path = QLineEdit(self.groupBox_2)
        self.voice_sample_path.setObjectName(u"voice_sample_path")

        self.horizontalLayout_2.addWidget(self.voice_sample_path)

        self.browse_voice_sample_path_button = QPushButton(self.groupBox_2)
        self.browse_voice_sample_path_button.setObjectName(u"browse_voice_sample_path_button")

        self.horizontalLayout_2.addWidget(self.browse_voice_sample_path_button)


        self.verticalLayout.addWidget(self.groupBox_2)

        self.groupBox = QGroupBox(open_voice_preferences)
        self.groupBox.setObjectName(u"groupBox")
        self.gridLayout = QGridLayout(self.groupBox)
        self.gridLayout.setObjectName(u"gridLayout")
        self.language_combobox = QComboBox(self.groupBox)
        self.language_combobox.setObjectName(u"language_combobox")

        self.gridLayout.addWidget(self.language_combobox, 0, 0, 1, 1)


        self.verticalLayout.addWidget(self.groupBox)

        self.speed_slider = SliderWidget(open_voice_preferences)
        self.speed_slider.setObjectName(u"speed_slider")
        self.speed_slider.setProperty(u"slider_minimum", 1)
        self.speed_slider.setProperty(u"slider_maximum", 100)
        self.speed_slider.setProperty(u"spinbox_minimum", 0.000000000000000)
        self.speed_slider.setProperty(u"spinbox_maximum", 1.000000000000000)
        self.speed_slider.setProperty(u"display_as_float", True)
        self.speed_slider.setProperty(u"slider_single_step", 0)
        self.speed_slider.setProperty(u"slider_page_step", 0)
        self.speed_slider.setProperty(u"spinbox_single_step", 0.010000000000000)
        self.speed_slider.setProperty(u"spinbox_double_step", 0.100000000000000)

        self.verticalLayout.addWidget(self.speed_slider)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout.addItem(self.verticalSpacer)


        self.retranslateUi(open_voice_preferences)
        self.language_combobox.currentTextChanged.connect(open_voice_preferences.language_changed)

        QMetaObject.connectSlotsByName(open_voice_preferences)
    # setupUi

    def retranslateUi(self, open_voice_preferences):
        self.groupBox_2.setTitle(QCoreApplication.translate("open_voice_preferences", u"MP3 Voice Sample", None))
        self.voice_sample_path.setText("")
        self.voice_sample_path.setPlaceholderText(QCoreApplication.translate("open_voice_preferences", u"MP3 voice sample", None))
#if QT_CONFIG(tooltip)
        self.browse_voice_sample_path_button.setToolTip(QCoreApplication.translate("open_voice_preferences", u"Browse for an MP3 voice sample to use with OpenVoice", None))
#endif // QT_CONFIG(tooltip)
        self.browse_voice_sample_path_button.setText(QCoreApplication.translate("open_voice_preferences", u"Browse", None))
        self.groupBox.setTitle(QCoreApplication.translate("open_voice_preferences", u"Language", None))
        self.language_combobox.setCurrentText("")
        self.speed_slider.setProperty(u"settings_property", QCoreApplication.translate("open_voice_preferences", u"openvoice_settings.speed", None))
        self.speed_slider.setProperty(u"label_text", QCoreApplication.translate("open_voice_preferences", u"Speed", None))
        pass
    # retranslateUi

