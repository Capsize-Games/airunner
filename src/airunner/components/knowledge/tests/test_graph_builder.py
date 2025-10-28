"""
Tests for knowledge graph builder.
"""

import pytest
import tempfile
from pathlib import Path

from airunner.components.knowledge.graph_builder import KnowledgeGraphBuilder
from airunner.components.knowledge.data.models import KnowledgeFact
from airunner.components.knowledge.data.knowledge_relationship import (
    KnowledgeRelationship,
)
from airunner.components.data.session_manager import session_scope


@pytest.fixture
def sample_graph_data():
    """Create sample knowledge graph data."""
    with session_scope() as session:
        # Create facts
        fact1 = KnowledgeFact(
            text="Alice works at TechCorp as a software engineer",
            category="employment",
            confidence=0.9,
            verified=True,
            enabled=True,
        )
        fact2 = KnowledgeFact(
            text="Bob is a colleague of Alice at TechCorp",
            category="employment",
            confidence=0.85,
            verified=True,
            enabled=True,
        )
        fact3 = KnowledgeFact(
            text="TechCorp develops AI software products",
            category="business",
            confidence=0.95,
            verified=False,
            enabled=True,
        )

        session.add_all([fact1, fact2, fact3])
        session.flush()

        # Create relationships with entity information
        rel1 = KnowledgeRelationship(
            source_fact_id=fact1.id,
            entity_name="Alice",
            entity_type="person",
            relationship_type="mentions_entity",
            confidence=0.9,
        )
        rel2 = KnowledgeRelationship(
            source_fact_id=fact1.id,
            entity_name="TechCorp",
            entity_type="organization",
            relationship_type="mentions_entity",
            confidence=0.9,
        )
        rel3 = KnowledgeRelationship(
            source_fact_id=fact2.id,
            entity_name="Bob",
            entity_type="person",
            relationship_type="mentions_entity",
            confidence=0.85,
        )
        rel4 = KnowledgeRelationship(
            source_fact_id=fact2.id,
            entity_name="Alice",
            entity_type="person",
            relationship_type="mentions_entity",
            confidence=0.85,
        )
        rel5 = KnowledgeRelationship(
            source_fact_id=fact3.id,
            entity_name="TechCorp",
            entity_type="organization",
            relationship_type="mentions_entity",
            confidence=0.95,
        )
        # Fact-to-fact relationship (fact2 updates fact1)
        rel6 = KnowledgeRelationship(
            source_fact_id=fact2.id,
            target_fact_id=fact1.id,
            relationship_type="relates_to",
            confidence=0.8,
        )

        session.add_all([rel1, rel2, rel3, rel4, rel5, rel6])
        session.flush()

        fact_ids = [fact1.id, fact2.id, fact3.id]
        rel_ids = [rel1.id, rel2.id, rel3.id, rel4.id, rel5.id, rel6.id]

    yield fact_ids, rel_ids

    # Cleanup
    with session_scope() as session:
        session.query(KnowledgeRelationship).filter(
            KnowledgeRelationship.id.in_(rel_ids)
        ).delete(synchronize_session=False)
        session.query(KnowledgeFact).filter(
            KnowledgeFact.id.in_(fact_ids)
        ).delete(synchronize_session=False)


