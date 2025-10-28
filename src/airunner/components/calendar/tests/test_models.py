"""Tests for calendar data models."""

from datetime import datetime, timedelta
from airunner.components.calendar.data.event import Event
from airunner.components.calendar.data.reminder import Reminder
from airunner.components.calendar.data.recurring_event import RecurringEvent


class TestEventModel:
    """Tests for Event model."""

    def test_event_creation(self):
        """Test creating a basic event."""
        start = datetime.now()
        end = start + timedelta(hours=1)

        event = Event(
            title="Test Meeting",
            description="A test meeting",
            start_time=start,
            end_time=end,
            location="Conference Room A",
            category="work",
        )

        assert event.title == "Test Meeting"
        assert event.description == "A test meeting"
        assert event.start_time == start
        assert event.end_time == end
        assert event.location == "Conference Room A"
        assert event.category == "work"
        # all_day defaults to False in the database, but may be None before persistence
        assert event.all_day in (False, None)
        # is_recurring defaults to False in the database, but may be None before persistence
        assert event.is_recurring in (False, None)

    def test_event_duration(self):
        """Test event duration calculation."""
        start = datetime(2025, 10, 27, 14, 0)
        end = datetime(2025, 10, 27, 15, 30)

        event = Event(
            title="90 Minute Meeting",
            start_time=start,
            end_time=end,
        )

        assert event.duration_minutes == 90

    def test_event_is_past(self):
        """Test past event detection."""
        past_start = datetime.now() - timedelta(days=2)
        past_end = datetime.now() - timedelta(days=1)

        past_event = Event(
            title="Past Event",
            start_time=past_start,
            end_time=past_end,
        )

        assert past_event.is_past is True

        future_start = datetime.now() + timedelta(days=1)
        future_end = datetime.now() + timedelta(days=2)

        future_event = Event(
            title="Future Event",
            start_time=future_start,
            end_time=future_end,
        )

        assert future_event.is_past is False

    def test_event_is_today(self):
        """Test today event detection."""
        today_start = datetime.now()
        today_end = today_start + timedelta(hours=1)

        today_event = Event(
            title="Today Event",
            start_time=today_start,
            end_time=today_end,
        )

        assert today_event.is_today is True

        yesterday = datetime.now() - timedelta(days=1)
        yesterday_end = yesterday + timedelta(hours=1)

        yesterday_event = Event(
            title="Yesterday Event",
            start_time=yesterday,
            end_time=yesterday_end,
        )

        assert yesterday_event.is_today is False

    def test_event_to_ical_dict(self):
        """Test iCal dictionary conversion."""
        start = datetime(2025, 10, 27, 14, 0)
        end = datetime(2025, 10, 27, 15, 0)

        event = Event(
            id=123,
            title="iCal Test",
            description="Test description",
            start_time=start,
            end_time=end,
            location="Test Location",
            category="personal",
        )

        ical_dict = event.to_ical_dict()

        assert ical_dict["summary"] == "iCal Test"
        assert ical_dict["description"] == "Test description"
        assert ical_dict["dtstart"] == start
        assert ical_dict["dtend"] == end
        assert ical_dict["location"] == "Test Location"
        assert ical_dict["uid"] == "airunner-event-123"
        assert ical_dict["categories"] == ["personal"]

    def test_all_day_event(self):
        """Test all-day event."""
        start = datetime(2025, 10, 27, 0, 0)
        end = datetime(2025, 10, 27, 23, 59)

        event = Event(
            title="All Day Event",
            start_time=start,
            end_time=end,
            all_day=True,
        )

        assert event.all_day is True


