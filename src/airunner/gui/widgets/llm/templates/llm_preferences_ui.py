# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'llm_preferences.ui'
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
from PySide6.QtWidgets import (QApplication, QComboBox, QGridLayout, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit,
    QPushButton, QSizePolicy, QSplitter, QVBoxLayout,
    QWidget)

class Ui_llm_preferences_widget(object):
    def setupUi(self, llm_preferences_widget):
        if not llm_preferences_widget.objectName():
            llm_preferences_widget.setObjectName(u"llm_preferences_widget")
        llm_preferences_widget.resize(1371, 957)
        self.gridLayout = QGridLayout(llm_preferences_widget)
        self.gridLayout.setObjectName(u"gridLayout")
        self.splitter = QSplitter(llm_preferences_widget)
        self.splitter.setObjectName(u"splitter")
        self.splitter.setOrientation(Qt.Vertical)
        self.groupBox = QGroupBox(self.splitter)
        self.groupBox.setObjectName(u"groupBox")
        self.gridLayout_3 = QGridLayout(self.groupBox)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.prefix = QPlainTextEdit(self.groupBox)
        self.prefix.setObjectName(u"prefix")

        self.gridLayout_3.addWidget(self.prefix, 0, 0, 1, 1)

        self.splitter.addWidget(self.groupBox)
        self.groupBox_2 = QGroupBox(self.splitter)
        self.groupBox_2.setObjectName(u"groupBox_2")
        self.gridLayout_4 = QGridLayout(self.groupBox_2)
        self.gridLayout_4.setObjectName(u"gridLayout_4")
        self.suffix = QPlainTextEdit(self.groupBox_2)
        self.suffix.setObjectName(u"suffix")

        self.gridLayout_4.addWidget(self.suffix, 0, 0, 1, 1)

        self.splitter.addWidget(self.groupBox_2)

        self.gridLayout.addWidget(self.splitter, 0, 0, 1, 1)

        self.groupBox_3 = QGroupBox(llm_preferences_widget)
        self.groupBox_3.setObjectName(u"groupBox_3")
        self.horizontalLayout_5 = QHBoxLayout(self.groupBox_3)
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")
        self.verticalLayout_2 = QVBoxLayout()
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.label = QLabel(self.groupBox_3)
        self.label.setObjectName(u"label")

        self.verticalLayout_2.addWidget(self.label)

        self.botname = QLineEdit(self.groupBox_3)
        self.botname.setObjectName(u"botname")
        self.botname.setCursorPosition(6)

        self.verticalLayout_2.addWidget(self.botname)


        self.horizontalLayout_5.addLayout(self.verticalLayout_2)

        self.verticalLayout_3 = QVBoxLayout()
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.label_2 = QLabel(self.groupBox_3)
        self.label_2.setObjectName(u"label_2")

        self.verticalLayout_3.addWidget(self.label_2)

        self.personality_type = QComboBox(self.groupBox_3)
        self.personality_type.addItem("")
        self.personality_type.addItem("")
        self.personality_type.addItem("")
        self.personality_type.addItem("")
        self.personality_type.addItem("")
        self.personality_type.setObjectName(u"personality_type")

        self.verticalLayout_3.addWidget(self.personality_type)


        self.horizontalLayout_5.addLayout(self.verticalLayout_3)


        self.gridLayout.addWidget(self.groupBox_3, 1, 0, 1, 1)

        self.groupBox_4 = QGroupBox(llm_preferences_widget)
        self.groupBox_4.setObjectName(u"groupBox_4")
        self.gridLayout_13 = QGridLayout(self.groupBox_4)
        self.gridLayout_13.setObjectName(u"gridLayout_13")
        self.username = QLineEdit(self.groupBox_4)
        self.username.setObjectName(u"username")

        self.gridLayout_13.addWidget(self.username, 0, 0, 1, 1)


        self.gridLayout.addWidget(self.groupBox_4, 2, 0, 1, 1)

        self.generate_characters_button = QPushButton(llm_preferences_widget)
        self.generate_characters_button.setObjectName(u"generate_characters_button")

        self.gridLayout.addWidget(self.generate_characters_button, 3, 0, 1, 1)

        QWidget.setTabOrder(self.prefix, self.suffix)
        QWidget.setTabOrder(self.suffix, self.botname)
        QWidget.setTabOrder(self.botname, self.username)

        self.retranslateUi(llm_preferences_widget)
        self.generate_characters_button.clicked.connect(llm_preferences_widget.action_button_clicked_generate_characters)
        self.username.textEdited.connect(llm_preferences_widget.username_text_changed)
        self.botname.textEdited.connect(llm_preferences_widget.botname_text_changed)
        self.personality_type.textHighlighted.connect(llm_preferences_widget.personality_type_changed)
        self.suffix.textChanged.connect(llm_preferences_widget.suffix_text_changed)
        self.prefix.textChanged.connect(llm_preferences_widget.prefix_text_changed)

        QMetaObject.connectSlotsByName(llm_preferences_widget)
    # setupUi

    def retranslateUi(self, llm_preferences_widget):
        llm_preferences_widget.setWindowTitle(QCoreApplication.translate("llm_preferences_widget", u"Form", None))
        self.groupBox.setTitle(QCoreApplication.translate("llm_preferences_widget", u"Prefix", None))
        self.groupBox_2.setTitle(QCoreApplication.translate("llm_preferences_widget", u"Suffix", None))
        self.groupBox_3.setTitle(QCoreApplication.translate("llm_preferences_widget", u"Bot details", None))
        self.label.setText(QCoreApplication.translate("llm_preferences_widget", u"Name", None))
        self.botname.setText(QCoreApplication.translate("llm_preferences_widget", u"ChatAI", None))
        self.label_2.setText(QCoreApplication.translate("llm_preferences_widget", u"Personality", None))
        self.personality_type.setItemText(0, QCoreApplication.translate("llm_preferences_widget", u"Nice", None))
        self.personality_type.setItemText(1, QCoreApplication.translate("llm_preferences_widget", u"Mean", None))
        self.personality_type.setItemText(2, QCoreApplication.translate("llm_preferences_widget", u"Weird", None))
        self.personality_type.setItemText(3, QCoreApplication.translate("llm_preferences_widget", u"Insane", None))
        self.personality_type.setItemText(4, QCoreApplication.translate("llm_preferences_widget", u"Random", None))

        self.groupBox_4.setTitle(QCoreApplication.translate("llm_preferences_widget", u"User name", None))
        self.username.setText(QCoreApplication.translate("llm_preferences_widget", u"User", None))
        self.generate_characters_button.setText(QCoreApplication.translate("llm_preferences_widget", u"Generate Characters", None))
    # retranslateUi

