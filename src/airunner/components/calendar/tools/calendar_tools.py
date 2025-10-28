"""LangChain tools for calendar event management."""

from datetime import datetime
from typing import Optional
from langchain_core.tools import BaseTool
from pydantic import BaseModel as PydanticBaseModel, Field
from airunner.components.calendar.data.event import Event
from airunner.components.calendar.data.reminder import Reminder
from airunner.components.calendar.data.recurring_event import RecurringEvent
from airunner.components.data.session_manager import session_scope


class CreateEventInput(PydanticBaseModel):
    """Input schema for create_event tool."""

    title: str = Field(description="Event title/name")
    description: Optional[str] = Field(
        default=None, description="Detailed event description"
    )
    start_time: str = Field(
        description="Start time in ISO format (YYYY-MM-DDTHH:MM:SS)"
    )
    end_time: str = Field(
        description="End time in ISO format (YYYY-MM-DDTHH:MM:SS)"
    )
    location: Optional[str] = Field(default=None, description="Event location")
    category: Optional[str] = Field(
        default=None,
        description="Event category (e.g., work, personal, meeting)",
    )
    all_day: bool = Field(
        default=False, description="Whether event is all-day"
    )


class CreateEventTool(BaseTool):
    """Tool for creating calendar events."""

    name: str = "create_event"
    description: str = (
        "Create a new calendar event with specified date, time, "
        "title, and optional description. Use ISO format for times "
        "(YYYY-MM-DDTHH:MM:SS)."
    )
    args_schema: type[PydanticBaseModel] = CreateEventInput

    def _run(
        self,
        title: str,
        start_time: str,
        end_time: str,
        description: Optional[str] = None,
        location: Optional[str] = None,
        category: Optional[str] = None,
        all_day: bool = False,
    ) -> str:
        """Create a calendar event.

        Args:
            title: Event title
            start_time: ISO format start time
            end_time: ISO format end time
            description: Event description
            location: Event location
            category: Event category
            all_day: All-day event flag

        Returns:
            Success message with event ID
        """
        try:
            # Parse datetime strings
            start_dt = datetime.fromisoformat(start_time)
            end_dt = datetime.fromisoformat(end_time)

            # Create event
            event = Event(
                title=title,
                description=description,
                start_time=start_dt,
                end_time=end_dt,
                location=location,
                category=category,
                all_day=all_day,
            )

            with session_scope() as session:
                session.add(event)
                session.flush()
                event_id = event.id

            return (
                f"Created event '{title}' (ID: {event_id}) "
                f"from {start_time} to {end_time}"
            )
        except Exception as e:
            return f"Error creating event: {str(e)}"


class ListEventsInput(PydanticBaseModel):
    """Input schema for list_events tool."""

    start_date: Optional[str] = Field(
        default=None,
        description="Filter start date in ISO format (YYYY-MM-DD)",
    )
    end_date: Optional[str] = Field(
        default=None,
        description="Filter end date in ISO format (YYYY-MM-DD)",
    )
    category: Optional[str] = Field(
        default=None, description="Filter by category"
    )
    limit: int = Field(
        default=10, description="Maximum number of events to return"
    )


class ListEventsTool(BaseTool):
    """Tool for listing calendar events."""

    name: str = "list_events"
    description: str = (
        "List calendar events, optionally filtered by date range "
        "and category. Returns upcoming events by default."
    )
    args_schema: type[PydanticBaseModel] = ListEventsInput

    def _run(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 10,
    ) -> str:
        """List calendar events.

        Args:
            start_date: Filter by start date
            end_date: Filter by end date
            category: Filter by category
            limit: Maximum results

        Returns:
            Formatted list of events
        """
        try:
            with session_scope() as session:
                query = session.query(Event)

                # Apply filters
                if start_date:
                    start_dt = datetime.fromisoformat(start_date)
                    query = query.filter(Event.start_time >= start_dt)
                else:
                    # Default to upcoming events
                    query = query.filter(Event.start_time >= datetime.now())

                if end_date:
                    end_dt = datetime.fromisoformat(end_date)
                    query = query.filter(Event.end_time <= end_dt)

                if category:
                    query = query.filter(Event.category == category)

                # Order by start time and limit
                events = query.order_by(Event.start_time).limit(limit).all()

                if not events:
                    return "No events found matching the criteria."

                # Format results
                result_lines = [f"Found {len(events)} event(s):"]
                for event in events:
                    duration = event.duration_minutes or 0
                    result_lines.append(
                        f"- [{event.id}] {event.title} | "
                        f"{event.start_time.strftime('%Y-%m-%d %H:%M')} | "
                        f"{duration}min"
                        f"{' | ' + event.location if event.location else ''}"
                        f"{' | ' + event.category if event.category else ''}"
                    )

                return "\n".join(result_lines)
        except Exception as e:
            return f"Error listing events: {str(e)}"


