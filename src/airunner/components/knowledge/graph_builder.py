"""
Knowledge graph builder.

Constructs NetworkX graph from knowledge facts and relationships.
"""

from typing import Dict, List, Optional, Set, Tuple
import networkx as nx

from airunner.components.knowledge.data.models import KnowledgeFact
from airunner.components.knowledge.data.knowledge_relationship import (
    KnowledgeRelationship,
)
from airunner.components.data.session_manager import session_scope
from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger


logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


class KnowledgeGraphBuilder:
    """
    Build NetworkX graph from knowledge data.

    Creates directed graph with entities as nodes and relationships as edges.
    Supports filtering, layout computation, and export.
    """

    def __init__(self):
        """Initialize graph builder."""
        self.graph: nx.DiGraph = nx.DiGraph()
        self._entity_facts: Dict[int, List[int]] = {}  # entity_id -> fact_ids
        self._fact_entities: Dict[int, List[int]] = {}  # fact_id -> entity_ids

    def build_from_facts(
        self,
        category: Optional[str] = None,
        verified_only: bool = False,
        min_confidence: float = 0.0,
    ) -> nx.DiGraph:
        """
        Build graph from knowledge facts.

        Args:
            category: Filter by category
            verified_only: Only include verified facts
            min_confidence: Minimum confidence threshold

        Returns:
            NetworkX directed graph
        """
        self.graph.clear()
        self._entity_facts.clear()
        self._fact_entities.clear()

        with session_scope() as session:
            # Load facts with filters
            query = session.query(KnowledgeFact).filter(
                KnowledgeFact.enabled.is_(True)
            )

            if category:
                query = query.filter(KnowledgeFact.category == category)

            if verified_only:
                query = query.filter(KnowledgeFact.verified.is_(True))

            if min_confidence > 0:
                query = query.filter(
                    KnowledgeFact.confidence >= min_confidence
                )

            facts = query.all()

            # Load relationships
            relationships = session.query(KnowledgeRelationship).all()

            # Build entity nodes from relationships
            entities_seen = {}  # entity_name -> node_id
            for rel in relationships:
                if rel.entity_name and rel.entity_name not in entities_seen:
                    node_id = (
                        f"entity_{rel.entity_name.lower().replace(' ', '_')}"
                    )
                    entities_seen[rel.entity_name] = node_id
                    self.graph.add_node(
                        node_id,
                        label=rel.entity_name,
                        entity_type=rel.entity_type or "unknown",
                        node_type="entity",
                    )

            # Build fact nodes
            for fact in facts:
                fact_node = f"fact_{fact.id}"
                self.graph.add_node(
                    fact_node,
                    label=(
                        fact.text[:50] + "..."
                        if len(fact.text) > 50
                        else fact.text
                    ),
                    text=fact.text,
                    category=fact.category or "",
                    confidence=fact.confidence,
                    verified=fact.verified,
                    node_type="fact",
                    fact_id=fact.id,
                )

                # Track fact-entity associations
                self._fact_entities[fact.id] = []

            # Build edges from relationships
            for rel in relationships:
                source_fact_node = f"fact_{rel.source_fact_id}"
                target_fact_node = (
                    f"fact_{rel.target_fact_id}"
                    if rel.target_fact_id
                    else None
                )

                # Fact-to-fact relationships
                if (
                    target_fact_node
                    and source_fact_node in self.graph
                    and target_fact_node in self.graph
                ):
                    self.graph.add_edge(
                        source_fact_node,
                        target_fact_node,
                        label=rel.relationship_type,
                        confidence=rel.confidence,
                        edge_type="fact_relationship",
                    )

                # Entity mentions in facts
                if rel.entity_name and source_fact_node in self.graph:
                    entity_node = entities_seen.get(rel.entity_name)
                    if entity_node:
                        self.graph.add_edge(
                            source_fact_node,
                            entity_node,
                            label="mentions",
                            edge_type="mention",
                        )

                        # Track associations
                        if rel.source_fact_id not in self._entity_facts:
                            self._entity_facts[rel.source_fact_id] = []
                        self._entity_facts[rel.source_fact_id].append(
                            entity_node
                        )
                        self._fact_entities[rel.source_fact_id].append(
                            entity_node
                        )

        logger.info(
            f"Built graph with {self.graph.number_of_nodes()} nodes "
            f"and {self.graph.number_of_edges()} edges"
        )

        return self.graph

    def get_entity_subgraph(
        self, entity_id: int, depth: int = 1
    ) -> nx.DiGraph:
        """
        Get subgraph centered on entity.

        Args:
            entity_id: Center entity ID
            depth: Number of hops to include

        Returns:
            Subgraph containing entity and neighbors
        """
        if entity_id not in self.graph:
            return nx.DiGraph()

        # Get nodes within depth hops
        nodes = {entity_id}
        current_layer = {entity_id}

        for _ in range(depth):
            next_layer = set()
            for node in current_layer:
                # Add predecessors and successors
                next_layer.update(self.graph.predecessors(node))
                next_layer.update(self.graph.successors(node))
            nodes.update(next_layer)
            current_layer = next_layer

        return self.graph.subgraph(nodes).copy()

    def get_fact_context(self, fact_id: int) -> nx.DiGraph:
        """
        Get subgraph for a fact and its entities.

        Args:
            fact_id: Fact ID

        Returns:
            Subgraph containing fact node and connected entities
        """
        fact_node = f"fact_{fact_id}"
        if fact_node not in self.graph:
            return nx.DiGraph()

        # Get all connected nodes
        nodes = {fact_node}
        nodes.update(self.graph.predecessors(fact_node))
        nodes.update(self.graph.successors(fact_node))

        return self.graph.subgraph(nodes).copy()

    def compute_layout(
        self, layout_algorithm: str = "spring"
    ) -> Dict[any, Tuple[float, float]]:
        """
        Compute node positions using layout algorithm.

        Args:
            layout_algorithm: Algorithm name (spring, circular, kamada_kawai, shell)

        Returns:
            Dictionary mapping node IDs to (x, y) positions
        """
        if not self.graph.nodes():
            return {}

        if layout_algorithm == "spring":
            return nx.spring_layout(self.graph, seed=42)
        elif layout_algorithm == "circular":
            return nx.circular_layout(self.graph)
        elif layout_algorithm == "kamada_kawai":
            return nx.kamada_kawai_layout(self.graph)
        elif layout_algorithm == "shell":
            return nx.shell_layout(self.graph)
        else:
            logger.warning(
                f"Unknown layout algorithm: {layout_algorithm}, using spring"
            )
            return nx.spring_layout(self.graph, seed=42)

    def export_to_graphml(self, output_path: str):
        """
        Export graph to GraphML format.

        Args:
            output_path: Path to output file
        """
        nx.write_graphml(self.graph, output_path)
        logger.info(f"Exported graph to GraphML: {output_path}")

    def export_to_json(self, output_path: str):
        """
        Export graph to JSON format.

        Args:
            output_path: Path to output file
        """
        import json

        data = nx.node_link_data(self.graph)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        logger.info(f"Exported graph to JSON: {output_path}")

    def get_graph_statistics(self) -> Dict[str, any]:
        """
        Compute graph statistics.

        Returns:
            Dictionary of graph metrics
        """
        if not self.graph.nodes():
            return {
                "nodes": 0,
                "edges": 0,
                "density": 0,
                "connected_components": 0,
            }

        stats = {
            "nodes": self.graph.number_of_nodes(),
            "edges": self.graph.number_of_edges(),
            "density": nx.density(self.graph),
            "connected_components": nx.number_weakly_connected_components(
                self.graph
            ),
        }

        # Count node types
        entity_count = sum(
            1
            for _, data in self.graph.nodes(data=True)
            if data.get("node_type") == "entity"
        )
        fact_count = sum(
            1
            for _, data in self.graph.nodes(data=True)
            if data.get("node_type") == "fact"
        )

        stats["entity_nodes"] = entity_count
        stats["fact_nodes"] = fact_count

        # Most connected nodes
        if self.graph.nodes():
            degrees = dict(self.graph.degree())
            if degrees:
                most_connected = max(degrees, key=degrees.get)
                stats["most_connected_node"] = most_connected
                stats["max_connections"] = degrees[most_connected]

        return stats

    def find_shortest_path(
        self, source_id: int, target_id: int
    ) -> Optional[List[int]]:
        """
        Find shortest path between two entities.

        Args:
            source_id: Source entity ID
            target_id: Target entity ID

        Returns:
            List of node IDs in path, or None if no path exists
        """
        try:
            path = nx.shortest_path(
                self.graph, source=source_id, target=target_id
            )
            return path
        except nx.NetworkXNoPath:
            logger.debug(f"No path found between {source_id} and {target_id}")
            return None
        except nx.NodeNotFound:
            logger.warning(
                f"Node not found: source={source_id}, target={target_id}"
            )
            return None

    def get_entity_clusters(self) -> List[Set[int]]:
        """
        Find clusters of related entities.

        Returns:
            List of sets, each containing entity IDs in a cluster
        """
        # Get weakly connected components
        components = list(nx.weakly_connected_components(self.graph))

        # Filter to only entity nodes
        entity_clusters = []
        for component in components:
            entities = {
                node
                for node in component
                if self.graph.nodes[node].get("node_type") == "entity"
            }
            if entities:
                entity_clusters.append(entities)

        return entity_clusters
