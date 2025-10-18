"""
Relationship analyzer for tracking user-bot connection dynamics.

Tracks relationship progression: stranger → acquaintance → friend → close friend
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
class RelationshipState:
    """State of user-bot relationship."""

    # Relationship level
    level: str = "stranger"  # stranger, acquaintance, friend, close_friend

    # Trust & openness
    trust: float = 0.3  # 0.0 (no trust) to 1.0 (complete trust)
    openness: float = 0.3  # How openly user shares personal info

    # Interaction quality
    mutual_understanding: float = 0.3  # How well they "get" each other
    shared_experiences: int = 0  # Number of meaningful exchanges

    # Comfort & familiarity
    comfort_level: float = 0.3  # User's comfort with bot
    formality: float = 0.7  # 0.0=very casual, 1.0=very formal

    def to_dict(self) -> Dict[str, Any]:
        return {
            "level": self.level,
            "trust": self.trust,
            "openness": self.openness,
            "mutual_understanding": self.mutual_understanding,
            "shared_experiences": self.shared_experiences,
            "comfort_level": self.comfort_level,
            "formality": self.formality,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RelationshipState":
        return cls(
            level=data.get("level", "stranger"),
            trust=data.get("trust", 0.3),
            openness=data.get("openness", 0.3),
            mutual_understanding=data.get("mutual_understanding", 0.3),
            shared_experiences=data.get("shared_experiences", 0),
            comfort_level=data.get("comfort_level", 0.3),
            formality=data.get("formality", 0.7),
        )


class RelationshipAnalyzer(BaseAnalyzer):
    """
    Tracks the evolving relationship between user and bot.

    Influences conversation style, formality, and emotional depth.
    """

    def __init__(
        self,
        config: Optional[AnalyzerConfig] = None,
        logger=None,
    ):
        if config is None:
            config = AnalyzerConfig(
                temperature=0.3,
                max_new_tokens=250,
                min_new_tokens=40,
            )
        super().__init__(name="relationship", config=config, logger=logger)

    def build_prompt(
        self,
        user_message: str,
        bot_response: str,
        conversation_history: Optional[list] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Build prompt for relationship analysis."""
        context = context or {}
        current_relationship = context.get("current_relationship", {})

        current_state = ""
        if current_relationship:
            current_state = f"""
Current relationship state:
- Level: {current_relationship.get('level', 'stranger')}
- Trust: {current_relationship.get('trust', 0.3):.2f}
- Openness: {current_relationship.get('openness', 0.3):.2f}
- Shared experiences: {current_relationship.get('shared_experiences', 0)}
"""

        total_messages = (
            len(conversation_history) if conversation_history else 1
        )

        prompt = f"""Analyze the relationship between user and bot based on their conversation.

{current_state}

Total messages exchanged: {total_messages}

Latest exchange:
User: {user_message}
Bot: {bot_response}

Evaluate relationship progression. Consider:
1. Has user shared personal information? (increases trust & openness)
2. Are they asking deeper questions? (increases mutual_understanding)
3. Is conversation becoming more casual? (decreases formality)
4. Was this a meaningful exchange? (increment shared_experiences if yes)
5. Overall relationship level progression

Relationship levels:
- stranger: Initial contact, formal, surface-level
- acquaintance: Some familiarity, moderate trust
- friend: Regular interaction, good trust, personal sharing
- close_friend: Deep trust, very casual, highly personal

Return ONLY valid JSON:
{{
  "level": "stranger|acquaintance|friend|close_friend",
  "trust": 0.5,
  "openness": 0.4,
  "mutual_understanding": 0.5,
  "shared_experiences": 5,
  "comfort_level": 0.6,
  "formality": 0.4
}}

All scales are 0.0 to 1.0 except shared_experiences (integer count).
Values should progress gradually from current state.

Output (JSON only):"""

        return prompt

    def parse_response(self, response: str) -> Dict[str, Any]:
        """Parse relationship analysis response."""
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

            # Clamp float values
            for key in [
                "trust",
                "openness",
                "mutual_understanding",
                "comfort_level",
                "formality",
            ]:
                if key in data:
                    data[key] = max(0.0, min(1.0, float(data[key])))

            # Ensure shared_experiences is int
            if "shared_experiences" in data:
                data["shared_experiences"] = int(data["shared_experiences"])

            relationship = RelationshipState.from_dict(data)
            return relationship.to_dict()

        except (json.JSONDecodeError, ValueError, KeyError) as e:
            self.logger.warning(f"Failed to parse relationship response: {e}")
            self.logger.debug(f"Response was: {response[:200]}")
            return RelationshipState().to_dict()

    def should_run(self, context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Relationship analysis should run less frequently.

        Run every 5 messages to track progression.
        """
        context = context or {}
        message_count = context.get("message_count", 0)

        # Run on first message to establish baseline
        if message_count <= 1:
            return True

        # Then every 5 messages
        return message_count % 5 == 0