class UpdateEventInput(PydanticBaseModel):
    """Input schema for update_event tool."""

    event_id: int = Field(description="ID of event to update")
    title: Optional[str] = Field(default=None, description="New title")
    description: Optional[str] = Field(
        default=None, description="New description"
    )
    start_time: Optional[str] = Field(
        default=None, description="New start time (ISO format)"
    )
    end_time: Optional[str] = Field(
        default=None, description="New end time (ISO format)"
    )
    location: Optional[str] = Field(default=None, description="New location")
    category: Optional[str] = Field(default=None, description="New category")


class UpdateEventTool(BaseTool):
    """Tool for updating calendar events."""

    name: str = "update_event"
    description: str = (
        "Update an existing calendar event by ID. "
        "Only provided fields will be updated."
    )
    args_schema: type[PydanticBaseModel] = UpdateEventInput

    def _run(
        self,
        event_id: int,
        title: Optional[str] = None,
        description: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        location: Optional[str] = None,
        category: Optional[str] = None,
    ) -> str:
        """Update a calendar event.

        Args:
            event_id: Event ID to update
            title: New title
            description: New description
            start_time: New start time
            end_time: New end time
            location: New location
            category: New category

        Returns:
            Success or error message
        """
        try:
            with session_scope() as session:
                event = session.query(Event).filter_by(id=event_id).first()

                if not event:
                    return f"Event with ID {event_id} not found."

                # Update provided fields
                if title is not None:
                    event.title = title
                if description is not None:
                    event.description = description
                if start_time is not None:
                    event.start_time = datetime.fromisoformat(start_time)
                if end_time is not None:
                    event.end_time = datetime.fromisoformat(end_time)
                if location is not None:
                    event.location = location
                if category is not None:
                    event.category = category

                session.commit()

                return f"Updated event '{event.title}' (ID: {event_id})"
        except Exception as e:
            return f"Error updating event: {str(e)}"


class DeleteEventInput(PydanticBaseModel):
    """Input schema for delete_event tool."""

    event_id: int = Field(description="ID of event to delete")


class DeleteEventTool(BaseTool):
    """Tool for deleting calendar events."""

    name: str = "delete_event"
    description: str = "Delete a calendar event by ID."
    args_schema: type[PydanticBaseModel] = DeleteEventInput

    def _run(self, event_id: int) -> str:
        """Delete a calendar event.

        Args:
            event_id: Event ID to delete

        Returns:
            Success or error message
        """
        try:
            with session_scope() as session:
                event = session.query(Event).filter_by(id=event_id).first()

                if not event:
                    return f"Event with ID {event_id} not found."

                title = event.title
                session.delete(event)
                session.commit()

                return f"Deleted event '{title}' (ID: {event_id})"
        except Exception as e:
            return f"Error deleting event: {str(e)}"


class CreateReminderInput(PydanticBaseModel):
    """Input schema for create_reminder tool."""

    event_id: int = Field(description="ID of event to remind about")
    reminder_time: str = Field(
        description="Reminder time in ISO format (YYYY-MM-DDTHH:MM:SS)"
    )
    message: Optional[str] = Field(
        default=None, description="Custom reminder message"
    )
    repeat_interval_minutes: Optional[int] = Field(
        default=None, description="Repeat interval in minutes"
    )


