# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'batch_container.ui'
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
from PySide6.QtWidgets import (QApplication, QComboBox, QGridLayout, QListView,
    QPushButton, QSizePolicy, QWidget)
import airunner.feather_rc

class Ui_batch_conatiner(object):
    def setupUi(self, batch_conatiner):
        if not batch_conatiner.objectName():
            batch_conatiner.setObjectName(u"batch_conatiner")
        batch_conatiner.resize(480, 176)
        self.gridLayout = QGridLayout(batch_conatiner)
        self.gridLayout.setObjectName(u"gridLayout")
        self.image_folders = QComboBox(batch_conatiner)
        self.image_folders.setObjectName(u"image_folders")

        self.gridLayout.addWidget(self.image_folders, 0, 0, 1, 1)

        self.backButton = QPushButton(batch_conatiner)
        self.backButton.setObjectName(u"backButton")
        self.backButton.setVisible(False)

        self.gridLayout.addWidget(self.backButton, 1, 0, 1, 1)

        self.browse_to_folder_button = QPushButton(batch_conatiner)
        self.browse_to_folder_button.setObjectName(u"browse_to_folder_button")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.browse_to_folder_button.sizePolicy().hasHeightForWidth())
        self.browse_to_folder_button.setSizePolicy(sizePolicy)
        self.browse_to_folder_button.setMinimumSize(QSize(30, 30))
        self.browse_to_folder_button.setMaximumSize(QSize(30, 30))
        self.browse_to_folder_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        icon = QIcon()
        icon.addFile(u":/light/icons/feather/light/folder.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.browse_to_folder_button.setIcon(icon)

        self.gridLayout.addWidget(self.browse_to_folder_button, 0, 1, 1, 1)

        self.galleryView = QListView(batch_conatiner)
        self.galleryView.setObjectName(u"galleryView")

        self.gridLayout.addWidget(self.galleryView, 2, 0, 1, 2)


        self.retranslateUi(batch_conatiner)

        QMetaObject.connectSlotsByName(batch_conatiner)
    # setupUi

    def retranslateUi(self, batch_conatiner):
        batch_conatiner.setWindowTitle(QCoreApplication.translate("batch_conatiner", u"Form", None))
        self.backButton.setText(QCoreApplication.translate("batch_conatiner", u"\u2190 Back to date folder", None))
#if QT_CONFIG(tooltip)
        self.browse_to_folder_button.setToolTip(QCoreApplication.translate("batch_conatiner", u"Open path in file explorer", None))
#endif // QT_CONFIG(tooltip)
        self.browse_to_folder_button.setText("")
    # retranslateUi

