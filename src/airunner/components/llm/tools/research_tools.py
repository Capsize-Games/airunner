"""Research mode tools for synthesis and durable evidence capture."""

from typing import Any, List

from airunner.components.agents.runtime import AgentRunStatus
from airunner.components.agents.runtime import ResearchBriefRecord
from airunner.components.agents.runtime import ResearchEvidenceRecord
from airunner.components.agents.runtime import ResearchReviewStatus
from airunner.components.agents.runtime import ResearchRunRecord
from airunner.components.agents.runtime import ResearchSourceRecord
from airunner.components.document_editor.project import AirunnerProjectService
from airunner.components.document_editor.project import (
    AirunnerProjectStateService,
)
from airunner.components.document_editor.project.airunner_active_project import (
    get_active_project_path,
)
from airunner.components.llm.core.tool_registry import tool, ToolCategory
from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


# Note: Web search and scraping tools are currently in web_tools.py
# They will be migrated here in a future update, but for now we create
# complementary research-specific tools


def _resolve_research_project_path(project_path: str = "") -> str:
    """Return the initialized project path for research state tools."""
    resolved = project_path or get_active_project_path() or ""
    if not resolved:
        raise ValueError(
            "Research tools require an active or explicit project path."
        )
    project_service = AirunnerProjectService(resolved)
    if not project_service.exists():
        raise ValueError("Research tools require an initialized project.")
    return project_service.project_path


def _research_state_service(
    project_path: str = "",
) -> AirunnerProjectStateService:
    """Return the project-state service used by research tools."""
    project_service = AirunnerProjectService(
        _resolve_research_project_path(project_path)
    )
    return AirunnerProjectStateService(project_service)


def _review_status(status: str = "") -> ResearchReviewStatus | None:
    """Return the normalized research review status filter."""
    if not status:
        return None
    return ResearchReviewStatus(status)


def _source_payload(source: ResearchSourceRecord) -> dict[str, Any]:
    """Return a compact tool payload for one research source."""
    return {
        "source_id": source.record_id,
        "title": source.title,
        "url": source.url,
        "status": source.status.value,
        "excerpt": source.excerpt,
        "authors": list(source.authors),
        "failure_reason": source.failure_reason,
    }


def _evidence_match_blob(
    evidence: ResearchEvidenceRecord,
    sources: list[ResearchSourceRecord],
) -> str:
    """Return searchable text for one evidence record and its sources."""
    source_text = "\n".join(
        f"{source.title}\n{source.url}\n{source.excerpt}" for source in sources
    )
    metadata_text = "\n".join(
        str(value) for value in evidence.metadata.values()
    )
    return "\n".join(
        [
            evidence.fact_text,
            evidence.quote_text,
            evidence.numeric_value,
            evidence.numeric_unit,
            evidence.confidence,
            source_text,
            metadata_text,
        ]
    ).lower()


def _evidence_payload(
    evidence: ResearchEvidenceRecord,
    sources: list[ResearchSourceRecord],
) -> dict[str, Any]:
    """Return a compact tool payload for one evidence match."""
    return {
        "evidence_id": evidence.record_id,
        "run_id": evidence.run_id,
        "status": evidence.status.value,
        "evidence_kind": evidence.evidence_kind,
        "confidence": evidence.confidence,
        "fact_text": evidence.fact_text,
        "quote_text": evidence.quote_text,
        "numeric_value": evidence.numeric_value,
        "numeric_unit": evidence.numeric_unit,
        "source_ids": list(evidence.source_ids),
        "sources": [_source_payload(source) for source in sources],
    }


def _confidence_weight(confidence: str) -> float:
    """Return a numeric weight for one evidence confidence label."""
    weights = {"high": 1.0, "medium": 0.7, "low": 0.4}
    return weights.get(confidence.lower(), 0.5)