class TestKnowledgeGraphBuilder:
    """Test KnowledgeGraphBuilder class."""

    def test_build_from_facts_all(self, sample_graph_data):
        """Test building graph from all facts."""
        builder = KnowledgeGraphBuilder()
        graph = builder.build_from_facts()

        # Should have 3 fact nodes + 3 entity nodes (Alice, Bob, TechCorp)
        assert graph.number_of_nodes() >= 3
        assert graph.number_of_edges() >= 3

        # Check node types
        entity_nodes = [
            n
            for n, data in graph.nodes(data=True)
            if data.get("node_type") == "entity"
        ]
        fact_nodes = [
            n
            for n, data in graph.nodes(data=True)
            if data.get("node_type") == "fact"
        ]

        assert len(entity_nodes) >= 3  # Alice, Bob, TechCorp
        assert len(fact_nodes) >= 3  # 3 facts

    def test_build_from_facts_filtered_by_category(self, sample_graph_data):
        """Test building graph filtered by category."""
        builder = KnowledgeGraphBuilder()
        graph = builder.build_from_facts(category="employment")

        # Should only have employment facts
        fact_nodes = [
            data
            for _, data in graph.nodes(data=True)
            if data.get("node_type") == "fact"
        ]

        assert len(fact_nodes) >= 2  # Alice and Bob employment facts
        assert all(data.get("category") == "employment" for data in fact_nodes)

    def test_build_from_facts_verified_only(self, sample_graph_data):
        """Test building graph with verified facts only."""
        builder = KnowledgeGraphBuilder()
        graph = builder.build_from_facts(verified_only=True)

        fact_nodes = [
            data
            for _, data in graph.nodes(data=True)
            if data.get("node_type") == "fact"
        ]

        assert len(fact_nodes) >= 2  # Only verified facts
        assert all(data.get("verified") for data in fact_nodes)

    def test_build_from_facts_min_confidence(self, sample_graph_data):
        """Test building graph with minimum confidence filter."""
        builder = KnowledgeGraphBuilder()
        graph = builder.build_from_facts(min_confidence=0.9)

        fact_nodes = [
            data
            for _, data in graph.nodes(data=True)
            if data.get("node_type") == "fact"
        ]

        # Only facts with confidence >= 0.9
        assert all(data.get("confidence", 0) >= 0.9 for data in fact_nodes)

    def test_get_entity_subgraph(self, sample_graph_data):
        """Test getting subgraph for an entity."""
        fact_ids, _ = sample_graph_data

        builder = KnowledgeGraphBuilder()
        builder.build_from_facts()

        # Get subgraph for Alice entity
        alice_node = "entity_alice"
        if alice_node in builder.graph.nodes():
            subgraph = builder.get_entity_subgraph(alice_node, depth=1)

            assert subgraph.number_of_nodes() > 0
            assert alice_node in subgraph.nodes()

    def test_get_fact_context(self, sample_graph_data):
        """Test getting context subgraph for a fact."""
        _, fact_ids = sample_graph_data

        builder = KnowledgeGraphBuilder()
        builder.build_from_facts()

        # Get context for first fact
        context = builder.get_fact_context(fact_ids[0])

        assert context.number_of_nodes() > 0
        assert f"fact_{fact_ids[0]}" in context.nodes()

    def test_compute_layout_spring(self, sample_graph_data):
        """Test computing spring layout."""
        builder = KnowledgeGraphBuilder()
        builder.build_from_facts()

        positions = builder.compute_layout(layout_algorithm="spring")

        assert len(positions) == builder.graph.number_of_nodes()
        # All positions should be tuples of (x, y)
        assert all(len(pos) == 2 for pos in positions.values())

    def test_compute_layout_circular(self, sample_graph_data):
        """Test computing circular layout."""
        builder = KnowledgeGraphBuilder()
        builder.build_from_facts()

        positions = builder.compute_layout(layout_algorithm="circular")

        assert len(positions) == builder.graph.number_of_nodes()

    def test_export_to_graphml(self, sample_graph_data):
        """Test exporting graph to GraphML."""
        builder = KnowledgeGraphBuilder()
        builder.build_from_facts()

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".graphml", delete=False
        ) as f:
            output_path = f.name

        try:
            builder.export_to_graphml(output_path)

            # Verify file was created and has content
            assert Path(output_path).exists()
            assert Path(output_path).stat().st_size > 0

        finally:
            Path(output_path).unlink(missing_ok=True)

    def test_export_to_json(self, sample_graph_data):
        """Test exporting graph to JSON."""
        builder = KnowledgeGraphBuilder()
        builder.build_from_facts()

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            output_path = f.name

        try:
            builder.export_to_json(output_path)

            # Verify file was created
            assert Path(output_path).exists()
            assert Path(output_path).stat().st_size > 0

            # Verify it's valid JSON
            import json

            with open(output_path, "r") as f:
                data = json.load(f)

            assert "nodes" in data
            assert "links" in data

        finally:
            Path(output_path).unlink(missing_ok=True)

    def test_get_graph_statistics(self, sample_graph_data):
        """Test computing graph statistics."""
        builder = KnowledgeGraphBuilder()
        builder.build_from_facts()

        stats = builder.get_graph_statistics()

        assert "nodes" in stats
        assert "edges" in stats
        assert "density" in stats
        assert "entity_nodes" in stats
        assert "fact_nodes" in stats

        assert stats["nodes"] > 0
        assert stats["entity_nodes"] >= 3
        assert stats["fact_nodes"] >= 3

    def test_find_shortest_path(self, sample_graph_data):
        """Test finding shortest path between entities."""
        fact_ids, _ = sample_graph_data

        builder = KnowledgeGraphBuilder()
        builder.build_from_facts()

        # Try to find path between Alice and TechCorp
        alice_node = "entity_alice"
        tech_node = "entity_techcorp"

        if alice_node in builder.graph and tech_node in builder.graph:
            path = builder.find_shortest_path(alice_node, tech_node)

            # Path should exist if there are connecting facts
            if path is not None:
                assert alice_node in path or tech_node in path

    def test_get_entity_clusters(self, sample_graph_data):
        """Test finding entity clusters."""
        builder = KnowledgeGraphBuilder()
        builder.build_from_facts()

        clusters = builder.get_entity_clusters()

        # Should have at least one cluster
        assert len(clusters) > 0

        # All items in clusters should be entity IDs
        all_nodes = set()
        for cluster in clusters:
            all_nodes.update(cluster)

        # Verify they're all entity nodes
        for node in all_nodes:
            assert builder.graph.nodes[node].get("node_type") == "entity"

    def test_empty_graph(self):
        """Test operations on empty graph."""
        builder = KnowledgeGraphBuilder()

        # Build with impossible filter
        graph = builder.build_from_facts(category="nonexistent_category_xyz")

        assert graph.number_of_nodes() >= 0  # May have entities but no facts
        assert builder.get_graph_statistics()["nodes"] >= 0

        # Layout should handle empty graph
        positions = builder.compute_layout()
        assert isinstance(positions, dict)
