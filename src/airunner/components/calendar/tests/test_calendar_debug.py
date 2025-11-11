"""Debug script to test calendar events creation and listing."""

from datetime import datetime, timedelta
from airunner.components.calendar.data.event import Event
from airunner.components.data.session_manager import session_scope


def main():
    print("Creating test events...")
    now = datetime.now()

    # Clean up first
    with session_scope() as session:
        deleted = session.query(Event).delete()
        session.commit()
        print(f"Deleted {deleted} existing events")

    # Create events
    with session_scope() as session:
        event1 = Event(
            title="Meeting A",
            start_time=now + timedelta(days=1),
            end_time=now + timedelta(days=1, hours=1),
            category="work",
        )
        event2 = Event(
            title="Meeting B",
            start_time=now + timedelta(days=2),
            end_time=now + timedelta(days=2, hours=1),
            category="personal",
        )
        session.add_all([event1, event2])
        session.commit()
        print(
            f"Created event1 ID={event1.id}: {event1.title} at {event1.start_time}"
        )
        print(
            f"Created event2 ID={event2.id}: {event2.title} at {event2.start_time}"
        )

    # Now test the calendar tool
    print("\nTesting list_calendar_events tool...")
    from airunner.components.llm.tools.calendar_tools import (
        list_calendar_events,
    )

    result = list_calendar_events()
    print(f"Tool result:\n{result}")

    # Also check what's in the database
    print("\nQuerying database directly...")
    with session_scope() as session:
        all_events = session.query(Event).all()
        print(f"Found {len(all_events)} events in database:")
        for event in all_events:
            print(f"  - {event.title}: {event.start_time} (id={event.id})")


if __name__ == "__main__":
    main()
