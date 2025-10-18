"""
Mood analyzer for tracking bot's emotional state.

Analyzes conversation to determine how the bot should feel based on:
- User's tone and sentiment
- Topic of conversation
- Bot's personality traits
- Conversation flow (positive, negative, neutral)
"""

import json
import re
from typing import Dict, Any, Optional
from dataclasses import dataclass

from airunner.components.llm.managers.agent.analysis.base_analyzer import (
    BaseAnalyzer,
    AnalyzerConfig,
)


@dataclass
class MoodState:
    """Multi-dimensional mood state."""

    # Primary emotion (happy, sad, excited, calm, frustrated, etc.)
    primary_emotion: str = "neutral"
    intensity: float = 0.5  # 0.0 (mild) to 1.0 (intense)

    # Emotional dimensions (inspired by psychology)
    valence: float = 0.5  # 0.0 (negative) to 1.0 (positive)
    arousal: float = 0.5  # 0.0 (calm) to 1.0 (excited)
    dominance: float = 0.5  # 0.0 (submissive) to 1.0 (dominant)

    # Social dimensions
    engagement: float = 0.5  # How interested/invested in conversation
    rapport: float = 0.5  # Connection with user

    # Context
    emoji: Optional[str] = "😐"
    description: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "primary_emotion": self.primary_emotion,
            "intensity": self.intensity,
            "valence": self.valence,
            "arousal": self.arousal,
            "dominance": self.dominance,
            "engagement": self.engagement,
            "rapport": self.rapport,
            "emoji": self.emoji,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MoodState":
        return cls(
            primary_emotion=data.get("primary_emotion", "neutral"),
            intensity=data.get("intensity", 0.5),
            valence=data.get("valence", 0.5),
            arousal=data.get("arousal", 0.5),
            dominance=data.get("dominance", 0.5),
            engagement=data.get("engagement", 0.5),
            rapport=data.get("rapport", 0.5),
            emoji=data.get("emoji", "😐"),
            description=data.get("description"),
        )


class MoodAnalyzer(BaseAnalyzer):
    """
    Analyzes conversation to determine bot's emotional state.

    Uses multi-dimensional emotion model for realistic mood simulation.
    """

    def __init__(
        self,
        config: Optional[AnalyzerConfig] = None,
        logger=None,
    ):
        # Mood analysis benefits from slightly higher temperature for variety
        if config is None:
            config = AnalyzerConfig(
                temperature=0.4,
                max_new_tokens=300,
                min_new_tokens=50,
            )
        super().__init__(name="mood", config=config, logger=logger)

    def build_prompt(
        self,
        user_message: str,
        bot_response: str,
        conversation_history: Optional[list] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Build prompt for mood analysis."""
        context = context or {}
        bot_name = context.get("bot_name", "Assistant")
        bot_personality = context.get("bot_personality", "friendly")
        current_mood = context.get("current_mood")

        history_context = ""
        if conversation_history and len(conversation_history) > 0:
            recent = conversation_history[-3:]  # Last 3 exchanges
            history_lines = []
            for msg in recent:
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                if role == "user":
                    history_lines.append(f"User: {content}")
                elif role == "assistant":
                    history_lines.append(f"{bot_name}: {content}")
            history_context = "\n".join(history_lines)

        current_mood_text = ""
        if current_mood:
            current_mood_text = f"""
Current mood state:
- Emotion: {current_mood.get('primary_emotion', 'neutral')}
- Valence (negative/positive): {current_mood.get('valence', 0.5):.2f}
- Arousal (calm/excited): {current_mood.get('arousal', 0.5):.2f}
- Engagement: {current_mood.get('engagement', 0.5):.2f}
"""

        prompt = f"""You are analyzing a conversation to determine {bot_name}'s emotional state.

{bot_name}'s personality: {bot_personality}

{current_mood_text}

Recent conversation:
{history_context if history_context else "(no previous history)"}

Latest exchange:
User: {user_message}
{bot_name}: {bot_response}

Analyze how {bot_name} should feel after this exchange. Consider:
1. User's tone and sentiment
2. Topic sensitivity (personal issues, complaints, praise, etc.)
3. {bot_name}'s personality traits
4. Natural emotional progression from previous mood

Return ONLY valid JSON with this structure:
{{
  "primary_emotion": "happy|sad|excited|calm|frustrated|empathetic|curious|concerned|neutral",
  "intensity": 0.7,
  "valence": 0.6,
  "arousal": 0.5,
  "dominance": 0.5,
  "engagement": 0.8,
  "rapport": 0.7,
  "emoji": "😊",
  "description": "Brief description of emotional state"
}}

Scales are 0.0 to 1.0:
- valence: 0.0=very negative, 1.0=very positive
- arousal: 0.0=very calm, 1.0=very excited
- dominance: 0.0=submissive/uncertain, 1.0=confident/in-control
- engagement: 0.0=disengaged, 1.0=highly engaged
- rapport: 0.0=distant, 1.0=close connection
- intensity: 0.0=mild feeling, 1.0=intense feeling

Output (JSON only):"""

        return prompt

    def parse_response(self, response: str) -> Dict[str, Any]:
        """Parse mood analysis response."""
        response = response.strip()

        # Remove markdown
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        response = response.strip()

        # Extract JSON
        json_match = re.search(r"\{[\s\S]*\}", response)
        if json_match:
            response = json_match.group(0)

        try:
            data = json.loads(response)

            # Clamp values to valid ranges
            for key in [
                "valence",
                "arousal",
                "dominance",
                "engagement",
                "rapport",
                "intensity",
            ]:
                if key in data:
                    data[key] = max(0.0, min(1.0, float(data[key])))

            mood = MoodState.from_dict(data)
            return mood.to_dict()

        except (json.JSONDecodeError, ValueError, KeyError) as e:
            self.logger.warning(f"Failed to parse mood response: {e}")
            self.logger.debug(f"Response was: {response[:200]}")
            # Return neutral mood as fallback
            return MoodState().to_dict()

    def should_run(self, context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Mood should be analyzed periodically, not every message.

        Run every 2-3 messages to save compute.
        """
        context = context or {}
        message_count = context.get("message_count", 0)

        # Always run on first few messages to establish baseline
        if message_count < 3:
            return True

        # Then run every 2 messages
        return message_count % 2 == 0
