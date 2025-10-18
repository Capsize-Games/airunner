"""
Sentiment analyzer for detecting user's emotional state.

Helps bot respond with appropriate empathy and tone.
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
class SentimentState:
    """User's emotional state detected from their message."""

    # Overall sentiment
    sentiment: str = "neutral"  # positive, negative, neutral, mixed

    # Specific emotions detected
    emotions: list = None  # joy, sadness, anger, fear, surprise, etc.

    # Intensity
    intensity: float = 0.5  # 0.0 (mild) to 1.0 (intense)

    # Needs/concerns
    user_needs: list = None  # help, validation, information, venting, etc.

    # Tone
    tone: str = "neutral"  # friendly, formal, urgent, casual, frustrated, etc.

    def __post_init__(self):
        if self.emotions is None:
            self.emotions = []
        if self.user_needs is None:
            self.user_needs = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sentiment": self.sentiment,
            "emotions": self.emotions,
            "intensity": self.intensity,
            "user_needs": self.user_needs,
            "tone": self.tone,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SentimentState":
        return cls(
            sentiment=data.get("sentiment", "neutral"),
            emotions=data.get("emotions", []),
            intensity=data.get("intensity", 0.5),
            user_needs=data.get("user_needs", []),
            tone=data.get("tone", "neutral"),
        )


class SentimentAnalyzer(BaseAnalyzer):
    """
    Analyzes user's emotional state and needs.

    Enables emotionally intelligent responses.
    """

    def __init__(
        self,
        config: Optional[AnalyzerConfig] = None,
        logger=None,
    ):
        if config is None:
            config = AnalyzerConfig(
                temperature=0.2,  # Lower temp for more consistent detection
                max_new_tokens=200,
                min_new_tokens=30,
            )
        super().__init__(name="sentiment", config=config, logger=logger)

    def build_prompt(
        self,
        user_message: str,
        bot_response: str,
        conversation_history: Optional[list] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Build prompt for sentiment analysis."""

        prompt = f"""Analyze the user's emotional state and needs from their message.

User's message: {user_message}

Identify:
1. Overall sentiment (positive, negative, neutral, mixed)
2. Specific emotions present (joy, sadness, anger, frustration, excitement, concern, etc.)
3. Intensity of emotion (0.0-1.0 scale)
4. What the user needs (help, validation, information, venting, reassurance, etc.)
5. Tone (friendly, formal, urgent, casual, frustrated, playful, etc.)

Return ONLY valid JSON:
{{
  "sentiment": "positive|negative|neutral|mixed",
  "emotions": ["emotion1", "emotion2"],
  "intensity": 0.7,
  "user_needs": ["need1", "need2"],
  "tone": "friendly|formal|urgent|casual|frustrated|playful|neutral"
}}

Output (JSON only):"""

        return prompt

    def parse_response(self, response: str) -> Dict[str, Any]:
        """Parse sentiment analysis response."""
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

            # Ensure lists
            if "emotions" in data and not isinstance(data["emotions"], list):
                data["emotions"] = [data["emotions"]]
            if "user_needs" in data and not isinstance(
                data["user_needs"], list
            ):
                data["user_needs"] = [data["user_needs"]]

            # Clamp intensity
            if "intensity" in data:
                data["intensity"] = max(
                    0.0, min(1.0, float(data["intensity"]))
                )

            sentiment = SentimentState.from_dict(data)
            return sentiment.to_dict()

        except (json.JSONDecodeError, ValueError, KeyError) as e:
            self.logger.warning(f"Failed to parse sentiment response: {e}")
            self.logger.debug(f"Response was: {response[:200]}")
            return SentimentState().to_dict()
