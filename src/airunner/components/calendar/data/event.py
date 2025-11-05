"""Event database model for calendar events."""

from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Boolean,
    Text,
    ForeignKey,
)
from sqlalchemy.orm import relationship
from airunner.components.data.models.base import BaseModel


class Event(BaseModel):
    """Calendar event model.

    Represents a calendar event with title, description, start/end times,
    location, and recurrence settings.

    Attributes:
        id: Primary key
        title: Event title
        description: Detailed event description
        start_time: Event start date and time
        end_time: Event end date and time
        location: Physical or virtual location
        all_day: Whether event is an all-day event
        is_recurring: Whether event is part of a recurring series
        recurring_event_id: Foreign key to RecurringEvent if recurring
        category: Event category (e.g., "work", "personal", "meeting")
        color: Color code for calendar display (hex format)
        reminders: Related reminder objects
    """

    __tablename__ = "calendar_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime, nullable=False)
    location = Column(String(500), nullable=True)
    all_day = Column(Boolean, default=False, nullable=False)
    is_recurring = Column(Boolean, default=False, nullable=False, index=True)
    recurring_event_id = Column(
        Integer,
        ForeignKey("recurring_events.id"),
        nullable=True,
        index=True,
        comment="Reference to recurring_events.id if part of series",
    )
    category = Column(String(50), nullable=True, index=True)
    color = Column(String(7), nullable=True, default="#3788D8")

    # Relationships
    # reminders relationship defined in Reminder model

    def __repr__(self) -> str:
        """String representation of event.

        Returns:
            String showing event title and start time
        """
        return f"<Event(title='{self.title}', start='{self.start_time}')>"

    @property
    def duration_minutes(self) -> Optional[int]:
        """Calculate event duration in minutes.

        Returns:
            Duration in minutes, or None if times invalid
        """
        if self.start_time and self.end_time:
            delta = self.end_time - self.start_time
            return int(delta.total_seconds() / 60)
        return None

    @property
    def is_past(self) -> bool:
        """Check if event is in the past.

        Returns:
            True if event end time has passed
        """
        return self.end_time < datetime.now() if self.end_time else False

    @property
    def is_today(self) -> bool:
        """Check if event occurs today.

        Returns:
            True if event start time is today
        """
        if not self.start_time:
            return False
        today = datetime.now().date()
        return self.start_time.date() == today

    def to_ical_dict(self) -> dict:
        """Convert event to iCal-compatible dictionary.

        Returns:
            Dictionary with iCal standard fields
        """
        now = datetime.now()
        return {
            "summary": self.title,
            "description": self.description or "",
            "dtstart": self.start_time,
            "dtend": self.end_time,
            "location": self.location or "",
            "uid": (
                f"airunner-event-{self.id}"
                if self.id
                else f"airunner-event-temp"
            ),
            "created": getattr(self, "created_at", now),
            "last-modified": getattr(self, "updated_at", now),
            "categories": [self.category] if self.category else [],
        }
