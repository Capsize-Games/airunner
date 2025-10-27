"""Reminder database model for event reminders."""

from datetime import datetime, timedelta
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from airunner.components.data.models.base import BaseModel


class Reminder(BaseModel):
    """Event reminder model.

    Represents a reminder notification for a calendar event.

    Attributes:
        id: Primary key
        event_id: Foreign key to associated event
        reminder_time: When the reminder should trigger
        message: Custom reminder message (optional)
        is_sent: Whether reminder has been sent
        repeat_interval_minutes: Interval for repeating reminders (optional)
        event: Related event object
    """

    __tablename__ = "calendar_reminders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(
        Integer, ForeignKey("calendar_events.id"), nullable=False, index=True
    )
    reminder_time = Column(DateTime, nullable=False, index=True)
    message = Column(String(500), nullable=True)
    is_sent = Column(Boolean, default=False, nullable=False, index=True)
    repeat_interval_minutes = Column(Integer, nullable=True)

    # Relationships
    event = relationship("Event", backref="reminders", foreign_keys=[event_id])

    def __repr__(self) -> str:
        """String representation of reminder.

        Returns:
            String showing reminder time and event ID
        """
        return f"<Reminder(event_id={self.event_id}, time='{self.reminder_time}')>"

    @property
    def is_past_due(self) -> bool:
        """Check if reminder time has passed.

        Returns:
            True if reminder time is in the past
        """
        return self.reminder_time < datetime.now()

    @property
    def is_upcoming(self) -> bool:
        """Check if reminder is upcoming (within next hour).

        Returns:
            True if reminder is in the next hour
        """
        now = datetime.now()
        one_hour = now + timedelta(hours=1)
        return now <= self.reminder_time <= one_hour

    @property
    def minutes_until(self) -> int:
        """Calculate minutes until reminder triggers.

        Returns:
            Minutes until reminder (negative if past)
        """
        delta = self.reminder_time - datetime.now()
        return int(delta.total_seconds() / 60)

    def mark_sent(self) -> None:
        """Mark reminder as sent and schedule next if repeating."""
        self.is_sent = True

        # If repeating, schedule next reminder
        if self.repeat_interval_minutes:
            self.reminder_time += timedelta(
                minutes=self.repeat_interval_minutes
            )
            self.is_sent = False
