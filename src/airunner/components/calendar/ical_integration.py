"""iCal import/export functionality for calendar events."""

from datetime import datetime
from typing import List, Dict
from icalendar import Calendar, Event as ICalEvent
from airunner.components.calendar.data.event import Event
from airunner.components.calendar.data.recurring_event import RecurringEvent


class ICalIntegration:
    """Handles iCal (RFC 5545) import and export operations.

    Provides methods to convert between AI Runner calendar events
    and iCal format for interoperability with other calendar applications.
    """

    def __init__(self):
        """Initialize iCal integration."""

    def export_to_ical(self, events: List[Event]) -> str:
        """Export events to iCal format.

        Args:
            events: List of Event objects to export

        Returns:
            iCal format string (RFC 5545)
        """
        cal = Calendar()
        cal.add("prodid", "-//AI Runner Calendar//airunner//EN")
        cal.add("version", "2.0")
        cal.add("calscale", "GREGORIAN")
        cal.add("method", "PUBLISH")

        for event in events:
            ical_event = ICalEvent()
            event_dict = event.to_ical_dict()

            ical_event.add("summary", event_dict["summary"])
            ical_event.add("dtstart", event_dict["dtstart"])
            ical_event.add("dtend", event_dict["dtend"])
            ical_event.add("dtstamp", datetime.now())
            ical_event.add("uid", event_dict["uid"])
            ical_event.add("created", event_dict["created"])
            ical_event.add("last-modified", event_dict["last-modified"])

            if event_dict["description"]:
                ical_event.add("description", event_dict["description"])

            if event_dict["location"]:
                ical_event.add("location", event_dict["location"])

            if event_dict["categories"]:
                ical_event.add("categories", event_dict["categories"])

            cal.add_component(ical_event)

        return cal.to_ical().decode("utf-8")

    def import_from_ical(self, ical_string: str) -> List[Dict]:
        """Import events from iCal format.

        Args:
            ical_string: iCal format string to parse

        Returns:
            List of dictionaries with event data ready for Event creation
        """
        cal = Calendar.from_ical(ical_string)
        events = []

        for component in cal.walk():
            if component.name == "VEVENT":
                event_data = {
                    "title": str(component.get("summary", "")),
                    "description": str(component.get("description", "")),
                    "location": str(component.get("location", "")),
                    "start_time": component.get("dtstart").dt,
                    "end_time": component.get("dtend").dt,
                    "category": None,
                    "all_day": False,
                }

                # Handle all-day events: dtstart.dt may be a date or datetime
                dtstart_val = component.get("dtstart").dt
                try:
                    # all-day events in ical are typically date objects, not datetimes
                    from datetime import date

                    if isinstance(dtstart_val, date) and not isinstance(
                        dtstart_val, datetime
                    ):
                        event_data["all_day"] = True
                except Exception:
                    # Fallback: preserve previous behavior if introspection fails
                    if hasattr(dtstart_val, "date"):
                        event_data["all_day"] = True

                # Extract categories
                categories = component.get("categories")
                if categories:
                    if hasattr(categories, "cats"):
                        event_data["category"] = (
                            categories.cats[0] if categories.cats else None
                        )
                    elif isinstance(categories, str):
                        event_data["category"] = categories

                # Handle recurrence rules
                rrule = component.get("rrule")
                if rrule:
                    event_data["is_recurring"] = True
                    event_data["recurrence_rule"] = str(rrule)

                events.append(event_data)

        return events

    def export_recurring_to_ical(self, recurring_event: RecurringEvent) -> str:
        """Export recurring event pattern to iCal RRULE.

        Args:
            recurring_event: RecurringEvent object

        Returns:
            RRULE string
        """
        return recurring_event.to_rrule()

    def parse_rrule(self, rrule_string: str) -> Dict:
        """Parse iCal RRULE into dictionary.

        Args:
            rrule_string: RRULE string (e.g., "FREQ=WEEKLY;INTERVAL=2;BYDAY=MO,WE,FR")

        Returns:
            Dictionary with recurrence parameters
        """
        parts = rrule_string.split(";")
        rule_dict = {}

        for part in parts:
            if "=" in part:
                key, value = part.split("=", 1)
                rule_dict[key] = value

        # Map FREQ to recurrence_type
        freq_map = {
            "DAILY": "daily",
            "WEEKLY": "weekly",
            "MONTHLY": "monthly",
            "YEARLY": "yearly",
        }

        result = {
            "recurrence_type": freq_map.get(
                rule_dict.get("FREQ", "DAILY"), "daily"
            ),
            "interval": int(rule_dict.get("INTERVAL", 1)),
            "days_of_week": None,
            "day_of_month": None,
            "max_occurrences": None,
            "end_date": None,
        }

        # Parse BYDAY
        if "BYDAY" in rule_dict:
            day_map = {
                "MO": 0,
                "TU": 1,
                "WE": 2,
                "TH": 3,
                "FR": 4,
                "SA": 5,
                "SU": 6,
            }
            days = [
                str(day_map.get(d, 0)) for d in rule_dict["BYDAY"].split(",")
            ]
            result["days_of_week"] = ",".join(days)

        # Parse BYMONTHDAY
        if "BYMONTHDAY" in rule_dict:
            result["day_of_month"] = int(rule_dict["BYMONTHDAY"])

        # Parse COUNT
        if "COUNT" in rule_dict:
            result["max_occurrences"] = int(rule_dict["COUNT"])

        # Parse UNTIL
        if "UNTIL" in rule_dict:
            # Parse iCal datetime format
            until_str = rule_dict["UNTIL"]
            try:
                result["end_date"] = datetime.strptime(
                    until_str, "%Y%m%dT%H%M%SZ"
                )
            except ValueError:
                try:
                    result["end_date"] = datetime.strptime(until_str, "%Y%m%d")
                except ValueError:
                    pass

        return result


# Convenience functions
def export_events_to_file(events: List[Event], file_path: str) -> None:
    """Export events to .ics file.

    Args:
        events: List of Event objects
        file_path: Path to output .ics file
    """
    integration = ICalIntegration()
    ical_data = integration.export_to_ical(events)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(ical_data)


def import_events_from_file(file_path: str) -> List[Dict]:
    """Import events from .ics file.

    Args:
        file_path: Path to .ics file

    Returns:
        List of event data dictionaries
    """
    integration = ICalIntegration()

    with open(file_path, "r", encoding="utf-8") as f:
        ical_data = f.read()

    return integration.import_from_ical(ical_data)
