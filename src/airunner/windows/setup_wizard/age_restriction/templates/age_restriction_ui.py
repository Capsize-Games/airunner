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
from PySide6.QtWidgets import (QApplication, QCheckBox, QFrame, QGridLayout,
    QLabel, QScrollArea, QSizePolicy, QSpacerItem,
    QWidget)

class Ui_age_restriction_warning(object):
    def setupUi(self, age_restriction_warning):
        if not age_restriction_warning.objectName():
            age_restriction_warning.setObjectName(u"age_restriction_warning")
        age_restriction_warning.resize(915, 605)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(age_restriction_warning.sizePolicy().hasHeightForWidth())
        age_restriction_warning.setSizePolicy(sizePolicy)
        age_restriction_warning.setMinimumSize(QSize(915, 0))
        self.gridLayout = QGridLayout(age_restriction_warning)
        self.gridLayout.setObjectName(u"gridLayout")
        self.label = QLabel(age_restriction_warning)
        self.label.setObjectName(u"label")
        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        self.label.setFont(font)

        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)

        self.line = QFrame(age_restriction_warning)
        self.line.setObjectName(u"line")
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout.addWidget(self.line, 1, 0, 1, 2)

        self.scrollArea = QScrollArea(age_restriction_warning)
        self.scrollArea.setObjectName(u"scrollArea")
        self.scrollArea.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 889, 544))
        self.gridLayout_2 = QGridLayout(self.scrollAreaWidgetContents)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.checkBox = QCheckBox(self.scrollAreaWidgetContents)
        self.checkBox.setObjectName(u"checkBox")
        font1 = QFont()
        font1.setBold(True)
        self.checkBox.setFont(font1)

        self.gridLayout_2.addWidget(self.checkBox, 8, 0, 1, 1)

        self.label_5 = QLabel(self.scrollAreaWidgetContents)
        self.label_5.setObjectName(u"label_5")
        self.label_5.setWordWrap(True)

        self.gridLayout_2.addWidget(self.label_5, 4, 0, 1, 1)

        self.label_3 = QLabel(self.scrollAreaWidgetContents)
        self.label_3.setObjectName(u"label_3")
        font2 = QFont()
        font2.setBold(True)
        font2.setItalic(False)
        self.label_3.setFont(font2)
        self.label_3.setWordWrap(True)

        self.gridLayout_2.addWidget(self.label_3, 1, 0, 1, 1)

        self.label_4 = QLabel(self.scrollAreaWidgetContents)
        self.label_4.setObjectName(u"label_4")
        font3 = QFont()
        font3.setPointSize(12)
        font3.setBold(True)
        self.label_4.setFont(font3)

        self.gridLayout_2.addWidget(self.label_4, 0, 0, 1, 1)

        self.line_3 = QFrame(self.scrollAreaWidgetContents)
        self.line_3.setObjectName(u"line_3")
        self.line_3.setFrameShape(QFrame.Shape.HLine)
        self.line_3.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout_2.addWidget(self.line_3, 7, 0, 1, 1)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout_2.addItem(self.verticalSpacer, 6, 0, 1, 1)

        self.line_4 = QFrame(self.scrollAreaWidgetContents)
        self.line_4.setObjectName(u"line_4")
        self.line_4.setFrameShape(QFrame.Shape.HLine)
        self.line_4.setFrameShadow(QFrame.Shadow.Sunken)

        self.gridLayout_2.addWidget(self.line_4, 2, 0, 1, 1)

        self.label_2 = QLabel(self.scrollAreaWidgetContents)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setFont(font1)

        self.gridLayout_2.addWidget(self.label_2, 3, 0, 1, 1)

        self.checkBox_2 = QCheckBox(self.scrollAreaWidgetContents)
        self.checkBox_2.setObjectName(u"checkBox_2")
        self.checkBox_2.setFont(font1)

        self.gridLayout_2.addWidget(self.checkBox_2, 9, 0, 1, 1)

        self.scrollArea.setWidget(self.scrollAreaWidgetContents)

        self.gridLayout.addWidget(self.scrollArea, 2, 0, 1, 1)


        self.retranslateUi(age_restriction_warning)
        self.checkBox.clicked["bool"].connect(age_restriction_warning.age_agreement_clicked)
        self.checkBox_2.clicked["bool"].connect(age_restriction_warning.read_agreement_clicked)

        QMetaObject.connectSlotsByName(age_restriction_warning)
    # setupUi

    def retranslateUi(self, age_restriction_warning):
        age_restriction_warning.setWindowTitle(QCoreApplication.translate("age_restriction_warning", u"Form", None))
        self.label.setText(QCoreApplication.translate("age_restriction_warning", u"AI Runner is for users of 18 years of age or older", None))
        self.checkBox.setText(QCoreApplication.translate("age_restriction_warning", u"I am at least 18 years old and agree to the terms and conditions", None))
        self.label_5.setText(QCoreApplication.translate("age_restriction_warning", u"This application utilizes advanced AI models capable of generating a wide range of digital images. Users are advised to exercise caution and comply with local laws when creating images. The software might produce content deemed sensitive or inappropriate, which could include illegal content in certain jurisdictions. It is the user's responsibility to ensure that all content generated complies with applicable laws and regulations.\n"
"\n"
"Please be aware that AI-generated content could unintentionally replicate copyrighted materials or incorporate features from copyrighted artworks. This has been a subject of legal scrutiny as seen in controversies such as those surrounding technologies like Stable Diffusion. Users must handle the outputs responsibly and are encouraged to critically assess the legality of their creations.", None))
        self.label_3.setText(QCoreApplication.translate("age_restriction_warning", u"This application may generate content that is not suitable for all audiences, including nude images. Please confirm that you are at least 18 years oldbefore proceeding.", None))
        self.label_4.setText(QCoreApplication.translate("age_restriction_warning", u"Age Restriction and User Agreement", None))
        self.label_2.setText(QCoreApplication.translate("age_restriction_warning", u"Content Warning and Legal Disclaimer", None))
        self.checkBox_2.setText(QCoreApplication.translate("age_restriction_warning", u"I have read and understood the age restrictions, content warnings, and legal disclaimers provided above. I agree to abide by these guidelines", None))
    # retranslateUi

