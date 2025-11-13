"""Section synthesis mixin for DeepResearchAgent.

This mixin provides methods for synthesizing different sections of research documents
using LLM-generated content.
"""

import logging
from langchain_core.messages import HumanMessage

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
            return """
🔍 CRITICAL: DISAMBIGUATE MULTIPLE PEOPLE
If research notes contain information about DIFFERENT people with similar names:
- Clearly identify each person as a SEPARATE individual
- State distinguishing facts (occupation, age, location, dates)
- DO NOT conflate facts from different people into one biography
- Example: "Joe Curlee (software engineer, active 2025)" vs "Joseph 'Joey' Curlee (farmer, died 2023)"
- Use the exact names and details from the sources to keep them distinct
"""
        else:
            return """
🔍 Note: If sources contain information about different entities with similar names, distinguish them clearly.
"""

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
            notes_content: Full notes content for context
            research_summary: High-level research summary

        Returns:
            Synthesized introduction text
        """
        # Extract relevant notes for context
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

        prompt = f"""Write a comprehensive introduction for a research report on: {topic}

{f"THESIS: {thesis}" if thesis else ""}

{summary_section}RESEARCH NOTES (use these for context and facts):
{relevant_notes}

Key entities: {", ".join(entities[:5])}
Main themes: {", ".join(themes[:3])}
{disambiguation}
❌ ABSOLUTE PROHIBITIONS - VIOLATING THESE IS UNACCEPTABLE:
1. NEVER invent companies, employers, job titles, or work history not in notes
2. NEVER confuse projects/games created with companies worked for
3. NEVER use inflated language like "prominent figure", "renowned expert", "leading authority"
4. NEVER claim accomplishments, awards, or recognition not explicitly in notes
5. NEVER invent mentorship relationships, collaborations, or associations
6. NEVER fabricate names of people, places, or organizations

✅ REQUIRED PRACTICES:
1. ONLY state facts that appear VERBATIM in the research notes
2. Use NEUTRAL, FACTUAL language - no marketing speak or hyperbole
3. If a game/project is mentioned, state: "created [project name]" or "developed [project name]"
4. If employment is mentioned, use EXACT company names and titles from notes
5. Be SPECIFIC to the individual - avoid generic industry background
6. HANDLE FICTION: May mention creative works (e.g., "published story 'X'") but don't treat plot as fact
7. If uncertain or lacking info, write LESS rather than inventing details
8. FACT-CHECK: Before writing each sentence, verify it against the notes

STRUCTURE (CONCISE - ~{word_count} words total):
1. Opening (1 sentence): Identify who/what without inflated claims
2. Key Facts (2-3 sentences): Most important VERIFIED facts from notes
3. Scope (1-2 sentences): What this research covers
4. Transition (1 sentence): Bridge to next section

Write ONLY the introduction content. No labels, headers, or markers."""

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

        # Get disambiguation instructions
        disambiguation = self._get_disambiguation_instructions(topic)

        prompt = f"""Write a detailed background section for a research report on: {topic}

Key entities: {", ".join(entities[:10])}
Main themes: {", ".join(themes)}
{disambiguation}
❌ ABSOLUTE PROHIBITIONS:
1. NEVER write generic industry/field history unless directly tied to the subject
2. NEVER invent projects, products, companies, or affiliations
3. NEVER use inflated language like "prominent", "renowned", "leading", "major contributor"
4. NEVER fabricate employment history, collaborations, or partnerships
5. NEVER confuse projects created with companies worked for
6. If researching a PERSON: NEVER write generic "software engineering background" - be SPECIFIC

✅ REQUIRED PRACTICES:
1. Write ONLY about the SPECIFIC subject being researched
2. Use EXACT names and details from research notes
3. State projects as "created [X]" or "developed [X]", NOT "worked at [X]"
4. Be CONCRETE and SPECIFIC - avoid generic filler
5. Use neutral, factual language - no marketing speak
6. FACT-CHECK each sentence against notes before writing it

STRUCTURE (CONCISE):
1. Core Context (1-2 paragraphs): Specific background of the subject
2. Key Definitions (1 paragraph, IF NEEDED): Define terms only if essential
3. Transition (1 sentence): Bridge to analysis

For PERSON topics: Focus entirely on the individual - skip all generic background.

Write ONLY the background content. No labels or headers."""

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

        # Get disambiguation instructions
        disambiguation = self._get_disambiguation_instructions(topic)

        prompt = f"""Write a comprehensive analysis section for a research report on: {topic}

