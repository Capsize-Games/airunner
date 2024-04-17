# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'stable_diffusion_welcome_screen.ui'
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
from PySide6.QtWidgets import (QApplication, QFrame, QGridLayout, QLabel,
    QRadioButton, QSizePolicy, QSpacerItem, QWidget)

class Ui_stable_diffusion_welcome_screen(object):
    def setupUi(self, stable_diffusion_welcome_screen):
        if not stable_diffusion_welcome_screen.objectName():
            stable_diffusion_welcome_screen.setObjectName(u"stable_diffusion_welcome_screen")
        stable_diffusion_welcome_screen.resize(403, 251)
        self.gridLayout = QGridLayout(stable_diffusion_welcome_screen)
        self.gridLayout.setObjectName(u"gridLayout")
        self.verticalSpacer = QSpacerItem(20, 139, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout.addItem(self.verticalSpacer, 6, 0, 1, 1)

        self.line = QFrame(stable_diffusion_welcome_screen)
        self.line.setObjectName(u"line")
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout.addWidget(self.line, 2, 0, 1, 1)

        self.label = QLabel(stable_diffusion_welcome_screen)
        self.label.setObjectName(u"label")
        font = QFont()
        font.setPointSize(11)
        font.setBold(True)
        self.label.setFont(font)

        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)

        self.radioButton = QRadioButton(stable_diffusion_welcome_screen)
        self.radioButton.setObjectName(u"radioButton")
        self.radioButton.setChecked(True)

        self.gridLayout.addWidget(self.radioButton, 4, 0, 1, 1)

        self.radioButton_2 = QRadioButton(stable_diffusion_welcome_screen)
        self.radioButton_2.setObjectName(u"radioButton_2")

        self.gridLayout.addWidget(self.radioButton_2, 5, 0, 1, 1)

        self.label_2 = QLabel(stable_diffusion_welcome_screen)
        self.label_2.setObjectName(u"label_2")
        font1 = QFont()
        font1.setBold(True)
        self.label_2.setFont(font1)

        self.gridLayout.addWidget(self.label_2, 3, 0, 1, 1)

        self.label_3 = QLabel(stable_diffusion_welcome_screen)
        self.label_3.setObjectName(u"label_3")
        self.label_3.setWordWrap(True)

        self.gridLayout.addWidget(self.label_3, 1, 0, 1, 1)


        self.retranslateUi(stable_diffusion_welcome_screen)
        self.radioButton.toggled.connect(stable_diffusion_welcome_screen.yes_toggled)
        self.radioButton_2.toggled.connect(stable_diffusion_welcome_screen.no_toggled)

        QMetaObject.connectSlotsByName(stable_diffusion_welcome_screen)
    # setupUi

    def retranslateUi(self, stable_diffusion_welcome_screen):
        stable_diffusion_welcome_screen.setWindowTitle(QCoreApplication.translate("stable_diffusion_welcome_screen", u"Form", None))
        self.label.setText(QCoreApplication.translate("stable_diffusion_welcome_screen", u"Stable Diffusion setup", None))
        self.radioButton.setText(QCoreApplication.translate("stable_diffusion_welcome_screen", u"Yes", None))
        self.radioButton_2.setText(QCoreApplication.translate("stable_diffusion_welcome_screen", u"No", None))
        self.label_2.setText(QCoreApplication.translate("stable_diffusion_welcome_screen", u"Would you like to use Stable Diffusion as your Image Generator?", None))
        self.label_3.setText(QCoreApplication.translate("stable_diffusion_welcome_screen", u"Stable Diffusion is an open-source AI image generator powered by Diffusers. It enables the creation of images from text prompts. Depending on the selected model, there is a potential for generating content that could be considered unsafe or disturbing. While measures have been implemented to mitigate this risk, no AI model can be guaranteed to be completely safe.", None))
    # retranslateUi

