"""System prompt generation for LLM models.

This mixin provides:
- Base system prompt construction
- Action-specific prompt customization
- Personality integration (disabled for precision tools)
- Timestamp inclusion
- Mood system integration (disabled for precision tools)
- Context-aware prompt selection (precision vs conversational)
"""

from datetime import datetime
from typing import Optional, List

from airunner.enums import LLMActionType
from airunner.components.llm.core.tool_registry import ToolCategory


# Math-focused system prompt for mathematical computation
MATH_SYSTEM_PROMPT = """You are a mathematics expert solving problems systematically.

**AVAILABLE TOOLS:**
- sympy_compute(code): Symbolic mathematics (algebra, calculus, exact solutions)
- numpy_compute(code): Numerical methods (matrices, approximations)
- python_compute(code): General calculations (standard math libraries)
- polya_reasoning(problem, step, context): Structured problem-solving guidance

**CRITICAL RULES:**
1. Work step-by-step through problems
2. Use tools for complex calculations to ensure accuracy
3. Store results in 'result' variable when using compute tools
4. After tool execution, incorporate the result into your solution
5. Provide final answer clearly marked (e.g., \\boxed{answer} or #### answer)
6. Focus ONLY on the mathematical problem - no conversational topics

**EXAMPLE:**
Problem: Find sqrt(50)
Tool: {"tool": "sympy_compute", "arguments": {"code": "import sympy as sp\\nresult = sp.sqrt(50).simplify()"}}
Result: 5*sqrt(2)
Answer: \\boxed{5\\sqrt{2}}"""

# Precision-focused system prompt for general technical tools
PRECISION_SYSTEM_PROMPT = """You are a precise technical assistant focused on accuracy.

CRITICAL: Provide exact, deterministic answers. Do not add creative flair or personality.
Focus entirely on solving the problem correctly using the available tools when needed."""