Key entities to analyze: {", ".join(entities[:10])}
Themes to explore: {", ".join(themes)}
{disambiguation}
❌ ABSOLUTE PROHIBITIONS:
1. NEVER invent companies, employers, job titles, or work history
2. NEVER use inflated claims like "major contributor", "significant impact", "widely recognized"
3. NEVER fabricate statistics, studies, partnerships, or collaborations
4. NEVER confuse projects created with employment
5. NEVER claim mentorship, influence, or reach not documented in notes

✅ REQUIRED PRACTICES:
1. Analyze ONLY facts explicitly stated in notes
2. State projects as "created [X]" or "developed [X]"
3. Use neutral, evidence-based language
4. Acknowledge limitations and gaps in evidence
5. HANDLE FICTION: May mention creative works but don't analyze plot as real events
6. FACT-CHECK: Verify each claim against notes before writing

STRUCTURE (CONCISE):
1. Key Findings (1-2 paragraphs): Most important verifiable discoveries
2. Patterns (1 paragraph): Observable connections or themes (if any)
3. Limitations (1 paragraph): Gaps, uncertainties, or missing information

Write ONLY the analysis content. No labels or headers."""

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

        # Get disambiguation instructions
        disambiguation = self._get_disambiguation_instructions(topic)

        prompt = f"""Write a comprehensive implications section for a research report on: {topic}

Main themes: {", ".join(themes)}
{disambiguation}
❌ ABSOLUTE PROHIBITIONS:
1. NEVER invent scenarios, predictions, or impacts not supported by evidence
2. NEVER use inflated language about significance or impact
3. NEVER make broad industry claims not supported by research
4. NEVER fabricate contributions, influence, or outcomes

✅ REQUIRED PRACTICES:
1. Discuss ONLY implications supported by documented findings
2. Use neutral, evidence-based language
3. Be SPECIFIC to the subject - avoid generic speculation
4. For PERSON topics: Focus on documented work, not inflated claims
5. Acknowledge limitations and uncertainty

STRUCTURE (CONCISE):
1. Significance (1 paragraph): Why findings matter (based on evidence only)
2. Key Takeaways (1 paragraph): Most important supported implications

Write ONLY the implications content. No labels or headers."""

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

        # Get disambiguation instructions
        disambiguation = self._get_disambiguation_instructions(topic)

        prompt = f"""Write a comprehensive conclusion for a research report on: {topic}

Main themes covered: {", ".join(themes)}
{disambiguation}
❌ ABSOLUTE PROHIBITIONS:
1. NEVER introduce new information, claims, or details not in the research
2. NEVER invent companies, employers, projects, affiliations, or accomplishments
3. NEVER use inflated language like "significant contribution", "major impact"
4. NEVER fabricate collaborations, mentorship, or partnerships

✅ REQUIRED PRACTICES:
1. Summarize ONLY findings explicitly documented in research
2. Use neutral, factual language - no marketing speak
3. Be SPECIFIC to the subject - avoid generic conclusions
4. Acknowledge what was NOT found or remains uncertain
5. FACT-CHECK: Verify each statement against research before writing

STRUCTURE (CONCISE):
1. Summary (1-2 paragraphs): Synthesize verified findings
2. Limitations (1 paragraph): Gaps, uncertainties, missing information
3. Closing (1-2 sentences): Final thought

Write ONLY the conclusion content. No labels or headers."""

        try:
            response = self._base_model.invoke([HumanMessage(content=prompt)])
            conclusion = response.content.strip()
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
            response = self._base_model.invoke([HumanMessage(content=prompt)])
            abstract = response.content.strip()
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
        themes = parsed_notes.get("top_themes", [])
        entities = parsed_notes.get("entities", [])
        if isinstance(entities, set):
            entities = list(entities)

        # Get disambiguation instructions
        disambiguation = self._get_disambiguation_instructions(topic)

        # Build context from previous sections
        previous_context = ""
        if previous_sections:
            prev_names = list(previous_sections.keys())[:3]
            previous_context = (
                f"Previous sections covered: {', '.join(prev_names)}"
            )

        prompt = f"""Write a comprehensive section titled "{section_name}" for a research report on: {topic}

Main themes: {", ".join(themes[:5])}
Key entities: {", ".join(entities[:8])}
{previous_context}
{disambiguation}
The section should:
- Address the topic indicated by the section title: "{section_name}"
- Be well-researched and detailed (500-800 words)
- Use clear, professional language
- Include relevant facts and analysis from the research
- Be structured with clear progression of ideas
- Avoid claiming current events or dates
- Use timeless language
- Build naturally on previous sections

Write ONLY the section content, no labels or section headers."""

        try:
            response = self._base_model.invoke([HumanMessage(content=prompt)])
            content = response.content.strip()
            return self._normalize_temporal_references(content)
        except Exception as e:
            logger.error(f"Failed to synthesize {section_name}: {e}")
            return f"Analysis of {section_name.lower()} related to {topic}."
