# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'mistral_license.ui'
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
from PySide6.QtWidgets import (QApplication, QGridLayout, QLabel, QScrollArea,
    QSizePolicy, QTextBrowser, QWidget)

class Ui_mistral_license(object):
    def setupUi(self, mistral_license):
        if not mistral_license.objectName():
            mistral_license.setObjectName(u"mistral_license")
        mistral_license.resize(746, 1131)
        self.gridLayout = QGridLayout(mistral_license)
        self.gridLayout.setObjectName(u"gridLayout")
        self.scrollArea = QScrollArea(mistral_license)
        self.scrollArea.setObjectName(u"scrollArea")
        self.scrollArea.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 726, 1088))
        self.gridLayout_2 = QGridLayout(self.scrollAreaWidgetContents)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.textBrowser = QTextBrowser(self.scrollAreaWidgetContents)
        self.textBrowser.setObjectName(u"textBrowser")

        self.gridLayout_2.addWidget(self.textBrowser, 0, 0, 1, 1)

        self.scrollArea.setWidget(self.scrollAreaWidgetContents)

        self.gridLayout.addWidget(self.scrollArea, 1, 0, 1, 1)

        self.label = QLabel(mistral_license)
        self.label.setObjectName(u"label")
        font = QFont()
        font.setPointSize(11)
        font.setBold(True)
        self.label.setFont(font)

        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)


        self.retranslateUi(mistral_license)

        QMetaObject.connectSlotsByName(mistral_license)
    # setupUi

    def retranslateUi(self, mistral_license):
        mistral_license.setWindowTitle(QCoreApplication.translate("mistral_license", u"Form", None))
        self.textBrowser.setHtml(QCoreApplication.translate("mistral_license", u"<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
"<html><head><meta name=\"qrichtext\" content=\"1\" /><meta charset=\"utf-8\" /><style type=\"text/css\">\n"
"p, li { white-space: pre-wrap; }\n"
"hr { height: 1px; border-width: 0; }\n"
"li.unchecked::marker { content: \"\\2610\"; }\n"
"li.checked::marker { content: \"\\2612\"; }\n"
"</style></head><body style=\" font-family:'Ubuntu'; font-size:11pt; font-weight:400; font-style:normal;\">\n"
"<h1 style=\" margin-top:18px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:xx-large; font-weight:700;\">Mistral AI Research License</span></h1>\n"
"<p style=\" margin-top:12px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">If You want to use a Mistral Model, a Derivative or an Output for any purpose that is not expressly authorized under this Agreement, You must request a license from Mistral AI, whic"
                        "h Mistral AI may grant to You in Mistral AI's sole discretion. To discuss such a license, please contact Mistral AI via the website contact form: <a href=\"https://mistral.ai/contact/\"><span style=\" text-decoration: underline; color:#308cc6;\">https://mistral.ai/contact/</span></a></p>\n"
"<h2 style=\" margin-top:16px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:x-large; font-weight:700;\">1. Scope and acceptance</span></h2>\n"
"<p style=\" margin-top:12px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-weight:700;\">1.1. Scope of the Agreement.</span> This Agreement applies to any use, modification, or Distribution of any Mistral Model by You, regardless of the source You obtained a copy of such Mistral Model.<br /><span style=\" font-weight:700;\">1.2. Acceptance.</span> By accessing, using, modifying, Distributing a Mistral Model, or by creating, using or distributi"
                        "ng a Derivative of the Mistral Model, You agree to be bound by this Agreement.<br /><span style=\" font-weight:700;\">1.3. Acceptance on behalf of a third-party.</span> If You accept this Agreement on behalf of Your employer or another person or entity, You warrant and represent that You have the authority to act and accept this Agreement on their behalf. In such a case, the word &quot;You&quot; in this Agreement will refer to Your employer or such other person or entity.</p>\n"
"<h2 style=\" margin-top:16px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:x-large; font-weight:700;\">2. License</span></h2>\n"
"<p style=\" margin-top:12px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-weight:700;\">2.1. Grant of rights</span>. Subject to Section 3 below, Mistral AI hereby grants You a non-exclusive, royalty-free, worldwide, non-sublicensable, non-transferable, limited licens"
                        "e to use, copy, modify, and Distribute under the conditions provided in Section 2.2 below, the Mistral Model and any Derivatives made by or for Mistral AI and to create Derivatives of the Mistral Model.<br /><span style=\" font-weight:700;\">2.2. Distribution of Mistral Model and Derivatives made by or for Mistral AI.</span> Subject to Section 3 below, You may Distribute copies of the Mistral Model and/or Derivatives made by or for Mistral AI, under the following conditions: You must make available a copy of this Agreement to third-party recipients of the Mistral Models and/or Derivatives made by or for Mistral AI you Distribute, it being specified that any rights to use the Mistral Models and/or Derivatives made by or for Mistral AI shall be directly granted by Mistral AI to said third-party recipients pursuant to the Mistral AI Research License agreement executed between these parties; You must retain in all copies of the Mistral Models the following attribution notice within a &quot;Notice&quot; text file d"
                        "istributed as part of such copies: &quot;Licensed by Mistral AI under the Mistral AI Research License&quot;.<br /><span style=\" font-weight:700;\">2.3. Distribution of Derivatives made by or for You.</span> Subject to Section 3 below, You may Distribute any Derivatives made by or for You under additional or different terms and conditions, provided that: In any event, the use and modification of Mistral Model and/or Derivatives made by or for Mistral AI shall remain governed by the terms and conditions of this Agreement; You include in any such Derivatives made by or for You prominent notices stating that You modified the concerned Mistral Model; and Any terms and conditions You impose on any third-party recipients relating to Derivatives made by or for You shall neither limit such third-party recipients' use of the Mistral Model or any Derivatives made by or for Mistral AI in accordance with the Mistral AI Research License nor conflict with any of its terms and conditions.</p>\n"
"<h2 style=\" margin-top:16px"
                        "; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:x-large; font-weight:700;\">3. Limitations</span></h2>\n"
"<p style=\" margin-top:12px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-weight:700;\">3.1. Misrepresentation.</span> You must not misrepresent or imply, through any means, that the Derivatives made by or for You and/or any modified version of the Mistral Model You Distribute under your name and responsibility is an official product of Mistral AI or has been endorsed, approved or validated by Mistral AI, unless You are authorized by Us to do so in writing.<br /><span style=\" font-weight:700;\">3.2. Usage Limitation.</span> You shall only use the Mistral Models, Derivatives (whether or not created by Mistral AI) and Outputs for Research Purposes.</p>\n"
"<h2 style=\" margin-top:16px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-in"
                        "dent:0px;\"><span style=\" font-size:x-large; font-weight:700;\">4. Intellectual Property</span></h2>\n"
"<p style=\" margin-top:12px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-weight:700;\">4.1. Trademarks.</span> No trademark licenses are granted under this Agreement, and in connection with the Mistral Models, You may not use any name or mark owned by or associated with Mistral AI or any of its affiliates, except (i) as required for reasonable and customary use in describing and Distributing the Mistral Models and Derivatives made by or for Mistral AI and (ii) for attribution purposes as required by this Agreement.<br /><span style=\" font-weight:700;\">4.2. Outputs.</span> We claim no ownership rights in and to the Outputs. You are solely responsible for the Outputs You generate and their subsequent uses in accordance with this Agreement. Any Outputs shall be subject to the restrictions set out in Section 3 of this Agreement.<br /><span"
                        " style=\" font-weight:700;\">4.3. Derivatives.</span> By entering into this Agreement, You accept that any Derivatives that You may create or that may be created for You shall be subject to the restrictions set out in Section 3 of this Agreement.</p>\n"
"<h2 style=\" margin-top:16px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:x-large; font-weight:700;\">5. Liability</span></h2>\n"
"<p style=\" margin-top:12px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-weight:700;\">5.1. Limitation of liability.</span> In no event, unless required by applicable law (such as deliberate and grossly negligent acts) or agreed to in writing, shall Mistral AI be liable to You for damages, including any direct, indirect, special, incidental, or consequential damages of any character arising as a result of this Agreement or out of the use or inability to use the Mistral Models and Derivativ"
                        "es (including but not limited to damages for loss of data, loss of goodwill, loss of expected profit or savings, work stoppage, computer failure or malfunction, or any damage caused by malware or security breaches), even if Mistral AI has been advised of the possibility of such damages.<br /><span style=\" font-weight:700;\">5.2. Indemnification.</span> You agree to indemnify and hold harmless Mistral AI from and against any claims, damages, or losses arising out of or related to Your use or Distribution of the Mistral Models and Derivatives.</p>\n"
"<h2 style=\" margin-top:16px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:x-large; font-weight:700;\">6. Warranty</span></h2>\n"
"<p style=\" margin-top:12px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-weight:700;\">6.1. Disclaimer.</span> Unless required by applicable law or prior agreed to by Mistral AI in writing, Mis"
                        "tral AI provides the Mistral Models and Derivatives on an &quot;AS IS&quot; BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied, including, without limitation, any warranties or conditions of TITLE, NON-INFRINGEMENT, MERCHANTABILITY, or FITNESS FOR A PARTICULAR PURPOSE. Mistral AI does not represent nor warrant that the Mistral Models and Derivatives will be error-free, meet Your or any third party's requirements, be secure or will allow You or any third party to achieve any kind of result or generate any kind of content. You are solely responsible for determining the appropriateness of using or Distributing the Mistral Models and Derivatives and assume any risks associated with Your exercise of rights under this Agreement.</p>\n"
"<h2 style=\" margin-top:16px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:x-large; font-weight:700;\">7. Termination</span></h2>\n"
"<p style=\" margin-top:12px; margin-bottom:12px;"
                        " margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-weight:700;\">7.1. Term.</span> This Agreement is effective as of the date of your acceptance of this Agreement or access to the concerned Mistral Models or Derivatives and will continue until terminated in accordance with the following terms.<br /><span style=\" font-weight:700;\">7.2. Termination.</span> Mistral AI may terminate this Agreement at any time if You are in breach of this Agreement. Upon termination of this Agreement, You must cease to use all Mistral Models and Derivatives and shall permanently delete any copy thereof. The following provisions, in their relevant parts, will survive any termination or expiration of this Agreement, each for the duration necessary to achieve its own intended purpose (e.g. the liability provision will survive until the end of the applicable limitation period):Sections 5 (Liability), 6(Warranty), 7 (Termination) and 8 (General Provisions).<br /><span style=\" font-weight:70"
                        "0;\">7.3. Litigation.</span> If You initiate any legal action or proceedings against Us or any other entity (including a cross-claim or counterclaim in a lawsuit), alleging that the Model or a Derivative, or any part thereof, infringe upon intellectual property or other rights owned or licensable by You, then any licenses granted to You under this Agreement will immediately terminate as of the date such legal action or claim is filed or initiated.</p>\n"
"<h2 style=\" margin-top:16px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:x-large; font-weight:700;\">8. General provisions</span></h2>\n"
"<p style=\" margin-top:12px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-weight:700;\">8.1. Governing laws.</span> This Agreement will be governed by the laws of France, without regard to choice of law principles, and the UN Convention on Contracts for the International Sale of G"
                        "oods does not apply to this Agreement.<br /><span style=\" font-weight:700;\">8.2. Competent jurisdiction.</span> The courts of Paris shall have exclusive jurisdiction of any dispute arising out of this Agreement.<br /><span style=\" font-weight:700;\">8.3. Severability.</span> If any provision of this Agreement is held to be invalid, illegal or unenforceable, the remaining provisions shall be unaffected thereby and remain valid as if such provision had not been set forth herein.</p>\n"
"<h2 style=\" margin-top:16px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:x-large; font-weight:700;\">9. Definitions</span></h2>\n"
"<p style=\" margin-top:12px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">&quot;Agreement&quot;: means this Mistral AI Research License agreement governing the access, use, and Distribution of the Mistral Models, Derivatives and Outputs.<br />&quot;Derivative&quot;: means an"
                        "y (i) modified version of the Mistral Model (including but not limited to any customized or fine-tuned version thereof), (ii) work based on the Mistral Model, or (iii) any other derivative work thereof.<br />&quot;Distribution&quot;, &quot;Distributing&quot;, &quot;Distribute&quot; or &quot;Distributed&quot;: means supplying, providing or making available, by any means, a copy of the Mistral Models and/or the Derivatives as the case may be, subject to Section 3 of this Agreement.<br />&quot;Mistral AI&quot;, &quot;We&quot; or &quot;Us&quot;: means Mistral AI, a French soci\u00e9t\u00e9 par actions simplifi\u00e9e registered in the Paris commercial registry under the number 952 418 325, and having its registered seat at 15, rue des Halles, 75001 Paris.<br />&quot;Mistral Model&quot;: means the foundational large language model(s), and its elements which include algorithms, software, instructed checkpoints, parameters, source code (inference code, evaluation code and, if applicable, fine-tuning code) and any oth"
                        "er elements associated thereto made available by Mistral AI under this Agreement, including, if any, the technical documentation, manuals and instructions for the use and operation thereof.<br />&quot;Research Purposes&quot;: means any use of a Mistral Model, Derivative, or Output that is solely for (a) personal, scientific or academic research, and (b) for non-profit and non-commercial purposes, and not directly or indirectly connected to any commercial activities or business operations. For illustration purposes, Research Purposes does not include (1) any usage of the Mistral Model, Derivative or Output by individuals or contractors employed in or engaged by companies in the context of (a) their daily tasks, or (b) any activity (including but not limited to any testing or proof-of-concept) that is intended to generate revenue, nor (2) any Distribution by a commercial entity of the Mistral Model, Derivative or Output whether in return for payment or free of charge, in any medium or form, including but not lim"
                        "ited to through a hosted or managed service (e.g. SaaS, cloud instances, etc.), or behind a software layer.<br />&quot;Outputs&quot;: means any content generated by the operation of the Mistral Models or the Derivatives from a prompt (i.e., text instructions) provided by users. For the avoidance of doubt, Outputs do not include any components of a Mistral Models, such as any fine-tuned versions of the Mistral Models, the weights, or parameters.<br />&quot;You&quot;: means the individual or entity entering into this Agreement with Mistral AI.</p></body></html>", None))
        self.label.setText(QCoreApplication.translate("mistral_license", u"Mistral AI Research License", None))
    # retranslateUi