class TestReminderModel:
    """Tests for Reminder model."""

    def test_reminder_creation(self):
        """Test creating a reminder."""
        reminder_time = datetime.now() + timedelta(hours=1)

        reminder = Reminder(
            event_id=1,
            reminder_time=reminder_time,
            message="Meeting in 1 hour!",
            is_sent=False,
        )

        assert reminder.event_id == 1
        assert reminder.reminder_time == reminder_time
        assert reminder.message == "Meeting in 1 hour!"
        assert reminder.is_sent is False

    def test_reminder_is_past_due(self):
        """Test past due reminder detection."""
        past_time = datetime.now() - timedelta(hours=1)

        past_reminder = Reminder(
            event_id=1,
            reminder_time=past_time,
        )

        assert past_reminder.is_past_due is True

        future_time = datetime.now() + timedelta(hours=1)

        future_reminder = Reminder(
            event_id=1,
            reminder_time=future_time,
        )

        assert future_reminder.is_past_due is False

    def test_reminder_is_upcoming(self):
        """Test upcoming reminder detection (within 1 hour)."""
        upcoming_time = datetime.now() + timedelta(minutes=30)

        upcoming_reminder = Reminder(
            event_id=1,
            reminder_time=upcoming_time,
        )

        assert upcoming_reminder.is_upcoming is True

        far_future = datetime.now() + timedelta(hours=2)

        far_reminder = Reminder(
            event_id=1,
            reminder_time=far_future,
        )

        assert far_reminder.is_upcoming is False

    def test_reminder_minutes_until(self):
        """Test minutes until reminder calculation."""
        reminder_time = datetime.now() + timedelta(minutes=45)

        reminder = Reminder(
            event_id=1,
            reminder_time=reminder_time,
        )

        # Allow for small time drift in test execution
        minutes = reminder.minutes_until
        assert 44 <= minutes <= 46

    def test_reminder_mark_sent(self):
        """Test marking reminder as sent."""
        reminder_time = datetime.now() + timedelta(hours=1)

        reminder = Reminder(
            event_id=1,
            reminder_time=reminder_time,
            is_sent=False,
        )

        reminder.mark_sent()

        assert reminder.is_sent is True

    def test_reminder_repeat(self):
        """Test repeating reminder."""
        original_time = datetime.now() + timedelta(hours=1)

        reminder = Reminder(
            event_id=1,
            reminder_time=original_time,
            repeat_interval_minutes=60,
            is_sent=False,
        )

        reminder.mark_sent()

        # Should reschedule for 1 hour later and reset is_sent
        assert reminder.reminder_time == original_time + timedelta(minutes=60)
        assert reminder.is_sent is False


