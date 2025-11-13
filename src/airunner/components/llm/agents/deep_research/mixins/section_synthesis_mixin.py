"""Section synthesis mixin for DeepResearchAgent.

This mixin provides methods for synthesizing different sections of research documents
using LLM-generated content.
"""

import logging
from langchain_core.messages import HumanMessage

logger = logging.getLogger(__name__)


class SectionSynthesisMixin:
    """Provides section synthesis methods for research documents."""

    def _synthesize_introduction(
        self,
        topic: str,
        parsed_notes: dict,
        thesis: str = "",
        previous_sections: dict = None,
        word_count: int = 500,
    ) -> str:
        """Synthesize an introduction section.

        Args:
            topic: The research topic
            parsed_notes: Parsed research notes
            thesis: The thesis statement (optional)
            previous_sections: Previously written sections (optional)
            word_count: Target word count (default: 500)

        Returns:
            Synthesized introduction text
        """
        # Convert sets to lists if necessary
        entities = parsed_notes.get("entities", [])
        if isinstance(entities, set):
            entities = list(entities)
        # Use top_themes (list) instead of themes (dict)
        themes = parsed_notes.get("top_themes", [])

        prompt = f"""Write a comprehensive introduction for a research report on: {topic}

Key entities to mention: {", ".join(entities[:5])}
Main themes to cover: {", ".join(themes[:3])}

The introduction should:
- Be approximately {word_count} words
- Provide context and background
- Clearly state the purpose and scope
- Preview main themes and findings
- Be engaging and well-structured
- Avoid claiming current events or dates
- Use timeless language

Write ONLY the introduction content, no labels or section headers."""

        try:
            response = self._base_model.invoke([HumanMessage(content=prompt)])
            intro = response.content.strip()

            # Validate the introduction
            if len(intro.split()) < word_count // 2:
                logger.warning("Introduction too short, using fallback")
                return self._fallback_introduction(topic, parsed_notes)

            return self._normalize_temporal_references(intro)

        except Exception as e:
            logger.error(f"Failed to synthesize introduction: {e}")
            return self._fallback_introduction(topic, parsed_notes)

    def _fallback_introduction(self, topic: str, parsed_notes: dict) -> str:
        """Generate a basic introduction fallback.

        Args:
            topic: The research topic
            parsed_notes: Parsed research notes

        Returns:
            Basic introduction text
        """
        themes = parsed_notes.get("themes", [])
        theme_text = (
            f" Key areas of focus include {', '.join(themes[:3])}."
            if themes
            else ""
        )
        return f"This research report examines {topic}.{theme_text}"

    def _synthesize_background(
        self,
        topic: str,
        parsed_notes: dict,
        thesis: str = "",
        previous_sections: dict = None,
    ) -> str:
        """Synthesize a background section.

        Args:
            topic: The research topic
            parsed_notes: Parsed research notes
            thesis: The thesis statement (optional)
            previous_sections: Previously written sections (optional)

        Returns:
            Synthesized background text
        """
        # Convert sets to lists if necessary
        entities = parsed_notes.get("entities", [])
        if isinstance(entities, set):
            entities = list(entities)
        # Use top_themes (list) instead of themes (dict)
        themes = parsed_notes.get("top_themes", [])

        prompt = f"""Write a detailed background section for a research report on: {topic}

Key entities: {", ".join(entities[:10])}
Main themes: {", ".join(themes)}

The background should:
- Provide historical context and evolution
- Define key concepts and terminology
- Explain relevant theories or frameworks
- Be well-structured with clear progression
- Avoid claiming current events or dates
- Use timeless, evergreen language

Write ONLY the background content, no labels or section headers."""

        try:
            response = self._base_model.invoke([HumanMessage(content=prompt)])
            background = response.content.strip()
            return self._normalize_temporal_references(background)
        except Exception as e:
            logger.error(f"Failed to synthesize background: {e}")
            return f"Background information on {topic}."

    def _synthesize_analysis(
        self,
        topic: str,
        parsed_notes: dict,
        thesis: str = "",
        previous_sections: dict = None,
    ) -> str:
        """Synthesize an analysis section.

        Args:
            topic: The research topic
            parsed_notes: Parsed research notes
            thesis: The thesis statement (optional)
            previous_sections: Previously written sections (optional)

        Returns:
            Synthesized analysis text
        """
        # Convert sets to lists if necessary
        entities = parsed_notes.get("entities", [])
        if isinstance(entities, set):
            entities = list(entities)
        # Use top_themes (list) instead of themes (dict)
        themes = parsed_notes.get("top_themes", [])

        prompt = f"""Write a comprehensive analysis section for a research report on: {topic}

Key entities to analyze: {", ".join(entities[:10])}
Themes to explore: {", ".join(themes)}

The analysis should:
- Examine patterns, trends, and relationships
- Compare and contrast different perspectives
- Identify strengths, weaknesses, and gaps
- Use evidence-based reasoning
- Be balanced and objective
- Avoid claiming current events or dates
- Use timeless language

Write ONLY the analysis content, no labels or section headers."""

        try:
            response = self._base_model.invoke([HumanMessage(content=prompt)])
            analysis = response.content.strip()
            return self._normalize_temporal_references(analysis)
        except Exception as e:
            logger.error(f"Failed to synthesize analysis: {e}")
            return f"Analysis of {topic}."

    def _synthesize_implications(
        self,
        topic: str,
        parsed_notes: dict,
        thesis: str = "",
        previous_sections: dict = None,
    ) -> str:
        """Synthesize an implications section.

        Args:
            topic: The research topic
            parsed_notes: Parsed research notes
            thesis: The thesis statement (optional)
            previous_sections: Previously written sections (optional)

        Returns:
            Synthesized implications text
        """
        # Use top_themes (list) instead of themes (dict)
        themes = parsed_notes.get("top_themes", [])

        prompt = f"""Write a comprehensive implications section for a research report on: {topic}

Main themes: {", ".join(themes)}

The implications should:
- Discuss practical applications and consequences
- Identify key stakeholders and impacts
- Highlight opportunities and challenges
- Consider short-term and long-term effects
- Be forward-looking but not speculative
- Avoid claiming current events or dates
- Use timeless language

Write ONLY the implications content, no labels or section headers."""

        try:
            response = self._base_model.invoke([HumanMessage(content=prompt)])
            implications = response.content.strip()
            return self._normalize_temporal_references(implications)
        except Exception as e:
            logger.error(f"Failed to synthesize implications: {e}")
            return f"Implications of findings on {topic}."

    def _synthesize_conclusion(
        self,
        topic: str,
        parsed_notes: dict,
        thesis: str = "",
        previous_sections: dict = None,
    ) -> str:
        """Synthesize a conclusion section.

        Args:
            topic: The research topic
            parsed_notes: Parsed research notes
            thesis: The thesis statement (optional)
            previous_sections: Previously written sections (optional)

        Returns:
            Synthesized conclusion text
        """
        # Use top_themes (list) instead of themes (dict)
        themes = parsed_notes.get("top_themes", [])

        prompt = f"""Write a comprehensive conclusion for a research report on: {topic}

Main themes covered: {", ".join(themes)}

The conclusion should:
- Summarize key findings and insights
- Reinforce main arguments and themes
- Provide synthesis and integration
- Offer final reflections and takeaways
- Be concise yet comprehensive
- Avoid claiming current events or dates
- Use timeless language

Write ONLY the conclusion content, no labels or section headers."""

        try:
            response = self._base_model.invoke([HumanMessage(content=prompt)])
            conclusion = response.content.strip()
            return self._normalize_temporal_references(conclusion)
        except Exception as e:
            logger.error(f"Failed to synthesize conclusion: {e}")
            return f"Conclusion of research on {topic}."
