"""Unit tests for calendar tools in ToolRegistry system."""

import pytest
from datetime import datetime, timedelta
from airunner.components.llm.tools.calendar_tools import (
    create_calendar_event,
    list_calendar_events,
    update_calendar_event,
    delete_calendar_event,
)
from airunner.components.calendar.data.event import Event
from airunner.components.data.session_manager import session_scope


@pytest.fixture(autouse=True)
def cleanup_test_data():
    """Clean up test data after each test."""
    yield
    # Cleanup after test
    with session_scope() as session:
        session.query(Event).delete()
        session.commit()


class TestCreateCalendarEvent:
    """Tests for create_calendar_event tool."""

    def test_create_event_basic(self):
        """Test creating a basic calendar event."""
        start = datetime.now() + timedelta(days=1)
        end = start + timedelta(hours=1)

        result = create_calendar_event(
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

    def test_create_event_minimal(self):
        """Test creating event with only required fields."""
        start = datetime.now() + timedelta(days=1)
        end = start + timedelta(hours=1)

        result = create_calendar_event(
            title="Simple Event",
            start_time=start.isoformat(),
            end_time=end.isoformat(),
        )

        assert "Created event 'Simple Event'" in result

        with session_scope() as session:
            event = (
                session.query(Event).filter_by(title="Simple Event").first()
            )
            assert event is not None
            assert event.description is None
            assert event.location is None

    def test_create_event_all_day(self):
        """Test creating an all-day event."""
        start = datetime.now().replace(hour=0, minute=0, second=0)
        end = start.replace(hour=23, minute=59, second=59)

        result = create_calendar_event(
            title="Conference",
            start_time=start.isoformat(),
            end_time=end.isoformat(),
            all_day=True,
        )

        assert "Created event 'Conference'" in result

        with session_scope() as session:
            event = session.query(Event).filter_by(title="Conference").first()
            assert event is not None
            assert event.all_day is True

    def test_create_event_invalid_datetime(self):
        """Test creating event with invalid datetime format."""
        result = create_calendar_event(
            title="Bad Event",
            start_time="not-a-date",
            end_time="also-not-a-date",
        )

        assert "Error creating event" in result


class TestListCalendarEvents:
    """Tests for list_calendar_events tool."""

    def test_list_events_upcoming(self):
        """Test listing upcoming events (default behavior)."""
        now = datetime.now()

        # Create past event (should not appear)
        with session_scope() as session:
            past_event = Event(
                title="Past Event",
                start_time=now - timedelta(days=1),
                end_time=now - timedelta(days=1, hours=-1),
            )
            session.add(past_event)
            session.commit()

        # Create future events
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

        result = list_calendar_events()

        assert "Found 2 event(s):" in result
        assert "Event 1" in result
        assert "Event 2" in result
        assert "Past Event" not in result

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

        result = list_calendar_events(category="work")

        assert "Found 1 event(s):" in result
        assert "Work Event" in result
        assert "Personal Event" not in result

    def test_list_events_with_date_range(self):
        """Test listing events filtered by date range."""
        now = datetime.now()
        start_filter = (now + timedelta(days=2)).strftime("%Y-%m-%d")
        end_filter = (now + timedelta(days=5)).strftime("%Y-%m-%d")

        with session_scope() as session:
            event1 = Event(
                title="Before Range",
                start_time=now + timedelta(days=1),
                end_time=now + timedelta(days=1, hours=1),
            )
            event2 = Event(
                title="In Range",
                start_time=now + timedelta(days=3),
                end_time=now + timedelta(days=3, hours=1),
            )
            event3 = Event(
                title="After Range",
                start_time=now + timedelta(days=10),
                end_time=now + timedelta(days=10, hours=1),
            )
            session.add_all([event1, event2, event3])
            session.commit()

        result = list_calendar_events(
            start_date=start_filter, end_date=end_filter
        )

        assert "In Range" in result
        assert "Before Range" not in result
        assert "After Range" not in result

    def test_list_events_with_limit(self):
        """Test limiting number of returned events."""
        now = datetime.now()
        with session_scope() as session:
            for i in range(5):
                event = Event(
                    title=f"Event {i}",
                    start_time=now + timedelta(days=i + 1),
                    end_time=now + timedelta(days=i + 1, hours=1),
                )
                session.add(event)
            session.commit()

        result = list_calendar_events(limit=3)

        assert "Found 3 event(s):" in result

    def test_list_events_no_results(self):
        """Test listing when no events match criteria."""
        result = list_calendar_events()

        assert "No events found" in result


class TestUpdateCalendarEvent:
    """Tests for update_calendar_event tool."""

    def test_update_event_title(self):
        """Test updating event title."""
        now = datetime.now()
        with session_scope() as session:
            event = Event(
                title="Original Title",
                start_time=now + timedelta(days=1),
                end_time=now + timedelta(days=1, hours=1),
            )
            session.add(event)
            session.flush()
            event_id = event.id

        result = update_calendar_event(event_id=event_id, title="New Title")

        assert "Updated event 'New Title'" in result

        with session_scope() as session:
            event = session.query(Event).filter_by(id=event_id).first()
            assert event.title == "New Title"

    def test_update_event_multiple_fields(self):
        """Test updating multiple event fields."""
        now = datetime.now()
        with session_scope() as session:
            event = Event(
                title="Original",
                description="Old description",
                location="Old location",
                start_time=now + timedelta(days=1),
                end_time=now + timedelta(days=1, hours=1),
                category="work",
            )
            session.add(event)
            session.flush()
            event_id = event.id

        new_start = now + timedelta(days=2)
        new_end = new_start + timedelta(hours=2)

        result = update_calendar_event(
            event_id=event_id,
            title="New Title",
            description="New description",
            location="New location",
            start_time=new_start.isoformat(),
            end_time=new_end.isoformat(),
            category="personal",
        )

        assert "Updated event" in result

        with session_scope() as session:
            event = session.query(Event).filter_by(id=event_id).first()
            assert event.title == "New Title"
            assert event.description == "New description"
            assert event.location == "New location"
            assert event.category == "personal"

    def test_update_event_nonexistent(self):
        """Test updating non-existent event."""
        result = update_calendar_event(event_id=99999, title="New Title")

        assert "Error: Event with ID 99999 not found" in result

    def test_update_event_partial(self):
        """Test updating only some fields (others unchanged)."""
        now = datetime.now()
        with session_scope() as session:
            event = Event(
                title="Original",
                description="Keep this",
                start_time=now + timedelta(days=1),
                end_time=now + timedelta(days=1, hours=1),
            )
            session.add(event)
            session.flush()
            event_id = event.id

        result = update_calendar_event(event_id=event_id, title="New Title")

        with session_scope() as session:
            event = session.query(Event).filter_by(id=event_id).first()
            assert event.title == "New Title"
            assert event.description == "Keep this"  # Unchanged


class TestDeleteCalendarEvent:
    """Tests for delete_calendar_event tool."""

    def test_delete_event(self):
        """Test deleting an event."""
        now = datetime.now()
        with session_scope() as session:
            event = Event(
                title="To Delete",
                start_time=now + timedelta(days=1),
                end_time=now + timedelta(days=1, hours=1),
            )
            session.add(event)
            session.flush()
            event_id = event.id

        result = delete_calendar_event(event_id=event_id)

        assert "Deleted event 'To Delete'" in result
        assert f"ID: {event_id}" in result

        # Verify deletion
        with session_scope() as session:
            event = session.query(Event).filter_by(id=event_id).first()
            assert event is None

    def test_delete_event_nonexistent(self):
        """Test deleting non-existent event."""
        result = delete_calendar_event(event_id=99999)

        assert "Error: Event with ID 99999 not found" in result
