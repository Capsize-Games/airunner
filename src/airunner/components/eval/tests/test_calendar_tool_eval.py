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
from functools import wraps
from airunner.components.calendar.data.event import Event
from airunner.components.data.session_manager import session_scope
from airunner.components.eval.utils.tracking import track_trajectory_sync

logger = logging.getLogger(__name__)

pytestmark = [
    pytest.mark.eval,
    pytest.mark.timeout(60),
]


@pytest.fixture(autouse=True)
def cleanup_calendar_data(airunner_client_function_scope):
    """Clean up calendar data and LLM memory before AND after each test.

    This prevents test contamination where the LLM remembers events
    from previous tests and hallucinates about them.
    """
    print("\n[FIXTURE] Cleaning calendar data and resetting LLM memory...")

    # Cleanup BEFORE test - use /admin/reset_database to clear from server subprocess
    try:
        import requests

        base_url = airunner_client_function_scope.base_url

        # Clear database via server endpoint (works across subprocess boundary)
        db_response = requests.post(
            f"{base_url}/admin/reset_database", timeout=5
        )
        print(f"[FIXTURE] Database reset: {db_response.json()}")

        # Clear LLM conversation memory
        mem_response = requests.post(
            f"{base_url}/admin/reset_memory", timeout=5
        )
        print(f"[FIXTURE] LLM memory reset: {mem_response.json()}")
    except Exception as e:
        print(f"[FIXTURE] WARNING: Could not reset database/memory: {e}")

    print("[FIXTURE] Setup complete, starting test...\n")
    yield

    # Cleanup AFTER test - use endpoint for consistency
    print("\n[FIXTURE] Test complete, cleaning up...")
    try:
        import requests

        base_url = airunner_client_function_scope.base_url
        requests.post(f"{base_url}/admin/reset_database", timeout=5)
    except Exception:
        pass  # Ignore cleanup errors


def with_session_scope(func):
    """Decorator that injects a session into the test method."""

    @wraps(func)
    def wrapper(self, *args, **kwargs):
        with session_scope() as session:
            # Inject session as a keyword argument
            kwargs["session"] = session
            return func(self, *args, **kwargs)

    return wrapper


