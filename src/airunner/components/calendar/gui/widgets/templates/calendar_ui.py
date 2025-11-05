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
from PySide6.QtWidgets import (QApplication, QCalendarWidget, QFrame, QHBoxLayout,
    QLabel, QListWidget, QListWidgetItem, QPushButton,
    QSizePolicy, QSpacerItem, QSplitter, QVBoxLayout,
    QWidget)
import airunner.feather_rc

class Ui_calendar(object):
    def setupUi(self, calendar):
        if not calendar.objectName():
            calendar.setObjectName(u"calendar")
        calendar.resize(898, 654)
        self.verticalLayout = QVBoxLayout(calendar)
        self.verticalLayout.setSpacing(10)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.line = QFrame(calendar)
        self.line.setObjectName(u"line")
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFrameShadow(QFrame.Shadow.Sunken)

        self.verticalLayout.addWidget(self.line)

        self.splitter = QSplitter(calendar)
        self.splitter.setObjectName(u"splitter")
        self.splitter.setOrientation(Qt.Orientation.Horizontal)
        self.calendar_container = QWidget(self.splitter)
        self.calendar_container.setObjectName(u"calendar_container")
        self.calendar_layout = QVBoxLayout(self.calendar_container)
        self.calendar_layout.setSpacing(10)
        self.calendar_layout.setObjectName(u"calendar_layout")
        self.calendar_layout.setContentsMargins(0, 0, 10, 0)
        self.calendar_widget = QCalendarWidget(self.calendar_container)
        self.calendar_widget.setObjectName(u"calendar_widget")
        self.calendar_widget.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.calendar_widget.setGridVisible(True)
        self.calendar_widget.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)

        self.calendar_layout.addWidget(self.calendar_widget)

        self.controls_layout = QHBoxLayout()
        self.controls_layout.setSpacing(6)
        self.controls_layout.setObjectName(u"controls_layout")
        self.today_button = QPushButton(self.calendar_container)
        self.today_button.setObjectName(u"today_button")
        self.today_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        self.controls_layout.addWidget(self.today_button)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.controls_layout.addItem(self.horizontalSpacer)

        self.refresh_button = QPushButton(self.calendar_container)
        self.refresh_button.setObjectName(u"refresh_button")
        self.refresh_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        icon = QIcon()
        icon.addFile(u":/dark/icons/feather/dark/refresh-ccw.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.refresh_button.setIcon(icon)

        self.controls_layout.addWidget(self.refresh_button)


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
        self.new_event_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        icon1 = QIcon()
        icon1.addFile(u":/dark/icons/feather/dark/plus-square.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.new_event_button.setIcon(icon1)

        self.event_controls.addWidget(self.new_event_button)

        self.edit_event_button = QPushButton(self.events_container)
        self.edit_event_button.setObjectName(u"edit_event_button")
        self.edit_event_button.setEnabled(False)
        self.edit_event_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        icon2 = QIcon()
        icon2.addFile(u":/dark/icons/feather/dark/edit.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.edit_event_button.setIcon(icon2)

        self.event_controls.addWidget(self.edit_event_button)

        self.horizontalSpacer_2 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.event_controls.addItem(self.horizontalSpacer_2)

        self.delete_event_button = QPushButton(self.events_container)
        self.delete_event_button.setObjectName(u"delete_event_button")
        self.delete_event_button.setEnabled(False)
        self.delete_event_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        icon3 = QIcon()
        icon3.addFile(u":/dark/icons/feather/dark/trash.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.delete_event_button.setIcon(icon3)

        self.event_controls.addWidget(self.delete_event_button)


        self.events_layout.addLayout(self.event_controls)

        self.splitter.addWidget(self.events_container)

        self.verticalLayout.addWidget(self.splitter)


        self.retranslateUi(calendar)

        QMetaObject.connectSlotsByName(calendar)
    # setupUi

    def retranslateUi(self, calendar):
        calendar.setWindowTitle(QCoreApplication.translate("calendar", u"Calendar", None))
#if QT_CONFIG(tooltip)
        self.today_button.setToolTip(QCoreApplication.translate("calendar", u"Today", None))
#endif // QT_CONFIG(tooltip)
        self.today_button.setText(QCoreApplication.translate("calendar", u"Today", None))
#if QT_CONFIG(tooltip)
        self.refresh_button.setToolTip(QCoreApplication.translate("calendar", u"Refresh", None))
#endif // QT_CONFIG(tooltip)
        self.refresh_button.setText("")
        self.events_label.setText(QCoreApplication.translate("calendar", u"Events", None))
#if QT_CONFIG(tooltip)
        self.new_event_button.setToolTip(QCoreApplication.translate("calendar", u"New Event", None))
#endif // QT_CONFIG(tooltip)
        self.new_event_button.setText("")
#if QT_CONFIG(tooltip)
        self.edit_event_button.setToolTip(QCoreApplication.translate("calendar", u"Edit Event", None))
#endif // QT_CONFIG(tooltip)
        self.edit_event_button.setText("")
#if QT_CONFIG(tooltip)
        self.delete_event_button.setToolTip(QCoreApplication.translate("calendar", u"Delete Event", None))
#endif // QT_CONFIG(tooltip)
        self.delete_event_button.setText("")
    # retranslateUi

