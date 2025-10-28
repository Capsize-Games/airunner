"""Event creation and editing dialog."""

from datetime import datetime
from typing import Optional, Dict, Any
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QFormLayout,
    QLineEdit,
    QTextEdit,
    QDateTimeEdit,
    QCheckBox,
    QComboBox,
    QDialogButtonBox,
    QWidget,
    QMessageBox,
)
from PySide6.QtCore import QDateTime, QDate, QTime
from airunner.components.calendar.data.event import Event


class EventDialog(QDialog):
    """Dialog for creating and editing calendar events."""

    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize event dialog.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.setWindowTitle("Event")
        self.setMinimumWidth(500)
        self.setup_ui()

    def setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        # Title
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Event title")
        form_layout.addRow("Title:*", self.title_edit)

        # Description
        self.description_edit = QTextEdit()
        self.description_edit.setPlaceholderText(
            "Event description (optional)"
        )
        self.description_edit.setMaximumHeight(100)
        form_layout.addRow("Description:", self.description_edit)

        # Start time
        self.start_time_edit = QDateTimeEdit()
        self.start_time_edit.setCalendarPopup(True)
        self.start_time_edit.setDateTime(QDateTime.currentDateTime())
        self.start_time_edit.setDisplayFormat("yyyy-MM-dd HH:mm")
        form_layout.addRow("Start Time:*", self.start_time_edit)

        # End time
        self.end_time_edit = QDateTimeEdit()
        self.end_time_edit.setCalendarPopup(True)
        self.end_time_edit.setDateTime(
            QDateTime.currentDateTime().addSecs(3600)
        )
        self.end_time_edit.setDisplayFormat("yyyy-MM-dd HH:mm")
        form_layout.addRow("End Time:*", self.end_time_edit)

        # Location
        self.location_edit = QLineEdit()
        self.location_edit.setPlaceholderText("Event location (optional)")
        form_layout.addRow("Location:", self.location_edit)

        # Category
        self.category_combo = QComboBox()
        self.category_combo.setEditable(True)
        self.category_combo.addItems(
            ["", "work", "personal", "meeting", "appointment"]
        )
        form_layout.addRow("Category:", self.category_combo)

        # Color
        self.color_combo = QComboBox()
        self.color_combo.addItems(["#3788D8", "#F44336", "#4CAF50", "#FF9800"])
        form_layout.addRow("Color:", self.color_combo)

        # All day
        self.all_day_checkbox = QCheckBox("All-day event")
        self.all_day_checkbox.stateChanged.connect(self.on_all_day_changed)
        form_layout.addRow("", self.all_day_checkbox)

        layout.addLayout(form_layout)

        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.validate_and_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def on_all_day_changed(self, state: int) -> None:
        """Handle all-day checkbox state change."""
        is_all_day = bool(state)
        if is_all_day:
            self.start_time_edit.setDisplayFormat("yyyy-MM-dd")
            self.end_time_edit.setDisplayFormat("yyyy-MM-dd")
        else:
            self.start_time_edit.setDisplayFormat("yyyy-MM-dd HH:mm")
            self.end_time_edit.setDisplayFormat("yyyy-MM-dd HH:mm")

    def validate_and_accept(self) -> None:
        """Validate form and accept dialog."""
        if not self.title_edit.text().strip():
            QMessageBox.warning(self, "Validation Error", "Title is required.")
            return
        if self.end_time_edit.dateTime() <= self.start_time_edit.dateTime():
            QMessageBox.warning(
                self, "Validation Error", "End time must be after start time."
            )
            return
        self.accept()

    def set_start_date(self, date: datetime) -> None:
        """Set default start date."""
        qdt = QDateTime(
            QDate(date.year, date.month, date.day),
            QTime(date.hour, date.minute, 0),
        )
        self.start_time_edit.setDateTime(qdt)
        self.end_time_edit.setDateTime(qdt.addSecs(3600))

    def set_event_data(self, event: Event) -> None:
        """Populate form with event data for editing."""
        self.setWindowTitle("Edit Event")
        self.title_edit.setText(event.title or "")
        self.description_edit.setPlainText(event.description or "")

        start_qdt = QDateTime(
            QDate(
                event.start_time.year,
                event.start_time.month,
                event.start_time.day,
            ),
            QTime(event.start_time.hour, event.start_time.minute, 0),
        )
        self.start_time_edit.setDateTime(start_qdt)

        end_qdt = QDateTime(
            QDate(
                event.end_time.year, event.end_time.month, event.end_time.day
            ),
            QTime(event.end_time.hour, event.end_time.minute, 0),
        )
        self.end_time_edit.setDateTime(end_qdt)

        self.location_edit.setText(event.location or "")
        if event.category:
            self.category_combo.setCurrentText(event.category)
        if event.color:
            index = self.color_combo.findText(event.color)
            if index >= 0:
                self.color_combo.setCurrentIndex(index)
        self.all_day_checkbox.setChecked(event.all_day or False)

    def get_event_data(self) -> Dict[str, Any]:
        """Get event data from form."""
        start_qdt = self.start_time_edit.dateTime()
        start_dt = datetime(
            start_qdt.date().year(),
            start_qdt.date().month(),
            start_qdt.date().day(),
            start_qdt.time().hour(),
            start_qdt.time().minute(),
        )

        end_qdt = self.end_time_edit.dateTime()
        end_dt = datetime(
            end_qdt.date().year(),
            end_qdt.date().month(),
            end_qdt.date().day(),
            end_qdt.time().hour(),
            end_qdt.time().minute(),
        )

        description = self.description_edit.toPlainText().strip()
        location = self.location_edit.text().strip()
        category = self.category_combo.currentText().strip()

        return {
            "title": self.title_edit.text().strip(),
            "description": description if description else None,
            "start_time": start_dt,
            "end_time": end_dt,
            "location": location if location else None,
            "category": category if category else None,
            "color": self.color_combo.currentText(),
            "all_day": self.all_day_checkbox.isChecked(),
            "is_recurring": False,
        }
