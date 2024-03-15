# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'paths.ui'
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
from PySide6.QtWidgets import (QApplication, QGridLayout, QPushButton, QSizePolicy,
    QSpacerItem, QWidget)

from airunner.widgets.paths.path_widget import PathWidget

class Ui_paths_form(object):
    def setupUi(self, paths_form):
        if not paths_form.objectName():
            paths_form.setObjectName(u"paths_form")
        paths_form.resize(498, 1113)
        self.gridLayout = QGridLayout(paths_form)
        self.gridLayout.setObjectName(u"gridLayout")
        self.lora_path_widget = PathWidget(paths_form)
        self.lora_path_widget.setObjectName(u"lora_path_widget")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.lora_path_widget.sizePolicy().hasHeightForWidth())
        self.lora_path_widget.setSizePolicy(sizePolicy)
        self.lora_path_widget.setMinimumSize(QSize(0, 0))

        self.gridLayout.addWidget(self.lora_path_widget, 10, 0, 1, 1)

        self.vae_path_widget = PathWidget(paths_form)
        self.vae_path_widget.setObjectName(u"vae_path_widget")
        sizePolicy.setHeightForWidth(self.vae_path_widget.sizePolicy().hasHeightForWidth())
        self.vae_path_widget.setSizePolicy(sizePolicy)
        self.vae_path_widget.setMinimumSize(QSize(0, 0))

        self.gridLayout.addWidget(self.vae_path_widget, 12, 0, 1, 1)

        self.huggingface_cache_widget = PathWidget(paths_form)
        self.huggingface_cache_widget.setObjectName(u"huggingface_cache_widget")
        sizePolicy.setHeightForWidth(self.huggingface_cache_widget.sizePolicy().hasHeightForWidth())
        self.huggingface_cache_widget.setSizePolicy(sizePolicy)
        self.huggingface_cache_widget.setMinimumSize(QSize(0, 0))

        self.gridLayout.addWidget(self.huggingface_cache_widget, 1, 0, 1, 1)

        self.base_path_widget = PathWidget(paths_form)
        self.base_path_widget.setObjectName(u"base_path_widget")
        sizePolicy.setHeightForWidth(self.base_path_widget.sizePolicy().hasHeightForWidth())
        self.base_path_widget.setSizePolicy(sizePolicy)
        self.base_path_widget.setMinimumSize(QSize(0, 0))

        self.gridLayout.addWidget(self.base_path_widget, 2, 0, 1, 1)

        self.widget = PathWidget(paths_form)
        self.widget.setObjectName(u"widget")
        sizePolicy.setHeightForWidth(self.widget.sizePolicy().hasHeightForWidth())
        self.widget.setSizePolicy(sizePolicy)
        self.widget.setMinimumSize(QSize(0, 0))

        self.gridLayout.addWidget(self.widget, 15, 0, 1, 1)

        self.llm_txt2txt_path_widget = PathWidget(paths_form)
        self.llm_txt2txt_path_widget.setObjectName(u"llm_txt2txt_path_widget")
        sizePolicy.setHeightForWidth(self.llm_txt2txt_path_widget.sizePolicy().hasHeightForWidth())
        self.llm_txt2txt_path_widget.setSizePolicy(sizePolicy)
        self.llm_txt2txt_path_widget.setMinimumSize(QSize(0, 0))

        self.gridLayout.addWidget(self.llm_txt2txt_path_widget, 14, 0, 1, 1)

        self.video_path_widget = PathWidget(paths_form)
        self.video_path_widget.setObjectName(u"video_path_widget")
        sizePolicy.setHeightForWidth(self.video_path_widget.sizePolicy().hasHeightForWidth())
        self.video_path_widget.setSizePolicy(sizePolicy)
        self.video_path_widget.setMinimumSize(QSize(0, 0))

        self.gridLayout.addWidget(self.video_path_widget, 13, 0, 1, 1)

        self.documents_path_widget = PathWidget(paths_form)
        self.documents_path_widget.setObjectName(u"documents_path_widget")
        sizePolicy.setHeightForWidth(self.documents_path_widget.sizePolicy().hasHeightForWidth())
        self.documents_path_widget.setSizePolicy(sizePolicy)
        self.documents_path_widget.setMinimumSize(QSize(0, 0))

        self.gridLayout.addWidget(self.documents_path_widget, 17, 0, 1, 1)

        self.txt2vid_path_widget = PathWidget(paths_form)
        self.txt2vid_path_widget.setObjectName(u"txt2vid_path_widget")
        sizePolicy.setHeightForWidth(self.txt2vid_path_widget.sizePolicy().hasHeightForWidth())
        self.txt2vid_path_widget.setSizePolicy(sizePolicy)
        self.txt2vid_path_widget.setMinimumSize(QSize(0, 0))

        self.gridLayout.addWidget(self.txt2vid_path_widget, 8, 0, 1, 1)

        self.upscale_path_widget = PathWidget(paths_form)
        self.upscale_path_widget.setObjectName(u"upscale_path_widget")
        sizePolicy.setHeightForWidth(self.upscale_path_widget.sizePolicy().hasHeightForWidth())
        self.upscale_path_widget.setSizePolicy(sizePolicy)
        self.upscale_path_widget.setMinimumSize(QSize(0, 0))

        self.gridLayout.addWidget(self.upscale_path_widget, 7, 0, 1, 1)

        self.auto_button = QPushButton(paths_form)
        self.auto_button.setObjectName(u"auto_button")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Preferred)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.auto_button.sizePolicy().hasHeightForWidth())
        self.auto_button.setSizePolicy(sizePolicy1)
        self.auto_button.setMinimumSize(QSize(0, 0))

        self.gridLayout.addWidget(self.auto_button, 0, 0, 1, 1)

        self.txt2img_path_widget = PathWidget(paths_form)
        self.txt2img_path_widget.setObjectName(u"txt2img_path_widget")
        sizePolicy.setHeightForWidth(self.txt2img_path_widget.sizePolicy().hasHeightForWidth())
        self.txt2img_path_widget.setSizePolicy(sizePolicy)
        self.txt2img_path_widget.setMinimumSize(QSize(0, 0))

        self.gridLayout.addWidget(self.txt2img_path_widget, 3, 0, 1, 1)

        self.image_path_widget = PathWidget(paths_form)
        self.image_path_widget.setObjectName(u"image_path_widget")
        sizePolicy.setHeightForWidth(self.image_path_widget.sizePolicy().hasHeightForWidth())
        self.image_path_widget.setSizePolicy(sizePolicy)
        self.image_path_widget.setMinimumSize(QSize(0, 0))

        self.gridLayout.addWidget(self.image_path_widget, 11, 0, 1, 1)

        self.depth2img_path_widget = PathWidget(paths_form)
        self.depth2img_path_widget.setObjectName(u"depth2img_path_widget")
        sizePolicy.setHeightForWidth(self.depth2img_path_widget.sizePolicy().hasHeightForWidth())
        self.depth2img_path_widget.setSizePolicy(sizePolicy)
        self.depth2img_path_widget.setMinimumSize(QSize(0, 0))

        self.gridLayout.addWidget(self.depth2img_path_widget, 4, 0, 1, 1)

        self.inpaint_path_widget = PathWidget(paths_form)
        self.inpaint_path_widget.setObjectName(u"inpaint_path_widget")
        sizePolicy.setHeightForWidth(self.inpaint_path_widget.sizePolicy().hasHeightForWidth())
        self.inpaint_path_widget.setSizePolicy(sizePolicy)
        self.inpaint_path_widget.setMinimumSize(QSize(0, 0))

        self.gridLayout.addWidget(self.inpaint_path_widget, 6, 0, 1, 1)

        self.embeddings_path_widget = PathWidget(paths_form)
        self.embeddings_path_widget.setObjectName(u"embeddings_path_widget")
        sizePolicy.setHeightForWidth(self.embeddings_path_widget.sizePolicy().hasHeightForWidth())
        self.embeddings_path_widget.setSizePolicy(sizePolicy)
        self.embeddings_path_widget.setMinimumSize(QSize(0, 0))

        self.gridLayout.addWidget(self.embeddings_path_widget, 9, 0, 1, 1)

        self.pix2pix_path_widget = PathWidget(paths_form)
        self.pix2pix_path_widget.setObjectName(u"pix2pix_path_widget")
        sizePolicy.setHeightForWidth(self.pix2pix_path_widget.sizePolicy().hasHeightForWidth())
        self.pix2pix_path_widget.setSizePolicy(sizePolicy)
        self.pix2pix_path_widget.setMinimumSize(QSize(0, 0))

        self.gridLayout.addWidget(self.pix2pix_path_widget, 5, 0, 1, 1)

        self.llama_index_path_widget = PathWidget(paths_form)
        self.llama_index_path_widget.setObjectName(u"llama_index_path_widget")
        sizePolicy.setHeightForWidth(self.llama_index_path_widget.sizePolicy().hasHeightForWidth())
        self.llama_index_path_widget.setSizePolicy(sizePolicy)
        self.llama_index_path_widget.setMinimumSize(QSize(0, 0))

        self.gridLayout.addWidget(self.llama_index_path_widget, 18, 0, 1, 1)

        self.ebook_path_widget = PathWidget(paths_form)
        self.ebook_path_widget.setObjectName(u"ebook_path_widget")
        sizePolicy.setHeightForWidth(self.ebook_path_widget.sizePolicy().hasHeightForWidth())
        self.ebook_path_widget.setSizePolicy(sizePolicy)
        self.ebook_path_widget.setMinimumSize(QSize(0, 0))

        self.gridLayout.addWidget(self.ebook_path_widget, 16, 0, 1, 1)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout.addItem(self.verticalSpacer, 19, 0, 1, 1)


        self.retranslateUi(paths_form)
        self.auto_button.clicked.connect(paths_form.action_button_clicked_reset)

        QMetaObject.connectSlotsByName(paths_form)
    # setupUi

    def retranslateUi(self, paths_form):
        paths_form.setWindowTitle(QCoreApplication.translate("paths_form", u"Form", None))
        self.lora_path_widget.setProperty("title", QCoreApplication.translate("paths_form", u"LoRA Path", None))
        self.lora_path_widget.setProperty("description", QCoreApplication.translate("paths_form", u"Absolute path to the LOrA model directory", None))
        self.lora_path_widget.setProperty("path_name", QCoreApplication.translate("paths_form", u"lora_model_path", None))
        self.vae_path_widget.setProperty("title", QCoreApplication.translate("paths_form", u"Vae Model Path", None))
        self.vae_path_widget.setProperty("description", QCoreApplication.translate("paths_form", u"Absolute path to the vae models directory", None))
        self.vae_path_widget.setProperty("path_name", QCoreApplication.translate("paths_form", u"vae_model_path", None))
        self.huggingface_cache_widget.setProperty("title", QCoreApplication.translate("paths_form", u"Huggingface Cache", None))
        self.huggingface_cache_widget.setProperty("description", QCoreApplication.translate("paths_form", u"Path to the folder which contains the huggingface cache (requires restart)", None))
        self.huggingface_cache_widget.setProperty("path_name", QCoreApplication.translate("paths_form", u"hf_cache_path", None))
        self.base_path_widget.setProperty("title", QCoreApplication.translate("paths_form", u"Base Path", None))
        self.base_path_widget.setProperty("description", QCoreApplication.translate("paths_form", u"Absolute path to the directory which will hold all model directories", None))
        self.base_path_widget.setProperty("path_name", QCoreApplication.translate("paths_form", u"base_path", None))
        self.widget.setProperty("title", QCoreApplication.translate("paths_form", u"LLM seq2seq path", None))
        self.widget.setProperty("description", QCoreApplication.translate("paths_form", u"Absolute path to the LLM seq2seq model directory", None))
        self.widget.setProperty("path_name", QCoreApplication.translate("paths_form", u"llm_seq2seq_model_path", None))
        self.llm_txt2txt_path_widget.setProperty("title", QCoreApplication.translate("paths_form", u"LLM CasualLM path", None))
        self.llm_txt2txt_path_widget.setProperty("description", QCoreApplication.translate("paths_form", u"Absolute path to the LLM txt2txt model directory", None))
        self.llm_txt2txt_path_widget.setProperty("path_name", QCoreApplication.translate("paths_form", u"llm_casuallm_model_path", None))
        self.video_path_widget.setProperty("title", QCoreApplication.translate("paths_form", u"Video Path", None))
        self.video_path_widget.setProperty("description", QCoreApplication.translate("paths_form", u"Absolute path to the directory which will contain generated videos", None))
        self.video_path_widget.setProperty("path_name", QCoreApplication.translate("paths_form", u"video_path", None))
        self.documents_path_widget.setProperty("title", QCoreApplication.translate("paths_form", u"Documents Path", None))
        self.documents_path_widget.setProperty("description", QCoreApplication.translate("paths_form", u"Absolute path to directory containing documnets (txt, PDF)", None))
        self.documents_path_widget.setProperty("path_name", QCoreApplication.translate("paths_form", u"documents_path", None))
        self.txt2vid_path_widget.setProperty("title", QCoreApplication.translate("paths_form", u"Txt2vid Model Path", None))
        self.txt2vid_path_widget.setProperty("description", QCoreApplication.translate("paths_form", u"Absolute path to the txt2vid models directory", None))
        self.txt2vid_path_widget.setProperty("path_name", QCoreApplication.translate("paths_form", u"txt2vid_model_path", None))
        self.upscale_path_widget.setProperty("title", QCoreApplication.translate("paths_form", u"Upscale Model Path", None))
        self.upscale_path_widget.setProperty("description", QCoreApplication.translate("paths_form", u"Absolute path to the upscale model directory", None))
        self.upscale_path_widget.setProperty("path_name", QCoreApplication.translate("paths_form", u"upscale_model_path", None))
        self.auto_button.setText(QCoreApplication.translate("paths_form", u"Reset Paths to Default Values", None))
        self.txt2img_path_widget.setProperty("title", QCoreApplication.translate("paths_form", u"Txt2img / img2img Model Path", None))
        self.txt2img_path_widget.setProperty("description", QCoreApplication.translate("paths_form", u"Absolute path to the txt2img model directory", None))
        self.txt2img_path_widget.setProperty("path_name", QCoreApplication.translate("paths_form", u"txt2img_model_path", None))
        self.image_path_widget.setProperty("title", QCoreApplication.translate("paths_form", u"Image Path", None))
        self.image_path_widget.setProperty("description", QCoreApplication.translate("paths_form", u"Absolute path to the directory which will contain generated images", None))
        self.image_path_widget.setProperty("path_name", QCoreApplication.translate("paths_form", u"image_path", None))
        self.depth2img_path_widget.setProperty("title", QCoreApplication.translate("paths_form", u"Depth2img Model Path", None))
        self.depth2img_path_widget.setProperty("description", QCoreApplication.translate("paths_form", u"Absolute path to the depth2img model directory", None))
        self.depth2img_path_widget.setProperty("path_name", QCoreApplication.translate("paths_form", u"depth2img_model_path", None))
        self.inpaint_path_widget.setProperty("title", QCoreApplication.translate("paths_form", u"Inpaint / Outpaint Model Path", None))
        self.inpaint_path_widget.setProperty("description", QCoreApplication.translate("paths_form", u"Absolute path to the to the inpaint model directory", None))
        self.inpaint_path_widget.setProperty("path_name", QCoreApplication.translate("paths_form", u"inpaint_model_path", None))
        self.embeddings_path_widget.setProperty("title", QCoreApplication.translate("paths_form", u"Embeddings Path", None))
        self.embeddings_path_widget.setProperty("description", QCoreApplication.translate("paths_form", u"Absolute path to the Textual Inversion model directory", None))
        self.embeddings_path_widget.setProperty("path_name", QCoreApplication.translate("paths_form", u"embeddings_model_path", None))
        self.pix2pix_path_widget.setProperty("title", QCoreApplication.translate("paths_form", u"Pix2pix Model Path", None))
        self.pix2pix_path_widget.setProperty("description", QCoreApplication.translate("paths_form", u"Absolute path to the pix2pix model directory", None))
        self.pix2pix_path_widget.setProperty("path_name", QCoreApplication.translate("paths_form", u"pix2pix_model_path", None))
        self.llama_index_path_widget.setProperty("title", QCoreApplication.translate("paths_form", u"LLama Index Path", None))
        self.llama_index_path_widget.setProperty("description", QCoreApplication.translate("paths_form", u"Absolute path to directory which will store files for LLama Index", None))
        self.llama_index_path_widget.setProperty("path_name", QCoreApplication.translate("paths_form", u"llama_index_path", None))
        self.ebook_path_widget.setProperty("title", QCoreApplication.translate("paths_form", u"Ebook Path", None))
        self.ebook_path_widget.setProperty("description", QCoreApplication.translate("paths_form", u"Absolute path to directory containing ebooks (epub)", None))
        self.ebook_path_widget.setProperty("path_name", QCoreApplication.translate("paths_form", u"ebook_path", None))
    # retranslateUi

