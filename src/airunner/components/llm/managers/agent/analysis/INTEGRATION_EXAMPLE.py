"""
Example integration of Analysis System into BaseAgent.

This shows how to wire up the new analysis pipeline.
"""

# Add these imports at the top of base.py
from airunner.components.llm.managers.agent.analysis import (
    AnalysisManager,
    MoodAnalyzer,
    SentimentAnalyzer,
    RelationshipAnalyzer,
)


class BaseAgent:
    """Example modifications to BaseAgent."""

    def __init__(self, *args, **kwargs):
        # ... existing initialization ...

        # Initialize analysis system
        self.analysis_manager = None
        if self.llm_settings.use_conversation_analysis:  # Add this setting
            self.analysis_manager = AnalysisManager(
                analyzers=[
                    MoodAnalyzer(logger=self.logger),
                    SentimentAnalyzer(logger=self.logger),
                    RelationshipAnalyzer(logger=self.logger),
                ],
                parallel=False,  # Set True for parallel (faster)
                logger=self.logger,
            )
            self.logger.info("Conversation analysis enabled")

    def _llm_extract_callable(self, prompt: str, **kwargs) -> str:
        """
        LLM callable for analyzers (similar to knowledge extraction).

        This is the function analyzers use to call the LLM.
        """
        if not hasattr(self, "llm") or self.llm is None:
            self.logger.warning("LLM not available for analysis")
            return "[]"

        try:
            # Merge with base LLM settings
            merged_kwargs = {
                "do_sample": True,
                "temperature": 0.3,
                "max_new_tokens": 200,
                "min_new_tokens": 16,
                "top_p": 0.9,
                "top_k": 10,
                "repetition_penalty": 1.0,
                "use_cache": True,
            }
            merged_kwargs.update(kwargs)

            # Prevent min_length conflict
            if "max_tokens" in merged_kwargs:
                merged_kwargs["max_new_tokens"] = merged_kwargs.pop(
                    "max_tokens"
                )

            merged_kwargs["min_length"] = 0  # Avoid conflict

            self.logger.debug(f"Analysis LLM call with: {merged_kwargs}")

            response = self.llm.complete(prompt, **merged_kwargs)
            result = (
                response.text if hasattr(response, "text") else str(response)
            )

            self.logger.debug(f"Analysis response length: {len(result)} chars")

            return result

        except Exception as e:
            self.logger.error(
                f"LLM call failed during analysis: {e}", exc_info=True
            )
            return "{}"  # Return empty JSON object

    def _run_conversation_analysis(self, user_message: str, bot_response: str):
        """
        Run conversation analysis after generating response.

        Call this after you have both user message and bot response.
        """
        if not self.analysis_manager:
            return

        try:
            self.logger.info("Running conversation analysis...")

            # Get conversation history
            history = []
            if hasattr(self, "chat_memory") and self.chat_memory:
                all_messages = self.chat_memory.get_all()
                # Convert to dict format
                for msg in all_messages:
                    role = getattr(msg, "role", "unknown")
                    content = getattr(msg, "content", "")
                    if not content and hasattr(msg, "blocks"):
                        # Extract from blocks if needed
                        blocks = msg.blocks or []
                        texts = [
                            b.get("text", "") if isinstance(b, dict) else ""
                            for b in blocks
                        ]
                        content = " ".join(texts)
                    history.append({"role": role, "content": content})

            # Run analysis
            context = self.analysis_manager.analyze(
                user_message=user_message,
                bot_response=bot_response,
                llm_callable=self._llm_extract_callable,
                conversation_history=history,
            )

            self.logger.info(
                f"Analysis complete. Mood: {context.mood.get('primary_emotion') if context.mood else 'N/A'}"
            )

            # Update bot mood (emit signal)
            if context.mood and hasattr(self, "chatbot_api"):
                self.chatbot_api.update_mood(
                    mood=context.mood.get("primary_emotion", "neutral"),
                    emoji=context.mood.get("emoji", "😐"),
                )

            # Log full context for debugging
            self.logger.debug(f"Analysis context: {context.to_dict()}")

        except Exception as e:
            self.logger.error(
                f"Conversation analysis failed: {e}", exc_info=True
            )

    def handle_response(self, prompt: str, **kwargs):
        """
        Modified handle_response to include analysis.

        This is pseudo-code showing where to insert analysis.
        """
        # ... existing code to generate response ...
        # response_text = self.generate_response(prompt, **kwargs)

        # AFTER response generation, run analysis
        self._run_conversation_analysis(
            user_message=prompt,
            bot_response=response_text,
        )

        return response_text


# Add to llm_settings.py (or appropriate settings file)
class LLMSettings:
    """Add this setting."""

    use_conversation_analysis: bool = True  # Enable analysis system
    analysis_parallel: bool = False  # Run analyzers in parallel


# Example: How to add a new analyzer later
from airunner.components.llm.managers.agent.analysis import (
    BaseAnalyzer,
    AnalyzerConfig,
)


class EngagementAnalyzer(BaseAnalyzer):
    """Track conversation engagement and energy."""

    def __init__(self, config=None, logger=None):
        if config is None:
            config = AnalyzerConfig(
                temperature=0.3,
                max_new_tokens=200,
            )
        super().__init__(name="engagement", config=config, logger=logger)

    def build_prompt(
        self,
        user_message,
        bot_response,
        conversation_history=None,
        context=None,
    ):
        return f"""Analyze conversation engagement and energy level.

User: {user_message}
Bot: {bot_response}

Rate these factors (0.0 to 1.0):
1. energy_level: How energetic/lively is the conversation?
2. interest: How interested is the user?
3. topic_fatigue: Are they getting tired of the topic?
4. conversation_quality: Overall quality of exchange

Return JSON:
{{
  "energy_level": 0.7,
  "interest": 0.8,
  "topic_fatigue": 0.2,
  "conversation_quality": 0.75
}}

Output (JSON only):"""

    def parse_response(self, response):
        # ... standard JSON parsing ...
        import json
        import re

        response = response.strip()
        json_match = re.search(r"\{[\s\S]*\}", response)
        if json_match:
            response = json_match.group(0)
        try:
            return json.loads(response)
        except:
            return {
                "energy_level": 0.5,
                "interest": 0.5,
                "topic_fatigue": 0.5,
                "conversation_quality": 0.5,
            }

    def should_run(self, context=None):
        # Run every 3 messages
        context = context or {}
        return context.get("message_count", 0) % 3 == 0


# Then add it to the manager:
# agent.analysis_manager.add_analyzer(EngagementAnalyzer())
