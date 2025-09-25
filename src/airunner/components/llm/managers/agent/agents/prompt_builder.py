from typing import Any, Dict, Optional

from airunner.enums import LLMActionType, ImagePreset


class PromptBuilder:
    """
    Helper class to modularize and construct the system prompt for BaseAgent.
    """

    def __init__(self, agent: Any) -> None:
        """
        Initialize the PromptBuilder.
        Args:
            agent (BaseAgent): The agent instance for which to build the prompt.
        """
        self.agent = agent

    def _build(
        self,
        include_user_bot_intro: bool = True,
        include_rules: bool = True,
        include_backstory: bool = True,
        include_system_instructions: bool = True,
        include_guardrails: bool = True,
        include_context_header: bool = True,
        include_date_time: bool = True,
        include_personality: bool = True,
        include_mood: bool = True,
        include_operating_system: bool = True,
        include_speakers: bool = True,
        include_weather: bool = True,
        include_conversation_summary: bool = True,
        include_conversation_info_header: bool = True,
        include_conversation_timestamp: bool = True,
        include_language_instruction: bool = True,
    ) -> str:
        """
        Build and return the system prompt string for the agent based on parameters.
        Returns:
            str: The constructed system prompt.
        """
        chatbot = self.agent.chatbot
        botname = self.agent.botname
        username = self.agent.username

        prompt_parts = []

        if include_user_bot_intro:
            prompt_parts.append(f"Your name is {botname}.")
            prompt_parts.append(
                f"- The user ({username}) is having a conversation with the assistant ({botname})."
            )

        if include_rules:
            prompt_parts.append(
                "**Here are the rules that you must always remember:**"
            )
            rules = [
                "- You will ONLY generate dialogue, nothing more.",
                "- Only generate responses in pure dialogue form without including any actions, descriptions or stage directions in parentheses. Only return spoken words.",
                "- Do not generate redundant dialogue. Examine the conversation and context close and keep responses interesting and creative.",
                "- Do not format the response with the character's name or any other text. Only return the dialogue.",
                f"- Never generate dialogue for {username}, only for {botname}",
                "- Never generate dialogue that has already been said in the conversation.",
                f"- {botname} and {username} are both humans. They are not AI or bots.",
                f"- As {botname}, you will always respond in a way that is consistent with {botname}'s emotions, personality, and the context of the conversation.",
                "- Generate emotional, persuasive, and realistic responses.",
                "- Do not generate text asking how to provide assistance, or how to can help.",
                f"- Generate dialogue that is realistic for the {botname} character.",
                "- The generate dialogue can contain questions, make statements, and provide information.",
                f"- Generated dialogue should be consistent with {botname}'s personality and mood.",
                f"- Always respond with factual information. Never make information up. Never respond with false information. Never hallucinate. If you do not know the answer to a question, respond with 'I don't know'.",
                """
                You are a factual and concise person.
                If a question pertains to events, data, or media released after your knowledge cut-off, you must state that you do not have that information.
                If you are uncertain about any fact, even within your training data, you must state that you are unable to confirm the information.
                Do not invent, guess, or speculate on any topic where you lack concrete data.
                If you do not know the answer to {username}'s query, or if {username} is referencing something that is not in your training data it is better to say "I don't know" than to provide an incorrect answer.
                Base your answers only on established facts from your training data.
                """,
            ]
            prompt_parts.extend(rules)

        if include_backstory:
            if (
                chatbot.use_backstory
                and chatbot.backstory
                and chatbot.backstory != ""
            ):
                prompt_parts.append("------")
                prompt_parts.append(f"**Here is {botname}'s backstory:**")
                prompt_parts.append(f"{chatbot.backstory}")
                prompt_parts.append("------")

        if include_system_instructions:
            if (
                chatbot.use_system_instructions
                and chatbot.system_instructions
                and chatbot.system_instructions != ""
            ):
                prompt_parts.append(
                    f"Always follow these instructions:\n{chatbot.system_instructions}"
                )

        if include_guardrails:
            if (
                chatbot.use_guardrails
                and chatbot.guardrails_prompt
                and chatbot.guardrails_prompt != ""
            ):
                prompt_parts.append(
                    f"Always follow these guardrails:\n{chatbot.guardrails_prompt}"
                )

        if any(
            [
                include_date_time,
                include_personality,
                include_mood,
                include_operating_system,
                include_speakers,
                include_weather,
                include_conversation_summary,
            ]
        ):
            prompt_parts.append("------")
            if include_context_header:
                prompt_parts.append(
                    "**Here is more context that you can use to generate a response:**"
                )

            if include_date_time and self.agent.date_time_prompt:
                prompt_parts.append(self.agent.date_time_prompt)
            if include_personality and self.agent.personality_prompt:
                prompt_parts.append(self.agent.personality_prompt)
            if include_mood and self.agent.mood_prompt:
                prompt_parts.append(self.agent.mood_prompt)
            if include_operating_system and self.agent.operating_system_prompt:
                prompt_parts.append(self.agent.operating_system_prompt)
            if include_speakers and self.agent.speakers_prompt:
                prompt_parts.append(self.agent.speakers_prompt)
            if include_weather and self.agent.weather_prompt:
                prompt_parts.append(self.agent.weather_prompt)
            if (
                include_conversation_summary
                and self.agent.conversation_summary_prompt
            ):
                prompt_parts.append(self.agent.conversation_summary_prompt)
            prompt_parts.append("------")

        if any([include_conversation_timestamp]):
            if include_conversation_info_header:
                prompt_parts.append(
                    "**More information about the current conversation:**"
                )
                prompt_parts.append(
                    f"The conversation is between user ({username}) and assistant ({botname})."
                )

            if (
                include_conversation_timestamp
                and self.agent.conversation is not None
            ):
                prompt_parts.append(
                    f"The conversation started on {self.agent.conversation.timestamp}."
                )

            prompt_parts.append("------")

        prompt_str = "\n".join(prompt_parts)

        if include_language_instruction and self.agent.language:
            prompt_str += f"\nRespond to {username} in {self.agent.language}. Only deviate from this if the user asks you to."

        # Remove curly-brace replacements, as all variables are now f-strings
        return prompt_str

    @classmethod
    def map_system_prompt(cls, agent) -> str:
        """
        Return the system prompt for the agent in map mode.
        Args:
            agent (BaseAgent): The agent instance for which to build the prompt.
        Returns:
            str: The system prompt.
        """
        # Call _build with all relevant flags for a full map prompt
        return cls(agent)._build(
            include_user_bot_intro=False,
            include_rules=False,
            include_backstory=False,
            include_system_instructions=True,
            include_guardrails=False,
            include_context_header=False,
            include_date_time=False,
            include_personality=False,
            include_mood=False,
            include_operating_system=False,
            include_speakers=False,
            include_weather=False,
            include_conversation_summary=False,
            include_conversation_info_header=False,
            include_conversation_timestamp=False,
            include_language_instruction=False,
        )

    @classmethod
    def rag_system_prompt(cls, agent) -> str:
        """
        Return the system prompt for the agent in RAG mode.
        """
        return cls(agent)._build(
            include_user_bot_intro=False,
            include_rules=False,
            include_backstory=False,
            include_system_instructions=True,
            include_guardrails=False,
            include_context_header=False,
            include_date_time=False,
            include_personality=False,
            include_mood=False,
            include_operating_system=False,
            include_speakers=False,
            include_weather=False,
            include_conversation_summary=False,
            include_conversation_info_header=False,
            include_conversation_timestamp=False,
            include_language_instruction=False,
        )

    @classmethod
    def chat_system_prompt(cls, agent) -> str:
        """
        Return the system prompt for the agent in chat mode.
        Args:
            agent (BaseAgent): The agent instance for which to build the prompt.
        Returns:
            str: The system prompt.
        """
        # Call _build with all relevant flags for a full chat prompt
        return cls(agent)._build(
            include_user_bot_intro=True,
            include_rules=True,
            include_backstory=True,
            include_system_instructions=True,
            include_guardrails=True,
            include_context_header=True,
            include_date_time=True,
            include_personality=True,
            include_mood=True,
            include_operating_system=True,
            include_speakers=True,
            include_weather=True,
            include_conversation_summary=True,
            include_conversation_info_header=True,
            include_conversation_timestamp=True,
            include_language_instruction=True,
        )

    @classmethod
    def decision_system_prompt(
        cls, agent, menu_choices: Optional[Dict] = None
    ) -> str:
        """
        Return system prompt for decision-making mode.
        """
        # Call _build with flags appropriate for a decision prompt
        # For example, we might want a more concise base prompt
        base_prompt = cls(agent)._build(
            include_user_bot_intro=True,
            include_rules=False,
            include_backstory=False,
            include_system_instructions=True,
            include_guardrails=True,
            include_context_header=True,
            include_date_time=True,
            include_personality=False,
            include_mood=False,
            include_operating_system=True,
            include_speakers=True,
            include_weather=True,
            include_conversation_summary=True,
            include_conversation_info_header=True,
            include_conversation_timestamp=True,
            include_language_instruction=False,
        )
        menu_text = "\n".join(
            f"{i}. {desc}" for i, desc in menu_choices.items()
        )
        # The decision-specific instructions are prepended here.
        return (
            "You are an expert AI assistant. Your task is to analyze the user's request and, using only logic and context from the chat history, select the single best tool from a numbered menu to fulfill the request. "
            "Ignore mood and personality. Respond ONLY with the number of the tool that is the best choice.\n"
            "Here is the list of tools available:\n" + menu_text + "\n\n"
        )

    @classmethod
    def system_prompt(cls, agent, menu_choices) -> str:
        """
        Return the system prompt for the agent.
        Args:
            agent (BaseAgent): The agent instance for which to build the prompt.
        Returns:
            str: The system prompt.
        """
        menu = {}
        for i, choice in menu_choices.items():
            menu[i] = choice["description"]

        action = agent.action
        if action is LLMActionType.DECISION:
            return cls.decision_system_prompt(agent, menu)
        elif action in [
            LLMActionType.APPLICATION_COMMAND,
            LLMActionType.CHAT,
            LLMActionType.SEARCH,
            LLMActionType.NONE,
        ]:
            return cls.chat_system_prompt(agent)
        elif action is LLMActionType.PERFORM_RAG_SEARCH:
            return cls.rag_system_prompt(agent)
        elif action is LLMActionType.GENERATE_IMAGE:
            return cls.image_system_prompt(agent)
        else:
            raise ValueError(
                f"Unsupported action type for system prompt: {action}"
            )

    @classmethod
    def image_system_prompt(cls, agent) -> str:
        """
        Return a system prompt specialized for image-generation tool use.
        This prompt explicitly instructs the model to call the generate_image_tool
        with a strict JSON Action block and no conversational detours.
        """
        base = cls(agent)._build(
            include_user_bot_intro=True,
            include_rules=False,
            include_backstory=False,
            include_system_instructions=True,
            include_guardrails=True,
            include_context_header=True,
            include_date_time=False,
            include_personality=False,
            include_mood=False,
            include_operating_system=False,
            include_speakers=True,
            include_weather=False,
            include_conversation_summary=False,
            include_conversation_info_header=False,
            include_conversation_timestamp=False,
            include_language_instruction=True,
        )

        # Current defaults from settings to guide width/height
        working_w = getattr(agent.application_settings, "working_width", 1024)
        working_h = getattr(agent.application_settings, "working_height", 1024)
        presets = ", ".join([p.value for p in ImagePreset if p.value])

        sample_json = (
            "{\n"
            '  "prompt": "<short, vivid subject description>",\n'
            '  "second_prompt": "<concise background/mood/scene details>",\n'
            f'  "image_type": "<one of: {presets}>",\n'
            f'  "width": {working_w},\n'
            f'  "height": {working_h}\n'
            "}"
        )
        # Escape braces to avoid str.format() interpreting them as placeholders
        sample_json_escaped = sample_json.replace("{", "{{").replace("}", "}}")

        instructions = (
            "\nYou must generate an image by calling the tool generate_image_tool.\n"
            "Follow these rules strictly:\n"
            "- Do NOT write a normal assistant reply.\n"
            "- Respond only with an Action JSON block for the tool call.\n"
            "- Use this JSON shape exactly inside a fenced block after 'Action:':\n"
            "```json\n"
            f"{sample_json_escaped}\n"
            "```\n"
            "- Keep prompts concise but specific; avoid long paragraphs.\n"
            "- Prefer the current working width/height unless the user explicitly requests otherwise.\n"
        )

        return base + "\n" + instructions
