"""Calendar widget with month view and event management."""

from datetime import datetime, timedelta
from typing import List, Optional
from PySide6.QtWidgets import QListWidgetItem, QMessageBox, QToolButton
from PySide6.QtCore import Qt, QDate, Signal, Slot, QTimer
from PySide6.QtGui import QTextCharFormat, QColor
from airunner.components.calendar.data.event import Event
from airunner.components.data.session_manager import session_scope
from airunner.components.calendar.gui.widgets.event_dialog import EventDialog
from airunner.components.application.gui.widgets.base_widget import BaseWidget
from airunner.components.calendar.gui.widgets.templates.calendar_ui import (
    Ui_calendar,
)


class CalendarWidget(BaseWidget):
    """Main calendar widget with month view and event list.

    Displays a calendar with events highlighted and provides
    event creation, editing, and deletion functionality.

    Signals:
        event_created: Emitted when new event is created
        event_updated: Emitted when event is modified
        event_deleted: Emitted when event is removed
    """

    widget_class_ = Ui_calendar
    event_created = Signal(int)  # event_id
    event_updated = Signal(int)  # event_id
    event_deleted = Signal(int)  # event_id

    icons = [
        ("refresh-ccw", "refresh_button"),
        ("plus-square", "new_event_button"),
        ("edit", "edit_event_button"),
        ("trash", "delete_event_button"),
    ]

    def __init__(self, *args, **kwargs):
        """Initialize calendar widget.

        Args:
            *args: Variable length argument list
            **kwargs: Arbitrary keyword arguments
        """
        super().__init__(*args, **kwargs)
        self.selected_date: Optional[datetime] = None
        self.events_cache: List[Event] = []
        self.setup_connections()
        self.load_events()
        self.update_calendar_highlights()

        # Set calendar navigation icons after a short delay to ensure buttons exist
        QTimer.singleShot(0, self.setup_calendar_icons)

    def setup_calendar_icons(self) -> None:
        """Set icons for calendar navigation buttons after widget is initialized."""
        # QCalendarWidget uses QToolButton for navigation
        prev_button = self.ui.calendar_widget.findChild(
            QToolButton, "qt_calendar_prevmonth"
        )
        next_button = self.ui.calendar_widget.findChild(
            QToolButton, "qt_calendar_nextmonth"
        )

        if prev_button:
            prev_button.setObjectName("prev_month_button")
            prev_button.setText("")  # Remove text, just show icon

            # Add to icon manager's cache for theme-aware icon handling
            if self.icon_manager:
                self.icon_manager.icon_cache["prev_month_button"] = {
                    "icon_name": "chevron-left",
                    "widget": prev_button,
                }

        if next_button:
            next_button.setObjectName("next_month_button")
            next_button.setText("")  # Remove text, just show icon

            # Add to icon manager's cache for theme-aware icon handling
            if self.icon_manager:
                self.icon_manager.icon_cache["next_month_button"] = {
                    "icon_name": "chevron-right",
                    "widget": next_button,
                }

        # Now set the icons using the icon manager's theme logic
        if self.icon_manager:
            self.icon_manager.set_icons()

    def setup_connections(self) -> None:
        """Set up signal/slot connections for UI elements."""
        # Calendar connections
        self.ui.calendar_widget.clicked.connect(self.on_date_selected)

        # Button connections
        self.ui.today_button.clicked.connect(self.go_to_today)
        self.ui.refresh_button.clicked.connect(self.refresh_events)
        self.ui.new_event_button.clicked.connect(self.create_new_event)
        self.ui.edit_event_button.clicked.connect(self.edit_selected_event)
        self.ui.delete_event_button.clicked.connect(self.delete_selected_event)

        # Events list connection
        self.ui.events_list.itemSelectionChanged.connect(
            self.on_events_selection_changed
        )
        self.ui.events_list.itemDoubleClicked.connect(
            self.on_event_double_clicked
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
        self.ui.calendar_widget.setDateTextFormat(QDate(), fmt)

        # Highlight dates with events
        event_fmt = QTextCharFormat()
        event_fmt.setBackground(QColor("#e3f2fd"))

        for event in self.events_cache:
            qdate = QDate(
                event.start_time.year,
                event.start_time.month,
                event.start_time.day,
            )
            self.ui.calendar_widget.setDateTextFormat(qdate, event_fmt)

    @Slot(QDate)
    def on_date_selected(self, date: QDate) -> None:
        """Handle date selection in calendar.

        Args:
            date: Selected date
        """
        self.selected_date = datetime(date.year(), date.month(), date.day())
        self.update_events_list()

    def update_events_list(self) -> None:
        """Update the events list for selected date."""
        self.ui.events_list.clear()

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
        self.ui.events_label.setText(
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
            self.ui.events_list.addItem(item)

    @Slot()
    def on_events_selection_changed(self) -> None:
        """Handle events list selection change."""
        has_selection = len(self.ui.events_list.selectedItems()) > 0
        self.ui.edit_event_button.setEnabled(has_selection)
        self.ui.delete_event_button.setEnabled(has_selection)

    @Slot()
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

    @Slot(QListWidgetItem)
    def on_event_double_clicked(self, item: QListWidgetItem) -> None:
        """Handle double-click on event item.

        Args:
            item: Clicked list item
        """
        self.edit_selected_event()

    @Slot()
    def edit_selected_event(self) -> None:
        """Open dialog to edit selected event."""
        items = self.ui.events_list.selectedItems()
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

    @Slot()
    def delete_selected_event(self) -> None:
        """Delete selected event."""
        items = self.ui.events_list.selectedItems()
        if not items:
            return

        event_id = items[0].data(Qt.UserRole)

        # Confirm deletion
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

    @Slot()
    def go_to_today(self) -> None:
        """Navigate calendar to today's date."""
        today = QDate.currentDate()
        self.ui.calendar_widget.setSelectedDate(today)
        self.on_date_selected(today)

    @Slot()
    def refresh_events(self) -> None:
        """Reload events from database and refresh display."""
        self.load_events()
        self.update_calendar_highlights()
        if self.selected_date:
            self.update_events_list()
