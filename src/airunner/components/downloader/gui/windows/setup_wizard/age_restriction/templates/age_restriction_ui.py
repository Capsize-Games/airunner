# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'age_restriction.ui'
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

        self.formLayout_2.setWidget(0, QFormLayout.ItemRole.LabelRole, self.checkBox)

        self.label_7 = QLabel(age_restriction_warning)
        self.label_7.setObjectName(u"label_7")
        self.label_7.setWordWrap(True)

        self.formLayout_2.setWidget(0, QFormLayout.ItemRole.FieldRole, self.label_7)


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

        self.label = QLabel(age_restriction_warning)
        self.label.setObjectName(u"label")
        font4 = QFont()
        font4.setPointSize(14)
        font4.setBold(True)
        self.label.setFont(font4)

        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)


        self.retranslateUi(age_restriction_warning)
        self.checkBox.toggled.connect(age_restriction_warning.age_agreement_clicked)

        QMetaObject.connectSlotsByName(age_restriction_warning)
    # setupUi

    def retranslateUi(self, age_restriction_warning):
        age_restriction_warning.setWindowTitle(QCoreApplication.translate("age_restriction_warning", u"Form", None))
        self.checkBox.setText("")
        self.label_7.setText(QCoreApplication.translate("age_restriction_warning", u"I am at least 18 years old and agree to the terms and conditions", None))
        self.label_5.setText(QCoreApplication.translate("age_restriction_warning", u"This application utilizes advanced AI models capable of generating a wide range of digital images. Users are advised to exercise caution and comply with local laws when creating images. The software might produce content deemed sensitive or inappropriate, which could include illegal content in certain jurisdictions. It is the user's responsibility to ensure that all content generated complies with applicable laws and regulations.\n"
"\n"
"Please be aware that AI-generated content could unintentionally replicate copyrighted materials or incorporate features from copyrighted artworks. This has been a subject of legal scrutiny as seen in controversies such as those surrounding technologies like Stable Diffusion. Users must handle the outputs responsibly and are encouraged to critically assess the legality of their creations.", None))
        self.label_3.setText(QCoreApplication.translate("age_restriction_warning", u"**Age & Content Acknowledgment**\n"
"\n"
"Before using the AI image generation features, you must read and agree to the following:\n"
"\n"
"#### **1. Age Requirement**\n"
"\n"
"You must be **18 years of age or older** to use this feature. This is not negotiable.\n"
"\n"
"#### **2. Content & User Responsibility**\n"
"\n"
"* **Sensitive Content:** The AI is capable of generating a wide range of content, including material that may be considered sensitive, explicit, or NSFW (Not Safe For Work).\n"
"* **Legal Compliance:** You are solely responsible for the content you create. It is your responsibility to ensure that all generated content complies with the laws and regulations of your jurisdiction. The software might produce content that is illegal in certain regions.\n"
"* **Copyright Risk:** AI-generated content can unintentionally replicate or be substantially similar to copyrighted materials. You are responsible for how you use the generated images and for assessing the legal risks of copyright infringement.\n"
""
                        "\n"
"---\n"
"\n"
"### **Click \"Agree and Continue\" to Confirm**\n"
"\n"
"By clicking **\"Agree and Continue\"**, you hereby certify, acknowledge, and agree that:\n"
"\n"
"1.  **I am 18 years of age or older.**\n"
"2.  **I understand** the software can create explicit or potentially offensive content and I choose to proceed at my own risk.\n"
"3.  **I understand** the potential legal risks related to copyright and will use the generated content responsibly.\n"
"4.  **I accept full and sole responsibility** for the content I create and for ensuring it is lawful in my location.\n"
"          ", None))
        self.label_4.setText(QCoreApplication.translate("age_restriction_warning", u"Age Restriction and User Agreement", None))
        self.label_2.setText(QCoreApplication.translate("age_restriction_warning", u"Content Warning and Legal Disclaimer", None))
        self.label.setText(QCoreApplication.translate("age_restriction_warning", u"AI Runner is for users of 18 years of age or older", None))
    # retranslateUi

