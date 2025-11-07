"""Tests for calendar GUI widgets."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch
from PySide6.QtWidgets import QApplication
from airunner.components.calendar.gui.widgets.calendar_widget import (
    CalendarWidget,
)
from airunner.components.calendar.gui.widgets.event_dialog import EventDialog
from airunner.components.calendar.gui.calendar_tab import CalendarTab
from airunner.components.calendar.data.event import Event


@pytest.fixture(scope="module")
def qapp():
    """Create QApplication instance for tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def calendar_widget(qapp):
    """Create CalendarWidget instance."""
    widget = CalendarWidget()
    yield widget
    widget.deleteLater()


@pytest.fixture
def event_dialog(qapp):
    """Create EventDialog instance."""
    dialog = EventDialog()
    yield dialog
    dialog.deleteLater()


@pytest.fixture
def calendar_tab(qapp):
    """Create CalendarTab instance."""
    tab = CalendarTab()
    yield tab
    tab.deleteLater()


class TestEventDialog:
    """Tests for EventDialog."""

    def test_initialization(self, event_dialog):
        """Test dialog initialization."""
        assert event_dialog.windowTitle() == "Event"
        assert event_dialog.title_edit is not None
        assert event_dialog.description_edit is not None
        assert event_dialog.start_time_edit is not None
        assert event_dialog.end_time_edit is not None

    def test_get_event_data(self, event_dialog):
        """Test getting event data from form."""
        event_dialog.title_edit.setText("Test Event")
        event_dialog.description_edit.setPlainText("Test description")
        event_dialog.location_edit.setText("Test Location")
        event_dialog.category_combo.setCurrentText("meeting")

        data = event_dialog.get_event_data()

        assert data["title"] == "Test Event"
        assert data["description"] == "Test description"
        assert data["location"] == "Test Location"
        assert data["category"] == "meeting"
        assert isinstance(data["start_time"], datetime)
        assert isinstance(data["end_time"], datetime)
        assert data["end_time"] > data["start_time"]

    def test_set_event_data(self, event_dialog):
        """Test setting event data in form."""
        event = Event(
            title="Test Event",
            description="Test description",
            start_time=datetime.now(),
            end_time=datetime.now() + timedelta(hours=1),
            location="Test Location",
            category="meeting",
            color="#FF0000",
            all_day=False,
        )

        event_dialog.set_event_data(event)

        assert event_dialog.title_edit.text() == "Test Event"
        assert (
            event_dialog.description_edit.toPlainText() == "Test description"
        )
        assert event_dialog.location_edit.text() == "Test Location"
        assert event_dialog.category_combo.currentText() == "meeting"

    def test_validation_empty_title(self, event_dialog):
        """Test validation fails with empty title."""
        event_dialog.title_edit.setText("")

        with patch("PySide6.QtWidgets.QMessageBox.warning") as mock_warning:
            event_dialog.validate_and_accept()
            mock_warning.assert_called_once()

    def test_validation_end_before_start(self, event_dialog):
        """Test validation fails when end time is before start time."""
        event_dialog.title_edit.setText("Test Event")
        event_dialog.end_time_edit.setDateTime(
            event_dialog.start_time_edit.dateTime().addSecs(-3600)
        )

        with patch("PySide6.QtWidgets.QMessageBox.warning") as mock_warning:
            event_dialog.validate_and_accept()
            mock_warning.assert_called_once()

    def test_all_day_toggle(self, event_dialog):
        """Test all-day checkbox toggles time display."""
        # Trigger state change
        event_dialog.all_day_checkbox.setChecked(True)
        assert event_dialog.start_time_edit.displayFormat() == "yyyy-MM-dd"

        event_dialog.all_day_checkbox.setChecked(False)
        assert (
            event_dialog.start_time_edit.displayFormat() == "yyyy-MM-dd HH:mm"
        )


class TestCalendarWidget:
    """Tests for CalendarWidget."""

    def test_initialization(self, calendar_widget):
        """Test widget initialization."""
        assert calendar_widget.ui.calendar_widget is not None
        assert calendar_widget.ui.events_list is not None
        assert calendar_widget.events_cache is not None

    def test_load_events(self, calendar_widget):
        """Test loading events from database."""
        # Test that load_events runs without error
        calendar_widget.load_events()

        # events_cache should be a list
        assert isinstance(calendar_widget.events_cache, list)


class TestCalendarTab:
    """Tests for CalendarTab."""

    def test_initialization(self, calendar_tab):
        """Test tab initialization."""
        assert calendar_tab.calendar_widget is not None
        assert calendar_tab.view_combo is not None
        assert calendar_tab.sync_button is not None
        assert calendar_tab.today_button is not None

    def test_today_button(self, calendar_tab):
        """Test today button selects current date."""
        from datetime import date

        today = date.today()
        calendar_tab.on_today_clicked()

        selected = (
            calendar_tab.calendar_widget.ui.calendar_widget.selectedDate()
        )
        assert selected.year() == today.year
        assert selected.month() == today.month
        assert selected.day() == today.day

    def test_sync_signal(self, calendar_tab):
        """Test sync button emits signal."""
        signal_emitted = False

        def on_sync():
            nonlocal signal_emitted
            signal_emitted = True

        calendar_tab.sync_requested.connect(on_sync)
        calendar_tab.on_sync_clicked()

        assert signal_emitted
