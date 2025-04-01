# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'generator_tab_backup.ui'
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
from PySide6.QtWidgets import (QApplication, QGridLayout, QSizePolicy, QTabWidget,
    QWidget)

from airunner.gui.widgets.generator_form.generator_form_widget import GeneratorForm

class Ui_generator_tab(object):
    def setupUi(self, generator_tab):
        if not generator_tab.objectName():
            generator_tab.setObjectName(u"generator_tab")
        generator_tab.resize(330, 972)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(generator_tab.sizePolicy().hasHeightForWidth())
        generator_tab.setSizePolicy(sizePolicy)
        self.gridLayout_2 = QGridLayout(generator_tab)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.gridLayout_2.setContentsMargins(0, 0, 0, 0)
        self.generator_tabs = QTabWidget(generator_tab)
        self.generator_tabs.setObjectName(u"generator_tabs")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.generator_tabs.sizePolicy().hasHeightForWidth())
        self.generator_tabs.setSizePolicy(sizePolicy1)
        self.tab_stablediffusion = QWidget()
        self.tab_stablediffusion.setObjectName(u"tab_stablediffusion")
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.tab_stablediffusion.sizePolicy().hasHeightForWidth())
        self.tab_stablediffusion.setSizePolicy(sizePolicy2)
        self.gridLayout = QGridLayout(self.tab_stablediffusion)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.tab_widget_stablediffusion = QTabWidget(self.tab_stablediffusion)
        self.tab_widget_stablediffusion.setObjectName(u"tab_widget_stablediffusion")
        self.tab_widget_stablediffusion.setTabPosition(QTabWidget.West)
        self.tab_stablediffusion_txt2img = QWidget()
        self.tab_stablediffusion_txt2img.setObjectName(u"tab_stablediffusion_txt2img")
        sizePolicy2.setHeightForWidth(self.tab_stablediffusion_txt2img.sizePolicy().hasHeightForWidth())
        self.tab_stablediffusion_txt2img.setSizePolicy(sizePolicy2)
        self.gridLayout_7 = QGridLayout(self.tab_stablediffusion_txt2img)
        self.gridLayout_7.setObjectName(u"gridLayout_7")
        self.gridLayout_7.setContentsMargins(0, 0, 0, 0)
        self.generator_form_stablediffusion_txt2img = GeneratorForm(self.tab_stablediffusion_txt2img)
        self.generator_form_stablediffusion_txt2img.setObjectName(u"generator_form_stablediffusion_txt2img")

        self.gridLayout_7.addWidget(self.generator_form_stablediffusion_txt2img, 0, 0, 1, 1)

        self.tab_widget_stablediffusion.addTab(self.tab_stablediffusion_txt2img, "")
        self.tab_stablediffusion_outpaint = QWidget()
        self.tab_stablediffusion_outpaint.setObjectName(u"tab_stablediffusion_outpaint")
        sizePolicy2.setHeightForWidth(self.tab_stablediffusion_outpaint.sizePolicy().hasHeightForWidth())
        self.tab_stablediffusion_outpaint.setSizePolicy(sizePolicy2)
        self.gridLayout_10 = QGridLayout(self.tab_stablediffusion_outpaint)
        self.gridLayout_10.setObjectName(u"gridLayout_10")
        self.gridLayout_10.setContentsMargins(0, 0, 0, 0)
        self.generator_form_stablediffusion_outpaint = GeneratorForm(self.tab_stablediffusion_outpaint)
        self.generator_form_stablediffusion_outpaint.setObjectName(u"generator_form_stablediffusion_outpaint")

        self.gridLayout_10.addWidget(self.generator_form_stablediffusion_outpaint, 0, 0, 1, 1)

        self.tab_widget_stablediffusion.addTab(self.tab_stablediffusion_outpaint, "")
        self.tab_stablediffusion_depth2img = QWidget()
        self.tab_stablediffusion_depth2img.setObjectName(u"tab_stablediffusion_depth2img")
        sizePolicy2.setHeightForWidth(self.tab_stablediffusion_depth2img.sizePolicy().hasHeightForWidth())
        self.tab_stablediffusion_depth2img.setSizePolicy(sizePolicy2)
        self.gridLayout_11 = QGridLayout(self.tab_stablediffusion_depth2img)
        self.gridLayout_11.setObjectName(u"gridLayout_11")
        self.gridLayout_11.setContentsMargins(0, 0, 0, 0)
        self.generator_form_stablediffusion_depth2img = GeneratorForm(self.tab_stablediffusion_depth2img)
        self.generator_form_stablediffusion_depth2img.setObjectName(u"generator_form_stablediffusion_depth2img")

        self.gridLayout_11.addWidget(self.generator_form_stablediffusion_depth2img, 0, 0, 1, 1)

        self.tab_widget_stablediffusion.addTab(self.tab_stablediffusion_depth2img, "")
        self.tab_stablediffusion_pix2pix = QWidget()
        self.tab_stablediffusion_pix2pix.setObjectName(u"tab_stablediffusion_pix2pix")
        sizePolicy2.setHeightForWidth(self.tab_stablediffusion_pix2pix.sizePolicy().hasHeightForWidth())
        self.tab_stablediffusion_pix2pix.setSizePolicy(sizePolicy2)
        self.gridLayout_12 = QGridLayout(self.tab_stablediffusion_pix2pix)
        self.gridLayout_12.setObjectName(u"gridLayout_12")
        self.gridLayout_12.setContentsMargins(0, 0, 0, 0)
        self.generator_form_stablediffusion_pix2pix = GeneratorForm(self.tab_stablediffusion_pix2pix)
        self.generator_form_stablediffusion_pix2pix.setObjectName(u"generator_form_stablediffusion_pix2pix")

        self.gridLayout_12.addWidget(self.generator_form_stablediffusion_pix2pix, 0, 0, 1, 1)

        self.tab_widget_stablediffusion.addTab(self.tab_stablediffusion_pix2pix, "")
        self.tab_stablediffusion_upscale = QWidget()
        self.tab_stablediffusion_upscale.setObjectName(u"tab_stablediffusion_upscale")
        sizePolicy2.setHeightForWidth(self.tab_stablediffusion_upscale.sizePolicy().hasHeightForWidth())
        self.tab_stablediffusion_upscale.setSizePolicy(sizePolicy2)
        self.gridLayout_5 = QGridLayout(self.tab_stablediffusion_upscale)
        self.gridLayout_5.setObjectName(u"gridLayout_5")
        self.gridLayout_5.setContentsMargins(0, 0, 0, 0)
        self.generator_form_stablediffusion_upscale = GeneratorForm(self.tab_stablediffusion_upscale)
        self.generator_form_stablediffusion_upscale.setObjectName(u"generator_form_stablediffusion_upscale")

        self.gridLayout_5.addWidget(self.generator_form_stablediffusion_upscale, 0, 0, 1, 1)

        self.tab_widget_stablediffusion.addTab(self.tab_stablediffusion_upscale, "")
        self.tab_stablediffusion_superresolution = QWidget()
        self.tab_stablediffusion_superresolution.setObjectName(u"tab_stablediffusion_superresolution")
        sizePolicy2.setHeightForWidth(self.tab_stablediffusion_superresolution.sizePolicy().hasHeightForWidth())
        self.tab_stablediffusion_superresolution.setSizePolicy(sizePolicy2)
        self.gridLayout_6 = QGridLayout(self.tab_stablediffusion_superresolution)
        self.gridLayout_6.setObjectName(u"gridLayout_6")
        self.gridLayout_6.setContentsMargins(0, 0, 0, 0)
        self.generator_form_stablediffusion_superresolution = GeneratorForm(self.tab_stablediffusion_superresolution)
        self.generator_form_stablediffusion_superresolution.setObjectName(u"generator_form_stablediffusion_superresolution")

        self.gridLayout_6.addWidget(self.generator_form_stablediffusion_superresolution, 0, 0, 1, 1)

        self.tab_widget_stablediffusion.addTab(self.tab_stablediffusion_superresolution, "")
        self.tab_stablediffusion_txt2vid = QWidget()
        self.tab_stablediffusion_txt2vid.setObjectName(u"tab_stablediffusion_txt2vid")
        sizePolicy2.setHeightForWidth(self.tab_stablediffusion_txt2vid.sizePolicy().hasHeightForWidth())
        self.tab_stablediffusion_txt2vid.setSizePolicy(sizePolicy2)
        self.gridLayout_13 = QGridLayout(self.tab_stablediffusion_txt2vid)
        self.gridLayout_13.setObjectName(u"gridLayout_13")
        self.gridLayout_13.setContentsMargins(0, 0, 0, 0)
        self.generator_form_txt2vid = GeneratorForm(self.tab_stablediffusion_txt2vid)
        self.generator_form_txt2vid.setObjectName(u"generator_form_txt2vid")

        self.gridLayout_13.addWidget(self.generator_form_txt2vid, 0, 0, 1, 1)

        self.tab_widget_stablediffusion.addTab(self.tab_stablediffusion_txt2vid, "")

        self.gridLayout.addWidget(self.tab_widget_stablediffusion, 0, 0, 1, 1)

        self.generator_tabs.addTab(self.tab_stablediffusion, "")
        self.tab_kandinsky = QWidget()
        self.tab_kandinsky.setObjectName(u"tab_kandinsky")
        sizePolicy2.setHeightForWidth(self.tab_kandinsky.sizePolicy().hasHeightForWidth())
        self.tab_kandinsky.setSizePolicy(sizePolicy2)
        self.gridLayout_3 = QGridLayout(self.tab_kandinsky)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.gridLayout_3.setContentsMargins(0, 0, 0, 0)
        self.tab_widget_kandinsky = QTabWidget(self.tab_kandinsky)
        self.tab_widget_kandinsky.setObjectName(u"tab_widget_kandinsky")
        self.tab_widget_kandinsky.setTabPosition(QTabWidget.West)
        self.tab_kandinsky_txt2img = QWidget()
        self.tab_kandinsky_txt2img.setObjectName(u"tab_kandinsky_txt2img")
        sizePolicy2.setHeightForWidth(self.tab_kandinsky_txt2img.sizePolicy().hasHeightForWidth())
        self.tab_kandinsky_txt2img.setSizePolicy(sizePolicy2)
        self.gridLayout_8 = QGridLayout(self.tab_kandinsky_txt2img)
        self.gridLayout_8.setObjectName(u"gridLayout_8")
        self.gridLayout_8.setContentsMargins(0, 0, 0, 0)
        self.generator_form_kandinsky_txt2img = GeneratorForm(self.tab_kandinsky_txt2img)
        self.generator_form_kandinsky_txt2img.setObjectName(u"generator_form_kandinsky_txt2img")

        self.gridLayout_8.addWidget(self.generator_form_kandinsky_txt2img, 0, 0, 1, 1)

        self.tab_widget_kandinsky.addTab(self.tab_kandinsky_txt2img, "")
        self.tab_kandinsky_outpaint = QWidget()
        self.tab_kandinsky_outpaint.setObjectName(u"tab_kandinsky_outpaint")
        sizePolicy2.setHeightForWidth(self.tab_kandinsky_outpaint.sizePolicy().hasHeightForWidth())
        self.tab_kandinsky_outpaint.setSizePolicy(sizePolicy2)
        self.gridLayout_14 = QGridLayout(self.tab_kandinsky_outpaint)
        self.gridLayout_14.setObjectName(u"gridLayout_14")
        self.gridLayout_14.setContentsMargins(0, 0, 0, 0)
        self.generator_form_kandinsky_outpaint = GeneratorForm(self.tab_kandinsky_outpaint)
        self.generator_form_kandinsky_outpaint.setObjectName(u"generator_form_kandinsky_outpaint")

        self.gridLayout_14.addWidget(self.generator_form_kandinsky_outpaint, 0, 0, 1, 1)

        self.tab_widget_kandinsky.addTab(self.tab_kandinsky_outpaint, "")

        self.gridLayout_3.addWidget(self.tab_widget_kandinsky, 0, 0, 1, 1)

        self.generator_tabs.addTab(self.tab_kandinsky, "")
        self.tab_shape = QWidget()
        self.tab_shape.setObjectName(u"tab_shape")
        sizePolicy2.setHeightForWidth(self.tab_shape.sizePolicy().hasHeightForWidth())
        self.tab_shape.setSizePolicy(sizePolicy2)
        self.gridLayout_4 = QGridLayout(self.tab_shape)
        self.gridLayout_4.setObjectName(u"gridLayout_4")
        self.gridLayout_4.setContentsMargins(0, 0, 0, 0)
        self.tab_widget_shape = QTabWidget(self.tab_shape)
        self.tab_widget_shape.setObjectName(u"tab_widget_shape")
        self.tab_widget_shape.setTabPosition(QTabWidget.West)
        self.tab_shape_txt2img = QWidget()
        self.tab_shape_txt2img.setObjectName(u"tab_shape_txt2img")
        sizePolicy2.setHeightForWidth(self.tab_shape_txt2img.sizePolicy().hasHeightForWidth())
        self.tab_shape_txt2img.setSizePolicy(sizePolicy2)
        self.gridLayout_9 = QGridLayout(self.tab_shape_txt2img)
        self.gridLayout_9.setObjectName(u"gridLayout_9")
        self.gridLayout_9.setContentsMargins(0, 0, 0, 0)
        self.generator_form_shape_txt2img = GeneratorForm(self.tab_shape_txt2img)
        self.generator_form_shape_txt2img.setObjectName(u"generator_form_shape_txt2img")

        self.gridLayout_9.addWidget(self.generator_form_shape_txt2img, 0, 0, 1, 1)

        self.tab_widget_shape.addTab(self.tab_shape_txt2img, "")

        self.gridLayout_4.addWidget(self.tab_widget_shape, 0, 0, 1, 1)

        self.generator_tabs.addTab(self.tab_shape, "")

        self.gridLayout_2.addWidget(self.generator_tabs, 0, 0, 1, 1)


        self.retranslateUi(generator_tab)
        self.generator_tabs.currentChanged.connect(generator_tab.handle_generator_tab_changed)
        self.tab_widget_stablediffusion.currentChanged.connect(generator_tab.handle_tab_section_changed)

        self.generator_tabs.setCurrentIndex(0)
        self.tab_widget_stablediffusion.setCurrentIndex(0)
        self.tab_widget_kandinsky.setCurrentIndex(1)
        self.tab_widget_shape.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(generator_tab)
    # setupUi

    def retranslateUi(self, generator_tab):
        generator_tab.setWindowTitle(QCoreApplication.translate("generator_tab", u"Form", None))
        self.tab_stablediffusion_txt2img.setProperty("generator_section", QCoreApplication.translate("generator_tab", u"txt2img", None))
        self.tab_stablediffusion_txt2img.setProperty("generator_name", QCoreApplication.translate("generator_tab", u"stablediffusion", None))
        self.generator_form_stablediffusion_txt2img.setProperty("generator_section", QCoreApplication.translate("generator_tab", u"txt2img", None))
        self.generator_form_stablediffusion_txt2img.setProperty("generator_name", QCoreApplication.translate("generator_tab", u"stablediffusion", None))
        self.tab_widget_stablediffusion.setTabText(self.tab_widget_stablediffusion.indexOf(self.tab_stablediffusion_txt2img), QCoreApplication.translate("generator_tab", u"txt2img / img2img", None))
        self.tab_stablediffusion_outpaint.setProperty("generator_section", QCoreApplication.translate("generator_tab", u"outpaint", None))
        self.tab_stablediffusion_outpaint.setProperty("generator_name", QCoreApplication.translate("generator_tab", u"stablediffusion", None))
        self.generator_form_stablediffusion_outpaint.setProperty("generator_section", QCoreApplication.translate("generator_tab", u"outpaint", None))
        self.generator_form_stablediffusion_outpaint.setProperty("generator_name", QCoreApplication.translate("generator_tab", u"stablediffusion", None))
        self.tab_widget_stablediffusion.setTabText(self.tab_widget_stablediffusion.indexOf(self.tab_stablediffusion_outpaint), QCoreApplication.translate("generator_tab", u"inpaint / outapint", None))
        self.tab_stablediffusion_depth2img.setProperty("generator_section", QCoreApplication.translate("generator_tab", u"depth2img", None))
        self.tab_stablediffusion_depth2img.setProperty("generator_name", QCoreApplication.translate("generator_tab", u"stablediffusion", None))
        self.generator_form_stablediffusion_depth2img.setProperty("generator_section", QCoreApplication.translate("generator_tab", u"depth2img", None))
        self.generator_form_stablediffusion_depth2img.setProperty("generator_name", QCoreApplication.translate("generator_tab", u"stablediffusion", None))
        self.tab_widget_stablediffusion.setTabText(self.tab_widget_stablediffusion.indexOf(self.tab_stablediffusion_depth2img), QCoreApplication.translate("generator_tab", u"depth2img", None))
        self.tab_stablediffusion_pix2pix.setProperty("generator_section", QCoreApplication.translate("generator_tab", u"pix2pix", None))
        self.tab_stablediffusion_pix2pix.setProperty("generator_name", QCoreApplication.translate("generator_tab", u"stablediffusion", None))
        self.generator_form_stablediffusion_pix2pix.setProperty("generator_section", QCoreApplication.translate("generator_tab", u"pix2pix", None))
        self.generator_form_stablediffusion_pix2pix.setProperty("generator_name", QCoreApplication.translate("generator_tab", u"stablediffusion", None))
        self.tab_widget_stablediffusion.setTabText(self.tab_widget_stablediffusion.indexOf(self.tab_stablediffusion_pix2pix), QCoreApplication.translate("generator_tab", u"pix2pix", None))
        self.tab_stablediffusion_upscale.setProperty("generator_section", QCoreApplication.translate("generator_tab", u"upscale", None))
        self.tab_stablediffusion_upscale.setProperty("generator_name", QCoreApplication.translate("generator_tab", u"stablediffusion", None))
        self.generator_form_stablediffusion_upscale.setProperty("generator_section", QCoreApplication.translate("generator_tab", u"upscale", None))
        self.generator_form_stablediffusion_upscale.setProperty("generator_name", QCoreApplication.translate("generator_tab", u"stablediffusion", None))
        self.tab_widget_stablediffusion.setTabText(self.tab_widget_stablediffusion.indexOf(self.tab_stablediffusion_upscale), QCoreApplication.translate("generator_tab", u"upscale", None))
        self.tab_stablediffusion_superresolution.setProperty("generator_section", QCoreApplication.translate("generator_tab", u"superresolution", None))
        self.tab_stablediffusion_superresolution.setProperty("generator_name", QCoreApplication.translate("generator_tab", u"stablediffusion", None))
        self.generator_form_stablediffusion_superresolution.setProperty("generator_section", QCoreApplication.translate("generator_tab", u"superresolution", None))
        self.generator_form_stablediffusion_superresolution.setProperty("generator_name", QCoreApplication.translate("generator_tab", u"stablediffusion", None))
        self.tab_widget_stablediffusion.setTabText(self.tab_widget_stablediffusion.indexOf(self.tab_stablediffusion_superresolution), QCoreApplication.translate("generator_tab", u"superresolution", None))
        self.tab_stablediffusion_txt2vid.setProperty("generator_section", QCoreApplication.translate("generator_tab", u"txt2vid", None))
        self.tab_stablediffusion_txt2vid.setProperty("generator_name", QCoreApplication.translate("generator_tab", u"stablediffusion", None))
        self.generator_form_txt2vid.setProperty("generator_section", QCoreApplication.translate("generator_tab", u"txt2vid", None))
        self.generator_form_txt2vid.setProperty("generator_name", QCoreApplication.translate("generator_tab", u"stablediffusion", None))
        self.tab_widget_stablediffusion.setTabText(self.tab_widget_stablediffusion.indexOf(self.tab_stablediffusion_txt2vid), QCoreApplication.translate("generator_tab", u"txt2vid", None))
        self.generator_tabs.setTabText(self.generator_tabs.indexOf(self.tab_stablediffusion), QCoreApplication.translate("generator_tab", u"Stable Diffusion", None))
        self.tab_kandinsky_txt2img.setProperty("generator_section", QCoreApplication.translate("generator_tab", u"txt2img", None))
        self.tab_kandinsky_txt2img.setProperty("generator_name", QCoreApplication.translate("generator_tab", u"kandinsky", None))
        self.generator_form_kandinsky_txt2img.setProperty("generator_section", QCoreApplication.translate("generator_tab", u"txt2img", None))
        self.generator_form_kandinsky_txt2img.setProperty("generator_name", QCoreApplication.translate("generator_tab", u"kandinsky", None))
        self.tab_widget_kandinsky.setTabText(self.tab_widget_kandinsky.indexOf(self.tab_kandinsky_txt2img), QCoreApplication.translate("generator_tab", u"txt2img / img2img", None))
        self.tab_kandinsky_outpaint.setProperty("generator_section", QCoreApplication.translate("generator_tab", u"outpaint", None))
        self.tab_kandinsky_outpaint.setProperty("generator_name", QCoreApplication.translate("generator_tab", u"kandinsky", None))
        self.generator_form_kandinsky_outpaint.setProperty("generator_section", QCoreApplication.translate("generator_tab", u"outpaint", None))
        self.generator_form_kandinsky_outpaint.setProperty("generator_name", QCoreApplication.translate("generator_tab", u"kandinsky", None))
        self.tab_widget_kandinsky.setTabText(self.tab_widget_kandinsky.indexOf(self.tab_kandinsky_outpaint), QCoreApplication.translate("generator_tab", u"inpaint / outapint", None))
        self.generator_tabs.setTabText(self.generator_tabs.indexOf(self.tab_kandinsky), QCoreApplication.translate("generator_tab", u"Kandinsky", None))
        self.tab_shape_txt2img.setProperty("generator_section", QCoreApplication.translate("generator_tab", u"txt2img", None))
        self.tab_shape_txt2img.setProperty("generator_name", QCoreApplication.translate("generator_tab", u"shape", None))
        self.generator_form_shape_txt2img.setProperty("generator_section", QCoreApplication.translate("generator_tab", u"txt2img", None))
        self.generator_form_shape_txt2img.setProperty("generator_name", QCoreApplication.translate("generator_tab", u"shape", None))
        self.tab_widget_shape.setTabText(self.tab_widget_shape.indexOf(self.tab_shape_txt2img), QCoreApplication.translate("generator_tab", u"txt2img / img2img", None))
        self.generator_tabs.setTabText(self.generator_tabs.indexOf(self.tab_shape), QCoreApplication.translate("generator_tab", u"Shap-e", None))
    # retranslateUi

