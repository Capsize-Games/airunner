# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'sound_settings.ui'
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
from PySide6.QtWidgets import (QApplication, QComboBox, QGroupBox, QSizePolicy,
    QSpacerItem, QVBoxLayout, QWidget)

class Ui_SoundSettings(object):
    def setupUi(self, SoundSettings):
        if not SoundSettings.objectName():
            SoundSettings.setObjectName(u"SoundSettings")
        SoundSettings.resize(400, 300)
        self.verticalLayout = QVBoxLayout(SoundSettings)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.playbackGroup = QGroupBox(SoundSettings)
        self.playbackGroup.setObjectName(u"playbackGroup")
        self.playbackLayout = QVBoxLayout(self.playbackGroup)
        self.playbackLayout.setObjectName(u"playbackLayout")
        self.playbackComboBox = QComboBox(self.playbackGroup)
        self.playbackComboBox.setObjectName(u"playbackComboBox")

        self.playbackLayout.addWidget(self.playbackComboBox)


        self.verticalLayout.addWidget(self.playbackGroup)

        self.recordingGroup = QGroupBox(SoundSettings)
        self.recordingGroup.setObjectName(u"recordingGroup")
        self.recordingLayout = QVBoxLayout(self.recordingGroup)
        self.recordingLayout.setObjectName(u"recordingLayout")
        self.recordingComboBox = QComboBox(self.recordingGroup)
        self.recordingComboBox.setObjectName(u"recordingComboBox")

        self.recordingLayout.addWidget(self.recordingComboBox)


        self.verticalLayout.addWidget(self.recordingGroup)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout.addItem(self.verticalSpacer)


        self.retranslateUi(SoundSettings)

        QMetaObject.connectSlotsByName(SoundSettings)
    # setupUi

    def retranslateUi(self, SoundSettings):
        self.playbackGroup.setTitle(QCoreApplication.translate("SoundSettings", u"Playback Device", None))
        self.recordingGroup.setTitle(QCoreApplication.translate("SoundSettings", u"Recording Device", None))
        pass
    # retranslateUi