def _brief_summary(
    title: str,
    source_count: int,
    supported_findings: list[str],
    open_questions: list[str],
    coverage_score: float,
    confidence_score: float,
) -> str:
    """Return a deterministic executive summary for one brief."""
    summary = (
        f"{title} uses {source_count} recorded sources and "
        f"{len(supported_findings)} supported findings. Coverage is "
        f"{coverage_score:.2f} and confidence is {confidence_score:.2f}."
    )
    if supported_findings:
        summary += f" Strongest supported finding: {supported_findings[0]}"
    if open_questions:
        summary += f" Open question: {open_questions[0]}"
    return summary


def _brief_markdown(brief: ResearchBriefRecord) -> str:
    """Render one research brief package as stable markdown."""
    lines = [
        f"# {brief.title}",
        "",
        "## Executive Summary",
        "",
        brief.executive_summary,
        "",
        "## Coverage",
        "",
        f"- Coverage score: {brief.coverage_score:.2f}",
        f"- Confidence score: {brief.confidence_score:.2f}",
        "",
        "## Supported Findings",
        "",
    ]
    findings = brief.supported_findings or ["No supported findings yet."]
    for finding in findings:
        lines.append(f"- {finding}")
    lines.extend(["", "## Open Questions", ""])
    questions = brief.open_questions or ["No open questions recorded."]
    for question in questions:
        lines.append(f"- {question}")
    lines.extend(["", "## Weak Evidence", ""])
    weak_ids = brief.weak_evidence_ids or ["No weak evidence recorded."]
    for evidence_id in weak_ids:
        lines.append(f"- {evidence_id}")
    return "\n".join(lines)


@tool(
    name="start_research_run",
    category=ToolCategory.RESEARCH,
    description=(
        "Create a durable research run ledger inside the active AIRunner "
        "project before collecting sources or evidence."
    ),
)
def start_research_run(
    topic: str,
    query: str = "",
    project_path: str = "",
) -> dict[str, Any]:
    """Create one research run for durable source and evidence capture."""
    state_service = _research_state_service(project_path)
    research_run = ResearchRunRecord(
        topic=topic,
        query=query,
        status=AgentRunStatus.RUNNING,
    )
    state_service.save_research_run(research_run)
    return {
        "research_run_id": research_run.record_id,
        "topic": research_run.topic,
        "status": research_run.status.value,
        "project_path": state_service.project_service.project_path,
    }


@tool(
    name="record_research_source",
    category=ToolCategory.RESEARCH,
    description=(
        "Persist one accepted, rejected, or unresolved source with "
        "metadata for a research run."
    ),
)
def record_research_source(
    research_run_id: str,
    url: str,
    title: str = "",
    status: str = "unresolved",
    source_type: str = "web",
    excerpt: str = "",
    authors: List[str] | None = None,
    published_at: str = "",
    failure_reason: str = "",
    source_notes: str = "",
    project_path: str = "",
) -> dict[str, Any]:
    """Persist one research source under the active AIRunner project."""
    state_service = _research_state_service(project_path)
    source = ResearchSourceRecord(
        run_id=research_run_id,
        url=url,
        title=title,
        status=ResearchReviewStatus(status),
        source_type=source_type,
        excerpt=excerpt,
        authors=list(authors or []),
        published_at=published_at,
        failure_reason=failure_reason,
        metadata={"source_notes": source_notes} if source_notes else {},
    )
    state_service.save_research_source(source)
    return _source_payload(source) | {"research_run_id": research_run_id}


@tool(
    name="record_research_evidence",
    category=ToolCategory.RESEARCH,
    description=(
        "Persist one research fact, quote, or numeric finding with "
        "source attribution and review status."
    ),
)
def record_research_evidence(
    research_run_id: str,
    fact_text: str,
    source_ids: List[str],
    status: str = "unresolved",
    evidence_kind: str = "claim",
    confidence: str = "medium",
    quote_text: str = "",
    numeric_value: str = "",
    numeric_unit: str = "",
    notes: str = "",
    project_path: str = "",
) -> dict[str, Any]:
    """Persist one attributed evidence record for later synthesis."""
    state_service = _research_state_service(project_path)
    evidence = ResearchEvidenceRecord(
        run_id=research_run_id,
        fact_text=fact_text,
        source_ids=list(source_ids),
        status=ResearchReviewStatus(status),
        evidence_kind=evidence_kind,
        confidence=confidence,
        quote_text=quote_text,
        numeric_value=numeric_value,
        numeric_unit=numeric_unit,
        metadata={"notes": notes} if notes else {},
    )
    state_service.save_research_evidence(evidence)
    sources = [
        state_service.load_research_source(source_id)
        for source_id in evidence.source_ids
    ]
    return _evidence_payload(evidence, sources)


