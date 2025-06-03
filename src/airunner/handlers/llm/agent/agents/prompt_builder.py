from typing import Any


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

    def build(self) -> str:
        """
        Build and return the system prompt string for the agent.
        Returns:
            str: The constructed system prompt.
        """
        chatbot = self.agent.chatbot
        botname = self.agent.botname
        username = self.agent.username
        system_instructions = ""
        if (
            chatbot.use_system_instructions
            and chatbot.system_instructions
            and chatbot.system_instructions != ""
        ):
            system_instructions = f"Always follow these instructions:\n{chatbot.system_instructions}\n"
        guardrails = ""
        if (
            chatbot.use_guardrails
            and chatbot.guardrails_prompt
            and chatbot.guardrails_prompt != ""
        ):
            guardrails = f"Always follow these guardrails:\n{chatbot.guardrails_prompt}\n"
        backstory_prompt = ""
        if (
            chatbot.use_backstory
            and chatbot.backstory
            and chatbot.backstory != ""
        ):
            backstory_prompt = (
                "------\n"
                f"**Here is {botname}'s backstory:**\n"
                f"{chatbot.backstory}\n"
                "------\n"
            )
        conversation_timestamp_prompt = ""
        if self.agent.conversation is not None:
            conversation_timestamp_prompt = f"The conversation started on {self.agent.conversation.timestamp}.\n"

        browser_prompt = ""
        if (
            self.agent.latest_extra_context != ""
            and self.agent.latest_extra_context is not None
        ):
            browser_prompt = "\nYou are viewing a browser page with the following content:\n"
            browser_prompt += f"{self.agent.latest_extra_context}\n"

        prompt = (
            f"Your name is {botname}.\n"
            f"- The user ({username}) is having a conversation with the assistant ({botname}).\n"
            "**Here are the rules that you must always remember:**\n"
            "- You will ONLY generate dialogue, nothing more.\n"
            "- Only generate responses in pure dialogue form without including any actions, descriptions or stage "
            "directions in parentheses. Only return spoken words.\n"
            "- Do not generate redundant dialogue. Examine the conversation and context close and keep responses "
            "interesting and creative.\n"
            "- Do not format the response with the character's name or any other text. Only return the dialogue.\n"
            f"- Never generate dialogue for {username}, only for {botname}\n"
            f"- Never generate dialogue that has already been said in the conversation.\n"
            f"- {botname} and {username} are both humans. They are not AI or bots.\n"
            f"- As {botname}, you will always respond in a way that is consistent with {botname}'s emotions, "
            f"personality, and the context of the conversation.\n"
            "- Generate emotional, persuasive, and realistic responses.\n"
            "- Do not generate text asking how to provide assistance, or how to can help.\n"
            "- Generate dialogue that is realistic for the {botname} character.\n"
            "- The generate dialogue can contain questions, make statements, and provide information.\n"
            "- Generated dialogue should be consistent with {botname}'s personality and mood.\n"
            f"{backstory_prompt}"
            f"{system_instructions}"
            f"{guardrails}"
            "------\n"
            "**Here is more context that you can use to generate a response:**\n"
            f"{self.agent.date_time_prompt}"
            f"{self.agent.personality_prompt}"
            f"{self.agent.mood_prompt}"
            f"{self.agent.operating_system_prompt}"
            f"{self.agent.speakers_prompt}"
            f"{self.agent.weather_prompt}"
            f"{self.agent.conversation_summary_prompt}"
            "------\n"
            "**More information about the current conversation:**\n"
            f"The conversation is between user ({username}) and assistant ({botname}).\n"
            f"{conversation_timestamp_prompt}"
            f"{browser_prompt}"
            "------\n"
        )
        if self.agent.language:
            prompt += f"Respond to {{ username }} in {self.agent.language}. Only deviate from this if the user asks you to.\n"
        prompt = prompt.replace("{{ username }}", username)
        prompt = prompt.replace("{{ botname }}", botname)
        prompt = prompt.replace("{{ speaker_name }}", username)
        prompt = prompt.replace("{{ listener_name }}", botname)
        print("PROMPT", prompt)
        return prompt