class CreateReminderTool(BaseTool):
    """Tool for creating event reminders."""

    name: str = "create_reminder"
    description: str = (
        "Create a reminder for a calendar event. "
        "Optionally set repeat interval for recurring reminders."
    )
    args_schema: type[PydanticBaseModel] = CreateReminderInput

    def _run(
        self,
        event_id: int,
        reminder_time: str,
        message: Optional[str] = None,
        repeat_interval_minutes: Optional[int] = None,
    ) -> str:
        """Create an event reminder.

        Args:
            event_id: Event to remind about
            reminder_time: When to send reminder
            message: Custom message
            repeat_interval_minutes: Repeat interval

        Returns:
            Success or error message
        """
        try:
            # Verify event exists
            with session_scope() as session:
                event = session.query(Event).filter_by(id=event_id).first()

                if not event:
                    return f"Event with ID {event_id} not found."

                # Parse reminder time
                reminder_dt = datetime.fromisoformat(reminder_time)

                # Create reminder
                reminder = Reminder(
                    event_id=event_id,
                    reminder_time=reminder_dt,
                    message=message,
                    repeat_interval_minutes=repeat_interval_minutes,
                )

                session.add(reminder)
                session.flush()
                reminder_id = reminder.id

                repeat_info = (
                    f" (repeats every {repeat_interval_minutes}min)"
                    if repeat_interval_minutes
                    else ""
                )

                return (
                    f"Created reminder (ID: {reminder_id}) for "
                    f"event '{event.title}' at {reminder_time}{repeat_info}"
                )
        except Exception as e:
            return f"Error creating reminder: {str(e)}"


class ScheduleRecurringEventInput(PydanticBaseModel):
    """Input schema for schedule_recurring_event tool."""

    title: str = Field(description="Recurring event title")
    description: Optional[str] = Field(
        default=None, description="Event description"
    )
    recurrence_type: str = Field(
        description="Recurrence type: daily, weekly, monthly, yearly"
    )
    interval: int = Field(
        default=1, description="Interval (e.g., every 2 weeks)"
    )
    start_date: str = Field(
        description="Start date in ISO format (YYYY-MM-DDTHH:MM:SS)"
    )
    end_date: Optional[str] = Field(
        default=None, description="End date in ISO format"
    )
    days_of_week: Optional[str] = Field(
        default=None,
        description="Comma-separated days (0=Mon, 6=Sun) for weekly",
    )
    location: Optional[str] = Field(default=None, description="Location")
    category: Optional[str] = Field(default=None, description="Category")


class ScheduleRecurringEventTool(BaseTool):
    """Tool for creating recurring events."""

    name: str = "schedule_recurring_event"
    description: str = (
        "Create a recurring event pattern (daily, weekly, monthly, "
        "yearly). For weekly events, specify days_of_week as "
        "comma-separated (0=Monday, 6=Sunday)."
    )
    args_schema: type[PydanticBaseModel] = ScheduleRecurringEventInput

    def _run(
        self,
        title: str,
        recurrence_type: str,
        start_date: str,
        interval: int = 1,
        description: Optional[str] = None,
        end_date: Optional[str] = None,
        days_of_week: Optional[str] = None,
        location: Optional[str] = None,
        category: Optional[str] = None,
    ) -> str:
        """Create a recurring event pattern.

        Args:
            title: Event title
            recurrence_type: daily/weekly/monthly/yearly
            start_date: Start date
            interval: Recurrence interval
            description: Description
            end_date: Optional end date
            days_of_week: Days for weekly recurrence
            location: Location
            category: Category

        Returns:
            Success or error message
        """
        try:
            # Validate recurrence type
            valid_types = ["daily", "weekly", "monthly", "yearly"]
            if recurrence_type not in valid_types:
                return (
                    f"Invalid recurrence type '{recurrence_type}'. "
                    f"Must be one of: {', '.join(valid_types)}"
                )

            # Parse dates
            start_dt = datetime.fromisoformat(start_date)
            end_dt = datetime.fromisoformat(end_date) if end_date else None

            # Create recurring event
            recurring = RecurringEvent(
                title=title,
                description=description,
                recurrence_type=recurrence_type,
                interval=interval,
                days_of_week=days_of_week,
                start_date=start_dt,
                end_date=end_dt,
                location=location,
                category=category,
            )

            with session_scope() as session:
                session.add(recurring)
                session.flush()
                recurring_id = recurring.id

            end_info = f" until {end_date}" if end_date else ""

            return (
                f"Created {recurrence_type} recurring event "
                f"'{title}' (ID: {recurring_id}) starting "
                f"{start_date}{end_info}"
            )
        except Exception as e:
            return f"Error creating recurring event: {str(e)}"


# Tool registry
CALENDAR_TOOLS = [
    CreateEventTool(),
    ListEventsTool(),
    UpdateEventTool(),
    DeleteEventTool(),
    CreateReminderTool(),
    ScheduleRecurringEventTool(),
]