@tool(
    name="search_research_evidence",
    category=ToolCategory.RESEARCH,
    description=(
        "Search persisted research evidence and source metadata for later "
        "synthesis or review."
    ),
)
def search_research_evidence(
    query: str,
    research_run_id: str = "",
    status: str = "",
    limit: int = 5,
    project_path: str = "",
) -> dict[str, Any]:
    """Return evidence matches from the persisted research ledger."""
    state_service = _research_state_service(project_path)
    records = state_service.list_research_evidence(
        run_id=research_run_id or None,
        status=_review_status(status),
    )
    terms = [term for term in query.lower().split() if term.strip()]
    scored_matches: list[tuple[int, dict[str, Any]]] = []
    for evidence in records:
        sources = [
            state_service.load_research_source(source_id)
            for source_id in evidence.source_ids
        ]
        blob = _evidence_match_blob(evidence, sources)
        score = sum(1 for term in terms if term in blob) if terms else 1
        if score <= 0:
            continue
        scored_matches.append((score, _evidence_payload(evidence, sources)))
    scored_matches.sort(key=lambda item: item[0], reverse=True)
    return {
        "query": query,
        "match_count": len(scored_matches[:limit]),
        "matches": [payload for _score, payload in scored_matches[:limit]],
    }


@tool(
    name="generate_research_brief_package",
    category=ToolCategory.RESEARCH,
    description=(
        "Generate a structured research brief package from stored evidence, "
        "including summary, supported findings, open questions, scoring, "
        "and exportable artifacts."
    ),
)
def generate_research_brief_package(
    research_run_id: str,
    title: str = "",
    project_path: str = "",
) -> dict[str, Any]:
    """Create one stable brief package from a persisted research run."""
    state_service = _research_state_service(project_path)
    research_run = state_service.load_research_run(research_run_id)
    sources = state_service.list_research_sources(run_id=research_run_id)
    accepted = state_service.list_research_evidence(
        run_id=research_run_id,
        status=ResearchReviewStatus.ACCEPTED,
    )
    unresolved = state_service.list_research_evidence(
        run_id=research_run_id,
        status=ResearchReviewStatus.UNRESOLVED,
    )
    rejected = state_service.list_research_evidence(
        run_id=research_run_id,
        status=ResearchReviewStatus.REJECTED,
    )
    supported_findings = [item.fact_text for item in accepted]
    open_questions = [item.fact_text for item in unresolved]
    weak_evidence_ids = [
        item.record_id
        for item in accepted
        if _confidence_weight(item.confidence) < 0.7
    ] + [item.record_id for item in unresolved + rejected]
    total_evidence = len(accepted) + len(unresolved) + len(rejected)
    coverage_score = round(len(accepted) / max(total_evidence, 1), 2)
    confidence_total = sum(
        _confidence_weight(item.confidence) for item in accepted
    )
    confidence_score = round(confidence_total / max(len(accepted), 1), 2)
    brief_title = title or f"Research Brief: {research_run.topic}"
    summary = _brief_summary(
        brief_title,
        len(sources),
        supported_findings,
        open_questions,
        coverage_score,
        confidence_score,
    )
    brief = ResearchBriefRecord(
        run_id=research_run_id,
        title=brief_title,
        executive_summary=summary,
        supported_findings=supported_findings,
        open_questions=open_questions,
        weak_evidence_ids=weak_evidence_ids,
        coverage_score=coverage_score,
        confidence_score=confidence_score,
        metadata={
            "source_count": len(sources),
            "accepted_evidence_count": len(accepted),
            "unresolved_evidence_count": len(unresolved),
            "rejected_evidence_count": len(rejected),
        },
    )
    json_path = state_service._research_brief_path(brief.record_id)
    markdown_path = state_service.write_research_brief_markdown(
        brief.record_id,
        _brief_markdown(brief),
    )
    brief.artifact_paths = [json_path, markdown_path]
    state_service.save_research_brief(brief)
    return {
        "brief_id": brief.record_id,
        "research_run_id": research_run_id,
        "title": brief.title,
        "coverage_score": brief.coverage_score,
        "confidence_score": brief.confidence_score,
        "supported_findings_count": len(brief.supported_findings),
        "open_questions_count": len(brief.open_questions),
        "artifact_paths": list(brief.artifact_paths),
    }


