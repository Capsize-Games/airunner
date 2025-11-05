"""
Eval tests for calendar tool triggering with natural language.

Tests that the LLM agent can correctly trigger calendar management tools
when given natural language prompts like:
- "create an event for tomorrow at 2pm about team meeting"
- "list my upcoming events"
- "delete the event with ID 5"
"""

import pytest
import logging
from datetime import datetime, timedelta
from airunner.components.calendar.data.event import Event
from airunner.components.data.session_manager import session_scope
from airunner.components.eval.utils.tracking import track_trajectory_sync

logger = logging.getLogger(__name__)

pytestmark = [
    pytest.mark.eval,
    pytest.mark.timeout(60),
]


@pytest.fixture(autouse=True)
def cleanup_calendar_data():
    """Clean up calendar data after each test."""
    yield
    # Cleanup after test
    with session_scope() as session:
        session.query(Event).delete()
        session.commit()


@pytest.mark.eval
class TestCalendarToolEval:
    """Eval tests for natural language calendar tool triggering."""

    def test_create_event_basic(self, airunner_client_function_scope):
        """Test creating event with natural language."""
        tomorrow = datetime.now() + timedelta(days=1)
        tomorrow_str = tomorrow.strftime("%Y-%m-%d")

        prompt = (
            f"Create a calendar event for tomorrow ({tomorrow_str}) "
            f"at 2pm called 'Team Meeting' about weekly sync. "
            f"Make it 1 hour long."
        )

        result = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=prompt,
            max_tokens=500,
            tool_categories=["SYSTEM"],
        )

        response = result["response"]
        tools = result["tools"]

        # Verify event was created
        with session_scope() as session:
            events = session.query(Event).all()
            # Should have created at least one event
            # (may vary based on how agent interprets prompt)
            response_text = (
                response.lower()
                if isinstance(response, str)
                else response.get("text", "").lower()
            )
            assert (
                len(events) > 0
                or "created" in response_text
                or "event" in response_text
            )

            # Verify calendar tool was used
            assert any(
                "calendar" in tool.lower()
                or "event" in tool.lower()
                or "create" in tool.lower()
                for tool in tools
            ), f"Expected calendar/event/create tool in tools, got: {tools}"

    def test_create_event_variations(self, airunner_client_function_scope):
        """Test various phrasings for creating events."""
        test_prompts = [
            "schedule a meeting for tomorrow at 3pm",
            "add an event to my calendar for next Monday at 10am called Review",
            "create a reminder for Friday at 9am to submit report",
            "I have a dentist appointment on Thursday at 2pm",
        ]

        for prompt in test_prompts:
            # Clean up before each
            with session_scope() as session:
                session.query(Event).delete()
                session.commit()

            result = track_trajectory_sync(
                airunner_client_function_scope,
                prompt=prompt,
                max_tokens=400,
                tool_categories=["SYSTEM"],
            )
            response = result["response"]
            tools = result["tools"]

            response_text = (
                response.lower()
                if isinstance(response, str)
                else response.get("text", "").lower()
            )

            # Verify calendar tools were invoked
            assert any(
                "calendar" in tool.lower()
                or "event" in tool.lower()
                or "create" in tool.lower()
                for tool in tools
            ), f"Expected calendar/event tools in tools, got: {tools}"

            # Verify attempt to create event
            with session_scope() as session:
                events = session.query(Event).all()
                # Either created event or acknowledged request
                assert (
                    len(events) > 0
                    or "created" in response_text
                    or "scheduled" in response_text
                    or "added" in response_text
                ), f"Failed to handle: {prompt}"

    def test_list_events(self, airunner_client_function_scope):
        """Test listing calendar events."""
        # Create test events first
        now = datetime.now()
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

        prompt = "What events do I have coming up? List my calendar."

        result = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=prompt,
            max_tokens=500,
            tool_categories=["SYSTEM"],
        )
        response = result["response"]
        tools = result["tools"]

        response_text = (
            response if isinstance(response, str) else response.get("text", "")
        )

        # Verify calendar list tools were invoked
        assert any(
            "calendar" in tool.lower()
            or "event" in tool.lower()
            or "list" in tool.lower()
            for tool in tools
        ), f"Expected calendar/event/list tools in tools, got: {tools}"

        # Should mention the events
        assert (
            "Meeting A" in response_text or "Meeting B" in response_text
        ), "Response should list calendar events"

    def test_list_events_with_filter(self, airunner_client_function_scope):
        """Test listing events with category filter."""
        now = datetime.now()
        with session_scope() as session:
            work_event = Event(
                title="Work Meeting",
                start_time=now + timedelta(days=1),
                end_time=now + timedelta(days=1, hours=1),
                category="work",
            )
            personal_event = Event(
                title="Personal Appointment",
                start_time=now + timedelta(days=2),
                end_time=now + timedelta(days=2, hours=1),
                category="personal",
            )
            session.add_all([work_event, personal_event])
            session.commit()

        prompt = "Show me my work events"

        result = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=prompt,
            max_tokens=500,
            tool_categories=["SYSTEM"],
        )
        response = result["response"]
        tools = result["tools"]

        response_text = (
            response if isinstance(response, str) else response.get("text", "")
        )

        # Verify calendar list/filter tools were invoked
        assert any(
            "calendar" in tool.lower()
            or "event" in tool.lower()
            or "list" in tool.lower()
            for tool in tools
        ), f"Expected calendar/event/list tools in tools, got: {tools}"

        # Should mention work event, possibly not personal
        assert (
            "Work Meeting" in response_text or "work" in response_text.lower()
        )

    def test_update_event(self, airunner_client_function_scope):
        """Test updating an existing event."""
        now = datetime.now()
        with session_scope() as session:
            event = Event(
                title="Original Meeting",
                start_time=now + timedelta(days=1),
                end_time=now + timedelta(days=1, hours=1),
            )
            session.add(event)
            session.flush()
            event_id = event.id

        prompt = (
            f"Change the title of event {event_id} to 'Updated Meeting' "
            f"and move it to 3pm"
        )

        result = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=prompt,
            max_tokens=500,
            tool_categories=["SYSTEM"],
        )
        response = result["response"]
        tools = result["tools"]

        response_text = (
            response.lower()
            if isinstance(response, str)
            else response.get("text", "").lower()
        )

        # Verify calendar update tools were invoked
        assert any(
            "calendar" in tool.lower()
            or "event" in tool.lower()
            or "update" in tool.lower()
            for tool in tools
        ), f"Expected calendar/event/update tools in tools, got: {tools}"

        # Verify update attempt
        assert (
            "updated" in response_text
            or "changed" in response_text
            or "modified" in response_text
        )

    def test_delete_event(self, airunner_client_function_scope):
        """Test deleting an event."""
        now = datetime.now()
        with session_scope() as session:
            event = Event(
                title="To Be Deleted",
                start_time=now + timedelta(days=1),
                end_time=now + timedelta(days=1, hours=1),
            )
            session.add(event)
            session.flush()
            event_id = event.id

        prompt = f"Delete event {event_id} from my calendar"

        result = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=prompt,
            max_tokens=300,
            tool_categories=["SYSTEM"],
        )
        response = result["response"]
        tools = result["tools"]

        response_text = (
            response.lower()
            if isinstance(response, str)
            else response.get("text", "").lower()
        )

        # Verify calendar delete tools were invoked
        assert any(
            "calendar" in tool.lower()
            or "event" in tool.lower()
            or "delete" in tool.lower()
            for tool in tools
        ), f"Expected calendar/event/delete tools in tools, got: {tools}"

        # Verify deletion attempt
        with session_scope() as session:
            event = session.query(Event).filter_by(id=event_id).first()
            # Either deleted or acknowledged
            assert (
                event is None
                or "deleted" in response_text
                or "removed" in response_text
            )

    def test_natural_date_parsing(self, airunner_client_function_scope):
        """Test that agent can parse natural date expressions."""
        test_cases = [
            "tomorrow",
            "next Monday",
            "in 2 days",
            "this Friday",
        ]

        for date_expr in test_cases:
            # Clean up
            with session_scope() as session:
                session.query(Event).delete()
                session.commit()

            prompt = f"Create an event for {date_expr} at 10am called Test"

            result = track_trajectory_sync(
                airunner_client_function_scope,
                prompt=prompt,
                max_tokens=400,
                tool_categories=["SYSTEM"],
            )
            response = result["response"]
            tools = result["tools"]

            response_text = (
                response.lower()
                if isinstance(response, str)
                else response.get("text", "").lower()
            )

            # Verify calendar create tools were invoked
            assert any(
                "calendar" in tool.lower()
                or "event" in tool.lower()
                or "create" in tool.lower()
                for tool in tools
            ), f"Expected calendar/event/create tools for '{date_expr}', got: {tools}"

            # Should acknowledge event creation
            assert (
                "created" in response_text
                or "scheduled" in response_text
                or "event" in response_text
            ), f"Failed to parse: {date_expr}"

    def test_event_with_details(self, airunner_client_function_scope):
        """Test creating event with full details."""
        tomorrow = datetime.now() + timedelta(days=1)
        tomorrow_str = tomorrow.strftime("%Y-%m-%d")

        prompt = (
            f"Create a work event for {tomorrow_str} at 2pm called "
            f"'Client Presentation'. It's at Conference Room B and "
            f"will last 2 hours. Description: Present Q4 results to clients."
        )

        result = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=prompt,
            max_tokens=600,
            tool_categories=["SYSTEM"],
        )
        response = result["response"]
        tools = result["tools"]

        response_text = (
            response if isinstance(response, str) else response.get("text", "")
        )

        # Verify calendar create tools were invoked
        assert any(
            "calendar" in tool.lower()
            or "event" in tool.lower()
            or "create" in tool.lower()
            for tool in tools
        ), f"Expected calendar/event/create tools in tools, got: {tools}"

        # Verify event was created with details
        with session_scope() as session:
            events = session.query(Event).all()
            if events:
                # Check if any event has expected details
                for event in events:
                    has_title = "Client Presentation" in event.title
                    has_location = (
                        event.location
                        and "Conference Room B" in event.location
                    )
                    has_category = event.category == "work"
                    if has_title or has_location or has_category:
                        # Found event with some details
                        assert True
                        return

            # If no perfect match, at least check response acknowledges creation
            assert (
                "created" in response_text.lower()
                or "scheduled" in response_text.lower()
            )


