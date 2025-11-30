"""
Calendar event management tools.

Provides tools for creating, listing, updating, and deleting calendar events
using the new @tool decorator system for ToolRegistry integration.
"""

from datetime import datetime
from typing import Annotated

from airunner.components.llm.core.tool_registry import tool, ToolCategory
from airunner.components.calendar.data.event import Event
from airunner.components.data.session_manager import session_scope
from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


@tool(
    name="create_calendar_event",
    category=ToolCategory.SYSTEM,
    description=(
        "Create a new calendar event with a specific date, time, title, "
        "and optional description. Use ISO format for times (YYYY-MM-DDTHH:MM:SS). "
        "Example: create an event for tomorrow at 2pm about team meeting."
    ),
    return_direct=False,
    requires_api=False,
)
def create_calendar_event(
    title: Annotated[str, "Event title/name"],
    start_time: Annotated[
        str, "Start time in ISO format (YYYY-MM-DDTHH:MM:SS)"
    ],
    end_time: Annotated[str, "End time in ISO format (YYYY-MM-DDTHH:MM:SS)"],
    description: Annotated[str, "Detailed event description"] = "",
    location: Annotated[str, "Event location"] = "",
    category: Annotated[
        str, "Event category (e.g., work, personal, meeting)"
    ] = "",
    all_day: Annotated[bool, "Whether event is all-day"] = False,
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

    """
    try:
        from airunner.components.calendar.data.event import Event
        from airunner.components.data.session_manager import session_scope

        # Parse datetime strings
        start_dt = datetime.fromisoformat(start_time)
        end_dt = datetime.fromisoformat(end_time)

        # Create event
        event = Event(
            title=title,
            description=description or None,
            start_time=start_dt,
            end_time=end_dt,
            location=location or None,
            category=category or None,
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


@tool(
    name="list_calendar_events",
    category=ToolCategory.SYSTEM,
    description=(
        "List calendar events, optionally filtered by date range and category. "
        "Returns upcoming events by default. Use this to check what's on the calendar."
    ),
    return_direct=False,
    requires_api=False,
)
def list_calendar_events(
    start_date: Annotated[
        str, "Filter start date in ISO format (YYYY-MM-DD)"
    ] = "",
    end_date: Annotated[
        str, "Filter end date in ISO format (YYYY-MM-DD)"
    ] = "",
    category: Annotated[str, "Filter by category"] = "",
    limit: Annotated[int, "Maximum number of events to return"] = 10,
) -> str:
    """List calendar events.

    Args:
        start_date: Filter by start date
        end_date: Filter by end date
        category: Filter by category
        limit: Maximum results

    """
    try:
        with session_scope() as session:
            # DEBUG: First check what events exist in database
            all_events = session.query(Event).all()
            logger.info(
                f"[CALENDAR DEBUG] Total events in database: {len(all_events)}"
            )
            for evt in all_events:
                logger.info(
                    f"[CALENDAR DEBUG]   - {evt.title}: {evt.start_time}"
                )

            query = session.query(Event)

            # Apply filters
            if start_date:
                start_dt = datetime.fromisoformat(start_date)
                logger.info(
                    f"[CALENDAR DEBUG] Filtering start_time >= {start_dt}"
                )
                query = query.filter(Event.start_time >= start_dt)
            else:
                # Default to upcoming events
                now = datetime.now()
                logger.info(
                    f"[CALENDAR DEBUG] No start_date, filtering start_time >= {now}"
                )
                query = query.filter(Event.start_time >= now)

            if end_date:
                end_dt = datetime.fromisoformat(end_date)
                logger.info(f"[CALENDAR DEBUG] Filtering end_time <= {end_dt}")
                query = query.filter(Event.end_time <= end_dt)

            if category:
                logger.info(
                    f"[CALENDAR DEBUG] Filtering category == {category}"
                )
                query = query.filter(Event.category == category)

            # Order by start time and limit
            events = query.order_by(Event.start_time).limit(limit).all()
            logger.info(
                f"[CALENDAR DEBUG] Query returned {len(events)} events"
            )

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
        logger.error(
            f"[CALENDAR DEBUG] Error listing events: {e}", exc_info=True
        )
        return f"Error listing events: {str(e)}"


@tool(
    name="update_calendar_event",
    category=ToolCategory.SYSTEM,
    description=(
        "Update an existing calendar event. "
        "Specify event ID and the fields to update. "
        "Use this to reschedule or modify event details."
    ),
    return_direct=False,
    requires_api=False,
)
def update_calendar_event(
    event_id: Annotated[int, "ID of event to update"],
    title: Annotated[str, "New title"] = "",
    description: Annotated[str, "New description"] = "",
    start_time: Annotated[str, "New start time (ISO format)"] = "",
    end_time: Annotated[str, "New end time (ISO format)"] = "",
    location: Annotated[str, "New location"] = "",
    category: Annotated[str, "New category"] = "",
) -> str:
    """Update an existing calendar event.

    Args:
        event_id: ID of event to update
        title: New title
        description: New description
        start_time: New start time
        end_time: New end time
        location: New location
        category: New category

    """
    try:
        from airunner.components.calendar.data.event import Event
        from airunner.components.data.session_manager import session_scope

        with session_scope() as session:
            event = session.query(Event).filter_by(id=event_id).first()

            if not event:
                return f"Error: Event with ID {event_id} not found"

            # Update fields if provided
            if title:
                event.title = title
            if description:
                event.description = description
            if start_time:
                event.start_time = datetime.fromisoformat(start_time)
            if end_time:
                event.end_time = datetime.fromisoformat(end_time)
            if location:
                event.location = location
            if category:
                event.category = category

            session.commit()

        return f"Updated event '{event.title}' (ID: {event_id})"
    except Exception as e:
        return f"Error updating event: {str(e)}"


@tool(
    name="delete_calendar_event",
    category=ToolCategory.SYSTEM,
    description=(
        "Delete a calendar event by ID. "
        "Use this to remove cancelled or outdated events."
    ),
    return_direct=False,
    requires_api=False,
)
def delete_calendar_event(
    event_id: Annotated[int, "ID of event to delete"],
) -> str:
    """Delete a calendar event.

    Args:
        event_id: ID of event to delete

    """
    try:
        from airunner.components.calendar.data.event import Event
        from airunner.components.data.session_manager import session_scope

        with session_scope() as session:
            event = session.query(Event).filter_by(id=event_id).first()

            if not event:
                return f"Error: Event with ID {event_id} not found"

            event_title = event.title
            session.delete(event)
            session.commit()

        return f"Deleted event '{event_title}' (ID: {event_id})"
    except Exception as e:
        return f"Error deleting event: {str(e)}"