@tool(
    name="synthesize_sources",
    category=ToolCategory.RESEARCH,
    description=(
        "Synthesize information from multiple sources into a coherent summary. "
        "Takes a list of source texts and combines their key points, "
        "identifying common themes and resolving conflicts."
    ),
)
def synthesize_sources(sources: List[str], topic: str = "") -> str:
    """
    Synthesize information from multiple sources.

    Args:
        sources: List of source texts to synthesize
        topic: Optional topic to focus synthesis on

    """
    logger.info(
        f"Synthesizing {len(sources)} sources"
        + (f" on topic: {topic}" if topic else "")
    )

    if not sources:
        return "No sources provided for synthesis."

    # Count total words across sources
    total_words = sum(len(s.split()) for s in sources)

    # Identify common themes (simple keyword extraction)
    all_words = " ".join(sources).lower().split()
    word_freq = {}
    for word in all_words:
        if len(word) > 4:  # Skip short words
            word_freq[word] = word_freq.get(word, 0) + 1

    common_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[
        :5
    ]

    return (
        f"Synthesis of {len(sources)} sources ({total_words} total words):\n\n"
        f"Common themes: {', '.join(w for w, _ in common_words)}\n\n"
        "Key findings:\n"
        f"- Source 1 highlights: {sources[0][:100]}...\n"
        + (
            f"- Source 2 highlights: {sources[1][:100]}...\n"
            if len(sources) > 1
            else ""
        )
        + (
            f"- Additional sources provide supporting evidence\n"
            if len(sources) > 2
            else ""
        )
        + "\n(Full synthesis implementation pending)"
    )


@tool(
    name="cite_sources",
    category=ToolCategory.RESEARCH,
    description=(
        "Format citations in various academic styles (APA, MLA, Chicago). "
        "Provide source information and desired citation style."
    ),
)
def cite_sources(
    title: str,
    authors: List[str] = None,
    year: str = "",
    url: str = "",
    style: str = "APA",
) -> str:
    """
    Format academic citations.

    Args:
        title: Title of the source
        authors: List of author names
        year: Publication year
        url: URL if online source
        style: Citation style (APA, MLA, Chicago)

    """
    logger.info(f"Formatting citation in {style} style")

    authors = authors or ["Unknown Author"]
    author_str = ", ".join(authors[:3])  # First 3 authors
    if len(authors) > 3:
        author_str += ", et al."

    if style.upper() == "APA":
        citation = f"{author_str} ({year}). {title}."
        if url:
            citation += f" Retrieved from {url}"
    elif style.upper() == "MLA":
        citation = f'{author_str}. "{title}." {year}.'
        if url:
            citation += f" Web. <{url}>"
    elif style.upper() == "CHICAGO":
        citation = f'{author_str}. "{title}." {year}.'
        if url:
            citation += f" Accessed at {url}."
    else:
        citation = f"{author_str}. {title}. {year}. {url}"

    return citation


