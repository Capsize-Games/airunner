# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'stable_diffusion_license.ui'
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

class Ui_stable_diffusion_license(object):
    def setupUi(self, stable_diffusion_license):
        if not stable_diffusion_license.objectName():
            stable_diffusion_license.setObjectName(u"stable_diffusion_license")
        stable_diffusion_license.resize(518, 603)
        self.gridLayout = QGridLayout(stable_diffusion_license)
        self.gridLayout.setObjectName(u"gridLayout")
        self.label = QLabel(stable_diffusion_license)
        self.label.setObjectName(u"label")
        font = QFont()
        font.setPointSize(11)
        font.setBold(True)
        self.label.setFont(font)

        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)

        self.scrollArea = QScrollArea(stable_diffusion_license)
        self.scrollArea.setObjectName(u"scrollArea")
        self.scrollArea.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 488, 3690))
        self.gridLayout_2 = QGridLayout(self.scrollAreaWidgetContents)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.label_2 = QLabel(self.scrollAreaWidgetContents)
        self.label_2.setObjectName(u"label_2")

        self.gridLayout_2.addWidget(self.label_2, 0, 0, 1, 1)

        self.scrollArea.setWidget(self.scrollAreaWidgetContents)

        self.gridLayout.addWidget(self.scrollArea, 1, 0, 1, 1)

        self.checkBox = QCheckBox(stable_diffusion_license)
        self.checkBox.setObjectName(u"checkBox")

        self.gridLayout.addWidget(self.checkBox, 2, 0, 1, 1)


        self.retranslateUi(stable_diffusion_license)
        self.checkBox.clicked["bool"].connect(stable_diffusion_license.agreement_clicked)

        QMetaObject.connectSlotsByName(stable_diffusion_license)
    # setupUi

    def retranslateUi(self, stable_diffusion_license):
        stable_diffusion_license.setWindowTitle(QCoreApplication.translate("stable_diffusion_license", u"Form", None))
        self.label.setText(QCoreApplication.translate("stable_diffusion_license", u"Stable Diffusion License", None))
        self.label_2.setText(QCoreApplication.translate("stable_diffusion_license", u"\n"
"Copyright (c) 2022 Robin Rombach and Patrick Esser and contributors \n"
" \n"
"CreativeML Open RAIL-M \n"
"dated August 22, 2022 \n"
" \n"
"Section I: PREAMBLE \n"
" \n"
"Multimodal generative models are being widely adopted and used, and have \n"
"the potential to transform the way artists, among other individuals, \n"
"conceive and benefit from AI or ML technologies as a tool for content \n"
"creation. \n"
" \n"
"Notwithstanding the current and potential benefits that these artifacts \n"
"can bring to society at large, there are also concerns about potential \n"
"misuses of them, either due to their technical limitations or ethical \n"
"considerations. \n"
" \n"
"In short, this license strives for both the open and responsible \n"
"downstream use of the accompanying model. When it comes to the open \n"
"character, we took inspiration from open source permissive licenses \n"
"regarding the grant of IP rights. Referring to the downstream responsible \n"
"use, we added use-based restrictions not permitting"
                        " the use of the Model \n"
"in very specific scenarios, in order for the licensor to be able to \n"
"enforce the license in case potential misuses of the Model may occur. At \n"
"the same time, we strive to promote open and responsible research on \n"
"generative models for art and content generation. \n"
" \n"
"Even though downstream derivative versions of the model could be released \n"
"under different licensing terms, the latter will always have to include - \n"
"at minimum - the same use-based restrictions as the ones in the original \n"
"license (this license). We believe in the intersection between open and \n"
"responsible AI development; thus, this License aims to strike a balance \n"
"between both in order to enable responsible open-science in the field of \n"
"AI. \n"
" \n"
"This License governs the use of the model (and its derivatives) and is \n"
"informed by the model card associated with the model. \n"
" \n"
"NOW THEREFORE, You and Licensor agree as follows: \n"
" \n"
"1. Definitions \n"
" \n"
"-"
                        " \"License\" means the terms and conditions for use, reproduction, and \n"
"Distribution as defined in this document. \n"
"- \"Data\" means a collection of information and/or content extracted from \n"
"the dataset used with the Model, including to train, pretrain, or \n"
"otherwise evaluate the Model. The Data is not licensed under this \n"
"License. \n"
"- \"Output\" means the results of operating a Model as embodied in \n"
"informational content resulting therefrom. \n"
"- \"Model\" means any accompanying machine-learning based assemblies \n"
"(including checkpoints), consisting of learnt weights, parameters \n"
"(including optimizer states), corresponding to the model architecture as \n"
"embodied in the Complementary Material, that have been trained or tuned, \n"
"in whole or in part on the Data, using the Complementary Material. \n"
"- \"Derivatives of the Model\" means all modifications to the Model, works \n"
"based on the Model, or any other model which is created or initialized by \n"
"transfer of pa"
                        "tterns of the weights, parameters, activations or output of \n"
"the Model, to the other model, in order to cause the other model to \n"
"perform similarly to the Model, including - but not limited to - \n"
"distillation methods entailing the use of intermediate data \n"
"representations or methods based on the generation of synthetic data by \n"
"the Model for training the other model. \n"
"- \"Complementary Material\" means the accompanying source code and scripts \n"
"used to define, run, load, benchmark or evaluate the Model, and used to \n"
"prepare data for training or evaluation, if any. This includes any \n"
"accompanying documentation, tutorials, examples, etc, if any. \n"
"- \"Distribution\" means any transmission, reproduction, publication or \n"
"other sharing of the Model or Derivatives of the Model to a third party, \n"
"including providing the Model as a hosted service made available by \n"
"electronic or other remote means - e.g. API-based or web access. \n"
"- \"Licensor\" means the copyright "
                        "owner or entity authorized by the \n"
"copyright owner that is granting the License, including the persons or \n"
"entities that may have rights in the Model and/or distributing the Model. \n"
"- \"You\" (or \"Your\") means an individual or Legal Entity exercising \n"
"permissions granted by this License and/or making use of the Model for \n"
"whichever purpose and in any field of use, including usage of the Model \n"
"in an end-use application - e.g. chatbot, translator, image generator. \n"
"- \"Third Parties\" means individuals or legal entities that are not under \n"
"common control with Licensor or You. \n"
"- \"Contribution\" means any work of authorship, including the original \n"
"version of the Model and any modifications or additions to that Model or \n"
"Derivatives of the Model thereof, that is intentionally submitted to \n"
"Licensor for inclusion in the Model by the copyright owner or by an \n"
"individual or Legal Entity authorized to submit on behalf of the \n"
"copyright owner. For the purpose"
                        "s of this definition, \"submitted\" means \n"
"any form of electronic, verbal, or written communication sent to the \n"
"Licensor or its representatives, including but not limited to \n"
"communication on electronic mailing lists, source code control systems, \n"
"and issue tracking systems that are managed by, or on behalf of, the \n"
"Licensor for the purpose of discussing and improving the Model, but \n"
"excluding communication that is conspicuously marked or otherwise \n"
"designated in writing by the copyright owner as \"Not a Contribution.\" \n"
"- \"Contributor\" means Licensor and any individual or Legal Entity on \n"
"behalf of whom a Contribution has been received by Licensor and \n"
"subsequently incorporated within the Model. \n"
" \n"
"Section II: INTELLECTUAL PROPERTY RIGHTS \n"
" \n"
"Both copyright and patent grants apply to the Model, Derivatives of the \n"
"Model and Complementary Material. The Model and Derivatives of the Model \n"
"are subject to additional terms as described in Section II"
                        "I. \n"
" \n"
"2. Grant of Copyright License. Subject to the terms and conditions of \n"
"this License, each Contributor hereby grants to You a perpetual, \n"
"worldwide, non-exclusive, no-charge, royalty-free, irrevocable copyright \n"
"license to reproduce, prepare, publicly display, publicly perform, \n"
"sublicense, and distribute the Complementary Material, the Model, and \n"
"Derivatives of the Model. \n"
"3. Grant of Patent License. Subject to the terms and conditions of this \n"
"License and where and as applicable, each Contributor hereby grants to \n"
"You a perpetual, worldwide, non-exclusive, no-charge, royalty-free, \n"
"irrevocable (except as stated in this paragraph) patent license to make, \n"
"have made, use, offer to sell, sell, import, and otherwise transfer the \n"
"Model and the Complementary Material, where such license applies only to \n"
"those patent claims licensable by such Contributor that are necessarily \n"
"infringed by their Contribution(s) alone or by combination of their \n"
"C"
                        "ontribution(s) with the Model to which such Contribution(s) was \n"
"submitted. If You institute patent litigation against any entity \n"
"(including a cross-claim or counterclaim in a lawsuit) alleging that the \n"
"Model and/or Complementary Material or a Contribution incorporated within \n"
"the Model and/or Complementary Material constitutes direct or \n"
"contributory patent infringement, then any patent licenses granted to You \n"
"under this License for the Model and/or Work shall terminate as of the \n"
"date such litigation is asserted or filed. \n"
" \n"
"Section III: CONDITIONS OF USAGE, DISTRIBUTION AND REDISTRIBUTION \n"
" \n"
"4. Distribution and Redistribution. You may host for Third Party remote \n"
"access purposes (e.g. software-as-a-service), reproduce and distribute \n"
"copies of the Model or Derivatives of the Model thereof in any medium, \n"
"with or without modifications, provided that You meet the following \n"
"conditions: \n"
"Use-based restrictions as referenced in paragraph 5 MUST "
                        "be included as \n"
"an enforceable provision by You in any type of legal agreement (e.g. a \n"
"license) governing the use and/or distribution of the Model or \n"
"Derivatives of the Model, and You shall give notice to subsequent users \n"
"You Distribute to, that the Model or Derivatives of the Model are subject \n"
"to paragraph 5. This provision does not apply to the use of Complementary \n"
"Material. \n"
"You must give any Third Party recipients of the Model or Derivatives of \n"
"the Model a copy of this License; \n"
"You must cause any modified files to carry prominent notices stating that \n"
"You changed the files; \n"
"You must retain all copyright, patent, trademark, and attribution notices \n"
"excluding those notices that do not pertain to any part of the Model, \n"
"Derivatives of the Model. \n"
"You may add Your own copyright statement to Your modifications and may \n"
"provide additional or different license terms and conditions - respecting \n"
"paragraph 4.a. - for use, reproduction, or Distr"
                        "ibution of Your \n"
"modifications, or for any such Derivatives of the Model as a whole, \n"
"provided Your use, reproduction, and Distribution of the Model otherwise \n"
"complies with the conditions stated in this License. \n"
"5. Use-based restrictions. The restrictions set forth in Attachment A are \n"
"considered Use-based restrictions. Therefore You cannot use the Model and \n"
"the Derivatives of the Model for the specified restricted uses. You may \n"
"use the Model subject to this License, including only for lawful purposes \n"
"and in accordance with the License. Use may include creating any content \n"
"with, finetuning, updating, running, training, evaluating and/or \n"
"reparametrizing the Model. You shall require all of Your users who use \n"
"the Model or a Derivative of the Model to comply with the terms of this \n"
"paragraph (paragraph 5). \n"
"6. The Output You Generate. Except as set forth herein, Licensor claims \n"
"no rights in the Output You generate using the Model. You are accountable"
                        " \n"
"for the Output you generate and its subsequent uses. No use of the output \n"
"can contravene any provision as stated in the License. \n"
" \n"
"Section IV: OTHER PROVISIONS \n"
" \n"
"7. Updates and Runtime Restrictions. To the maximum extent permitted by \n"
"law, Licensor reserves the right to restrict (remotely or otherwise) \n"
"usage of the Model in violation of this License, update the Model through \n"
"electronic means, or modify the Output of the Model based on updates. You \n"
"shall undertake reasonable efforts to use the latest version of the \n"
"Model. \n"
"8. Trademarks and related. Nothing in this License permits You to make \n"
"use of Licensors\u2019 trademarks, trade names, logos or to otherwise suggest \n"
"endorsement or misrepresent the relationship between the parties; and any \n"
"rights not expressly granted herein are reserved by the Licensors. \n"
"9. Disclaimer of Warranty. Unless required by applicable law or agreed to \n"
"in writing, Licensor provides the Model and the Com"
                        "plementary Material \n"
"(and each Contributor provides its Contributions) on an \"AS IS\" BASIS, \n"
"WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied, \n"
"including, without limitation, any warranties or conditions of TITLE, \n"
"NON-INFRINGEMENT, MERCHANTABILITY, or FITNESS FOR A PARTICULAR PURPOSE. \n"
"You are solely responsible for determining the appropriateness of using \n"
"or redistributing the Model, Derivatives of the Model, and the \n"
"Complementary Material and assume any risks associated with Your exercise \n"
"of permissions under this License. \n"
"10. Limitation of Liability. In no event and under no legal theory, \n"
"whether in tort (including negligence), contract, or otherwise, unless \n"
"required by applicable law (such as deliberate and grossly negligent \n"
"acts) or agreed to in writing, shall any Contributor be liable to You for \n"
"damages, including any direct, indirect, special, incidental, or \n"
"consequential damages of any character arising as a resu"
                        "lt of this \n"
"License or out of the use or inability to use the Model and the \n"
"Complementary Material (including but not limited to damages for loss of \n"
"goodwill, work stoppage, computer failure or malfunction, or any and all \n"
"other commercial damages or losses), even if such Contributor has been \n"
"advised of the possibility of such damages. \n"
"11. Accepting Warranty or Additional Liability. While redistributing the \n"
"Model, Derivatives of the Model and the Complementary Material thereof, \n"
"You may choose to offer, and charge a fee for, acceptance of support, \n"
"warranty, indemnity, or other liability obligations and/or rights \n"
"consistent with this License. However, in accepting such obligations, You \n"
"may act only on Your own behalf and on Your sole responsibility, not on \n"
"behalf of any other Contributor, and only if You agree to indemnify, \n"
"defend, and hold each Contributor harmless for any liability incurred by, \n"
"or claims asserted against, such Contributor by r"
                        "eason of your accepting \n"
"any such warranty or additional liability. \n"
"12. If any provision of this License is held to be invalid, illegal or \n"
"unenforceable, the remaining provisions shall be unaffected thereby and \n"
"remain valid as if such provision had not been set forth herein. \n"
" \n"
"", None))
        self.checkBox.setText(QCoreApplication.translate("stable_diffusion_license", u"I have read and agree to the terms of the Stable Diffusion license", None))
    # retranslateUi

