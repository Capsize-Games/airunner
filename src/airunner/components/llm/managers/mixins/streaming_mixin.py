"""Streaming mixin for WorkflowManager.

Handles workflow execution via invoke and stream methods.
"""

import logging
import uuid
from contextlib import nullcontext
from typing import Optional, Dict, Any

from langchain_core.messages import HumanMessage, AIMessage


class StreamingMixin:
    """Manages workflow execution and streaming."""

    def __init__(self):
        """Initialize streaming mixin."""
        self.logger = logging.getLogger(__name__)
        self._compiled_workflow = None
        self._thread_id = "default"
        self._interrupted = False

    def invoke(self, user_input: str) -> Dict[str, Any]:
        """Invoke the workflow with user input.

        Args:
            user_input: User's message/prompt

        Returns:
            Workflow result dictionary
        """
        input_messages = [HumanMessage(user_input)]
        config = self._create_config()

        math_context = self._get_math_context()

        with math_context:
            return self._compiled_workflow.invoke(
                {"messages": input_messages}, config
            )

    def stream(
        self, user_input: str, generation_kwargs: Optional[Dict] = None
    ):
        """Stream the workflow execution with user input, yielding messages.

        Args:
            user_input: The user's message/prompt
            generation_kwargs: Optional dict of generation parameters
                (max_new_tokens, temperature, etc.)

        Yields:
            AIMessage instances as they are generated
        """
        initial_state = self._create_initial_state(
            user_input, generation_kwargs
        )
        config = self._create_config()

        math_context = self._get_math_context()
        last_yielded_count = 0  # Track how many messages we've yielded

        with math_context:
            for event in self._compiled_workflow.stream(
                initial_state,
                config,
                stream_mode="values",
            ):
                # Check interrupt flag on each event
                if self._interrupted:
                    break

                # Yield only NEW AI messages (not previously yielded)
                # Note: We don't filter by content because tool_calls may have empty content
                if self._has_ai_message(event):
                    messages = event["messages"]

                    # Only yield AIMessages we haven't yielded yet
                    # Count how many AIMessages are in the list
                    ai_message_count = sum(
                        1 for msg in messages if isinstance(msg, AIMessage)
                    )

                    print(
                        f"[STREAM DEBUG] Total messages: {len(messages)}, AI messages: {ai_message_count}, Already yielded: {last_yielded_count}",
                        flush=True,
                    )

                    # If there are more AIMessages than we've yielded, yield the new ones
                    if ai_message_count > last_yielded_count:
                        # Get all AIMessages
                        ai_messages = [
                            msg
                            for msg in messages
                            if isinstance(msg, AIMessage)
                        ]
                        # Yield only the ones we haven't yielded yet
                        for i in range(last_yielded_count, ai_message_count):
                            content_preview = (
                                ai_messages[i].content[:100]
                                if ai_messages[i].content
                                else "(empty)"
                            )
                            print(
                                f"[STREAM DEBUG] Yielding AI message #{i+1}: {content_preview}",
                                flush=True,
                            )
                            yield ai_messages[i]
                        last_yielded_count = ai_message_count

    def _create_initial_state(
        self, user_input: str, generation_kwargs: Optional[Dict]
    ) -> Dict[str, Any]:
        """Create initial state for workflow.

        Args:
            user_input: User's message
            generation_kwargs: Optional generation parameters

        Returns:
            Initial state dictionary
        """
        input_messages = [HumanMessage(user_input)]
        initial_state = {"messages": input_messages}

        if generation_kwargs:
            initial_state["generation_kwargs"] = generation_kwargs

        return initial_state

    def _create_config(self) -> Dict[str, Any]:
        """Create workflow configuration.

        Returns:
            Configuration dictionary
        """
        return {
            "configurable": {"thread_id": self._thread_id},
            "recursion_limit": 20,  # Prevent runaway tool loops
        }

    def _get_math_context(self):
        """Get math executor session context manager.

        Returns:
            Context manager for math executor session or nullcontext
        """
        try:
            from airunner.components.llm.tools.math_tools import (
                math_executor_session,
            )

            session_id = f"{self._thread_id}:{uuid.uuid4()}"
            return math_executor_session(session_id)
        except ImportError:
            return nullcontext()

    def _has_ai_message(self, event: Dict) -> bool:
        """Check if event contains messages.

        Args:
            event: Stream event dictionary

        Returns:
            True if event has messages
        """
        return "messages" in event and event["messages"]

    def set_interrupted(self, value: bool) -> None:
        """Set the interrupted flag to stop generation.

        Args:
            value: True to interrupt, False to resume
        """
        self._interrupted = value
        if value:
            self.logger.info("Workflow interrupted flag set")

    def is_interrupted(self) -> bool:
        """Check if generation has been interrupted.

        Returns:
            True if interrupted
        """
        return self._interrupted
