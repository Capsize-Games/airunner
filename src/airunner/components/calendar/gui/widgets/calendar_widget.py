"""Calendar widget with month view and event management."""

from datetime import datetime, timedelta
from typing import List, Optional
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QCalendarWidget,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QLabel,
    QSplitter,
)
from PySide6.QtCore import Qt, QDate, Signal
from PySide6.QtGui import QTextCharFormat, QColor
from airunner.components.calendar.data.event import Event
from airunner.components.data.session_manager import session_scope
from airunner.components.calendar.gui.widgets.event_dialog import EventDialog


class CalendarWidget(QWidget):
    """Main calendar widget with month view and event list.

    Displays a calendar with events highlighted and provides
    event creation, editing, and deletion functionality.

    Signals:
        event_created: Emitted when new event is created
        event_updated: Emitted when event is modified
        event_deleted: Emitted when event is removed
    """

    event_created = Signal(int)  # event_id
    event_updated = Signal(int)  # event_id
    event_deleted = Signal(int)  # event_id

    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize calendar widget.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.selected_date: Optional[datetime] = None
        self.events_cache: List[Event] = []
        self.setup_ui()
        self.load_events()
        self.update_calendar_highlights()

    def setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)

        # Title
        title = QLabel("Calendar")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        # Main splitter
        splitter = QSplitter(Qt.Horizontal)

        # Left side - Calendar
        calendar_container = QWidget()
        calendar_layout = QVBoxLayout(calendar_container)

        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(True)
        self.calendar.clicked.connect(self.on_date_selected)
        calendar_layout.addWidget(self.calendar)

        # Calendar controls
        controls_layout = QHBoxLayout()

        self.today_button = QPushButton("Today")
        self.today_button.clicked.connect(self.go_to_today)
        controls_layout.addWidget(self.today_button)

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.refresh_events)
        controls_layout.addWidget(self.refresh_button)

        controls_layout.addStretch()
        calendar_layout.addLayout(controls_layout)

        splitter.addWidget(calendar_container)

        # Right side - Events list
        events_container = QWidget()
        events_layout = QVBoxLayout(events_container)

        self.events_label = QLabel("Events")
        self.events_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        events_layout.addWidget(self.events_label)

        self.events_list = QListWidget()
        self.events_list.itemDoubleClicked.connect(
            self.on_event_double_clicked
        )
        events_layout.addWidget(self.events_list)

        # Event controls
        event_controls = QHBoxLayout()

        self.new_event_button = QPushButton("New Event")
        self.new_event_button.clicked.connect(self.create_new_event)
        event_controls.addWidget(self.new_event_button)

        self.edit_event_button = QPushButton("Edit")
        self.edit_event_button.clicked.connect(self.edit_selected_event)
        self.edit_event_button.setEnabled(False)
        event_controls.addWidget(self.edit_event_button)

        self.delete_event_button = QPushButton("Delete")
        self.delete_event_button.clicked.connect(self.delete_selected_event)
        self.delete_event_button.setEnabled(False)
        event_controls.addWidget(self.delete_event_button)

        events_layout.addLayout(event_controls)

        splitter.addWidget(events_container)
        splitter.setSizes([300, 400])

        layout.addWidget(splitter)

        # Connect events list selection
        self.events_list.itemSelectionChanged.connect(
            self.on_events_selection_changed
        )

    def load_events(self) -> None:
        """Load all events from database."""
        with session_scope() as session:
            self.events_cache = session.query(Event).all()
            # Detach from session
            session.expunge_all()

    def update_calendar_highlights(self) -> None:
        """Highlight dates that have events."""
        # Clear existing highlights
        fmt = QTextCharFormat()
        self.calendar.setDateTextFormat(QDate(), fmt)

        # Highlight dates with events
        event_fmt = QTextCharFormat()
        event_fmt.setBackground(QColor("#e3f2fd"))

        for event in self.events_cache:
            qdate = QDate(
                event.start_time.year,
                event.start_time.month,
                event.start_time.day,
            )
            self.calendar.setDateTextFormat(qdate, event_fmt)

    def on_date_selected(self, date: QDate) -> None:
        """Handle date selection in calendar.

        Args:
            date: Selected date
        """
        self.selected_date = datetime(date.year(), date.month(), date.day())
        self.update_events_list()

    def update_events_list(self) -> None:
        """Update the events list for selected date."""
        self.events_list.clear()

        if not self.selected_date:
            return

        # Filter events for selected date
        day_start = self.selected_date.replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        day_end = day_start + timedelta(days=1)

        day_events = [
            event
            for event in self.events_cache
            if day_start <= event.start_time < day_end
        ]

        # Update label
        self.events_label.setText(
            f"Events on {self.selected_date.strftime('%B %d, %Y')} "
            f"({len(day_events)})"
        )

        # Add events to list
        for event in sorted(day_events, key=lambda e: e.start_time):
            time_str = event.start_time.strftime("%H:%M")
            duration = event.duration_minutes or 0
            item_text = (
                f"{time_str} - {event.title} ({duration}min)"
                f"{' - ' + event.location if event.location else ''}"
            )

            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, event.id)
            self.events_list.addItem(item)

    def on_events_selection_changed(self) -> None:
        """Handle events list selection change."""
        has_selection = len(self.events_list.selectedItems()) > 0
        self.edit_event_button.setEnabled(has_selection)
        self.delete_event_button.setEnabled(has_selection)

    def create_new_event(self) -> None:
        """Open dialog to create new event."""
        dialog = EventDialog(self)

        # Pre-fill with selected date if available
        if self.selected_date:
            dialog.set_start_date(self.selected_date)

        if dialog.exec():
            event_data = dialog.get_event_data()
            self.save_new_event(event_data)

    def save_new_event(self, event_data: dict) -> None:
        """Save new event to database.

        Args:
            event_data: Event data dictionary
        """
        event = Event(**event_data)

        with session_scope() as session:
            session.add(event)
            session.flush()
            event_id = event.id

        self.refresh_events()
        self.event_created.emit(event_id)

    def on_event_double_clicked(self, item: QListWidgetItem) -> None:
        """Handle double-click on event item.

        Args:
            item: Clicked list item
        """
        self.edit_selected_event()

    def edit_selected_event(self) -> None:
        """Open dialog to edit selected event."""
        items = self.events_list.selectedItems()
        if not items:
            return

        event_id = items[0].data(Qt.UserRole)

        # Load event from database
        with session_scope() as session:
            event = session.query(Event).filter_by(id=event_id).first()
            if not event:
                return

            # Open dialog with event data
            dialog = EventDialog(self)
            dialog.set_event_data(event)

            if dialog.exec():
                event_data = dialog.get_event_data()

                # Update event
                for key, value in event_data.items():
                    setattr(event, key, value)

                session.commit()

        self.refresh_events()
        self.event_updated.emit(event_id)

    def delete_selected_event(self) -> None:
        """Delete selected event."""
        items = self.events_list.selectedItems()
        if not items:
            return

        event_id = items[0].data(Qt.UserRole)

        # Confirm deletion
        from PySide6.QtWidgets import QMessageBox

        reply = QMessageBox.question(
            self,
            "Confirm Deletion",
            "Are you sure you want to delete this event?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            with session_scope() as session:
                event = session.query(Event).filter_by(id=event_id).first()
                if event:
                    session.delete(event)
                    session.commit()

            self.refresh_events()
            self.event_deleted.emit(event_id)

    def go_to_today(self) -> None:
        """Navigate calendar to today's date."""
        today = QDate.currentDate()
        self.calendar.setSelectedDate(today)
        self.on_date_selected(today)

    def refresh_events(self) -> None:
        """Reload events from database and refresh display."""
        self.load_events()
        self.update_calendar_highlights()
        if self.selected_date:
            self.update_events_list()