@tool(
    name="organize_research",
    category=ToolCategory.RESEARCH,
    description=(
        "Organize research findings into a structured outline with topics, "
        "subtopics, and key points. Useful for organizing notes and planning papers."
    ),
)
def organize_research(findings: str, structure_type: str = "outline") -> str:
    """
    Organize research findings into a structure.

    Args:
        findings: Raw research findings text
        structure_type: Type of structure (outline, mind_map, categories)

    """
    logger.info(f"Organizing research as {structure_type}")

    # Split into paragraphs/sections
    sections = [s.strip() for s in findings.split("\n\n") if s.strip()]

    if structure_type == "outline":
        outline = "Research Outline:\n\n"
        for i, section in enumerate(sections, 1):
            outline += f"{i}. {section[:100]}...\n"
            # Add sub-points (simplified)
            sentences = section.split(". ")
            for j, sent in enumerate(sentences[:3], 1):
                if sent.strip():
                    outline += f"   {chr(96+j)}. {sent[:50]}...\n"
            outline += "\n"
        return outline

    elif structure_type == "categories":
        return (
            f"Research Categories ({len(sections)} main topics):\n\n"
            + "\n".join(
                f"Category {i}: {s[:80]}..." for i, s in enumerate(sections, 1)
            )
        )

    else:
        return f"Organized {len(sections)} research sections (full implementation pending)"


@tool(
    name="extract_key_points",
    category=ToolCategory.RESEARCH,
    description=(
        "Extract key points and main ideas from a research text. "
        "Identifies the most important information and creates a bulleted summary."
    ),
)
def extract_key_points(text: str, max_points: int = 5) -> str:
    """
    Extract key points from text.

    Args:
        text: The text to extract key points from
        max_points: Maximum number of key points to extract

    """
    logger.info(f"Extracting up to {max_points} key points")

    # Split into sentences
    sentences = []
    for s in text.replace("! ", ".|").replace("? ", ".|").split(".|"):
        s = s.strip()
        if s and len(s) > 20:  # Filter very short fragments
            sentences.append(s)

    # Score sentences by length and position (simple heuristic)
    scored = []
    for i, sent in enumerate(sentences):
        # Earlier sentences and moderate length get higher scores
        score = (1.0 / (i + 1)) * min(len(sent.split()), 30) / 30
        scored.append((score, sent))

    # Get top N sentences
    scored.sort(reverse=True)
    key_points = [sent for _, sent in scored[:max_points]]

    result = f"Key Points (extracted {len(key_points)} from {len(sentences)} sentences):\n\n"
    for i, point in enumerate(key_points, 1):
        result += f"{i}. {point}\n"

    return result


@tool(
    name="compare_sources",
    category=ToolCategory.RESEARCH,
    description=(
        "Compare multiple sources on the same topic, identifying agreements, "
        "disagreements, and unique perspectives from each source."
    ),
)
def compare_sources(source1: str, source2: str, source3: str = "") -> str:
    """
    Compare multiple sources.

    Args:
        source1: First source text
        source2: Second source text
        source3: Optional third source text

    """
    logger.info("Comparing sources")

    sources = [s for s in [source1, source2, source3] if s]

    # Calculate overlap (simple word-based)
    words1 = set(source1.lower().split())
    words2 = set(source2.lower().split())
    overlap = words1 & words2

    overlap_pct = (
        len(overlap) / max(len(words1), len(words2)) * 100
        if words1 or words2
        else 0
    )

    return (
        f"Source Comparison ({len(sources)} sources):\n\n"
        f"Source 1: {len(source1)} characters, {len(source1.split())} words\n"
        f"Source 2: {len(source2)} characters, {len(source2.split())} words\n"
        + (
            f"Source 3: {len(source3)} characters, {len(source3.split())} words\n"
            if source3
            else ""
        )
        + f"\nContent overlap: {overlap_pct:.1f}%\n"
        + f"Common themes: {', '.join(list(overlap)[:5])}\n\n"
        "Unique perspectives:\n"
        f"- Source 1: {source1[:100]}...\n"
        f"- Source 2: {source2[:100]}...\n"
        + (f"- Source 3: {source3[:100]}...\n" if source3 else "")
        + "\n(Detailed comparison implementation pending)"
    )
