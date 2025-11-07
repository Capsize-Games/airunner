"""Calendar tab widget for main application."""

from typing import Optional
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QComboBox,
)
from PySide6.QtCore import Signal, QDate
from airunner.components.calendar.gui.widgets.calendar_widget import (
    CalendarWidget,
)


class CalendarTab(QWidget):
    """Main calendar tab widget."""

    sync_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize calendar tab."""
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)

        # Toolbar
        toolbar_layout = QHBoxLayout()
        view_label = QLabel("View:")
        toolbar_layout.addWidget(view_label)

        self.view_combo = QComboBox()
        self.view_combo.addItems(["Month", "Week", "Year"])
        self.view_combo.currentTextChanged.connect(self.on_view_changed)
        toolbar_layout.addWidget(self.view_combo)
        toolbar_layout.addStretch()

        self.sync_button = QPushButton("Sync Calendar")
        self.sync_button.clicked.connect(self.on_sync_clicked)
        toolbar_layout.addWidget(self.sync_button)

        self.today_button = QPushButton("Today")
        self.today_button.clicked.connect(self.on_today_clicked)
        toolbar_layout.addWidget(self.today_button)

        layout.addLayout(toolbar_layout)

        # Calendar widget
        self.calendar_widget = CalendarWidget()
        layout.addWidget(self.calendar_widget)

        # Connect signals
        self.calendar_widget.event_created.connect(self.on_event_created)
        self.calendar_widget.event_updated.connect(self.on_event_updated)
        self.calendar_widget.event_deleted.connect(self.on_event_deleted)

    def on_view_changed(self, view: str) -> None:
        """Handle view change."""
        pass  # TODO: Implement week and year views

    def on_sync_clicked(self) -> None:
        """Handle sync button click."""
        self.sync_requested.emit()

    def on_today_clicked(self) -> None:
        """Handle today button click."""
        from datetime import date

        today = date.today()
        self.calendar_widget.ui.calendar_widget.setSelectedDate(
            QDate(today.year, today.month, today.day)
        )

    def on_event_created(self, event_id: int) -> None:
        """Handle event creation."""
        self.calendar_widget.load_events()

    def on_event_updated(self, event_id: int) -> None:
        """Handle event update."""
        self.calendar_widget.load_events()

    def on_event_deleted(self, event_id: int) -> None:
        """Handle event deletion."""
        self.calendar_widget.load_events()
