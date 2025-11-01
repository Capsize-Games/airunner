# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'calendar.ui'
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
from PySide6.QtWidgets import (QApplication, QCalendarWidget, QHBoxLayout, QLabel,
    QListWidget, QListWidgetItem, QPushButton, QSizePolicy,
    QSpacerItem, QSplitter, QVBoxLayout, QWidget)

class Ui_calendar(object):
    def setupUi(self, calendar):
        if not calendar.objectName():
            calendar.setObjectName(u"calendar")
        calendar.resize(898, 654)
        self.main_layout = QVBoxLayout(calendar)
        self.main_layout.setSpacing(10)
        self.main_layout.setObjectName(u"main_layout")
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.title = QLabel(calendar)
        self.title.setObjectName(u"title")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.title.sizePolicy().hasHeightForWidth())
        self.title.setSizePolicy(sizePolicy)
        self.title.setStyleSheet(u"font-size: 18px; font-weight: bold;")

        self.main_layout.addWidget(self.title)

        self.splitter = QSplitter(calendar)
        self.splitter.setObjectName(u"splitter")
        self.splitter.setOrientation(Qt.Orientation.Horizontal)
        self.calendar_container = QWidget(self.splitter)
        self.calendar_container.setObjectName(u"calendar_container")
        self.calendar_layout = QVBoxLayout(self.calendar_container)
        self.calendar_layout.setSpacing(10)
        self.calendar_layout.setObjectName(u"calendar_layout")
        self.calendar_layout.setContentsMargins(0, 0, 0, 0)
        self.calendar_widget = QCalendarWidget(self.calendar_container)
        self.calendar_widget.setObjectName(u"calendar_widget")
        self.calendar_widget.setGridVisible(True)
        self.calendar_widget.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)

        self.calendar_layout.addWidget(self.calendar_widget)

        self.controls_layout = QHBoxLayout()
        self.controls_layout.setSpacing(6)
        self.controls_layout.setObjectName(u"controls_layout")
        self.today_button = QPushButton(self.calendar_container)
        self.today_button.setObjectName(u"today_button")

        self.controls_layout.addWidget(self.today_button)

        self.refresh_button = QPushButton(self.calendar_container)
        self.refresh_button.setObjectName(u"refresh_button")

        self.controls_layout.addWidget(self.refresh_button)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.controls_layout.addItem(self.horizontalSpacer)


        self.calendar_layout.addLayout(self.controls_layout)

        self.splitter.addWidget(self.calendar_container)
        self.events_container = QWidget(self.splitter)
        self.events_container.setObjectName(u"events_container")
        self.events_layout = QVBoxLayout(self.events_container)
        self.events_layout.setSpacing(10)
        self.events_layout.setObjectName(u"events_layout")
        self.events_layout.setContentsMargins(10, 0, 10, 0)
        self.events_label = QLabel(self.events_container)
        self.events_label.setObjectName(u"events_label")
        self.events_label.setStyleSheet(u"font-size: 14px; font-weight: bold;")

        self.events_layout.addWidget(self.events_label)

        self.events_list = QListWidget(self.events_container)
        self.events_list.setObjectName(u"events_list")

        self.events_layout.addWidget(self.events_list)

        self.event_controls = QHBoxLayout()
        self.event_controls.setSpacing(6)
        self.event_controls.setObjectName(u"event_controls")
        self.new_event_button = QPushButton(self.events_container)
        self.new_event_button.setObjectName(u"new_event_button")

        self.event_controls.addWidget(self.new_event_button)

        self.edit_event_button = QPushButton(self.events_container)
        self.edit_event_button.setObjectName(u"edit_event_button")
        self.edit_event_button.setEnabled(False)

        self.event_controls.addWidget(self.edit_event_button)

        self.delete_event_button = QPushButton(self.events_container)
        self.delete_event_button.setObjectName(u"delete_event_button")
        self.delete_event_button.setEnabled(False)

        self.event_controls.addWidget(self.delete_event_button)


        self.events_layout.addLayout(self.event_controls)

        self.splitter.addWidget(self.events_container)

        self.main_layout.addWidget(self.splitter)


        self.retranslateUi(calendar)

        QMetaObject.connectSlotsByName(calendar)
    # setupUi

    def retranslateUi(self, calendar):
        calendar.setWindowTitle(QCoreApplication.translate("calendar", u"Calendar", None))
        self.title.setText(QCoreApplication.translate("calendar", u"Calendar", None))
        self.today_button.setText(QCoreApplication.translate("calendar", u"Today", None))
        self.refresh_button.setText(QCoreApplication.translate("calendar", u"Refresh", None))
        self.events_label.setText(QCoreApplication.translate("calendar", u"Events", None))
        self.new_event_button.setText(QCoreApplication.translate("calendar", u"New Event", None))
        self.edit_event_button.setText(QCoreApplication.translate("calendar", u"Edit", None))
        self.delete_event_button.setText(QCoreApplication.translate("calendar", u"Delete", None))
    # retranslateUi

