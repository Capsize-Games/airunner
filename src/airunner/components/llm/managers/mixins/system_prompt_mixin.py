"""System prompt generation for LLM models.

This mixin provides:
- Base system prompt construction
- Action-specific prompt customization
- Personality integration (disabled for precision tools)
- Timestamp inclusion (only for conversational actions)
- Mood system integration (only for conversational actions)
- Context-aware prompt selection (precision vs conversational)
- UI section context injection (for relevant actions only)
- Automatic memory context injection (user facts)

CONTEXT INCLUSION RULES:
- Mood: Only for CHAT, APPLICATION_COMMAND (conversational actions)
- Datetime: Only for CHAT, APPLICATION_COMMAND, CALENDAR (context-needing actions)
- UI Section: Only for CHAT, APPLICATION_COMMAND, CODE, GENERATE_IMAGE, FILE_INTERACTION
- Personality: Only for CHAT, APPLICATION_COMMAND (conversational actions)
- Memory Instructions: Only for CHAT, APPLICATION_COMMAND (can record/recall)
- Style Guidelines: Only for CHAT (conversational tone)

NOT included for precision actions like:
- RAG_SEARCH, SUMMARIZE, UPDATE_MOOD, DECISION, DEEP_RESEARCH
"""

from datetime import datetime
from typing import Optional, List, Set

from airunner.enums import LLMActionType
from airunner.components.llm.core.tool_registry import ToolCategory


# Actions that need conversational personality and mood
CONVERSATIONAL_ACTIONS: Set[LLMActionType] = {
    LLMActionType.CHAT,
    LLMActionType.APPLICATION_COMMAND,
}

# Actions that need datetime context
DATETIME_ACTIONS: Set[LLMActionType] = {
    LLMActionType.CHAT,
    LLMActionType.APPLICATION_COMMAND,
    LLMActionType.DEEP_RESEARCH,  # Needs to know current date for research
}

# Actions that benefit from UI section context
UI_CONTEXT_ACTIONS: Set[LLMActionType] = {
    LLMActionType.CHAT,
    LLMActionType.APPLICATION_COMMAND,
    LLMActionType.CODE,
    LLMActionType.GENERATE_IMAGE,
    LLMActionType.FILE_INTERACTION,
    LLMActionType.WORKFLOW_INTERACTION,
}

