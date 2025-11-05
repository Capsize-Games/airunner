"""
End-to-end integration tests for mode-based routing architecture.

Tests the complete flow: WorkflowManager → ParentGraphBuilder → Specialized Agents
"""

from unittest.mock import Mock, patch

from airunner.components.llm.managers.workflow_manager import (
    WorkflowManager,
)


class TestEndToEndModeRouting:
    """Test complete mode-based routing workflow."""

    def test_mode_routing_workflow_builds(self):
        """Test that mode-based workflow builds with all subgraphs."""
        mock_model = Mock()
        mock_model.bind_tools = Mock(return_value=mock_model)

        # Create workflow with mode routing enabled
        manager = WorkflowManager(
            system_prompt="Test prompt",
            chat_model=mock_model,
            tools=None,
            use_mode_routing=True,
        )

        assert manager._compiled_workflow is not None
        assert manager._use_mode_routing is True

    def test_mode_routing_with_tools(self):
        """Test mode routing works with tools provided."""
        mock_model = Mock()
        mock_model.bind_tools = Mock(return_value=mock_model)

        # Create a simple mock tool
        mock_tool = Mock()
        mock_tool.__name__ = "test_tool"

        manager = WorkflowManager(
            system_prompt="Test prompt",
            chat_model=mock_model,
            tools=[mock_tool],
            use_mode_routing=True,
        )

        assert manager._compiled_workflow is not None
        assert len(manager._tools) > 0

    def test_standard_workflow_unchanged(self):
        """Test that standard workflow still works (backward compatibility)."""
        mock_model = Mock()
        mock_model.bind_tools = Mock(return_value=mock_model)

        # Create workflow WITHOUT mode routing
        manager = WorkflowManager(
            system_prompt="Test prompt",
            chat_model=mock_model,
            tools=None,
            use_mode_routing=False,
        )

        assert manager._compiled_workflow is not None
        assert manager._use_mode_routing is False

    def test_mode_override_parameter_stored(self):
        """Test that mode override is properly stored."""
        mock_model = Mock()
        mock_model.bind_tools = Mock(return_value=mock_model)

        manager = WorkflowManager(
            system_prompt="Test prompt",
            chat_model=mock_model,
            tools=None,
            use_mode_routing=True,
            mode_override="author",
        )

        assert manager._mode_override == "author"

    @patch("airunner.components.llm.agents.author_agent.AuthorAgent.compile")
    @patch("airunner.components.llm.agents.code_agent.CodeAgent.compile")
    @patch(
        "airunner.components.llm.agents.research_agent.ResearchAgent.compile"
    )
    @patch("airunner.components.llm.agents.qa_agent.QAAgent.compile")
    def test_all_agents_compiled(
        self,
        mock_qa_compile,
        mock_research_compile,
        mock_code_compile,
        mock_author_compile,
    ):
        """Test that all specialized agents are compiled during initialization."""
        mock_model = Mock()
        mock_model.bind_tools = Mock(return_value=mock_model)

        # Mock the compile methods to return mock graphs
        mock_graph = Mock()
        mock_author_compile.return_value = mock_graph
        mock_code_compile.return_value = mock_graph
        mock_research_compile.return_value = mock_graph
        mock_qa_compile.return_value = mock_graph

        manager = WorkflowManager(
            system_prompt="Test prompt",
            chat_model=mock_model,
            tools=None,
            use_mode_routing=True,
        )

        # Verify all agents were compiled
        mock_author_compile.assert_called_once()
        mock_code_compile.assert_called_once()
        mock_research_compile.assert_called_once()
        mock_qa_compile.assert_called_once()

    def test_parent_graph_receives_all_subgraphs(self):
        """Test that ParentGraphBuilder receives all 5 subgraphs."""
        mock_model = Mock()
        mock_model.bind_tools = Mock(return_value=mock_model)

        with patch(
            "airunner.components.llm.managers.parent_graph_builder.ParentGraphBuilder"
        ) as mock_builder_cls:
            mock_builder = Mock()
            mock_builder.compile.return_value = Mock()
            mock_builder_cls.return_value = mock_builder

            manager = WorkflowManager(
                system_prompt="Test prompt",
                chat_model=mock_model,
                tools=None,
                use_mode_routing=True,
            )

            # Verify ParentGraphBuilder was called with all subgraphs
            mock_builder_cls.assert_called_once()
            call_kwargs = mock_builder_cls.call_args[1]

            assert "author_graph" in call_kwargs
            assert "code_graph" in call_kwargs
            assert "research_graph" in call_kwargs
            assert "qa_graph" in call_kwargs
            assert "general_graph" in call_kwargs

            # All subgraphs should be non-None
            assert call_kwargs["author_graph"] is not None
            assert call_kwargs["code_graph"] is not None
            assert call_kwargs["research_graph"] is not None
            assert call_kwargs["qa_graph"] is not None
            assert call_kwargs["general_graph"] is not None