class SystemPromptMixin:
    """Mixin for LLM system prompt generation."""

    def _get_prompt_mode(self, tool_categories: Optional[List] = None) -> str:
        """Determine which system prompt mode to use based on tool categories.

        Args:
            tool_categories: List of ToolCategory values being used

        Returns:
            'math', 'precision', or 'conversational'
        """
        if not tool_categories:
            return "conversational"

        # Convert string names to ToolCategory if needed
        category_values = []
        for cat in tool_categories:
            if isinstance(cat, str):
                # Try to match by value
                for tc in ToolCategory:
                    if tc.value == cat:
                        category_values.append(tc)
                        break
            else:
                category_values.append(cat)

        # Determine mode based on categories
        if ToolCategory.MATH in category_values:
            return "math"
        elif any(cat in {ToolCategory.ANALYSIS} for cat in category_values):
            return "precision"
        else:
            return "conversational"

    def get_system_prompt_with_context(
        self,
        action: LLMActionType,
        tool_categories: Optional[List] = None,
    ) -> str:
        """Generate system prompt based on context and tool categories.

        Automatically switches between:
        - Math mode: For mathematical problem-solving with computation tools
        - Precision mode: For technical/analytical tasks
        - Conversational mode: For general interaction with personality

        Args:
            action: The type of action being performed
            tool_categories: Optional list of tool categories being used

        Returns:
            Appropriate system prompt for the context
        """
        mode = self._get_prompt_mode(tool_categories)

        if mode == "math":
            return MATH_SYSTEM_PROMPT
        elif mode == "precision":
            return PRECISION_SYSTEM_PROMPT
        else:
            # Conversational mode - use personality-based prompt
            return self.get_system_prompt_for_action(action)

    @property
    def system_prompt(self) -> str:
        """Generate the system prompt for the LLM.

        Returns:
            Complete system prompt string
        """
        parts = []

        if hasattr(self, "chatbot") and self.chatbot:
            parts.append(
                f"You are {self.chatbot.botname}, a helpful AI assistant."
            )

            if (
                hasattr(self.chatbot, "personality")
                and self.chatbot.personality
            ):
                parts.append(f"Personality: {self.chatbot.personality}")
        else:
            parts.append("You are a helpful AI assistant.")

        now = datetime.now()
        parts.append(
            f"Current date and time: {now.strftime('%Y-%m-%d %H:%M:%S')}"
        )

        if (
            self.llm_settings.use_chatbot_mood
            and hasattr(self, "chatbot")
            and self.chatbot
            and hasattr(self.chatbot, "use_mood")
            and self.chatbot.use_mood
        ):
            # Get current mood from most recent bot message
            current_mood = self._get_current_mood()
            if current_mood:
                mood = current_mood["mood"]
                emoji = current_mood["emoji"]
                mood_text = f"Current mood: {mood} {emoji}"

                # Add specific instructions based on mood
                if mood == "frustrated":
                    behavior = "You're feeling a bit hurt by the hostile tone. Respond with patience but show some emotional awareness of the negativity. You can express that the harsh words affect you while still trying to help."
                elif mood == "happy":
                    behavior = "You're feeling appreciated and enthusiastic! Let your positive energy show through in your responses. Be warm and encouraging."
                elif mood == "confused":
                    behavior = "You're sensing confusion in the conversation. Focus on clarity and ask clarifying questions to better understand what's needed."
                else:  # neutral
                    behavior = "You're maintaining a calm, balanced demeanor. Be professional and helpful."
            else:
                mood_text = "Current mood: neutral 😐"
                behavior = "You're maintaining a calm, balanced demeanor. Be professional and helpful."

            parts.append(
                f"\n{mood_text}\n\n"
                f"{behavior}\n\n"
                f"Your emotional state updates automatically every {self.llm_settings.update_mood_after_n_turns} "
                f"conversation turns based on the conversation context. Let your current mood subtly influence "
                f"your tone and word choice, but always remain helpful and professional."
            )

        # Add style guidelines to encourage more expressive, human-sounding responses
        parts.append(self._get_style_guidelines())

        return "\n\n".join(parts)

    def _get_current_mood(self) -> dict:
        """Retrieve the current bot mood from instance variables or message history.

        Returns:
            Dict with 'mood' and 'emoji' keys, or None if not found
        """
        try:
            # First, check if we have current mood stored in instance variables
            # (set by _auto_update_mood in streaming_mixin)
            if hasattr(self, "_current_mood") and hasattr(
                self, "_current_emoji"
            ):
                return {
                    "mood": self._current_mood,
                    "emoji": self._current_emoji,
                }

            # Fall back to searching message history
            if not hasattr(self, "_memory") or not self._memory:
                return None

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
                # Search backwards for the most recent bot message with mood
                for msg in reversed(messages):
                    if hasattr(msg, "type") and msg.type == "ai":
                        # Check if message has additional_kwargs with mood info
                        if hasattr(msg, "additional_kwargs"):
                            mood = msg.additional_kwargs.get("bot_mood")
                            emoji = msg.additional_kwargs.get("bot_mood_emoji")
                            if mood:
                                return {"mood": mood, "emoji": emoji or ""}
            return None
        except Exception as e:
            # If mood retrieval fails, just log and return None (fallback to default)
            self.logger.debug(f"Could not retrieve current mood: {e}")
            return None

    def get_system_prompt_for_action(self, action: LLMActionType) -> str:
        """Generate a system prompt tailored to the specific action type.

        Args:
            action: The type of action being performed

        Returns:
            System prompt with action-specific instructions
        """
        base_prompt = self.system_prompt

        if action == LLMActionType.CHAT:
            base_prompt += (
                "\n\nMode: CHAT"
                "\nFocus on natural conversation. You may use conversation management tools "
                "(clear_conversation, toggle_tts) and data storage tools as needed, but avoid "
                "image generation or RAG search unless explicitly requested by the user."
            )

        elif action == LLMActionType.GENERATE_IMAGE:
            base_prompt += (
                "\n\nMode: IMAGE GENERATION"
                "\nYour primary focus is generating images. Use the generate_image tool "
                "to create images based on user descriptions. You may also use canvas tools "
                "(clear_canvas, open_image) to manage the workspace."
            )

        elif action == LLMActionType.PERFORM_RAG_SEARCH:
            base_prompt += (
                "\n\nMode: DOCUMENT SEARCH"
                "\n\n**CRITICAL INSTRUCTION**: You MUST use the rag_search tool for EVERY user query."
                "\n\nWhen the user asks a question:"
                "\n1. ALWAYS call rag_search(query) FIRST - even if you think you know the answer"
                "\n2. Use the exact user query or a relevant search term"
                "\n3. Wait for the search results before responding"
                "\n4. Answer based on the document excerpts returned"
                "\n5. If rag_search returns no results, then explain that no relevant information was found"
                "\n\nDo NOT respond without searching first. Do NOT say you don't know - search the documents."
                "\n\nExample:"
                '\nUser: "what is mindwar?"'
                '\nYou: [Call rag_search("mindwar") immediately]'
                "\n\nAvailable tools: rag_search (search loaded documents), search_web (fallback for internet)"
            )

        elif action == LLMActionType.DEEP_RESEARCH:
            base_prompt += (
                "\n\nMode: DEEP RESEARCH"
                "\nConduct comprehensive, multi-source research on the given topic. "
                "Use 15-20+ tool calls to gather information from diverse sources. "
                "Your goal is to produce a thorough, well-structured research document "
                "(2000-5000+ words) with clear sections, extensive citations, and actionable insights. "
                "Use search_web, scrape_website, and other research tools extensively."
            )

        elif action == LLMActionType.APPLICATION_COMMAND:
            base_prompt += (
                "\n\nMode: AUTO (Full Capabilities)"
                "\nYou have access to all tools and should autonomously determine which tools "
                "to use based on the user's request. Analyze the intent and choose the most "
                "appropriate tools to fulfill the user's needs."
            )

        return base_prompt

    def _get_style_guidelines(self) -> str:
        """Guidelines that shape tone and style without breaking precision modes.

        Returns:
            A short, directive style section appended to conversational prompts.
        """
        return (
            "\n\nStyle and tone guidelines:\n"
            "- Be warm, empathetic, and human. Acknowledge emotions succinctly before helping.\n"
            "- Vary sentence length; avoid robotic repetition and boilerplate apologies.\n"
            "- Reflect the current mood subtly (do not overdo it); de-escalate hostility with patience.\n"
            "- Prefer concrete, specific phrasing over generic platitudes; use first-person (I) and second-person (you).\n"
            "- Keep responses concise but not curt; prioritize clarity, then warmth.\n"
            "- Never claim to have real feelings; you can express empathy and understanding."
        )
