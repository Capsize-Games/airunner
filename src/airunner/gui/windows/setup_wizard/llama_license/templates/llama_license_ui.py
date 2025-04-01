# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'llama_license.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QGridLayout, QLabel,
    QScrollArea, QSizePolicy, QWidget)

class Ui_llama_license(object):
    def setupUi(self, llama_license):
        if not llama_license.objectName():
            llama_license.setObjectName(u"llama_license")
        llama_license.resize(568, 603)
        self.gridLayout_2 = QGridLayout(llama_license)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.scrollArea = QScrollArea(llama_license)
        self.scrollArea.setObjectName(u"scrollArea")
        self.scrollArea.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 739, 2007))
        self.gridLayout = QGridLayout(self.scrollAreaWidgetContents)
        self.gridLayout.setObjectName(u"gridLayout")
        self.label_2 = QLabel(self.scrollAreaWidgetContents)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setAlignment(Qt.AlignmentFlag.AlignLeading|Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout.addWidget(self.label_2, 0, 0, 1, 1)

        self.scrollArea.setWidget(self.scrollAreaWidgetContents)

        self.gridLayout_2.addWidget(self.scrollArea, 1, 0, 1, 1)

        self.label = QLabel(llama_license)
        self.label.setObjectName(u"label")
        font = QFont()
        font.setPointSize(11)
        font.setBold(True)
        self.label.setFont(font)

        self.gridLayout_2.addWidget(self.label, 0, 0, 1, 1)

        self.checkBox = QCheckBox(llama_license)
        self.checkBox.setObjectName(u"checkBox")

        self.gridLayout_2.addWidget(self.checkBox, 2, 0, 1, 1)


        self.retranslateUi(llama_license)
        self.checkBox.clicked["bool"].connect(llama_license.agreement_clicked)

        QMetaObject.connectSlotsByName(llama_license)
    # setupUi

    def retranslateUi(self, llama_license):
        llama_license.setWindowTitle(QCoreApplication.translate("llama_license", u"Form", None))
        self.label_2.setText(QCoreApplication.translate("llama_license", u"META LLAMA 3 COMMUNITY LICENSE AGREEMENT\n"
"Meta Llama 3 Version Release Date: April 18, 2024\n"
"\n"
"\u201cAgreement\u201d means the terms and conditions for use, reproduction, distribution and modification of the\n"
"Llama Materials set forth herein.\n"
"\n"
"\u201cDocumentation\u201d means the specifications, manuals and documentation accompanying Meta Llama 3\n"
"distributed by Meta at https://llama.meta.com/get-started/.\n"
"\n"
"\u201cLicensee\u201d or \u201cyou\u201d means you, or your employer or any other person or entity (if you are entering into\n"
"this Agreement on such person or entity\u2019s behalf), of the age required under applicable laws, rules or\n"
"regulations to provide legal consent and that has legal authority to bind your employer or such other\n"
"person or entity if you are entering in this Agreement on their behalf.\n"
"\n"
"\u201cMeta Llama 3\u201d means the foundational large language models and software and algorithms, including\n"
"machine-learning model code, trained model w"
                        "eights, inference-enabling code, training-enabling code,\n"
"fine-tuning enabling code and other elements of the foregoing distributed by Meta at\n"
"https://llama.meta.com/llama-downloads.\n"
"\n"
"\u201cLlama Materials\u201d means, collectively, Meta\u2019s proprietary Meta Llama 3 and Documentation (and any\n"
"portion thereof) made available under this Agreement.\n"
"\n"
"\u201cMeta\u201d or \u201cwe\u201d means Meta Platforms Ireland Limited (if you are located in or, if you are an entity, your\n"
"principal place of business is in the EEA or Switzerland) and Meta Platforms, Inc. (if you are located\n"
"outside of the EEA or Switzerland).\n"
"\n"
"By clicking \u201cI Accept\u201d below or by using or distributing any portion or element of the Llama Materials,\n"
"you agree to be bound by this Agreement.\n"
"\n"
"1. License Rights and Redistribution.\n"
"\n"
"  a. Grant of Rights. You are granted a non-exclusive, worldwide, non-transferable and royalty-free\n"
"limited license under Meta\u2019s intellectua"
                        "l property or other rights owned by Meta embodied in the Llama\n"
"Materials to use, reproduce, distribute, copy, create derivative works of, and make modifications to the\n"
"Llama Materials.\n"
"\n"
"  b. Redistribution and Use.\n"
"\n"
"      i. If you distribute or make available the Llama Materials (or any derivative works\n"
"thereof), or a product or service that uses any of them, including another AI model, you shall (A) provide\n"
"a copy of this Agreement with any such Llama Materials; and (B) prominently display \u201cBuilt with Meta\n"
"Llama 3\u201d on a related website, user interface, blogpost, about page, or product documentation. If you\n"
"use the Llama Materials to create, train, fine tune, or otherwise improve an AI model, which is\n"
"distributed or made available, you shall also include \u201cLlama 3\u201d at the beginning of any such AI model\n"
"name.\n"
"\n"
"      ii. If you receive Llama Materials, or any derivative works thereof, from a Licensee as part \n"
"of an integrated end use"
                        "r product, then Section 2 of this Agreement will not apply to you.\n"
"\n"
"      iii. You must retain in all copies of the Llama Materials that you distribute the following\n"
"attribution notice within a \u201cNotice\u201d text file distributed as a part of such copies: \u201cMeta Llama 3 is\n"
"licensed under the Meta Llama 3 Community License, Copyright \u00a9 Meta Platforms, Inc. All Rights\n"
"Reserved.\u201d\n"
"\n"
"      iv. Your use of the Llama Materials must comply with applicable laws and regulations\n"
"(including trade compliance laws and regulations) and adhere to the Acceptable Use Policy for the Llama\n"
"Materials (available at https://llama.meta.com/llama3/use-policy), which is hereby incorporated by\n"
"reference into this Agreement.\n"
"\n"
"      v. You will not use the Llama Materials or any output or results of the Llama Materials to\n"
"improve any other large language model (excluding Meta Llama 3 or derivative works thereof).\n"
"\n"
"2. Additional Commercial Terms. If, on the Meta "
                        "Llama 3 version release date, the monthly active users\n"
"of the products or services made available by or for Licensee, or Licensee\u2019s affiliates, is greater than 700\n"
"million monthly active users in the preceding calendar month, you must request a license from Meta,\n"
"which Meta may grant to you in its sole discretion, and you are not authorized to exercise any of the\n"
"rights under this Agreement unless or until Meta otherwise expressly grants you such rights.\n"
"\n"
"3. Disclaimer of Warranty. UNLESS REQUIRED BY APPLICABLE LAW, THE LLAMA MATERIALS AND ANY\n"
"OUTPUT AND RESULTS THEREFROM ARE PROVIDED ON AN \u201cAS IS\u201d BASIS, WITHOUT WARRANTIES OF\n"
"ANY KIND, AND META DISCLAIMS ALL WARRANTIES OF ANY KIND, BOTH EXPRESS AND IMPLIED,\n"
"INCLUDING, WITHOUT LIMITATION, ANY WARRANTIES OF TITLE, NON-INFRINGEMENT,\n"
"MERCHANTABILITY, OR FITNESS FOR A PARTICULAR PURPOSE. YOU ARE SOLELY RESPONSIBLE FOR\n"
"DETERMINING THE APPROPRIATENESS OF USING OR REDISTRIBUTING THE LLAMA MATERIALS AND\n"
"AS"
                        "SUME ANY RISKS ASSOCIATED WITH YOUR USE OF THE LLAMA MATERIALS AND ANY OUTPUT AND\n"
"RESULTS.\n"
"\n"
"4. Limitation of Liability. IN NO EVENT WILL META OR ITS AFFILIATES BE LIABLE UNDER ANY THEORY OF\n"
"LIABILITY, WHETHER IN CONTRACT, TORT, NEGLIGENCE, PRODUCTS LIABILITY, OR OTHERWISE, ARISING\n"
"OUT OF THIS AGREEMENT, FOR ANY LOST PROFITS OR ANY INDIRECT, SPECIAL, CONSEQUENTIAL,\n"
"INCIDENTAL, EXEMPLARY OR PUNITIVE DAMAGES, EVEN IF META OR ITS AFFILIATES HAVE BEEN ADVISED\n"
"OF THE POSSIBILITY OF ANY OF THE FOREGOING.\n"
"\n"
"5. Intellectual Property.\n"
"\n"
"  a. No trademark licenses are granted under this Agreement, and in connection with the Llama\n"
"Materials, neither Meta nor Licensee may use any name or mark owned by or associated with the other\n"
"or any of its affiliates, except as required for reasonable and customary use in describing and\n"
"redistributing the Llama Materials or as set forth in this Section 5(a). Meta hereby grants you a license to\n"
"use \u201cLlama 3\u201d (the \u201c"
                        "Mark\u201d) solely as required to comply with the last sentence of Section 1.b.i. You will\n"
"comply with Meta\u2019s brand guidelines (currently accessible at\n"
"https://about.meta.com/brand/resources/meta/company-brand/ ). All goodwill arising out of your use\n"
"of the Mark will inure to the benefit of Meta.\n"
"\n"
"  b. Subject to Meta\u2019s ownership of Llama Materials and derivatives made by or for Meta, with\n"
"respect to any derivative works and modifications of the Llama Materials that are made by you, as\n"
"between you and Meta, you are and will be the owner of such derivative works and modifications.\n"
"\n"
"  c. If you institute litigation or other proceedings against Meta or any entity (including a\n"
"cross-claim or counterclaim in a lawsuit) alleging that the Llama Materials or Meta Llama 3 outputs or\n"
"results, or any portion of any of the foregoing, constitutes infringement of intellectual property or other\n"
"rights owned or licensable by you, then any licenses granted to you under "
                        "this Agreement shall\n"
"terminate as of the date such litigation or claim is filed or instituted. You will indemnify and hold\n"
"harmless Meta from and against any claim by any third party arising out of or related to your use or\n"
"distribution of the Llama Materials.\n"
"\n"
"6. Term and Termination. The term of this Agreement will commence upon your acceptance of this\n"
"Agreement or access to the Llama Materials and will continue in full force and effect until terminated in\n"
"accordance with the terms and conditions herein. Meta may terminate this Agreement if you are in\n"
"breach of any term or condition of this Agreement. Upon termination of this Agreement, you shall delete\n"
"and cease use of the Llama Materials. Sections 3, 4 and 7 shall survive the termination of this\n"
"Agreement.\n"
"\n"
"7. Governing Law and Jurisdiction. This Agreement will be governed and construed under the laws of\n"
"the State of California without regard to choice of law principles, and the UN Convention on Contracts"
                        "\n"
"for the International Sale of Goods does not apply to this Agreement. The courts of California shall have\n"
"exclusive jurisdiction of any dispute arising out of this Agreement.", None))
        self.label.setText(QCoreApplication.translate("llama_license", u"META LLAMA 3 COMMUNITY LICENSE AGREEMENT", None))
        self.checkBox.setText(QCoreApplication.translate("llama_license", u"I have read and agree to the terms of the Meta LLama 3 License", None))
    # retranslateUi