class TestRecurringEventModel:
    """Tests for RecurringEvent model."""

    def test_recurring_event_creation(self):
        """Test creating a recurring event pattern."""
        start_date = datetime(2025, 10, 27, 10, 0)

        recurring = RecurringEvent(
            title="Weekly Team Meeting",
            description="Every Monday at 10am",
            recurrence_type="weekly",
            interval=1,
            days_of_week="0",  # Monday
            start_date=start_date,
            category="work",
        )

        assert recurring.title == "Weekly Team Meeting"
        assert recurring.recurrence_type == "weekly"
        assert recurring.interval == 1
        assert recurring.days_of_week == "0"

    def test_days_of_week_list(self):
        """Test parsing days of week."""
        recurring = RecurringEvent(
            title="Workweek Standup",
            recurrence_type="weekly",
            days_of_week="0,1,2,3,4",  # Mon-Fri
            start_date=datetime.now(),
        )

        days_list = recurring.days_of_week_list
        assert days_list == [0, 1, 2, 3, 4]

    def test_get_next_occurrence_daily(self):
        """Test calculating next occurrence for daily recurrence."""
        start = datetime(2025, 10, 27, 10, 0)

        recurring = RecurringEvent(
            title="Daily Reminder",
            recurrence_type="daily",
            interval=1,
            start_date=start,
        )

        next_occ = recurring.get_next_occurrence(start)
        expected = start + timedelta(days=1)

        assert next_occ == expected

    def test_get_next_occurrence_weekly(self):
        """Test calculating next occurrence for weekly recurrence."""
        start = datetime(2025, 10, 27, 10, 0)

        recurring = RecurringEvent(
            title="Weekly Meeting",
            recurrence_type="weekly",
            interval=1,
            start_date=start,
        )

        next_occ = recurring.get_next_occurrence(start)
        expected = start + timedelta(weeks=1)

        assert next_occ == expected

    def test_get_next_occurrence_with_end_date(self):
        """Test recurrence ending respects end_date."""
        start = datetime(2025, 10, 27, 10, 0)
        end = datetime(2025, 11, 1, 10, 0)  # 5 days later

        recurring = RecurringEvent(
            title="Limited Series",
            recurrence_type="daily",
            interval=1,
            start_date=start,
            end_date=end,
        )

        # After end date, should return None
        after_end = datetime(2025, 11, 2, 10, 0)
        next_occ = recurring.get_next_occurrence(after_end)

        assert next_occ is None

    def test_generate_occurrences(self):
        """Test generating list of occurrences."""
        start = datetime(2025, 10, 27, 10, 0)
        end = datetime(2025, 11, 3, 10, 0)  # 1 week later

        recurring = RecurringEvent(
            title="Daily Meeting",
            recurrence_type="daily",
            interval=1,
            start_date=start,
            end_date=end,
        )

        occurrences = recurring.generate_occurrences(start, end)

        # Should generate 7 days (Oct 27-Nov 2, inclusive of Nov 3 end)
        assert len(occurrences) >= 7
        assert occurrences[0] >= start
        assert occurrences[-1] <= end

    def test_generate_occurrences_with_limit(self):
        """Test occurrence generation respects limit."""
        start = datetime(2025, 10, 27, 10, 0)

        recurring = RecurringEvent(
            title="Unlimited Daily",
            recurrence_type="daily",
            interval=1,
            start_date=start,
        )

        occurrences = recurring.generate_occurrences(limit=5)

        assert len(occurrences) == 5

    def test_to_rrule_daily(self):
        """Test generating RRULE for daily recurrence."""
        recurring = RecurringEvent(
            title="Daily Event",
            recurrence_type="daily",
            interval=2,  # Every 2 days
            start_date=datetime.now(),
        )

        rrule = recurring.to_rrule()

        assert "FREQ=DAILY" in rrule
        assert "INTERVAL=2" in rrule

    def test_to_rrule_weekly_with_days(self):
        """Test generating RRULE for weekly recurrence with specific days."""
        recurring = RecurringEvent(
            title="Workweek Event",
            recurrence_type="weekly",
            interval=1,
            days_of_week="0,2,4",  # Mon, Wed, Fri
            start_date=datetime.now(),
        )

        rrule = recurring.to_rrule()

        assert "FREQ=WEEKLY" in rrule
        assert "BYDAY=MO,WE,FR" in rrule

    def test_to_rrule_with_end_date(self):
        """Test RRULE generation with end date."""
        end_date = datetime(2025, 12, 31, 23, 59)

        recurring = RecurringEvent(
            title="Limited Event",
            recurrence_type="daily",
            interval=1,
            start_date=datetime.now(),
            end_date=end_date,
        )

        rrule = recurring.to_rrule()

        assert "FREQ=DAILY" in rrule
        assert "UNTIL=" in rrule

    def test_to_rrule_with_count(self):
        """Test RRULE generation with max occurrences."""
        recurring = RecurringEvent(
            title="10 Times Event",
            recurrence_type="weekly",
            interval=1,
            start_date=datetime.now(),
            max_occurrences=10,
        )

        rrule = recurring.to_rrule()

        assert "FREQ=WEEKLY" in rrule
        assert "COUNT=10" in rrule


def test_monthly_recurrence_jan31_to_feb_clamps():
    """Jan 31 should produce Feb 28 (or 29 on leap years) when advancing monthly."""
    start = datetime(2025, 1, 31, 10, 0)

    recurring = RecurringEvent(
        title="End of Month",
        recurrence_type="monthly",
        interval=1,
        start_date=start,
    )

    next_occ = recurring.get_next_occurrence(start)

    # 2025 is not a leap year, so Feb has 28 days
    expected = datetime(2025, 2, 28, 10, 0)
    assert next_occ == expected


def test_monthly_recurrence_explicit_day_of_month_clamps():
    """When day_of_month is explicitly set to 31, next month with fewer days clamps to last day."""
    start = datetime(2025, 1, 15, 9, 0)

    recurring = RecurringEvent(
        title="Monthly By Day",
        recurrence_type="monthly",
        interval=1,
        day_of_month=31,
        start_date=start,
    )

    next_occ = recurring.get_next_occurrence(start)

    # February 2025 -> 28
    expected = datetime(2025, 2, 28, 9, 0)
    assert next_occ == expected


def test_monthly_recurrence_none_day_preserves_then_clamps():
    """If day_of_month is None, the current day is used then clamped in shorter months."""
    start = datetime(2025, 3, 31, 8, 0)

    recurring = RecurringEvent(
        title="Preserve Current Day",
        recurrence_type="monthly",
        interval=1,
        day_of_month=None,
        start_date=start,
    )

    next_occ = recurring.get_next_occurrence(start)

    # April has 30 days, so expect April 30
    expected = datetime(2025, 4, 30, 8, 0)
    assert next_occ == expected
