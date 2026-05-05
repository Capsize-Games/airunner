"""Focused tests for persisted research workflow tools."""

from airunner.components.document_editor.project import AirunnerProjectService
from airunner.components.document_editor.project import AirunnerProjectStateService
from airunner.components.llm.tools.research_tools import (
    record_research_evidence,
    record_research_source,
    search_research_evidence,
    start_research_run,
)


def test_research_tools_persist_research_ledgers(tmp_path):
    """Research tools should store runs, sources, and evidence."""
    project_path = tmp_path / "research-project"
    project_service = AirunnerProjectService(str(project_path))
    project_service.initialize(project_name="Research Project")
    state_service = AirunnerProjectStateService(project_service)

    started = start_research_run(
        topic="grid resilience",
        query="energy grid resilience recent studies",
        project_path=str(project_path),
    )
    source = record_research_source(
        research_run_id=started["research_run_id"],
        url="https://example.com/report",
        title="Grid Resilience Report",
        status="accepted",
        excerpt="Reserve capacity increased by 12 percent.",
        project_path=str(project_path),
    )
    evidence = record_research_evidence(
        research_run_id=started["research_run_id"],
        fact_text="Reserve capacity increased by 12 percent.",
        source_ids=[source["source_id"]],
        status="accepted",
        evidence_kind="numeric_fact",
        numeric_value="12",
        numeric_unit="percent",
        project_path=str(project_path),
    )

    restored_run = state_service.load_research_run(started["research_run_id"])
    restored_source = state_service.load_research_source(source["source_id"])
    restored_evidence = state_service.load_research_evidence(
        evidence["evidence_id"]
    )

    assert restored_run.topic == "grid resilience"
    assert restored_source.title == "Grid Resilience Report"
    assert restored_evidence.numeric_value == "12"
    assert restored_evidence.source_ids == [source["source_id"]]


def test_search_research_evidence_returns_attributed_matches(tmp_path):
    """Evidence search should return attributed, status-aware matches."""
    project_path = tmp_path / "research-project"
    project_service = AirunnerProjectService(str(project_path))
    project_service.initialize(project_name="Research Project")

    started = start_research_run(
        topic="grid resilience",
        query="energy grid resilience recent studies",
        project_path=str(project_path),
    )
    source = record_research_source(
        research_run_id=started["research_run_id"],
        url="https://example.com/report",
        title="Grid Resilience Report",
        status="accepted",
        excerpt="Reserve capacity increased by 12 percent.",
        project_path=str(project_path),
    )
    record_research_evidence(
        research_run_id=started["research_run_id"],
        fact_text="Reserve capacity increased by 12 percent.",
        source_ids=[source["source_id"]],
        status="accepted",
        evidence_kind="numeric_fact",
        numeric_value="12",
        numeric_unit="percent",
        quote_text="Reserve capacity increased by 12 percent.",
        project_path=str(project_path),
    )

    results = search_research_evidence(
        query="reserve capacity 12 percent",
        research_run_id=started["research_run_id"],
        status="accepted",
        project_path=str(project_path),
    )

    assert results["match_count"] == 1
    assert results["matches"][0]["evidence_kind"] == "numeric_fact"
    assert results["matches"][0]["sources"][0]["title"] == (
        "Grid Resilience Report"
    )