# Form implementation generated from reading ui file '/home/joe/Projects/imagetopixel/airunner/src/airunner/../../src/airunner/widgets/tts/templates/speecht5_preferences.ui'
#
# Created by: PyQt6 UI code generator 6.6.1
#
# WARNING: Any manual changes made to this file will be lost when pyuic6 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt6 import QtCore, QtGui, QtWidgets


class Ui_speecht5_preferences(object):
    def setupUi(self, speecht5_preferences):
        speecht5_preferences.setObjectName("speecht5_preferences")
        speecht5_preferences.resize(512, 787)
        self.gridLayout_7 = QtWidgets.QGridLayout(speecht5_preferences)
        self.gridLayout_7.setObjectName("gridLayout_7")
        spacerItem = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Expanding)
        self.gridLayout_7.addItem(spacerItem, 10, 0, 1, 1)
        self.use_bark = QtWidgets.QGroupBox(parent=speecht5_preferences)
        self.use_bark.setCheckable(False)
        self.use_bark.setObjectName("use_bark")
        self.gridLayout_8 = QtWidgets.QGridLayout(self.use_bark)
        self.gridLayout_8.setObjectName("gridLayout_8")
        self.groupBox_6 = QtWidgets.QGroupBox(parent=self.use_bark)
        self.groupBox_6.setObjectName("groupBox_6")
        self.gridLayout_2 = QtWidgets.QGridLayout(self.groupBox_6)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.semantic_temperature = SliderWidget(parent=self.groupBox_6)
        self.semantic_temperature.setProperty("slider_minimum", 1)
        self.semantic_temperature.setProperty("slider_maximum", 100)
        self.semantic_temperature.setProperty("spinbox_minimum", 0.0)
        self.semantic_temperature.setProperty("spinbox_maximum", 1.0)
        self.semantic_temperature.setProperty("display_as_float", True)
        self.semantic_temperature.setProperty("slider_single_step", 1)
        self.semantic_temperature.setProperty("slider_page_step", 10)
        self.semantic_temperature.setProperty("spinbox_single_step", 0.01)
        self.semantic_temperature.setProperty("spinbox_page_step", 0.1)
        self.semantic_temperature.setObjectName("semantic_temperature")
        self.gridLayout_2.addWidget(self.semantic_temperature, 0, 0, 1, 1)
        self.gridLayout_8.addWidget(self.groupBox_6, 5, 0, 1, 1)
        self.groupBox_4 = QtWidgets.QGroupBox(parent=self.use_bark)
        self.groupBox_4.setObjectName("groupBox_4")
        self.gridLayout_5 = QtWidgets.QGridLayout(self.groupBox_4)
        self.gridLayout_5.setObjectName("gridLayout_5")
        self.semantic_temperature_2 = SliderWidget(parent=self.groupBox_4)
        self.semantic_temperature_2.setProperty("slider_minimum", 1)
        self.semantic_temperature_2.setProperty("slider_maximum", 100)
        self.semantic_temperature_2.setProperty("spinbox_minimum", 0.0)
        self.semantic_temperature_2.setProperty("spinbox_maximum", 1.0)
        self.semantic_temperature_2.setProperty("display_as_float", True)
        self.semantic_temperature_2.setProperty("slider_single_step", 1)
        self.semantic_temperature_2.setProperty("slider_page_step", 10)
        self.semantic_temperature_2.setProperty("spinbox_single_step", 0.01)
        self.semantic_temperature_2.setProperty("spinbox_page_step", 0.1)
        self.semantic_temperature_2.setObjectName("semantic_temperature_2")
        self.gridLayout_5.addWidget(self.semantic_temperature_2, 0, 0, 1, 1)
        self.gridLayout_8.addWidget(self.groupBox_4, 4, 0, 1, 1)
        self.groupBox_2 = QtWidgets.QGroupBox(parent=self.use_bark)
        self.groupBox_2.setObjectName("groupBox_2")
        self.gridLayout_3 = QtWidgets.QGridLayout(self.groupBox_2)
        self.gridLayout_3.setObjectName("gridLayout_3")
        self.gender_combobox = QtWidgets.QComboBox(parent=self.groupBox_2)
        self.gender_combobox.setObjectName("gender_combobox")
        self.gender_combobox.addItem("")
        self.gender_combobox.addItem("")
        self.gridLayout_3.addWidget(self.gender_combobox, 0, 0, 1, 1)
        self.gridLayout_8.addWidget(self.groupBox_2, 1, 0, 1, 1)
        self.groupBox = QtWidgets.QGroupBox(parent=self.use_bark)
        self.groupBox.setObjectName("groupBox")
        self.gridLayout = QtWidgets.QGridLayout(self.groupBox)
        self.gridLayout.setObjectName("gridLayout")
        self.voice_combobox = QtWidgets.QComboBox(parent=self.groupBox)
        self.voice_combobox.setObjectName("voice_combobox")
        self.gridLayout.addWidget(self.voice_combobox, 0, 0, 1, 1)
        self.gridLayout_8.addWidget(self.groupBox, 2, 0, 1, 1)
        self.label_3 = QtWidgets.QLabel(parent=self.use_bark)
        font = QtGui.QFont()
        font.setPointSize(9)
        self.label_3.setFont(font)
        self.label_3.setObjectName("label_3")
        self.gridLayout_8.addWidget(self.label_3, 0, 0, 1, 1)
        self.groupBox_5 = QtWidgets.QGroupBox(parent=self.use_bark)
        self.groupBox_5.setObjectName("groupBox_5")
        self.gridLayout_6 = QtWidgets.QGridLayout(self.groupBox_5)
        self.gridLayout_6.setObjectName("gridLayout_6")
        self.semantic_temperature_3 = SliderWidget(parent=self.groupBox_5)
        self.semantic_temperature_3.setProperty("slider_minimum", 1)
        self.semantic_temperature_3.setProperty("slider_maximum", 100)
        self.semantic_temperature_3.setProperty("spinbox_minimum", 0.0)
        self.semantic_temperature_3.setProperty("spinbox_maximum", 1.0)
        self.semantic_temperature_3.setProperty("display_as_float", True)
        self.semantic_temperature_3.setProperty("slider_single_step", 1)
        self.semantic_temperature_3.setProperty("slider_page_step", 10)
        self.semantic_temperature_3.setProperty("spinbox_single_step", 0.01)
        self.semantic_temperature_3.setProperty("spinbox_page_step", 0.1)
        self.semantic_temperature_3.setObjectName("semantic_temperature_3")
        self.gridLayout_6.addWidget(self.semantic_temperature_3, 0, 0, 1, 1)
        self.gridLayout_8.addWidget(self.groupBox_5, 6, 0, 1, 1)
        self.groupBox_3 = QtWidgets.QGroupBox(parent=self.use_bark)
        self.groupBox_3.setCheckable(True)
        self.groupBox_3.setObjectName("groupBox_3")
        self.gridLayout_4 = QtWidgets.QGridLayout(self.groupBox_3)
        self.gridLayout_4.setObjectName("gridLayout_4")
        self.language_combobox = QtWidgets.QComboBox(parent=self.groupBox_3)
        self.language_combobox.setObjectName("language_combobox")
        self.gridLayout_4.addWidget(self.language_combobox, 1, 0, 1, 1)
        self.label = QtWidgets.QLabel(parent=self.groupBox_3)
        font = QtGui.QFont()
        font.setPointSize(9)
        self.label.setFont(font)
        self.label.setObjectName("label")
        self.gridLayout_4.addWidget(self.label, 0, 0, 1, 1)
        self.gridLayout_8.addWidget(self.groupBox_3, 3, 0, 1, 1)
        self.gridLayout_7.addWidget(self.use_bark, 0, 0, 1, 1)

        self.retranslateUi(speecht5_preferences)
        self.language_combobox.currentTextChanged['QString'].connect(speecht5_preferences.language_changed) # type: ignore
        self.voice_combobox.currentTextChanged['QString'].connect(speecht5_preferences.voice_changed) # type: ignore
        self.gender_combobox.currentTextChanged['QString'].connect(speecht5_preferences.gender_changed) # type: ignore
        QtCore.QMetaObject.connectSlotsByName(speecht5_preferences)

    def retranslateUi(self, speecht5_preferences):
        _translate = QtCore.QCoreApplication.translate
        speecht5_preferences.setWindowTitle(_translate("speecht5_preferences", "Form"))
        self.use_bark.setTitle(_translate("speecht5_preferences", "SpeechT5"))
        self.groupBox_6.setTitle(_translate("speecht5_preferences", "Pitch"))
        self.semantic_temperature.setProperty("settings_property", _translate("speecht5_preferences", "tts_settings.spd.pitch"))
        self.semantic_temperature.setProperty("slider_callback", _translate("speecht5_preferences", "handle_value_change"))
        self.groupBox_4.setTitle(_translate("speecht5_preferences", "Rate"))
        self.semantic_temperature_2.setProperty("settings_property", _translate("speecht5_preferences", "tts_settings.spd.rate"))
        self.semantic_temperature_2.setProperty("slider_callback", _translate("speecht5_preferences", "handle_value_change"))
        self.groupBox_2.setTitle(_translate("speecht5_preferences", "Gender"))
        self.gender_combobox.setItemText(0, _translate("speecht5_preferences", "Male"))
        self.gender_combobox.setItemText(1, _translate("speecht5_preferences", "Female"))
        self.groupBox.setTitle(_translate("speecht5_preferences", "Voice"))
        self.label_3.setText(_translate("speecht5_preferences", "Robotic, fast, no VRAM usage"))
        self.groupBox_5.setTitle(_translate("speecht5_preferences", "Volume"))
        self.semantic_temperature_3.setProperty("settings_property", _translate("speecht5_preferences", "tts_settings.spd.volume"))
        self.semantic_temperature_3.setProperty("slider_callback", _translate("speecht5_preferences", "handle_value_change"))
        self.groupBox_3.setTitle(_translate("speecht5_preferences", "Language"))
        self.label.setText(_translate("speecht5_preferences", "Override the system language"))
from airunner.widgets.slider.slider_widget import SliderWidget