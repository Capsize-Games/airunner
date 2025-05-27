# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'lora.ui'
##
## Created by: Qt User Interface Compiler version 6.9.0
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (
    QCoreApplication,
    QDate,
    QDateTime,
    QLocale,
    QMetaObject,
    QObject,
    QPoint,
    QRect,
    QSize,
    QTime,
    QUrl,
    Qt,
)
from PySide6.QtGui import (
    QBrush,
    QColor,
    QConicalGradient,
    QCursor,
    QFont,
    QFontDatabase,
    QGradient,
    QIcon,
    QImage,
    QKeySequence,
    QLinearGradient,
    QPainter,
    QPalette,
    QPixmap,
    QRadialGradient,
    QTransform,
)
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QGridLayout,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QWidget,
)

from airunner.gui.widgets.slider.slider_widget import SliderWidget
import airunner.feather_rc


class Ui_lora(object):
    def setupUi(self, lora):
        if not lora.objectName():
            lora.setObjectName("lora")
        lora.resize(518, 80)
        sizePolicy = QSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(lora.sizePolicy().hasHeightForWidth())
        lora.setSizePolicy(sizePolicy)
        lora.setMaximumSize(QSize(16777215, 16777215))
        font = QFont()
        font.setPointSize(9)
        lora.setFont(font)
        self.gridLayout_2 = QGridLayout(lora)
        self.gridLayout_2.setSpacing(0)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.gridLayout_2.setContentsMargins(0, 0, 0, 0)
        self.gridLayout = QGridLayout()
        self.gridLayout.setObjectName("gridLayout")
        self.gridLayout.setHorizontalSpacing(0)
        self.lora_container = QWidget(lora)
        self.lora_container.setObjectName("lora_container")
        self.gridLayout_3 = QGridLayout(self.lora_container)
        self.gridLayout_3.setObjectName("gridLayout_3")
        self.gridLayout_3.setHorizontalSpacing(5)
        self.gridLayout_3.setVerticalSpacing(10)
        self.gridLayout_3.setContentsMargins(0, 0, 0, 0)
        self.enabledCheckbox = QCheckBox(self.lora_container)
        self.enabledCheckbox.setObjectName("enabledCheckbox")

        self.gridLayout_3.addWidget(self.enabledCheckbox, 0, 0, 1, 1)

        self.trigger_word_edit = QLineEdit(self.lora_container)
        self.trigger_word_edit.setObjectName("trigger_word_edit")

        self.gridLayout_3.addWidget(self.trigger_word_edit, 2, 0, 1, 1)

        self.delete_button = QPushButton(self.lora_container)
        self.delete_button.setObjectName("delete_button")
        self.delete_button.setMinimumSize(QSize(24, 24))
        self.delete_button.setMaximumSize(QSize(24, 24))
        self.delete_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        icon = QIcon()
        icon.addFile(
            ":/dark/icons/feather/dark/trash-2.svg",
            QSize(),
            QIcon.Mode.Normal,
            QIcon.State.Off,
        )
        self.delete_button.setIcon(icon)

        self.gridLayout_3.addWidget(self.delete_button, 2, 2, 1, 1)

        self.scale_slider = SliderWidget(self.lora_container)
        self.scale_slider.setObjectName("scale_slider")
        sizePolicy.setHeightForWidth(self.scale_slider.sizePolicy().hasHeightForWidth())
        self.scale_slider.setSizePolicy(sizePolicy)
        self.scale_slider.setMinimumSize(QSize(0, 0))
        self.scale_slider.setProperty("slider_minimum", 0)
        self.scale_slider.setProperty("slider_maximum", 100)
        self.scale_slider.setProperty("spinbox_minimum", 0.000000000000000)
        self.scale_slider.setProperty("spinbox_maximum", 1.000000000000000)
        self.scale_slider.setProperty("display_as_float", True)
        self.scale_slider.setProperty("slider_single_step", 1)
        self.scale_slider.setProperty("slider_page_step", 5)
        self.scale_slider.setProperty("spinbox_single_step", 0.010000000000000)
        self.scale_slider.setProperty("spinbox_page_step", 0.100000000000000)
        self.scale_slider.setProperty("table_id", 0)

        self.gridLayout_3.addWidget(self.scale_slider, 1, 0, 1, 3)

        self.gridLayout.addWidget(self.lora_container, 0, 0, 2, 1)

        self.gridLayout_2.addLayout(self.gridLayout, 0, 0, 1, 1)

        self.retranslateUi(lora)
        self.trigger_word_edit.textChanged.connect(lora.action_changed_trigger_words)
        self.enabledCheckbox.toggled.connect(lora.action_toggled_lora_enabled)
        self.delete_button.clicked.connect(lora.action_clicked_button_deleted)

        QMetaObject.connectSlotsByName(lora)

    # setupUi

    def retranslateUi(self, lora):
        lora.setWindowTitle(QCoreApplication.translate("lora", "Form", None))
        self.enabledCheckbox.setText(
            QCoreApplication.translate("lora", "enabledCheckbox", None)
        )
        # if QT_CONFIG(tooltip)
        self.trigger_word_edit.setToolTip(
            QCoreApplication.translate(
                "lora",
                "<html><head/><body><p>Some LoRA require a trigger word to activate.</p><p>Make a note here for your records.</p></body></html>",
                None,
            )
        )
        # endif // QT_CONFIG(tooltip)
        self.trigger_word_edit.setPlaceholderText(
            QCoreApplication.translate("lora", "Trigger words (comma separated)", None)
        )
        # if QT_CONFIG(tooltip)
        self.delete_button.setToolTip(
            QCoreApplication.translate("lora", "Delete model", None)
        )
        # endif // QT_CONFIG(tooltip)
        self.delete_button.setText("")
        self.scale_slider.setProperty(
            "settings_property", QCoreApplication.translate("lora", "lora.scale", None)
        )
        self.scale_slider.setProperty(
            "label_text", QCoreApplication.translate("lora", "Scale", None)
        )

    # retranslateUi