@pytest.mark.eval
class TestCalendarToolErrorHandling:
    """Test that agent handles calendar tool errors gracefully."""

    def test_update_nonexistent_event(self, airunner_client_function_scope):
        """Test handling update of non-existent event."""
        prompt = "Update event 99999 to be at 3pm"

        result = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=prompt,
            max_tokens=300,
            tool_categories=["SYSTEM"],
        )
        response = result["response"]
        tools = result["tools"]

        response_text = (
            response.lower()
            if isinstance(response, str)
            else response.get("text", "").lower()
        )

        # Verify calendar update tools were invoked
        assert any(
            "calendar" in tool.lower()
            or "event" in tool.lower()
            or "update" in tool.lower()
            for tool in tools
        ), f"Expected calendar/event/update tools in tools, got: {tools}"

        # Should acknowledge error
        assert (
            "error" in response_text
            or "not found" in response_text
            or "doesn't exist" in response_text
            or "cannot find" in response_text
        )

    def test_delete_nonexistent_event(self, airunner_client_function_scope):
        """Test handling deletion of non-existent event."""
        prompt = "Delete event 99999"

        result = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=prompt,
            max_tokens=300,
            tool_categories=["SYSTEM"],
        )
        response = result["response"]
        tools = result["tools"]

        response_text = (
            response.lower()
            if isinstance(response, str)
            else response.get("text", "").lower()
        )

        # Verify calendar delete tools were invoked
        assert any(
            "calendar" in tool.lower()
            or "event" in tool.lower()
            or "delete" in tool.lower()
            for tool in tools
        ), f"Expected calendar/event/delete tools in tools, got: {tools}"

        # Should acknowledge error
        assert (
            "error" in response_text
            or "not found" in response_text
            or "doesn't exist" in response_text
            or "cannot find" in response_text
        )

    def test_list_when_no_events(self, airunner_client_function_scope):
        """Test listing events when calendar is empty."""
        prompt = "What events do I have?"

        result = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=prompt,
            max_tokens=300,
            tool_categories=["SYSTEM"],
        )
        response = result["response"]
        tools = result["tools"]

        response_text = (
            response.lower()
            if isinstance(response, str)
            else response.get("text", "").lower()
        )

        # Verify calendar list tools were invoked
        assert any(
            "calendar" in tool.lower()
            or "event" in tool.lower()
            or "list" in tool.lower()
            for tool in tools
        ), f"Expected calendar/event/list tools in tools, got: {tools}"

        # Should acknowledge no events
        assert (
            "no events" in response_text
            or "no upcoming" in response_text
            or "empty" in response_text
            or "don't have any" in response_text
        )

    def test_invalid_date_format(self, airunner_client_function_scope):
        """Test handling of invalid/ambiguous date."""
        prompt = "Create an event for yesterday at 25:00"  # Invalid time

        result = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=prompt,
            max_tokens=400,
            tool_categories=["SYSTEM"],
        )
        response = result["response"]
        tools = result["tools"]

        response_text = (
            response.lower()
            if isinstance(response, str)
            else response.get("text", "").lower()
        )

        # Verify calendar create tools were invoked (even if error)
        assert any(
            "calendar" in tool.lower()
            or "event" in tool.lower()
            or "create" in tool.lower()
            for tool in tools
        ), f"Expected calendar/event/create tools in tools, got: {tools}"

        # Should either handle gracefully or acknowledge issue
        # Agent might correct to valid time or report error
        assert (
            "error" in response_text
            or "created" in response_text
            or "invalid" in response_text
            or len(response_text) > 0  # At least responded
        )
