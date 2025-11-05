"""RecurringEvent database model for recurring event patterns."""

from datetime import datetime, timedelta
from typing import Optional, List
from sqlalchemy import Column, Integer, String, DateTime, Text
from airunner.components.data.models.base import BaseModel


class RecurringEvent(BaseModel):
    """Recurring event pattern model.

    Defines the recurrence pattern for a series of events.
    Supports daily, weekly, monthly, and yearly recurrence with
    various customization options.

    Attributes:
        title: Base title for recurring events
        description: Description template for events
        recurrence_rule: iCal-compatible RRULE string
        recurrence_type: Simple type (daily, weekly, monthly, yearly)
        interval: Recurrence interval (e.g., every 2 weeks)
        days_of_week: Comma-separated days (0=Monday, 6=Sunday)
        day_of_month: Day of month for monthly recurrence
        month_of_year: Month for yearly recurrence
        start_date: When recurrence starts
        end_date: When recurrence ends (optional)
        max_occurrences: Maximum number of occurrences (optional)
        location: Default location for events
        category: Event category
        color: Calendar display color
    """

    __tablename__ = "recurring_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    recurrence_rule = Column(Text, nullable=True)
    recurrence_type = Column(
        String(20),
        nullable=False,
        index=True,
        comment="daily, weekly, monthly, yearly",
    )
    interval = Column(
        Integer,
        default=1,
        nullable=False,
        comment="Recurrence interval (e.g., every 2 weeks)",
    )
    days_of_week = Column(
        String(50), nullable=True, comment="Comma-separated days: 0=Mon, 6=Sun"
    )
    day_of_month = Column(Integer, nullable=True)
    month_of_year = Column(Integer, nullable=True)
    start_date = Column(DateTime, nullable=False, index=True)
    end_date = Column(DateTime, nullable=True)
    max_occurrences = Column(Integer, nullable=True)
    location = Column(String(500), nullable=True)
    category = Column(String(50), nullable=True, index=True)
    color = Column(String(7), nullable=True, default="#3788D8")

    def __repr__(self) -> str:
        """String representation of recurring event.

        Returns:
            String showing title and recurrence type
        """
        return f"<RecurringEvent(title='{self.title}', type='{self.recurrence_type}')>"

    @property
    def days_of_week_list(self) -> List[int]:
        """Parse days_of_week into list of integers.

        Returns:
            List of day numbers (0=Monday, 6=Sunday)
        """
        if not self.days_of_week:
            return []
        return [int(day.strip()) for day in self.days_of_week.split(",")]

    def get_next_occurrence(
        self, after_date: Optional[datetime] = None
    ) -> Optional[datetime]:
        """Calculate the next occurrence date.

        Args:
            after_date: Calculate occurrence after this date (default: now)

        Returns:
            Next occurrence datetime, or None if series ended
        """
        if not after_date:
            after_date = datetime.now()

        # Check if series has ended
        if self.end_date and after_date >= self.end_date:
            return None

        # Start from series start date or after_date, whichever is later
        current = max(self.start_date, after_date)

        # Calculate based on recurrence type
        if self.recurrence_type == "daily":
            next_date = current + timedelta(days=self.interval)
        elif self.recurrence_type == "weekly":
            next_date = current + timedelta(weeks=self.interval)
        elif self.recurrence_type == "monthly":
            # Monthly increment: move forward by interval months and clamp day
            import calendar as _calendar

            month = current.month - 1 + self.interval
            year = current.year + month // 12
            month = (month % 12) + 1

            # Determine desired day: prefer configured day_of_month if provided,
            # otherwise keep the current day. Then clamp to the last day of target month.
            desired_day = (
                self.day_of_month
                if self.day_of_month is not None
                else current.day
            )
            last_day = _calendar.monthrange(year, month)[1]
            day = min(desired_day, last_day)

            # If the current time has hour/minute/second, preserve them; otherwise default to 00:00
            try:
                next_date = current.replace(year=year, month=month, day=day)
            except ValueError:
                # Fallback: set to the last valid day
                next_date = current.replace(
                    year=year, month=month, day=last_day
                )
        elif self.recurrence_type == "yearly":
            next_date = current.replace(year=current.year + self.interval)
        else:
            return None

        # Respect end_date
        if self.end_date and next_date > self.end_date:
            return None

        return next_date

    def generate_occurrences(
        self,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[datetime]:
        """Generate list of occurrence dates within a range.

        Args:
            start: Range start (default: series start_date)
            end: Range end (default: series end_date or 1 year from start)
            limit: Maximum occurrences to generate

        Returns:
            List of occurrence datetimes
        """
        if not start:
            start = self.start_date
        if not end:
            end = self.end_date or (start + timedelta(days=365))

        occurrences = []
        current = self.get_next_occurrence(start - timedelta(days=1))

        while current and current <= end and len(occurrences) < limit:
            if current >= start:
                occurrences.append(current)
            current = self.get_next_occurrence(current)

        return occurrences

    def to_rrule(self) -> str:
        """Convert to iCal RRULE format.

        Returns:
            RRULE string for iCal export
        """
        if self.recurrence_rule:
            return self.recurrence_rule

        # Build simple RRULE
        freq_map = {
            "daily": "DAILY",
            "weekly": "WEEKLY",
            "monthly": "MONTHLY",
            "yearly": "YEARLY",
        }

        rule = f"FREQ={freq_map.get(self.recurrence_type, 'DAILY')}"

        if self.interval > 1:
            rule += f";INTERVAL={self.interval}"

        if self.days_of_week:
            # Convert day numbers to iCal format (MO, TU, WE, etc.)
            day_map = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"]
            days = [day_map[d] for d in self.days_of_week_list]
            rule += f";BYDAY={','.join(days)}"

        if self.day_of_month:
            rule += f";BYMONTHDAY={self.day_of_month}"

        if self.end_date:
            rule += f";UNTIL={self.end_date.strftime('%Y%m%dT%H%M%SZ')}"
        elif self.max_occurrences:
            rule += f";COUNT={self.max_occurrences}"

        return rule
