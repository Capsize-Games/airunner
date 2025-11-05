"""Tests for calendar LangChain tools."""

import pytest
from datetime import datetime, timedelta
from airunner.components.calendar.tools.calendar_tools import (
    CreateEventTool,
    ListEventsTool,
    UpdateEventTool,
    DeleteEventTool,
    CreateReminderTool,
    ScheduleRecurringEventTool,
)
from airunner.components.calendar.data.event import Event
from airunner.components.calendar.data.reminder import Reminder
from airunner.components.calendar.data.recurring_event import RecurringEvent
from airunner.components.data.session_manager import session_scope


@pytest.fixture(autouse=True)
def cleanup_test_data():
    """Clean up test data after each test."""
    yield
    # Cleanup after test
    with session_scope() as session:
        session.query(Reminder).delete()
        session.query(Event).delete()
        session.query(RecurringEvent).delete()
        session.commit()


class TestCreateEventTool:
    """Tests for CreateEventTool."""

    def test_create_event(self):
        """Test creating a basic event."""
        tool = CreateEventTool()

        start = datetime.now() + timedelta(days=1)
        end = start + timedelta(hours=1)

        result = tool._run(
            title="Team Meeting",
            start_time=start.isoformat(),
            end_time=end.isoformat(),
            description="Weekly team sync",
            location="Conference Room A",
            category="work",
        )

        assert "Created event 'Team Meeting'" in result
        assert "ID:" in result

        # Verify in database
        with session_scope() as session:
            event = (
                session.query(Event).filter_by(title="Team Meeting").first()
            )
            assert event is not None
            assert event.description == "Weekly team sync"
            assert event.location == "Conference Room A"
            assert event.category == "work"

    def test_create_all_day_event(self):
        """Test creating an all-day event."""
        tool = CreateEventTool()

        start = datetime.now().replace(hour=0, minute=0, second=0)
        end = start.replace(hour=23, minute=59, second=59)

        result = tool._run(
            title="Conference",
            start_time=start.isoformat(),
            end_time=end.isoformat(),
            all_day=True,
        )

        assert "Created event 'Conference'" in result


class TestListEventsTool:
    """Tests for ListEventsTool."""

    def test_list_events(self):
        """Test listing events."""
        # Create test events
        now = datetime.now()
        with session_scope() as session:
            event1 = Event(
                title="Event 1",
                start_time=now + timedelta(days=1),
                end_time=now + timedelta(days=1, hours=1),
                category="work",
            )
            event2 = Event(
                title="Event 2",
                start_time=now + timedelta(days=2),
                end_time=now + timedelta(days=2, hours=1),
                category="personal",
            )
            session.add_all([event1, event2])
            session.commit()

        tool = ListEventsTool()
        result = tool._run()

        assert "Found 2 event(s):" in result
        assert "Event 1" in result
        assert "Event 2" in result

    def test_list_events_with_category_filter(self):
        """Test listing events filtered by category."""
        now = datetime.now()
        with session_scope() as session:
            event1 = Event(
                title="Work Event",
                start_time=now + timedelta(days=1),
                end_time=now + timedelta(days=1, hours=1),
                category="work",
            )
            event2 = Event(
                title="Personal Event",
                start_time=now + timedelta(days=2),
                end_time=now + timedelta(days=2, hours=1),
                category="personal",
            )
            session.add_all([event1, event2])
            session.commit()

        tool = ListEventsTool()
        result = tool._run(category="work")

        assert "Found 1 event(s):" in result
        assert "Work Event" in result
        assert "Personal Event" not in result

    def test_list_events_with_date_filter(self):
        """Test listing events filtered by date range."""
        now = datetime.now()
        with session_scope() as session:
            event1 = Event(
                title="This Week",
                start_time=now + timedelta(days=3),
                end_time=now + timedelta(days=3, hours=1),
            )
            event2 = Event(
                title="Next Month",
                start_time=now + timedelta(days=35),
                end_time=now + timedelta(days=35, hours=1),
            )
            session.add_all([event1, event2])
            session.commit()

        tool = ListEventsTool()
        end_date = (now + timedelta(days=7)).date().isoformat()
        result = tool._run(end_date=end_date)

        assert "This Week" in result
        assert "Next Month" not in result

    def test_list_events_empty(self):
        """Test listing events when none exist."""
        tool = ListEventsTool()
        result = tool._run()

        assert "No events found" in result


class TestUpdateEventTool:
    """Tests for UpdateEventTool."""

    def test_update_event(self):
        """Test updating an event."""
        # Create test event
        with session_scope() as session:
            event = Event(
                title="Original Title",
                start_time=datetime.now() + timedelta(days=1),
                end_time=datetime.now() + timedelta(days=1, hours=1),
                description="Original description",
            )
            session.add(event)
            session.flush()
            event_id = event.id

        tool = UpdateEventTool()
        result = tool._run(
            event_id=event_id,
            title="Updated Title",
            description="Updated description",
        )

        assert "Updated event 'Updated Title'" in result

        # Verify changes
        with session_scope() as session:
            event = session.query(Event).filter_by(id=event_id).first()
            assert event.title == "Updated Title"
            assert event.description == "Updated description"

    def test_update_event_not_found(self):
        """Test updating non-existent event."""
        tool = UpdateEventTool()
        result = tool._run(event_id=99999, title="New Title")

        assert "not found" in result


