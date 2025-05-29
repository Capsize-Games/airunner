"""
Functional test for SearchNode in NodeGraphQt.
"""

import pytest
from airunner.gui.widgets.nodegraph.nodes.llm.search_node import SearchNode


@pytest.fixture
def node():
    return SearchNode()


def test_node_properties(node):
    assert node.NODE_NAME == "Aggregated Search"
    assert node.get_property("query") == ""
    assert node.get_property("category") == "all"


def test_node_run_node_empty_query(node):
    node.set_property("query", "")
    node.set_property("category", "web")
    node.run_node()
    assert node.get_output_val("results") == []