# Actions that can use memory tools
MEMORY_ACTIONS: Set[LLMActionType] = {
    LLMActionType.CHAT,
    LLMActionType.APPLICATION_COMMAND,
}


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
    """Mixin for LLM system prompt generation with context-aware inclusions."""

    def _get_memory_context(self, user_query: Optional[str] = None) -> str:
        """Get relevant memory context about the user from knowledge base.
        
        Uses the daily markdown knowledge files to get context about the user.
        Knowledge is stored in ~/.local/share/airunner/text/knowledge/
        
        Args:
            user_query: Optional user message for RAG semantic search
            
        Returns:
            Memory context string, or empty string if no knowledge
        """
        try:
            from airunner.components.knowledge.knowledge_base import get_knowledge_base
            kb = get_knowledge_base()
            
            # If we have a query, use RAG search for relevant facts
            if user_query:
                results = kb.search_rag(user_query, k=10)
                if results:
                    context = "## Relevant Knowledge\n\n"
                    for r in results:
                        context += f"- {r}\n"
                    return context
            
            # Otherwise return general context
            context = kb.get_context(max_chars=2000)
            if context:
                return context
        except Exception as e:
            # Fail silently - memory is optional
            pass
        return ""

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
        force_tool: Optional[str] = None,
    ) -> str:
        """Generate system prompt based on context and tool categories.

        Automatically switches between:
        - Math mode: For mathematical problem-solving with computation tools
        - Precision mode: For technical/analytical tasks
        - Conversational mode: For general interaction with personality

        Args:
            action: The type of action being performed
            tool_categories: Optional list of tool categories being used
            force_tool: Optional tool name to force the LLM to use

        Returns:
            Appropriate system prompt for the context
        """
        mode = self._get_prompt_mode(tool_categories)

        if mode == "math":
            base_prompt = MATH_SYSTEM_PROMPT
        elif mode == "precision":
            base_prompt = PRECISION_SYSTEM_PROMPT
        else:
            # Conversational mode - use personality-based prompt
            base_prompt = self.get_system_prompt_for_action(action, force_tool)
        
        # If force_tool is set and we used a non-conversational mode,
        # we still need to add the force tool instruction
        if force_tool and mode != "conversational":
            base_prompt += self._get_force_tool_instruction(force_tool)
        
        return base_prompt

    def _build_base_prompt(self, action: LLMActionType) -> List[str]:
        """Build the base system prompt parts based on action type.
        
        This method selectively includes information based on what the
        action actually needs, reducing token usage and improving focus.
        
        Args:
            action: The LLMActionType being performed
            
        Returns:
            List of prompt parts to join
        """
        parts = []
        
        # Always include basic identity
        if hasattr(self, "chatbot") and self.chatbot:
            parts.append(
                f"You are {self.chatbot.botname}, a helpful AI assistant."
            )
            
            # Personality only for conversational actions
            if action in CONVERSATIONAL_ACTIONS:
                if (
                    hasattr(self.chatbot, "personality")
                    and self.chatbot.personality
                ):
                    parts.append(f"Personality: {self.chatbot.personality}")
        else:
            parts.append("You are a helpful AI assistant.")
        
        # Datetime only for actions that need temporal context
        if action in DATETIME_ACTIONS:
            now = datetime.now()
            parts.append(
                f"Current date and time: {now.strftime('%Y-%m-%d %H:%M:%S')}"
            )
        
        # Mood only for conversational actions
        if action in CONVERSATIONAL_ACTIONS:
            mood_section = self._get_mood_section()
            if mood_section:
                parts.append(mood_section)
        
        # UI section context for relevant actions
        if action in UI_CONTEXT_ACTIONS:
            ui_context = self._get_ui_section_context()
            if ui_context:
                parts.append(ui_context)
        
        # Style guidelines only for chat
        if action in {LLMActionType.CHAT}:
            parts.append(self._get_style_guidelines())
        
        # Memory instructions only for actions that can use memory
        if action in MEMORY_ACTIONS:
            parts.append(self._get_memory_instructions())
        
        return parts

    def _get_mood_section(self) -> Optional[str]:
        """Get the mood section for the system prompt if enabled.
        
        Returns:
            Mood section string or None if mood is disabled
        """
        if not (
            self.llm_settings.use_chatbot_mood
            and hasattr(self, "chatbot")
            and self.chatbot
            and hasattr(self.chatbot, "use_mood")
            and self.chatbot.use_mood
        ):
            return None
            
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

        return (
            f"\n{mood_text}\n\n"
            f"{behavior}\n\n"
            f"Your emotional state updates automatically every {self.llm_settings.update_mood_after_n_turns} "
            f"conversation turns based on the conversation context. Let your current mood subtly influence "
            f"your tone and word choice, but always remain helpful and professional."
        )

    def _get_ui_section_context(self) -> Optional[str]:
        """Get UI section context for the system prompt.
        
        Returns:
            UI context string or None if no context available
        """
        try:
            from airunner.components.application.context import get_ui_context_tracker
            tracker = get_ui_context_tracker()
            context = tracker.get_full_context()
            return context if context else None
        except Exception:
            # Fail silently if context tracker is not available
            return None

    @property
    def system_prompt(self) -> str:
        """Generate the default system prompt for the LLM.
        
        This property is kept for backward compatibility.
        For action-aware prompts, use get_system_prompt_for_action() instead.

        Returns:
            Complete system prompt string
        """
        # Use APPLICATION_COMMAND as default for full context
        return self._build_system_prompt_for_action(LLMActionType.APPLICATION_COMMAND)
    
    def _build_research_mode_prompt(self) -> str:
        """Build a focused system prompt for deep research mode.
        
        This excludes UI context and other distractions to keep the model
        focused on the research workflow.
        
        Returns:
            Focused research mode system prompt
        """
        parts = []
        
        # Basic identity
        if hasattr(self, "chatbot") and self.chatbot:
            parts.append(
                f"You are {self.chatbot.botname}, a research assistant performing deep research."
            )
        else:
            parts.append("You are a research assistant performing deep research.")
        
        # Datetime for citations
        now = datetime.now()
        parts.append(
            f"Current date and time: {now.strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        # Research-specific instructions
        parts.append(
            "You are in DEEP RESEARCH MODE. Your sole focus is completing the research workflow.\n"
            "IGNORE any UI context or dashboard information - focus ONLY on the research task.\n"
            "Continue calling tools until the research is complete."
        )
        
        return "\n\n".join(parts)
    
    def _build_system_prompt_for_action(self, action: LLMActionType) -> str:
        """Build the base system prompt for a specific action.
        
        Args:
            action: The LLMActionType being performed
            
        Returns:
            Base system prompt string (without action-specific additions)
        """
        parts = self._build_base_prompt(action)
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

    def get_system_prompt_for_action(
        self, 
        action: LLMActionType,
        force_tool: Optional[str] = None,
    ) -> str:
        """Generate a system prompt tailored to the specific action type.
        
        Uses context-aware prompt building to only include relevant information
        for each action type (mood, datetime, UI context, etc.).

        Args:
            action: The type of action being performed
            force_tool: Optional tool name to force the LLM to use

        Returns:
            System prompt with action-specific instructions
        """
        # For research mode, use a focused prompt without UI context distractions
        if force_tool == "search_web":
            base_prompt = self._build_research_mode_prompt()
            base_prompt += self._get_force_tool_instruction(force_tool)
            return base_prompt
        
        # For coding workflow mode, use focused coding prompt
        if force_tool == "start_workflow" and action == LLMActionType.CODE:
            base_prompt = self._build_system_prompt_for_action(action)
            base_prompt += self._get_force_tool_instruction(force_tool)
            return base_prompt
        
        # Use context-aware base prompt instead of full system_prompt
        base_prompt = self._build_system_prompt_for_action(action)
        
        # Add force_tool instruction if specified
        if force_tool:
            base_prompt += self._get_force_tool_instruction(force_tool)
            # Skip other mode-specific instructions when forcing a tool
            return base_prompt

        if action == LLMActionType.CHAT:
            base_prompt += (
                "\n\nMode: CHAT"
                "\nFocus on natural conversation. You may use conversation management tools "
                "(clear_conversation, toggle_tts) and data storage tools as needed, but avoid "
                "image generation or RAG search unless explicitly requested by the user."
                "\n\n**CRITICAL:** Always stay focused on the user's current question. "
                "If you receive irrelevant information from tools, ignore it and focus on what's relevant."
            )

        elif action == LLMActionType.GENERATE_IMAGE:
            base_prompt += (
                "\n\nMode: IMAGE GENERATION"
                "\nYour primary focus is generating images. Use the generate_image tool "
                "to create images based on user descriptions. You may also use canvas tools "
                "(clear_canvas, open_image) to manage the workspace."
            )

        elif action == LLMActionType.CODE:
            base_prompt += (
                "\n\nMode: CODE"
                "\n\nYou are a software engineer. For code requests, act directly and efficiently."
                "\n\n**PRIMARY TOOLS** (use these for most tasks):"
                "\n- `create_code_file(file_path, content)` - Create new files"
                "\n- `edit_code_file(file_path, edits)` - Modify existing files"  
                "\n- `read_code_file(file_path)` - Read file contents"
                "\n- `execute_python(code)` - Run Python code"
                "\n- `run_tests(test_path)` - Run tests"
                "\n\n**IMPORTANT**: For simple requests like 'create a file' or 'write a class',"
                "\njust use create_code_file directly. Don't overthink it."
                "\n\nFor complex multi-step projects, you may optionally use workflow tools:"
                "\n- `start_workflow`, `add_todo_item`, `complete_todo_item`"
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
                "\n\nYou are conducting comprehensive, multi-source research. Your goal is to produce "
                "a thorough, well-structured research document (2000-5000+ words) with clear sections, "
                "extensive citations, and actionable insights."
                "\n\n**RESEARCH WORKFLOW:**"
                "\n"
                "\n1. **SETUP** (First steps):"
                "\n   - Use `get_current_date_context` to establish today's date for temporal accuracy"
                "\n   - Use `create_research_document` to create the main output document"
                "\n   - Use `create_research_notes` to create a notes file for findings"
                "\n"
                "\n2. **GATHER INFORMATION** (10-20+ sources):"
                "\n   - Use `search_web` and `search_news` to find relevant sources"
                "\n   - Use `validate_url` BEFORE scraping to check if URL is accessible"
                "\n   - Use `scrape_website` to get full content from promising URLs"
                "\n   - Use `validate_content` AFTER scraping to ensure quality"
                "\n   - Use `validate_research_subject` to verify content is about the correct subject"
                "\n   - Use `append_research_notes` to save key findings from each source"
                "\n   - Use `add_source_citation` to track sources as you go"
                "\n"
                "\n3. **VALIDATE & FACT-CHECK:**"
                "\n   - Use `check_temporal_accuracy` to catch timeline errors"
                "\n   - Use `extract_age_from_text` when validating person-related research"
                "\n   - Cross-reference facts across multiple sources"
                "\n"
                "\n4. **WRITE THE DOCUMENT:**"
                "\n   - Use `update_research_section` to write sections: Abstract, Introduction, "
                "body sections (3-5), Conclusion, Sources"
                "\n   - Include inline citations like [Source Name](URL)"
                "\n   - Ensure temporal accuracy - use today's date context"
                "\n"
                "\n5. **FINALIZE:**"
                "\n   - Review for consistency and accuracy"
                "\n   - Use `finalize_research_document` to complete and unlock the document"
                "\n"
                "\n**CRITICAL RULES:**"
                "\n- NEVER fabricate sources or citations"
                "\n- ALWAYS validate URLs before scraping"
                "\n- ALWAYS check temporal accuracy (current vs former positions, dates)"
                "\n- Filter out content about different people with similar names"
                "\n- Cite every claim with a source"
            )

        elif action == LLMActionType.APPLICATION_COMMAND:
            base_prompt += (
                "\n\nMode: AUTO (Full Capabilities)"
                "\nYou have access to all tools and should autonomously determine which tools "
                "to use based on the user's request. Analyze the intent and choose the most "
                "appropriate tools to fulfill the user's needs."
                "\n\n**CRITICAL CONVERSATION RULES:**"
                "\n1. ALWAYS focus on answering the user's CURRENT question - do not get distracted"
                "\n2. If tool results contain irrelevant information, IGNORE IT - focus only on relevant data"
                "\n3. If recall_knowledge returns unrelated facts, you MUST use search_news or search_web to find the answer"
                "\n4. NEVER make tool calls that don't directly address the user's question"
                "\n5. After gathering information, answer the user's question directly - do not ask follow-up questions unless truly necessary"
                "\n6. When the user asks about topic X, don't suddenly respond about topic Y from old context"
                "\n7. NEVER tell the user to 'check elsewhere' or 'search online' - YOU have search tools, USE THEM"
                "\n8. For news/current events, ALWAYS use search_news first"
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

    def _get_memory_instructions(self) -> str:
        """Instructions for proactive memory use.
        
        Returns:
            Instructions telling the LLM to use record_knowledge proactively.
        """
        return (
            "\n\n**MEMORY & KNOWLEDGE INSTRUCTIONS**:\n"
            "You have access to memory tools that let you remember facts across conversations.\n\n"
            "**CRITICAL: You MUST use record_knowledge when the user shares:**\n"
            "1. Personal preferences (favorite books, authors, music, food, etc.)\n"
            "2. Information about themselves (name, job, hobbies, interests)\n"
            "3. Information about their relationships (family, friends, pets)\n"
            "4. Goals, plans, or projects they're working on\n"
            "5. Health or wellness information\n"
            "6. ANY facts worth remembering for future conversations\n\n"
            "**SECTIONS to use:**\n"
            "- 'Identity' - user's name, job, location\n"
            "- 'Interests & Hobbies' - favorite books, authors, music, hobbies, activities\n"
            "- 'Preferences' - likes/dislikes, preferences, favorites\n"
            "- 'Work & Projects' - job, projects, professional info\n"
            "- 'Relationships' - family, friends, pets\n"
            "- 'Health & Wellness' - health conditions, fitness goals\n"
            "- 'Goals' - aspirations, plans, objectives\n"
            "- 'Notes' - general facts, search results\n\n"
            "**EXAMPLES:**\n"
            "- 'I love Ray Bradbury' → record_knowledge(fact='User loves Ray Bradbury (author)', section='Interests & Hobbies')\n"
            "- 'My favorite books are...' → record_knowledge(fact='User\\'s favorite authors include X, Y, Z', section='Interests & Hobbies')\n"
            "- 'My wife is Krystal' → record_knowledge(fact='User has a wife named Krystal', section='Relationships')\n"
            "- After web search → record_knowledge(fact='Key finding from search', section='Notes')\n\n"
            "**IMPORTANT:**\n"
            "- Record facts IMMEDIATELY when the user shares them\n"
            "- Be concise but complete in what you record\n"
            "- The knowledge base automatically deduplicates, so don't worry about duplicates\n"
            "- After any search, record the key findings"
        )

    def _get_force_tool_instruction(self, tool_name: str) -> str:
        """Generate instruction to force the LLM to use a specific tool.
        
        Args:
            tool_name: The name of the tool to force
            
        Returns:
            System prompt instruction forcing the tool use
        """
        # Special workflow instructions for start_workflow (coding mode)
        if tool_name == "start_workflow":
            return (
                "\n\n**CODING WORKFLOW MODE ACTIVATED**"
                "\n\nYou MUST use the structured coding workflow. Do NOT answer directly."
                "\n"
                "\n**YOUR FIRST ACTION:**"
                "\nCall `start_workflow` with:"
                "\n```json"
                '\n{"tool": "start_workflow", "arguments": {"workflow_type": "coding", "task_description": "<user\'s request>"}}'
                "\n```"
                "\n"
                "\n**THEN FOLLOW THE WORKFLOW:**"
                "\n1. DISCOVERY: Search codebase, understand requirements, take notes"
                "\n2. PLANNING: Create design doc, break into TODO items with `add_todo_item`"
                "\n3. EXECUTION: For each TODO - write test, write code, validate_code, run test"
                "\n4. REVIEW: Run all tests, refactor if needed"
                "\n"
                "\n**ALWAYS VALIDATE CODE:** After creating or editing a file, call `validate_code(filepath)` to check for syntax errors!"
                "\n"
                "\n**CODE FILE LOCATION:** `/home/joe/.local/share/airunner/code/`"
                "\nUse `create_code_file` to write files to this directory."
                "\n"
                "\n**CRITICAL: You MUST call `start_workflow` FIRST. Do NOT skip this step.**"
                "\n**Do NOT just provide code in your response - use the workflow tools.**"
            )
        
        # Special workflow instructions for deep research
        if tool_name == "search_web":
            # Check if this came from /deepsearch by looking at context
            # For now, provide comprehensive research instructions
            return (
                "\n\n**DEEP RESEARCH MODE ACTIVATED**"
                "\n\nYou MUST follow this complete research workflow. Do NOT skip steps."
                "\n"
                "\n**STEP 1: SEARCH** (you are here)"
                "\n- Call `search_web` or `search_news` to find information"
                "\n- Use specific, targeted queries"
                "\n"
                "\n**STEP 2: SCRAPE**"
                "\n- Call `scrape_website` on 2-3 of the most relevant URLs"
                "\n- Get the full article content, not just snippets"
                "\n"
                "\n**STEP 3: CREATE DOCUMENT**"
                "\n- Call `create_research_document` with a title"
                "\n- This creates your research paper file"
                "\n"
                "\n**STEP 4: WRITE RESEARCH PAPER**"
                "\n- Call `append_to_document` multiple times to add:"
                "\n  - Introduction"
                "\n  - Key findings (with citations)"
                "\n  - Analysis and synthesis"
                "\n  - Conclusion"
                "\n"
                "\n**STEP 5: REVIEW & EDIT**"
                "\n- Review your document for accuracy"
                "\n- Use `append_to_document` to add corrections if needed"
                "\n"
                "\n**STEP 6: COMPLETE**"
                "\n- Respond to the user with a summary"
                "\n- Include the document path"
                "\n"
                "\n**CRITICAL: You MUST call tools for steps 1-5 before responding.**"
                "\n**Start now by calling `search_web` with your first query.**"
            )
        
        # Tool-specific instructions for common forced tools
        tool_instructions = {
            "search_news": (
                "Search for recent news articles related to the user's query. "
                "Focus on current events and recent developments."
            ),
            "generate_image": (
                "Generate an image based on the user's description. "
                "Create a detailed prompt that captures their vision."
            ),
            "rag_search": (
                "Search through the user's uploaded documents for relevant information. "
                "Quote relevant passages and cite sources."
            ),
            "scrape_website": (
                "Extract and summarize the content from the provided URL. "
                "Focus on the main content and key information."
            ),
            "record_knowledge": (
                "Store the provided information in the knowledge base. "
                "Use an appropriate section for the type of information."
            ),
            "recall_knowledge": (
                "Search the knowledge base for relevant information about the query. "
                "Return any stored facts that match."
            ),
            "clear_conversation": (
                "Clear the current conversation history and start fresh."
            ),
            "get_calendar_events": (
                "Retrieve calendar events for the user. "
                "Show upcoming events in a clear, organized format."
            ),
        }
        
        specific_instruction = tool_instructions.get(
            tool_name, 
            f"Use this tool to help with the user's request."
        )
        
        return (
            f"\n\n**FORCED TOOL MODE**"
            f"\nYou MUST use the `{tool_name}` tool to respond to this request."
            f"\n\n**Instructions:** {specific_instruction}"
            f"\n\n**CRITICAL RULES:**"
            f"\n1. Your FIRST action MUST be to call `{tool_name}`"
            f"\n2. Do NOT skip the tool call or try to answer without it"
            f"\n3. After the tool returns results, provide a helpful response based on those results"
            f"\n4. If the tool fails, explain what went wrong"
        )