class TestDeleteEventTool:
    """Tests for DeleteEventTool."""

    def test_delete_event(self):
        """Test deleting an event."""
        # Create test event
        with session_scope() as session:
            event = Event(
                title="To Delete",
                start_time=datetime.now() + timedelta(days=1),
                end_time=datetime.now() + timedelta(days=1, hours=1),
            )
            session.add(event)
            session.flush()
            event_id = event.id

        tool = DeleteEventTool()
        result = tool._run(event_id=event_id)

        assert "Deleted event 'To Delete'" in result

        # Verify deletion
        with session_scope() as session:
            event = session.query(Event).filter_by(id=event_id).first()
            assert event is None

    def test_delete_event_not_found(self):
        """Test deleting non-existent event."""
        tool = DeleteEventTool()
        result = tool._run(event_id=99999)

        assert "not found" in result


class TestCreateReminderTool:
    """Tests for CreateReminderTool."""

    def test_create_reminder(self):
        """Test creating a reminder."""
        # Create test event
        with session_scope() as session:
            event = Event(
                title="Important Meeting",
                start_time=datetime.now() + timedelta(days=1),
                end_time=datetime.now() + timedelta(days=1, hours=1),
            )
            session.add(event)
            session.flush()
            event_id = event.id

        tool = CreateReminderTool()
        reminder_time = (datetime.now() + timedelta(hours=23)).isoformat()

        result = tool._run(
            event_id=event_id,
            reminder_time=reminder_time,
            message="Meeting in 1 hour!",
        )

        assert "Created reminder" in result
        assert "Important Meeting" in result

        # Verify in database
        with session_scope() as session:
            reminder = (
                session.query(Reminder).filter_by(event_id=event_id).first()
            )
            assert reminder is not None
            assert reminder.message == "Meeting in 1 hour!"

    def test_create_repeating_reminder(self):
        """Test creating a repeating reminder."""
        # Create test event
        with session_scope() as session:
            event = Event(
                title="Daily Standup",
                start_time=datetime.now() + timedelta(days=1),
                end_time=datetime.now() + timedelta(days=1, hours=1),
            )
            session.add(event)
            session.flush()
            event_id = event.id

        tool = CreateReminderTool()
        reminder_time = (datetime.now() + timedelta(hours=23)).isoformat()

        result = tool._run(
            event_id=event_id,
            reminder_time=reminder_time,
            repeat_interval_minutes=60,
        )

        assert "repeats every 60min" in result

    def test_create_reminder_invalid_event(self):
        """Test creating reminder for non-existent event."""
        tool = CreateReminderTool()
        reminder_time = datetime.now().isoformat()

        result = tool._run(
            event_id=99999,
            reminder_time=reminder_time,
        )

        assert "not found" in result


class TestScheduleRecurringEventTool:
    """Tests for ScheduleRecurringEventTool."""

    def test_schedule_daily_recurring(self):
        """Test scheduling daily recurring event."""
        tool = ScheduleRecurringEventTool()

        start = datetime.now() + timedelta(days=1)
        end = start + timedelta(days=30)

        result = tool._run(
            title="Daily Backup",
            recurrence_type="daily",
            start_date=start.isoformat(),
            end_date=end.isoformat(),
            interval=1,
        )

        assert "Created daily recurring event" in result
        assert "Daily Backup" in result

        # Verify in database
        with session_scope() as session:
            recurring = (
                session.query(RecurringEvent)
                .filter_by(title="Daily Backup")
                .first()
            )
            assert recurring is not None
            assert recurring.recurrence_type == "daily"
            assert recurring.interval == 1

    def test_schedule_weekly_recurring(self):
        """Test scheduling weekly recurring event."""
        tool = ScheduleRecurringEventTool()

        start = datetime.now() + timedelta(days=1)

        result = tool._run(
            title="Weekly Team Meeting",
            recurrence_type="weekly",
            start_date=start.isoformat(),
            interval=1,
            days_of_week="0,2,4",  # Mon, Wed, Fri
            category="work",
        )

        assert "Created weekly recurring event" in result

        # Verify in database
        with session_scope() as session:
            recurring = (
                session.query(RecurringEvent)
                .filter_by(title="Weekly Team Meeting")
                .first()
            )
            assert recurring is not None
            assert recurring.recurrence_type == "weekly"
            assert recurring.days_of_week == "0,2,4"
            assert recurring.category == "work"

    def test_schedule_recurring_invalid_type(self):
        """Test scheduling with invalid recurrence type."""
        tool = ScheduleRecurringEventTool()

        start = datetime.now() + timedelta(days=1)

        result = tool._run(
            title="Invalid Event",
            recurrence_type="hourly",  # Invalid
            start_date=start.isoformat(),
        )

        assert "Invalid recurrence type" in result
