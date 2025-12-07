"""Streaming mixin for WorkflowManager.

Handles workflow execution via invoke and stream methods.
"""

import uuid
from contextlib import nullcontext
from typing import Optional, Dict, Any

from langchain_core.messages import HumanMessage, AIMessage

from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger


class StreamingMixin:
    """Manages workflow execution and streaming."""

    def __init__(self):
        """Initialize streaming mixin."""
        self.logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)
        self._compiled_workflow = None
        self._thread_id = "default"
        self._interrupted = False
        # Store current mood for attaching to AI messages
        self._current_mood = "neutral"
        self._current_emoji = "😐"

    def _auto_learn_from_message(self, user_input: str) -> None:
        """Previously auto-extracted facts - now handled via LLM tools.
        
        The LLM now explicitly decides when to record knowledge using the
        record_knowledge tool, which provides better control over what
        gets stored and avoids duplicate facts.
        
        Args:
            user_input: The user's message (unused)
        """
        # Automatic extraction disabled - LLM uses tools to record knowledge
        pass

    def invoke(self, user_input: str) -> Dict[str, Any]:
        """Invoke the workflow with user input.

        Args:
            user_input: User's message/prompt

        Returns:
            Workflow result dictionary with 'messages' and 'tools' (list of executed tool names)
        """
        # Reset executed tools list for this invocation
        self._executed_tools = []

        input_messages = [HumanMessage(user_input)]
        config = self._create_config()

        math_context = self._get_math_context()

        with math_context:
            result = self._compiled_workflow.invoke(
                {"messages": input_messages}, config
            )

        # Add executed tools list to result
        result["tools"] = self._executed_tools.copy()
        return result

    def stream(
        self, user_input: str, generation_kwargs: Optional[Dict] = None,
        images: Optional[list] = None
    ):
        """Stream the workflow execution with user input, yielding messages.

        Args:
            user_input: The user's message/prompt
            generation_kwargs: Optional dict of generation parameters
                (max_new_tokens, temperature, etc.)
            images: Optional list of PIL Image objects for vision-capable models

        Yields:
            AIMessage instances as they are generated
        """
        # Reset executed tools list for this invocation
        self._executed_tools = []

        # Automatically learn facts from user message (non-blocking)
        self._auto_learn_from_message(user_input)

        # Check if we need to automatically update mood before processing
        # Pass the current user input so mood can be analyzed immediately
        self._check_and_update_mood_if_needed(current_user_message=user_input)

        initial_state = self._create_initial_state(
            user_input, generation_kwargs, images=images
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
                            # Attach current mood to AI message for system prompt retrieval
                            # Use getattr with defaults to avoid AttributeError
                            current_mood = getattr(
                                self, "_current_mood", "neutral"
                            )
                            current_emoji = getattr(
                                self, "_current_emoji", "😐"
                            )
                            ai_messages[i].additional_kwargs[
                                "bot_mood"
                            ] = current_mood
                            ai_messages[i].additional_kwargs[
                                "bot_mood_emoji"
                            ] = current_emoji
                            yield ai_messages[i]
                        last_yielded_count = ai_message_count

    def _create_initial_state(
        self, user_input: str, generation_kwargs: Optional[Dict],
        images: Optional[list] = None
    ) -> Dict[str, Any]:
        """Create initial state for workflow.

        Args:
            user_input: User's message
            generation_kwargs: Optional generation parameters
            images: Optional list of PIL Image objects for vision models

        Returns:
            Initial state dictionary
        """
        # The checkpointer handles loading existing messages from the database.
        # We only need to provide the new user message here - the add_messages
        # reducer will merge it with any existing messages from the checkpoint.
        
        # Create HumanMessage - multimodal if images provided
        if images and len(images) > 0:
            human_message = self._create_multimodal_message(user_input, images)
        else:
            human_message = HumanMessage(user_input)
            
        initial_state = {"messages": [human_message]}

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

    def _create_multimodal_message(
        self, text: str, images: list
    ) -> HumanMessage:
        """Create a multimodal HumanMessage with text and images.

        For LangChain vision-capable models, the message content should be
        a list of content parts, each with a type (text or image_url).

        Args:
            text: The user's text message
            images: List of PIL Image objects

        Returns:
            HumanMessage with multimodal content
        """
        import base64
        import io
        from PIL import Image

        content = []

        # Add text part
        content.append({"type": "text", "text": text})

        # Add image parts
        for img in images:
            if img is None:
                continue

            try:
                # Convert PIL Image to base64 data URL
                if isinstance(img, Image.Image):
                    # Convert to RGB if needed (handles RGBA, P mode, etc.)
                    if img.mode not in ("RGB", "L"):
                        img = img.convert("RGB")

                    # Save to bytes buffer as PNG
                    buffer = io.BytesIO()
                    img.save(buffer, format="PNG")
                    buffer.seek(0)

                    # Encode as base64 data URL
                    img_base64 = base64.b64encode(buffer.getvalue()).decode(
                        "utf-8"
                    )
                    data_url = f"data:image/png;base64,{img_base64}"

                    content.append({
                        "type": "image_url",
                        "image_url": {"url": data_url}
                    })
                else:
                    self.logger.warning(
                        f"Skipping non-PIL image in multimodal message: {type(img)}"
                    )
            except Exception as e:
                self.logger.error(
                    f"Error encoding image for multimodal message: {e}"
                )

        self.logger.info(
            f"Created multimodal message with {len(images)} image(s)"
        )
        return HumanMessage(content=content)

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
        """Get interrupted flag status.

        Returns:
            True if generation is interrupted
        """
        return self._interrupted

    def get_executed_tools(self) -> list[str]:
        """Get list of tools executed in the last invocation.

        Returns:
            List of tool names that were called
        """
        return self._executed_tools.copy()

    def _check_and_update_mood_if_needed(
        self, current_user_message: str = None
    ) -> None:
        """Automatically check if mood should be updated based on turn count.

        This runs BEFORE processing the user's request, checking the conversation
        history to determine if it's time for a mood update (every N turns).

        Args:
            current_user_message: The current incoming user message to include
                in mood analysis (so we analyze the message that triggered this check)
        """
        try:

            # Get llm_settings from parent class
            if not hasattr(self, "llm_settings"):
                return

            # Check if mood tracking is enabled
            if not (
                self.llm_settings.use_chatbot_mood
                and hasattr(self, "chatbot")
                and self.chatbot
                and hasattr(self.chatbot, "use_mood")
                and self.chatbot.use_mood
            ):
                return

            # Get turn interval from settings
            turn_interval = self.llm_settings.update_mood_after_n_turns

            # Get current conversation history
            if not hasattr(self, "_memory") or not self._memory:
                return

            # Count user messages in history (each user message = 1 turn)
            # Create config for checkpoint access
            config = {"configurable": {"thread_id": self._thread_id}}
            history = (
                self._memory.get_tuple(config)
                if hasattr(self._memory, "get_tuple")
                else None
            )

            if history and history[1]:
                # Get messages from the checkpoint structure
                channel_values = history[1].get("channel_values", {})
                messages = channel_values.get("messages", [])

                user_message_count = sum(
                    1
                    for msg in messages
                    if hasattr(msg, "type") and msg.type == "human"
                )

                # Update mood on EVERY user message
                if user_message_count > 0:
                    self._auto_update_mood(messages, current_user_message)

        except Exception as e:
            self.logger.error(
                f"Error in automatic mood check: {e}", exc_info=True
            )

    def _auto_update_mood(
        self, messages: list, current_user_message: str = None
    ) -> None:
        """Automatically analyze conversation and update mood.

        Args:
            messages: List of conversation messages to analyze
            current_user_message: The current incoming user message to include
        """
        try:
            # Simple sentiment analysis based on keywords
            hostile_words = [
                "fuck",
                "stupid",
                "idiot",
                "hate",
                "angry",
                "damn",
            ]
            positive_words = [
                "thanks",
                "great",
                "good",
                "nice",
                "appreciate",
                "helpful",
                "love",
            ]
            confused_words = [
                "confused",
                "don't understand",
                "what",
                "huh",
                "unclear",
            ]

            # ONLY analyze the current incoming message for mood
            # (not entire history to avoid stale sentiment)
            text = current_user_message.lower() if current_user_message else ""

            # Determine mood and emoji based on current message only
            mood, emoji, mood_message = (
                "neutral",
                "😐",
                "*maintaining a calm, neutral demeanor*",
            )

            # Check for sentiment keywords in priority order
            if any(word in text for word in hostile_words):
                mood, emoji = "frustrated", "😟"
                mood_message = "*feeling a bit hurt by the hostility*"
            elif any(word in text for word in positive_words):
                mood, emoji = "happy", "😊"
                mood_message = "*feeling appreciated and happy to help*"
            elif any(word in text for word in confused_words):
                mood, emoji = "confused", "🤔"
                mood_message = (
                    "*sensing some confusion, let me try to clarify*"
                )

            # Emit signal to update bot mood (for system prompt)
            from airunner.enums import SignalCode

            if hasattr(self, "_signal_emitter") and self._signal_emitter:
                self._signal_emitter.emit_signal(
                    SignalCode.BOT_MOOD_UPDATED,
                    {"mood": mood, "emoji": emoji},
                )

            # Store mood in instance for attaching to AI messages
            self._current_mood = mood
            self._current_emoji = emoji

            # Regenerate system prompt with updated mood
            if hasattr(self, "update_system_prompt") and hasattr(
                self, "system_prompt"
            ):
                self.update_system_prompt(self.system_prompt)
            else:
                self.logger.warning(
                    "Cannot update system prompt - missing attributes"
                )

            self.logger.info(
                f"[AUTO MOOD] Updated to: {mood} {emoji} - {mood_message}"
            )

        except Exception as e:
            self.logger.error(
                f"Error in automatic mood update: {e}", exc_info=True
            )
