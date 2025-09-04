# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'privacy_policy.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QGridLayout, QLabel,
    QScrollArea, QSizePolicy, QWidget)

class Ui_privacy_policy(object):
    def setupUi(self, privacy_policy):
        if not privacy_policy.objectName():
            privacy_policy.setObjectName(u"privacy_policy")
        privacy_policy.resize(400, 526)
        self.gridLayout_2 = QGridLayout(privacy_policy)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.scrollArea = QScrollArea(privacy_policy)
        self.scrollArea.setObjectName(u"scrollArea")
        self.scrollArea.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 366, 1565))
        self.gridLayout = QGridLayout(self.scrollAreaWidgetContents)
        self.gridLayout.setObjectName(u"gridLayout")
        self.label_2 = QLabel(self.scrollAreaWidgetContents)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setWordWrap(True)

        self.gridLayout.addWidget(self.label_2, 0, 0, 1, 1)

        self.scrollArea.setWidget(self.scrollAreaWidgetContents)

        self.gridLayout_2.addWidget(self.scrollArea, 1, 0, 1, 1)

        self.label = QLabel(privacy_policy)
        self.label.setObjectName(u"label")
        font = QFont()
        font.setPointSize(11)
        font.setBold(True)
        self.label.setFont(font)

        self.gridLayout_2.addWidget(self.label, 0, 0, 1, 1)

        self.checkBox = QCheckBox(privacy_policy)
        self.checkBox.setObjectName(u"checkBox")

        self.gridLayout_2.addWidget(self.checkBox, 2, 0, 1, 1)


        self.retranslateUi(privacy_policy)
        self.checkBox.clicked["bool"].connect(privacy_policy.agreement_clicked)

        QMetaObject.connectSlotsByName(privacy_policy)
    # setupUi

    def retranslateUi(self, privacy_policy):
        privacy_policy.setWindowTitle(QCoreApplication.translate("privacy_policy", u"Form", None))
        self.label_2.setText(QCoreApplication.translate("privacy_policy", u"AI Runner Privacy Policy\n"
"\n"
"**Last Updated: September 5, 2025**\n"
"\n"
"This Privacy Policy describes how Capsize LLC (\"Capsize,\" \"we,\" \"us,\" or \"our\") handles information in connection with your use of the AI Runner software (\"Software\"). Our guiding principle is privacy-by-design. The Software is built to run locally on your machine, giving you maximum control over your data.\n"
"\n"
"This policy will explain:\n"
"1.  Our Core Privacy Philosophy\n"
"2.  Information We **Do Not** Collect\n"
"3.  Information Processed **Locally** on Your Device\n"
"4.  Information Shared with **Third-Party Services**\n"
"5.  Your Control and Data Rights\n"
"6.  Security\n"
"7.  Children's Privacy\n"
"8.  Changes to This Policy\n"
"9.  Contact Us\n"
"\n"
"#### 1. Our Core Privacy Philosophy\n"
"\n"
"Your privacy is paramount. AI Runner is engineered to be a local-first application, meaning the vast majority of its operations, including AI model inference, data processing, and storage, occur directly on your com"
                        "puter. We do not operate servers that collect or store your personal data from the Software.\n"
"\n"
"#### 2. Information We Do Not Collect\n"
"\n"
"Capsize LLC **does not** collect, store, or have access to any of the following data through your use of the Software:\n"
"\n"
"* Your conversations or interactions with AI agents.\n"
"* The content of your documents or websites processed by the Retrieval-Augmented Generation (RAG) feature.\n"
"* Your voice data from real-time conversations.\n"
"* Images or art you generate.\n"
"* The adapted \"moods\" or \"personalities\" of your AI agents.\n"
"* Your browsing history from the built-in browser.\n"
"* Your IP address or unique device identifiers.\n"
"\n"
"All of the above data remains under your control on your local machine.\n"
"\n"
"#### 3. Information Processed Locally on Your Device\n"
"\n"
"While we don't collect your data, the Software needs to process certain information on your device to function. This processing is confined to your machine. Types of data "
                        "processed locally include:\n"
"\n"
"* **User Inputs:** Text, voice commands, and images you provide to the Software.\n"
"* **AI Model Outputs:** The Generated Content produced by the AI models.\n"
"* **RAG Data:** A local index of the documents and web pages you choose to make available to your AI agents.\n"
"* **Configuration and Profile Data:** Your saved agent personalities, moods, and conversation history, which are stored in a local SQLite database on your machine.\n"
"\n"
"#### 4. Information Shared with Third-Party Services\n"
"\n"
"Certain optional features in AI Runner require an internet connection to function by sending data to external, third-party services. **You control whether to enable these features.** When you use them, you are sending your data directly to that service, and your interaction is governed by their respective privacy policies.\n"
"\n"
"We encourage you to review the privacy policies of any third-party service you choose to connect with AI Runner.\n"
"\n"
"**A. Integrated Optiona"
                        "l Services:**\n"
"The Software may offer built-in integrations for your convenience. These services are disabled by default. If you enable them, they may receive the following data:\n"
"\n"
"* **OpenMeteo (Weather API):** Receives your general location coordinates to provide weather forecasts.\n"
"* **OpenStreetMap (Maps API):** Receives location data to display maps.\n"
"* **Aggregated Search Tool (e.g., DuckDuckGo, Wikipedia):** Receives the search queries you enter.\n"
"\n"
"**B. User-Configured API Services:**\n"
"AI Runner allows you to connect to external AI model providers by entering your own API keys. This provides flexibility but means you are responsible for the data you send.\n"
"\n"
"* **Examples:** OpenRouter, a custom Ollama endpoint, or other future LLM/image model providers.\n"
"* **Data Sent:** When you use one of these services, the **prompts you provide** (which may include text from your conversations, documents, or image descriptions) are sent to that provider to be processed.\n"
"* **You"
                        "r Responsibility:** Your use of these services is subject entirely to that provider's privacy policy and terms of service. **Capsize LLC has no control over how these third parties collect, use, or store your data.**\n"
"\n"
"#### 5. Your Control and Data Rights\n"
"\n"
"Because your data is stored locally, you have direct control over it. You can:\n"
"\n"
"* **Access Your Data:** Access conversation logs and other data stored within the local AI Runner directory on your computer.\n"
"* **Delete Your Data:** Delete individual conversations, RAG indexes, or the entire local database to permanently erase your history and agent profiles.\n"
"* **Disable Third-Party Services:** You can choose not to provide API keys or use features that connect to external services, keeping the application entirely offline.\n"
"\n"
"As a resident of Colorado, you have specific rights under the Colorado Privacy Act (CPA). While Capsize LLC does not act as a data controller for your personal information, we support your rights by de"
                        "signing the Software to give you the technical ability to manage your own data.\n"
"\n"
"#### 6. Security\n"
"\n"
"We take the security of the Software seriously. We implement measures to protect the application's integrity, such as enforcing HTTPS for any local server communication. However, you are responsible for the overall security of your own computer, network, and the data you choose to process with AI Runner.\n"
"\n"
"#### 7. Children's Privacy\n"
"\n"
"The Software is not intended for or directed at individuals under the age of 18. We do not knowingly collect personal information from children. If you are a parent or guardian and believe your child has used this software in a way that concerns you, please contact us.\n"
"\n"
"#### 8. Changes to This Policy\n"
"\n"
"We may update this Privacy Policy from time to time. We will notify you of any significant changes by updating the \"Last Updated\" date of this policy and may provide a notice within the Software or on our website. We encourage you to revi"
                        "ew this policy periodically.\n"
"\n"
"#### 9. Contact Us\n"
"\n"
"If you have any questions or concerns about this Privacy Policy, please contact us at:\n"
"\n"
"**contact@capsizegames.com**\n"
"", None))
        self.label.setText(QCoreApplication.translate("privacy_policy", u"Privacy Policy", None))
        self.checkBox.setText(QCoreApplication.translate("privacy_policy", u"I have read and agree to the terms of the Privacy Policy", None))
    # retranslateUi