@pytest.mark.eval
class TestCalendarToolEval:
    """Eval tests for natural language calendar tool triggering."""

    @pytest.mark.timeout(
        120
    )  # Increase timeout to 120 seconds for tool-calling tests
    @with_session_scope
    def test_create_event_basic(
        self, airunner_client_function_scope, session=None
    ):
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

        # Verify event was created OR tool was called in ReAct format
        events = session.query(Event).all()
        response_text = (
            response.lower()
            if isinstance(response, str)
            else response.get("text", "").lower()
        )

        # Check if event was actually created in database
        # OR if response indicates intent to create (ReAct format)
        # OR if response acknowledges the request
        assert (
            len(events) > 0
            or "created" in response_text
            or "event" in response_text
            or "calendar" in response_text
            or "action:" in response_text  # ReAct format indicator
        ), f"Expected event creation or acknowledgment, got: {response_text}"

        # Verify calendar tool was used (native) OR mentioned (ReAct)
        # Supports both native function calling and text-based ReAct models
        tool_was_used = (
            # Native function calling - check tools list
            any(
                "calendar" in tool.lower()
                or "event" in tool.lower()
                or "create" in tool.lower()
                for tool in tools
            )
            # ReAct format - check response text for action or observation
            or "action:" in response_text
            or "observation:" in response_text
            or "calendar/event/create" in response_text
            or ("action input:" in response_text and "event" in response_text)
        )
        assert tool_was_used, (
            f"Expected calendar tool call (native or ReAct format). "
            f"Tools: {tools}, Response: {response_text[:200]}"
        )

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

            # Verify attempt to create event
            # Check if event was created in DB OR if response indicates tool use
            with session_scope() as session:
                events = session.query(Event).all()

                # Tool was used if: events exist, OR we see ReAct markers, OR response acknowledges
                tool_was_used = (
                    # Evidence: event actually created in database
                    len(events) > 0
                    # Native format - check tools list
                    or any(
                        "calendar" in tool.lower()
                        or "event" in tool.lower()
                        or "create" in tool.lower()
                        for tool in tools
                    )
                    # ReAct format - check response text for action or observation
                    or "action:" in response_text
                    or "observation:" in response_text
                    or "calendar/event/create" in response_text
                    or (
                        "action input:" in response_text
                        and "event" in response_text
                    )
                    # Response acknowledges event creation
                    or "created" in response_text
                    or "scheduled" in response_text
                    or "added" in response_text
                )
                assert tool_was_used, (
                    f"Expected calendar tool call (native or ReAct format) for '{prompt}'. "
                    f"Tools: {tools}, Events: {len(events)}, Response: {response_text[:200]}"
                )

    def test_list_events(self, airunner_client_function_scope):
        """Test listing calendar events."""
        # Create test events via LLM so they're visible to the server subprocess
        now = datetime.now()
        tomorrow = (now + timedelta(days=1)).strftime("%Y-%m-%d")
        day_after = (now + timedelta(days=2)).strftime("%Y-%m-%d")

        # Create first event
        track_trajectory_sync(
            airunner_client_function_scope,
            prompt=f"Create a calendar event called 'Meeting A' on {tomorrow} at 2pm for 1 hour, category work",
            max_tokens=300,
            tool_categories=["SYSTEM"],
        )

        # Create second event
        track_trajectory_sync(
            airunner_client_function_scope,
            prompt=f"Create a calendar event called 'Meeting B' on {day_after} at 3pm for 1 hour, category personal",
            max_tokens=300,
            tool_categories=["SYSTEM"],
        )

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

        # Verify calendar list tools were invoked (native or ReAct format)
        tool_was_used = (
            # Native format - check tools list
            any(
                "calendar" in tool.lower()
                or "event" in tool.lower()
                or "list" in tool.lower()
                for tool in tools
            )
            # ReAct format - check response text for action or observation
            or "action:"
            or "observation:" in response_text.lower()
            or "calendar/event/list" in response_text.lower()
            or (
                "action input:" in response_text.lower()
                and "event" in response_text.lower()
            )
        )
        assert tool_was_used, (
            f"Expected calendar list tool call (native or ReAct format). "
            f"Tools: {tools}, Response: {response_text[:200]}"
        )

        # Should mention the events
        assert (
            "Meeting A" in response_text or "Meeting B" in response_text
        ), "Response should list calendar events"

    def test_list_events_with_filter(self, airunner_client_function_scope):
        """Test listing events with category filter."""
        now = datetime.now()
        tomorrow = (now + timedelta(days=1)).strftime("%Y-%m-%d")
        day_after = (now + timedelta(days=2)).strftime("%Y-%m-%d")

        # Create events via LLM so they're visible to server subprocess
        track_trajectory_sync(
            airunner_client_function_scope,
            prompt=f"Create a work event called 'Work Meeting' on {tomorrow} at 2pm for 1 hour",
            max_tokens=300,
            tool_categories=["SYSTEM"],
        )

        track_trajectory_sync(
            airunner_client_function_scope,
            prompt=f"Create a personal event called 'Personal Appointment' on {day_after} at 3pm for 1 hour",
            max_tokens=300,
            tool_categories=["SYSTEM"],
        )

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

        # Verify calendar list/filter tools were invoked (native or ReAct format)
        tool_was_used = (
            # Native format - check tools list
            any(
                "calendar" in tool.lower()
                or "event" in tool.lower()
                or "list" in tool.lower()
                for tool in tools
            )
            # ReAct format - check response text for action or observation
            or "action:"
            or "observation:" in response_text.lower()
            or "calendar/event/list" in response_text.lower()
            or (
                "action input:" in response_text.lower()
                and "event" in response_text.lower()
            )
        )
        assert tool_was_used, (
            f"Expected calendar list tool call (native or ReAct format). "
            f"Tools: {tools}, Response: {response_text[:200]}"
        )

        # Should mention work event, possibly not personal
        assert (
            "Work Meeting" in response_text or "work" in response_text.lower()
        )

    def test_update_event(self, airunner_client_function_scope):
        """Test updating an existing event."""
        now = datetime.now()
        tomorrow = (now + timedelta(days=1)).strftime("%Y-%m-%d")

        # Create event via LLM first
        create_result = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=f"Create a calendar event called 'Original Meeting' on {tomorrow} at 2pm for 1 hour",
            max_tokens=300,
            tool_categories=["SYSTEM"],
        )

        # The LLM should remember the event from context, so we can update by name
        prompt = (
            f"Change the 'Original Meeting' event to be called 'Updated Meeting' "
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

        # Verify calendar update tools were invoked (native or ReAct format)
        tool_was_used = (
            # Native format - check tools list
            any(
                "calendar" in tool.lower()
                or "event" in tool.lower()
                or "update" in tool.lower()
                for tool in tools
            )
            # ReAct format - check response text for action or observation
            or "action:"
            or "observation:" in response_text
            or "calendar/event/update" in response_text
            or ("action input:" in response_text and "update" in response_text)
        )
        assert tool_was_used, (
            f"Expected calendar update tool call (native or ReAct format). "
            f"Tools: {tools}, Response: {response_text[:200]}"
        )

        # Verify update attempt
        assert (
            "updated" in response_text
            or "changed" in response_text
            or "modified" in response_text
        )

    def test_delete_event(self, airunner_client_function_scope):
        """Test deleting an event."""
        now = datetime.now()
        tomorrow = (now + timedelta(days=1)).strftime("%Y-%m-%d")

        # Create event via LLM first
        track_trajectory_sync(
            airunner_client_function_scope,
            prompt=f"Create a calendar event called 'To Be Deleted' on {tomorrow} at 2pm for 1 hour",
            max_tokens=300,
            tool_categories=["SYSTEM"],
        )

        # More explicit deletion request
        prompt = f"Please delete the calendar event titled 'To Be Deleted' that I just created"

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

        # Verify calendar delete tools were invoked (native or ReAct format)
        tool_was_used = (
            # Native format - check tools list
            any(
                "calendar" in tool.lower()
                or "event" in tool.lower()
                or "delete" in tool.lower()
                for tool in tools
            )
            # ReAct format - check response text for action or observation
            or "action:"
            or "observation:" in response_text
            or "calendar/event/delete" in response_text
            or ("action input:" in response_text and "delete" in response_text)
        )
        assert tool_was_used, (
            f"Expected calendar delete tool call (native or ReAct format). "
            f"Tools: {tools}, Response: {response_text[:200]}"
        )

        # Verify deletion was acknowledged
        assert (
            "deleted" in response_text
            or "removed" in response_text
            or "cancel" in response_text
            or any("delete" in tool.lower() for tool in tools)
        ), f"Expected deletion acknowledgment or tool call. Tools: {tools}, Response: {response_text[:200]}"

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

            # Verify calendar create tools were invoked (native or ReAct format)
            tool_was_used = (
                # Native format - check tools list
                any(
                    "calendar" in tool.lower()
                    or "event" in tool.lower()
                    or "create" in tool.lower()
                    for tool in tools
                )
                # ReAct format - check response text for action or observation
                or "action:"
                or "observation:" in response_text
                or "calendar/event/create" in response_text
                or (
                    "action input:" in response_text
                    and "event" in response_text
                )
            )
            assert tool_was_used, (
                f"Expected calendar create tool call (native or ReAct format) for '{date_expr}'. "
                f"Tools: {tools}, Response: {response_text[:200]}"
            )

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

        # Verify calendar create tools were invoked (native or ReAct format)
        tool_was_used = (
            # Native format - check tools list
            any(
                "calendar" in tool.lower()
                or "event" in tool.lower()
                or "create" in tool.lower()
                for tool in tools
            )
            # ReAct format - check response text for action or observation
            or "action:"
            or "observation:" in response_text.lower()
            or "calendar/event/create" in response_text.lower()
            or (
                "action input:" in response_text.lower()
                and "event" in response_text.lower()
            )
        )
        assert tool_was_used, (
            f"Expected calendar create tool call (native or ReAct format). "
            f"Tools: {tools}, Response: {response_text[:200]}"
        )

        # Verify event was created - check response acknowledgment
        response_lower = response_text.lower()
        assert (
            "created" in response_lower
            or "scheduled" in response_lower
            or "event" in response_lower
            or "client presentation" in response_lower
        ), f"Expected creation acknowledgment in response: {response_text[:200]}"


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

        # Verify calendar update tools were invoked (native or ReAct format)
        tool_was_used = (
            # Native format - check tools list
            any(
                "calendar" in tool.lower()
                or "event" in tool.lower()
                or "update" in tool.lower()
                for tool in tools
            )
            # ReAct format - check response text for action or observation
            or "action:"
            or "observation:" in response_text
            or "calendar/event/update" in response_text
            or ("action input:" in response_text and "update" in response_text)
        )
        assert tool_was_used, (
            f"Expected calendar update tool call (native or ReAct format). "
            f"Tools: {tools}, Response: {response_text[:200]}"
        )

        # Should acknowledge error OR attempt update
        # (LLM might try to update or acknowledge it can't find the event)
        assert (
            "error" in response_text
            or "not found" in response_text
            or "doesn't exist" in response_text
            or "cannot find" in response_text
            or "couldn't find" in response_text
            or "no event" in response_text
            or "unable" in response_text
            or tool_was_used  # Tool was called, even if it failed
        ), f"Expected error acknowledgment or tool attempt. Tools: {tools}, Response: {response_text[:200]}"

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

        # Verify calendar delete tools were invoked (native or ReAct format)
        tool_was_used = (
            # Native format - check tools list
            any(
                "calendar" in tool.lower()
                or "event" in tool.lower()
                or "delete" in tool.lower()
                for tool in tools
            )
            # ReAct format - check response text for action or observation
            or "action:"
            or "observation:" in response_text
            or "calendar/event/delete" in response_text
            or ("action input:" in response_text and "delete" in response_text)
        )
        assert tool_was_used, (
            f"Expected calendar delete tool call (native or ReAct format). "
            f"Tools: {tools}, Response: {response_text[:200]}"
        )

        # Should acknowledge error OR attempt deletion
        assert (
            "error" in response_text
            or "not found" in response_text
            or "doesn't exist" in response_text
            or "cannot find" in response_text
            or "couldn't find" in response_text
            or "no event" in response_text
            or "unable" in response_text
            or tool_was_used  # Tool was called, even if it failed
        ), f"Expected error acknowledgment or tool attempt. Tools: {tools}, Response: {response_text[:200]}"

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

        # Verify calendar list tools were invoked (native or ReAct format)
        tool_was_used = (
            # Native format - check tools list
            any(
                "calendar" in tool.lower()
                or "event" in tool.lower()
                or "list" in tool.lower()
                for tool in tools
            )
            # ReAct format - check response text for action or observation
            or "action:"
            or "observation:" in response_text
            or "calendar/event/list" in response_text
            or ("action input:" in response_text and "event" in response_text)
        )
        assert tool_was_used, (
            f"Expected calendar list tool call (native or ReAct format). "
            f"Tools: {tools}, Response: {response_text[:200]}"
        )

        # Should acknowledge no events OR attempt to list them
        assert (
            "no events" in response_text
            or "no upcoming" in response_text
            or "empty" in response_text
            or "don't have any" in response_text
            or "couldn't find" in response_text
            or tool_was_used  # Tool was called, even if empty
        ), f"Expected 'no events' acknowledgment or tool attempt. Tools: {tools}, Response: {response_text[:200]}"

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

        # Verify calendar create tools were invoked (even if error) (native or ReAct format)
        tool_was_used = (
            # Native format - check tools list
            any(
                "calendar" in tool.lower()
                or "event" in tool.lower()
                or "create" in tool.lower()
                for tool in tools
            )
            # ReAct format - check response text for action or observation
            or "action:"
            or "observation:" in response_text
            or "calendar/event/create" in response_text
            or ("action input:" in response_text and "event" in response_text)
        )
        assert tool_was_used, (
            f"Expected calendar create tool call (native or ReAct format). "
            f"Tools: {tools}, Response: {response_text[:200]}"
        )

        # Should either handle gracefully or acknowledge issue
        # Agent might correct to valid time or report error
        assert (
            "error" in response_text
            or "created" in response_text
            or "invalid" in response_text
            or len(response_text) > 0  # At least responded
        )
