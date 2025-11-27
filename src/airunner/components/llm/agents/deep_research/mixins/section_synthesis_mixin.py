"""Section synthesis mixin for DeepResearchAgent.

This mixin provides methods for synthesizing different sections of research documents
using LLM-generated content.
"""

import logging
import re
from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)


class SectionSynthesisMixin:
    """Provides section synthesis methods for research documents."""

    @staticmethod
    def _get_disambiguation_instructions(topic: str) -> str:
        """Get instructions for disambiguating multiple people/entities.

        Args:
            topic: The research topic

        Returns:
            Disambiguation instructions to include in LLM prompts
        """
        # Check if this is likely a person (2+ words, no obvious non-person indicators)
        topic_lower = topic.lower()
        is_person = len(topic.split()) >= 2 and not any(
            keyword in topic_lower
            for keyword in [
                "company",
                "organization",
                "event",
                "concept",
                "the ",
            ]
        )

        if is_person:
            return """CRITICAL: DISAMBIGUATE INDIVIDUALS
- Treat every person with a similar name as a separate individual
- Include distinguishing facts (role, organization, timeframe, geography)
- Never merge biographies or attributes unless sources explicitly do so
- Use titles that match the timeframe being described; avoid guessing current roles

TIMELINE ACCURACY:
- Anchor statements to the evidence provided (dates, elections, appointments)
- If the timeframe is unclear, describe the action relative to the cited source rather than to "now"
"""
        else:
            return """CRITICAL: DISAMBIGUATE ENTITIES
- Distinguish organizations, agencies, or locations that share similar names
- Note jurisdiction, mission, or geography to keep them separate
- Avoid blending facts from different entities into one description
"""

    def _prepend_synthesis_system_prompt(self, messages: list) -> None:
        """Insert the prose-writing system prompt ahead of user instructions."""

        prompt = (
            self._get_synthesis_system_prompt()
            if hasattr(self, "_get_synthesis_system_prompt")
            else getattr(self, "_synthesis_system_prompt", None)
        )
        if not prompt:
            prompt = getattr(self, "_system_prompt", None)
        if prompt:
            messages.insert(0, SystemMessage(content=prompt))

    @staticmethod
    def _writing_rules() -> str:
        """Return shared guardrails for synthesis prompts."""

        return """RULES:
- Use only facts supported by the provided research notes or context.
- Keep tone neutral, analytical, and timeless (avoid 'currently', 'recently').
- Never invent organizations, people, numbers, or relationships.
    - Only assign formal titles or offices to people if that exact pairing appears in the notes; otherwise describe them generically or acknowledge the uncertainty.
- If information is missing, acknowledge the gap instead of speculating.
- Quote or paraphrase carefully—every claim must be traceable to the notes.
- Align conclusions with the cited evidence (e.g., refusing to sign a safety pledge is evidence of opposition to regulation, not support for it).
- Each section must advance the argument with at least one NEW stake, data point, or perspective; mention earlier material only to show contrast or consequence.
- Vary diction—reuse of the same descriptive word more than a few times per section is discouraged.
- AVOID REPETITIVE STARTS: Do not start paragraphs with "The administration's stance", "This approach", "The current administration", or similar phrases. Vary your sentence structures (e.g., start with a preposition, a dependent clause, or the subject of the action).
- AVOID TITLE ECHO: Do not overuse words from the research topic (e.g., if the topic is "National Housing Agenda", avoid repeating "agenda" constantly). Use synonyms like "position", "perspective", "policy", "viewpoint".
- Never narrate the writing process (omit phrases such as "here is the section" or "next section")."""

    def _format_previous_section_summaries(
        self,
        previous_sections: dict | None,
        max_sections: int = 3,
        max_chars: int = 220,
    ) -> str:
        """Return short summaries of prior sections to discourage repetition."""

        if not previous_sections:
            return ""

        summaries = []
        items = list(previous_sections.items())[-max_sections:]
        for name, text in items:
            snippet = self._extract_section_snippet(text, max_chars)
            if snippet:
                summaries.append(f"- {name}: {snippet}")

        if not summaries:
            return ""

        summary_block = "\n".join(summaries)
        return (
            "PREVIOUSLY COVERED (avoid repeating these points):\n"
            f"{summary_block}\n\n"
        )

    @staticmethod
    def _extract_section_snippet(text: str, max_chars: int) -> str:
        """Pull the first sentence or two from a section for prompt context."""

        if not text:
            return ""

        clean = re.sub(r"\s+", " ", text.strip())
        if not clean:
            return ""

        sentences = re.split(r"(?<=[\.!?])\s+", clean)
        snippet = sentences[0] if sentences else clean

        if len(snippet) > max_chars:
            snippet = snippet[: max_chars - 3].rstrip() + "..."

        return snippet

    def _extract_relevant_notes(
        self, notes_content: str, max_chars: int = 8000
    ) -> str:
        """Extract relevant portions of notes for synthesis.

        Args:
            notes_content: Full notes content
            max_chars: Maximum characters to include

        Returns:
            Trimmed notes content
        """
        if len(notes_content) <= max_chars:
            return notes_content

        # Try to extract just the notes section (skip metadata header)
        if "## Notes" in notes_content:
            notes_section = notes_content.split("## Notes", 1)[1]
            if len(notes_section) <= max_chars:
                return notes_section
            # Truncate to max_chars
            return (
                notes_section[:max_chars]
                + "\n\n[Additional notes truncated...]"
            )

        # Fallback: just truncate
        return (
            notes_content[:max_chars] + "\n\n[Additional notes truncated...]"
        )

    def _synthesize_introduction(
        self,
        topic: str,
        parsed_notes: dict,
        thesis: str = "",
        previous_sections: dict = None,
        word_count: int = 500,
        notes_content: str = "",
        research_summary: str = "",
    ) -> str:
        """Synthesize an introduction section.

        Args:
            topic: The research topic
            parsed_notes: Parsed research notes
            thesis: The thesis statement (optional)
            previous_sections: Previously written sections (optional)
            word_count: Target word count (default: 500)
            notes_content: Full notes content for context (fallback if RAG unavailable)
            research_summary: High-level research summary

        Returns:
            Synthesized introduction text
        """
        # Try to get context from RAG first
        rag_context = self._query_rag_for_section(
            "introduction", topic, max_results=8
        )

        if rag_context:
            logger.info(
                f"[Synthesis] Using RAG context for introduction ({len(rag_context)} chars)"
            )
            relevant_notes = rag_context
        else:
            # Fallback to direct notes extraction
            logger.info(
                "[Synthesis] RAG unavailable, using direct notes for introduction"
            )
            relevant_notes = self._extract_relevant_notes(
                notes_content, max_chars=6000
            )

        # Convert sets to lists if necessary
        entities = parsed_notes.get("entities", [])
        if isinstance(entities, set):
            entities = list(entities)
        # Use top_themes (list) instead of themes (dict)
        themes = parsed_notes.get("top_themes", [])

        # Get disambiguation instructions
        disambiguation = self._get_disambiguation_instructions(topic)

        # Build prompt with summary if available
        summary_section = ""
        if research_summary:
            summary_section = f"""RESEARCH SUMMARY (high-level overview):
{research_summary}

"""

        rules = self._writing_rules()
        prompt = f"""Write an introduction (~{word_count} words) for a research report on {topic}.

    {f'THESIS: {thesis}\n' if thesis else ''}{summary_section}RESEARCH NOTES:
    {relevant_notes}

    Key entities: {", ".join(entities[:5])}
    Main themes: {", ".join(themes[:3])}
    {disambiguation}
    {rules}

    Structure:
    1. Opening sentence that frames the topic and stakes.
    2. 2-3 sentences summarizing the most relevant verified facts tied to the thesis.
    3. Closing sentence that previews the report's scope.

    Return only the introduction text—no labels or extra commentary."""

        try:
            messages = [HumanMessage(content=prompt)]
            self._prepend_synthesis_system_prompt(messages)
            response = self._base_model.invoke(
                messages,
                temperature=0.3,
                max_new_tokens=1024,
            )
            intro = self._clean_llm_output(
                response.content.strip(), "Introduction"
            )

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
        # Query RAG for background-specific context
        rag_context = self._query_rag_for_section(
            "background", topic, max_results=8
        )

        if rag_context:
            logger.info(
                f"[Synthesis] Using RAG context for background ({len(rag_context)} chars)"
            )
            context_section = f"""RESEARCH NOTES (use these for context and facts):
{rag_context}

"""
        else:
            logger.info("[Synthesis] RAG unavailable for background section")
            context_section = ""

        # Convert sets to lists if necessary
        entities = parsed_notes.get("entities", [])
        if isinstance(entities, set):
            entities = list(entities)
        # Use top_themes (list) instead of themes (dict)
        themes = parsed_notes.get("top_themes", [])

        # Get disambiguation instructions
        disambiguation = self._get_disambiguation_instructions(topic)

        rules = self._writing_rules()
        prompt = f"""Write a concise background section for a research report on {topic}.

    {context_section}Key entities: {", ".join(entities[:10])}
    Main themes: {", ".join(themes)}
    {disambiguation}
    {rules}

    Focus on:
    - Core context that explains why the topic matters.
    - Brief definitions only when essential for understanding.
    - A final sentence that transitions toward analysis.

    Return only the background text without headers."""

        try:
            messages = [HumanMessage(content=prompt)]
            self._prepend_synthesis_system_prompt(messages)
            response = self._base_model.invoke(
                messages,
                temperature=0.3,
                max_new_tokens=1536,
            )
            background = self._clean_llm_output(
                response.content.strip(), "Background"
            )
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
        # Query RAG for analysis-specific context
        rag_context = self._query_rag_for_section(
            "analysis", topic, max_results=8
        )

        if rag_context:
            logger.info(
                f"[Synthesis] Using RAG context for analysis ({len(rag_context)} chars)"
            )
            context_section = f"""RESEARCH NOTES (use these for context and facts):
{rag_context}

"""
        else:
            logger.info("[Synthesis] RAG unavailable for analysis section")
            context_section = ""

        # Convert sets to lists if necessary
        entities = parsed_notes.get("entities", [])
        if isinstance(entities, set):
            entities = list(entities)
        # Use top_themes (list) instead of themes (dict)
        themes = parsed_notes.get("top_themes", [])

        # Get disambiguation instructions
        disambiguation = self._get_disambiguation_instructions(topic)

        previous_summary = self._format_previous_section_summaries(
            previous_sections
        )

        differentiation_rules = """DIFFERENTIATION RULES:
- Lead with a claim unique to this section and tie it to new evidence.
- Mention earlier material only to contrast or escalate the stakes.
- Close by pointing to the next unresolved tension or decision."""

        rules = self._writing_rules()
        prompt = f"""Write an analysis section for a research report on {topic}.

    {context_section}{previous_summary}Key entities to analyze: {", ".join(entities[:10])}
    Themes to explore: {", ".join(themes)}
    {disambiguation}
    {rules}
    {differentiation_rules}

    Structure:
    1. Key findings grounded in the notes.
    2. Patterns or tensions that emerge from those findings.
    3. Limitations or unanswered questions.

    Return only the analysis text without extra commentary."""

        try:
            messages = [HumanMessage(content=prompt)]
            self._prepend_synthesis_system_prompt(messages)
            response = self._base_model.invoke(
                messages,
                temperature=0.3,
                max_new_tokens=1536,
            )
            analysis = self._clean_llm_output(
                response.content.strip(), "Analysis"
            )
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
        # Query RAG for implications-specific context
        rag_context = self._query_rag_for_section(
            "implications", topic, max_results=6
        )

        if rag_context:
            logger.info(
                f"[Synthesis] Using RAG context for implications ({len(rag_context)} chars)"
            )
            context_section = f"""RESEARCH NOTES (use these for context and facts):
{rag_context}

"""
        else:
            logger.info("[Synthesis] RAG unavailable for implications section")
            context_section = ""

        # Use top_themes (list) instead of themes (dict)
        themes = parsed_notes.get("top_themes", [])

        # Get disambiguation instructions
        disambiguation = self._get_disambiguation_instructions(topic)

        previous_summary = self._format_previous_section_summaries(
            previous_sections
        )

        differentiation_rules = """DIFFERENTIATION RULES:
- Extract new consequences or stakeholder impacts rather than repeating earlier observations.
- Each paragraph should link evidence to a clear implication for policy, markets, or society.
- End with a forward-looking signal about what decision or risk remains."""

        rules = self._writing_rules()
        prompt = f"""Write an implications section for a research report on {topic}.

    {context_section}{previous_summary}Main themes: {", ".join(themes)}
    {disambiguation}
    {rules}
    {differentiation_rules}

    Focus on:
    - Evidence-backed significance of the findings.
    - Concrete takeaways for policy, industry, or stakeholders.
    - Any constraints or uncertainties the reader should keep in mind.

    Return only the implications text—no headers."""

        try:
            messages = [HumanMessage(content=prompt)]
            self._prepend_synthesis_system_prompt(messages)
            response = self._base_model.invoke(
                messages,
                temperature=0.3,
                max_new_tokens=1536,
            )
            implications = self._clean_llm_output(
                response.content.strip(), "Implications"
            )
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

        # Get disambiguation instructions
        disambiguation = self._get_disambiguation_instructions(topic)

        rules = self._writing_rules()
        prompt = f"""Write a conclusion for a research report on {topic}.

    Main themes covered: {", ".join(themes)}
    {disambiguation}
    {rules}

    Structure:
    1. Brief synthesis of the verified findings.
    2. Explicit mention of gaps or limitations.
    3. A closing sentence that reinforces the report's purpose without introducing new facts.

    Return only the conclusion text."""

        try:
            messages = [HumanMessage(content=prompt)]
            self._prepend_synthesis_system_prompt(messages)
            response = self._base_model.invoke(
                messages,
                temperature=0.3,
                max_new_tokens=1024,
            )
            conclusion = self._clean_llm_output(
                response.content.strip(), "Conclusion"
            )
            return self._normalize_temporal_references(conclusion)
        except Exception as e:
            logger.error(f"Failed to synthesize conclusion: {e}")
            return f"Conclusion of research on {topic}."

    def _synthesize_abstract(
        self,
        topic: str,
        parsed_notes: dict,
        thesis: str = "",
        previous_sections: dict = None,
        notes_content: str = "",
        research_summary: str = "",
    ) -> str:
        """Synthesize an abstract section.

        Args:
            topic: The research topic
            parsed_notes: Parsed research notes
            thesis: The thesis statement (optional)
            previous_sections: Previously written sections (optional)
            notes_content: Full notes content (unused here)
            research_summary: High-level research summary

        Returns:
            Synthesized abstract text
        """
        themes = parsed_notes.get("top_themes", [])
        num_sources = len(parsed_notes.get("sources", []))

        # Build prompt with summary if available
        summary_section = ""
        if research_summary:
            summary_section = f"""RESEARCH SUMMARY (high-level overview):
{research_summary}

"""

        prompt = f"""Write a concise abstract for a research report on: {topic}

{summary_section}Main themes: {", ".join(themes[:5])}
Thesis: {thesis if thesis else "Comprehensive analysis of " + topic}
Number of sources: {num_sources}

The abstract should:
- Be 150-250 words
- Summarize the scope and purpose of the research
- Highlight key themes and findings
- Be self-contained and informative
- Avoid claiming current events or dates
- Use timeless, professional language

Write ONLY the abstract content, no labels or section headers."""

        try:
            messages = [HumanMessage(content=prompt)]
            self._prepend_synthesis_system_prompt(messages)
            response = self._base_model.invoke(
                messages,
                temperature=0.3,
                max_new_tokens=512,
            )
            abstract = self._clean_llm_output(
                response.content.strip(), "Abstract"
            )
            return self._normalize_temporal_references(abstract)
        except Exception as e:
            logger.error(f"Failed to synthesize abstract: {e}")
            return f"This research examines {topic} through comprehensive analysis of available sources."

    def _synthesize_generic_section(
        self,
        section_name: str,
        topic: str,
        parsed_notes: dict,
        thesis: str = "",
        previous_sections: dict = None,
    ) -> str:
        """Synthesize a generic custom section based on its name.

        Args:
            section_name: Name of the section to synthesize
            topic: The research topic
            parsed_notes: Parsed research notes
            thesis: The thesis statement (optional)
            previous_sections: Previously written sections (optional)

        Returns:
            Synthesized section text
        """
        # Query RAG for section-specific context
        rag_context = self._query_rag_for_section(
            section_name, topic, max_results=8
        )

        if rag_context:
            logger.info(
                f"[Synthesis] Using RAG context for '{section_name}' ({len(rag_context)} chars)"
            )
            context_section = f"""RESEARCH NOTES (use these for context and facts):
{rag_context}

"""
        else:
            logger.info(
                f"[Synthesis] RAG unavailable for '{section_name}' section"
            )
            context_section = ""

        themes = parsed_notes.get("top_themes", [])
        entities = parsed_notes.get("entities", [])
        if isinstance(entities, set):
            entities = list(entities)

        # Get disambiguation instructions
        disambiguation = self._get_disambiguation_instructions(topic)

        previous_summary = self._format_previous_section_summaries(
            previous_sections
        )

        differentiation_rules = """DIFFERENTIATION RULES:
- Start with the tension or question unique to this section title.
- Introduce at least one piece of evidence not fully explored earlier (see summaries above).
- Use transitions that show progress (cause → effect, action → response) instead of restating context.
- Finish with a sentence that tees up the next unresolved thread or implication."""

        rules = self._writing_rules()
        prompt = f"""Write a {section_name} section (target 500-800 words) for a research report on {topic}.

    {context_section}{previous_summary}Main themes: {", ".join(themes[:5])}
    Key entities: {", ".join(entities[:8])}
    {disambiguation}
    {rules}
    {differentiation_rules}

    Guidance:
    - Address the focus implied by "{section_name}" and tie every claim to the notes.
    - Organize the section with a clear beginning, middle, and end so ideas flow naturally.
    - Reference earlier sections only when it adds clarity; otherwise keep the section self-contained.

    Return only the section text (no extra labels)."""

        try:
            messages = [HumanMessage(content=prompt)]
            self._prepend_synthesis_system_prompt(messages)
            response = self._base_model.invoke(
                messages,
                temperature=0.3,
                max_new_tokens=1536,
            )
            content = self._clean_llm_output(
                response.content.strip(), section_name
            )
            return self._normalize_temporal_references(content)
        except Exception as e:
            logger.error(f"Failed to synthesize {section_name}: {e}")
            return f"Analysis of {section_name.lower()} related to {topic}."

    def _synthesize_sources(self, parsed_notes: dict) -> str:
        """Synthesize Sources section from parsed notes.

        Args:
            parsed_notes: Parsed research notes containing source URLs

        Returns:
            Formatted sources section with numbered list of URLs
        """
        # Extract unique source URLs from parsed notes
        sources = parsed_notes.get("sources", [])

        if not sources:
            logger.warning("[Synthesis] No sources found in parsed notes")
            return "No sources were recorded during research."

        # Format sources as numbered list
        source_lines = []
        for i, source in enumerate(sources, 1):
            # Handle both string URLs and dict objects
            if isinstance(source, dict):
                url = source.get("url", "")
                title = source.get("title", "")
                if title:
                    source_lines.append(f"{i}. [{title}]({url})")
                else:
                    source_lines.append(f"{i}. {url}")
            else:
                source_lines.append(f"{i}. {source}")

        sources_text = "\n".join(source_lines)
        logger.info(
            f"[Synthesis] Generated sources list with {len(sources)} entries"
        )

        return sources_text
