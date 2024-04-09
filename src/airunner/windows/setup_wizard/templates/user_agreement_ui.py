# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'user_agreement.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QGridLayout, QLabel,
    QScrollArea, QSizePolicy, QWidget)

class Ui_user_agreement(object):
    def setupUi(self, user_agreement):
        if not user_agreement.objectName():
            user_agreement.setObjectName(u"user_agreement")
        user_agreement.resize(400, 602)
        self.gridLayout_2 = QGridLayout(user_agreement)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.scrollArea = QScrollArea(user_agreement)
        self.scrollArea.setObjectName(u"scrollArea")
        self.scrollArea.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 366, 902))
        self.gridLayout = QGridLayout(self.scrollAreaWidgetContents)
        self.gridLayout.setObjectName(u"gridLayout")
        self.label_2 = QLabel(self.scrollAreaWidgetContents)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setWordWrap(True)

        self.gridLayout.addWidget(self.label_2, 0, 0, 1, 1)

        self.scrollArea.setWidget(self.scrollAreaWidgetContents)

        self.gridLayout_2.addWidget(self.scrollArea, 1, 0, 1, 1)

        self.label = QLabel(user_agreement)
        self.label.setObjectName(u"label")
        font = QFont()
        font.setPointSize(11)
        font.setBold(True)
        self.label.setFont(font)

        self.gridLayout_2.addWidget(self.label, 0, 0, 1, 1)

        self.checkBox = QCheckBox(user_agreement)
        self.checkBox.setObjectName(u"checkBox")

        self.gridLayout_2.addWidget(self.checkBox, 2, 0, 1, 1)


        self.retranslateUi(user_agreement)
        self.checkBox.clicked["bool"].connect(user_agreement.agreement_clicked)

        QMetaObject.connectSlotsByName(user_agreement)
    # setupUi

    def retranslateUi(self, user_agreement):
        user_agreement.setWindowTitle(QCoreApplication.translate("user_agreement", u"Form", None))
        self.label_2.setText(QCoreApplication.translate("user_agreement", u"AI Runner - User Agreement\n"
"\n"
"This User Agreement (\"Agreement\") is a legal agreement between you and Capsize LLC governing your use of the AI Runner software (\"Software\"). By using the Software, you agree to the terms and conditions outlined in this Agreement.\n"
"\n"
"1. Data Collection:\n"
" - AI Runner collects voice and data samples from the user for the purpose of enhancing user experience and improving the Software's functionality.\n"
" - All collected data is stored locally on your machine and is not transmitted to any third-party services.\n"
"\n"
"2. Data Usage:\n"
" - The collected data may be used by Capsize LLC for research and development purposes, including but not limited to training machine learning models and statistical analysis.\n"
" - Capsize LLC may analyze the data to improve the functionality and performance of AI Runner.\n"
"\n"
"3. Data Privacy:\n"
" - Capsize LLC is committed to protecting your privacy.\n"
" - Your data will not be shared with any third parties without your "
                        "explicit consent.\n"
" - We will take all necessary measures to safeguard your data from unauthorized access or disclosure.\n"
"\n"
"4. Consent:\n"
" - By using AI Runner, you consent to the collection and usage of your data as described in this Agreement.\n"
"\n"
"5. Liability:\n"
" - Capsize LLC is not liable for any damages or losses arising from the use of AI Runner or the data collected by it.\n"
"\n"
"6. Changes to Agreement:\n"
" - Capsize LLC reserves the right to modify this Agreement at any time. Any changes will be notified to users through AI Runner or Capsize LLC's website.\n"
"\n"
"7. Contact:\n"
" - If you have any questions or concerns about this Agreement or AI Runner, please contact Capsize LLC at [insert contact information].\n"
"\n"
"8. Experimental Features:\n"
" - AI Runner includes highly experimental features such as vision and voice processing chatbots and image generation capabilities.\n"
" - These features are intended for use by adults and experts only and should not be relied upon "
                        "for critical or sensitive tasks.\n"
" - The outputs generated by these experimental features may be inaccurate, biased, or inappropriate, and should be treated with caution and skepticism.\n"
" - Capsize LLC makes no guarantees or warranties regarding the performance, reliability, or suitability of these experimental features.\n"
"\n"
"9. Open Source Software:\n"
" - AI Runner is an open source software application that is capable of running open source AI models.\n"
" - The use of open source AI models within AI Runner is subject to the respective licenses and terms of those models.\n"
" - Capsize LLC is not responsible for the functionality, performance, or content of the open source AI models used within AI Runner.\n"
"\n"
"By using AI Runner, you acknowledge that you have read, understood, and agree to be bound by the terms and conditions of this Agreement.", None))
        self.label.setText(QCoreApplication.translate("user_agreement", u"User Agreement", None))
        self.checkBox.setText(QCoreApplication.translate("user_agreement", u"I have read and agree to the terms of the User Agreement", None))
    # retranslateUi

