# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'age_restriction.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QFormLayout, QFrame,
    QGridLayout, QLabel, QScrollArea, QSizePolicy,
    QSpacerItem, QWidget)

class Ui_age_restriction_warning(object):
    def setupUi(self, age_restriction_warning):
        if not age_restriction_warning.objectName():
            age_restriction_warning.setObjectName(u"age_restriction_warning")
        age_restriction_warning.resize(460, 506)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(age_restriction_warning.sizePolicy().hasHeightForWidth())
        age_restriction_warning.setSizePolicy(sizePolicy)
        age_restriction_warning.setMinimumSize(QSize(0, 0))
        self.gridLayout = QGridLayout(age_restriction_warning)
        self.gridLayout.setObjectName(u"gridLayout")
        self.formLayout_2 = QFormLayout()
        self.formLayout_2.setObjectName(u"formLayout_2")
        self.checkBox = QCheckBox(age_restriction_warning)
        self.checkBox.setObjectName(u"checkBox")
        font = QFont()
        font.setBold(False)
        self.checkBox.setFont(font)

        self.formLayout_2.setWidget(0, QFormLayout.LabelRole, self.checkBox)

        self.label_7 = QLabel(age_restriction_warning)
        self.label_7.setObjectName(u"label_7")
        self.label_7.setWordWrap(True)

        self.formLayout_2.setWidget(0, QFormLayout.FieldRole, self.label_7)


        self.gridLayout.addLayout(self.formLayout_2, 5, 0, 1, 1)

        self.line = QFrame(age_restriction_warning)
        self.line.setObjectName(u"line")
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout.addWidget(self.line, 1, 0, 1, 2)

        self.line_3 = QFrame(age_restriction_warning)
        self.line_3.setObjectName(u"line_3")
        self.line_3.setFrameShape(QFrame.Shape.HLine)
        self.line_3.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout.addWidget(self.line_3, 3, 0, 1, 1)

        self.scrollArea = QScrollArea(age_restriction_warning)
        self.scrollArea.setObjectName(u"scrollArea")
        self.scrollArea.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 420, 483))
        self.gridLayout_2 = QGridLayout(self.scrollAreaWidgetContents)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.label_5 = QLabel(self.scrollAreaWidgetContents)
        self.label_5.setObjectName(u"label_5")
        self.label_5.setWordWrap(True)

        self.gridLayout_2.addWidget(self.label_5, 4, 0, 1, 1)

        self.label_3 = QLabel(self.scrollAreaWidgetContents)
        self.label_3.setObjectName(u"label_3")
        font1 = QFont()
        font1.setBold(True)
        font1.setItalic(False)
        self.label_3.setFont(font1)
        self.label_3.setWordWrap(True)

        self.gridLayout_2.addWidget(self.label_3, 1, 0, 1, 1)

        self.label_4 = QLabel(self.scrollAreaWidgetContents)
        self.label_4.setObjectName(u"label_4")
        font2 = QFont()
        font2.setPointSize(12)
        font2.setBold(True)
        self.label_4.setFont(font2)

        self.gridLayout_2.addWidget(self.label_4, 0, 0, 1, 1)

        self.line_4 = QFrame(self.scrollAreaWidgetContents)
        self.line_4.setObjectName(u"line_4")
        self.line_4.setFrameShape(QFrame.Shape.HLine)
        self.line_4.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout_2.addWidget(self.line_4, 2, 0, 1, 1)

        self.label_2 = QLabel(self.scrollAreaWidgetContents)
        self.label_2.setObjectName(u"label_2")
        font3 = QFont()
        font3.setBold(True)
        self.label_2.setFont(font3)

        self.gridLayout_2.addWidget(self.label_2, 3, 0, 1, 1)

        self.verticalSpacer_2 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout_2.addItem(self.verticalSpacer_2, 5, 0, 1, 1)

        self.scrollArea.setWidget(self.scrollAreaWidgetContents)

        self.gridLayout.addWidget(self.scrollArea, 2, 0, 1, 1)

        self.formLayout = QFormLayout()
        self.formLayout.setObjectName(u"formLayout")
        self.checkBox_2 = QCheckBox(age_restriction_warning)
        self.checkBox_2.setObjectName(u"checkBox_2")
        self.checkBox_2.setFont(font3)

        self.formLayout.setWidget(0, QFormLayout.LabelRole, self.checkBox_2)

        self.label_6 = QLabel(age_restriction_warning)
        self.label_6.setObjectName(u"label_6")
        self.label_6.setWordWrap(True)

        self.formLayout.setWidget(0, QFormLayout.FieldRole, self.label_6)


        self.gridLayout.addLayout(self.formLayout, 8, 0, 1, 1)

        self.label = QLabel(age_restriction_warning)
        self.label.setObjectName(u"label")
        font4 = QFont()
        font4.setPointSize(14)
        font4.setBold(True)
        self.label.setFont(font4)

        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)


        self.retranslateUi(age_restriction_warning)
        self.checkBox.toggled.connect(age_restriction_warning.age_agreement_clicked)
        self.checkBox_2.toggled.connect(age_restriction_warning.read_agreement_clicked)

        QMetaObject.connectSlotsByName(age_restriction_warning)
    # setupUi

    def retranslateUi(self, age_restriction_warning):
        age_restriction_warning.setWindowTitle(QCoreApplication.translate("age_restriction_warning", u"Form", None))
        self.checkBox.setText("")
        self.label_7.setText(QCoreApplication.translate("age_restriction_warning", u"I am at least 18 years old and agree to the terms and conditions", None))
        self.label_5.setText(QCoreApplication.translate("age_restriction_warning", u"This application utilizes advanced AI models capable of generating a wide range of digital images. Users are advised to exercise caution and comply with local laws when creating images. The software might produce content deemed sensitive or inappropriate, which could include illegal content in certain jurisdictions. It is the user's responsibility to ensure that all content generated complies with applicable laws and regulations.\n"
"\n"
"Please be aware that AI-generated content could unintentionally replicate copyrighted materials or incorporate features from copyrighted artworks. This has been a subject of legal scrutiny as seen in controversies such as those surrounding technologies like Stable Diffusion. Users must handle the outputs responsibly and are encouraged to critically assess the legality of their creations.", None))
        self.label_3.setText(QCoreApplication.translate("age_restriction_warning", u"This application may generate content that is not suitable for all audiences, including nude images. Please confirm that you are at least 18 years old before proceeding.", None))
        self.label_4.setText(QCoreApplication.translate("age_restriction_warning", u"Age Restriction and User Agreement", None))
        self.label_2.setText(QCoreApplication.translate("age_restriction_warning", u"Content Warning and Legal Disclaimer", None))
        self.checkBox_2.setText("")
        self.label_6.setText(QCoreApplication.translate("age_restriction_warning", u"I have read and understood the age restrictions, content warnings, and legal disclaimers provided above. I agree to abide by these guidelines", None))
        self.label.setText(QCoreApplication.translate("age_restriction_warning", u"AI Runner is for users of 18 years of age or older", None))
    # retranslateUi

