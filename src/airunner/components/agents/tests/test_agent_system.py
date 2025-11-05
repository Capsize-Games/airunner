"""Integration tests for expert agent system."""

import pytest

from airunner.components.agents.expert_agent import (
    ExpertAgent,
    AgentCapability,
)
from airunner.components.agents.agent_registry import AgentRegistry
from airunner.components.agents.agent_router import AgentRouter
from airunner.components.agents.expert_agents import (
    CalendarExpertAgent,
    CodeExpertAgent,
    ResearchExpertAgent,
    CreativeExpertAgent,
)


# Mark all async tests with anyio
pytestmark = pytest.mark.anyio


class TestAgentCapability:
    """Tests for AgentCapability dataclass."""

    def test_capability_creation(self):
        """Test creating an agent capability."""
        capability = AgentCapability(
            name="test_capability",
            description="A test capability",
            keywords=["test", "capability"],
            priority=7,
        )

        assert capability.name == "test_capability"
        assert capability.description == "A test capability"
        assert capability.keywords == ["test", "capability"]
        assert capability.priority == 7

    def test_capability_default_priority(self):
        """Test default priority value."""
        capability = AgentCapability(
            name="test", description="Test", keywords=["test"]
        )

        assert capability.priority == 5


class TestExpertAgent:
    """Tests for ExpertAgent base class."""

    @pytest.fixture
    def mock_agent(self):
        """Create a mock expert agent for testing."""

        class MockAgent(ExpertAgent):
            async def execute_task(self, task, context=None):
                return {
                    "success": True,
                    "result": "Mock result",
                    "metadata": {},
                }

        agent = MockAgent("test_agent", "Test agent")
        agent.register_capability(
            "test_cap", "Test capability", ["test", "mock"], priority=8
        )
        return agent

    def test_agent_initialization(self, mock_agent):
        """Test agent initialization."""
        assert mock_agent.name == "test_agent"
        assert mock_agent.description == "Test agent"
        assert len(mock_agent.capabilities) == 1

    def test_register_capability(self, mock_agent):
        """Test registering a capability."""
        mock_agent.register_capability(
            "another_cap",
            "Another capability",
            ["another", "capability"],
            priority=6,
        )

        assert len(mock_agent.capabilities) == 2
        assert mock_agent.capabilities[1].name == "another_cap"

    def test_evaluate_task_with_match(self, mock_agent):
        """Test task evaluation with keyword match."""
        score = mock_agent.evaluate_task("This is a test task")
        assert score > 0.0
        assert score <= 1.0

    def test_evaluate_task_without_match(self, mock_agent):
        """Test task evaluation without keyword match."""
        score = mock_agent.evaluate_task("No keywords here")
        assert score == 0.0

    def test_get_available_tools(self, mock_agent):
        """Test getting available tools."""
        tools = mock_agent.get_available_tools()
        assert isinstance(tools, list)
        assert len(tools) == 0  # Base implementation returns empty list

    def test_agent_repr(self, mock_agent):
        """Test string representation."""
        assert repr(mock_agent) == "<ExpertAgent: test_agent>"


class TestAgentRegistry:
    """Tests for AgentRegistry."""

    @pytest.fixture
    def registry(self):
        """Create a fresh registry for each test."""
        return AgentRegistry()

    @pytest.fixture
    def sample_agents(self):
        """Create sample agents for testing."""
        return [
            CalendarExpertAgent(),
            CodeExpertAgent(),
            ResearchExpertAgent(),
        ]

    def test_registry_initialization(self, registry):
        """Test registry initialization."""
        assert len(registry) == 0
        assert registry.list_agents() == []

    def test_register_agent(self, registry, sample_agents):
        """Test registering an agent."""
        agent = sample_agents[0]
        registry.register(agent)

        assert len(registry) == 1
        assert agent.name in registry
        assert registry.get(agent.name) == agent

    def test_register_duplicate_agent(self, registry, sample_agents):
        """Test registering an agent with duplicate name."""
        agent = sample_agents[0]
        registry.register(agent)

        with pytest.raises(ValueError, match="already registered"):
            registry.register(agent)

    def test_unregister_agent(self, registry, sample_agents):
        """Test unregistering an agent."""
        agent = sample_agents[0]
        registry.register(agent)
        registry.unregister(agent.name)

        assert len(registry) == 0
        assert agent.name not in registry

    def test_unregister_nonexistent_agent(self, registry):
        """Test unregistering a non-existent agent."""
        with pytest.raises(KeyError, match="not found"):
            registry.unregister("nonexistent")

    def test_list_agents(self, registry, sample_agents):
        """Test listing all agents."""
        for agent in sample_agents:
            registry.register(agent)

        agent_names = registry.list_agents()
        assert len(agent_names) == 3
        assert all(agent.name in agent_names for agent in sample_agents)

    def test_list_agents_by_capability(self, registry, sample_agents):
        """Test listing agents by capability."""
        for agent in sample_agents:
            registry.register(agent)

        # Calendar agent has event_management capability
        calendar_agents = registry.list_agents_by_capability(
            "event_management"
        )
        assert "calendar_expert" in calendar_agents
        assert len(calendar_agents) == 1

    def test_find_agents_for_task(self, registry, sample_agents):
        """Test finding agents for a task."""
        for agent in sample_agents:
            registry.register(agent)

        # Calendar-related task
        results = registry.find_agents_for_task("Schedule a meeting tomorrow")
        assert len(results) > 0
        assert results[0][0] == "calendar_expert"  # Top match
        assert results[0][1] > 0.0  # Has a score

    def test_find_agents_with_min_score(self, registry, sample_agents):
        """Test finding agents with minimum score filter."""
        for agent in sample_agents:
            registry.register(agent)

        results = registry.find_agents_for_task(
            "Generic task", min_score=0.9  # High threshold
        )
        # May have no results or very few with this generic task
        assert isinstance(results, list)

    def test_get_agent_info(self, registry, sample_agents):
        """Test getting agent information."""
        agent = sample_agents[0]
        registry.register(agent)

        info = registry.get_agent_info(agent.name)
        assert info is not None
        assert info["name"] == agent.name
        assert info["description"] == agent.description
        assert "capabilities" in info
        assert "tools" in info

    def test_get_agent_info_nonexistent(self, registry):
        """Test getting info for non-existent agent."""
        info = registry.get_agent_info("nonexistent")
        assert info is None

    def test_clear_registry(self, registry, sample_agents):
        """Test clearing the registry."""
        for agent in sample_agents:
            registry.register(agent)

        assert len(registry) == 3
        registry.clear()
        assert len(registry) == 0


class TestAgentRouter:
    """Tests for AgentRouter."""

    @pytest.fixture
    def registry(self):
        """Create registry with sample agents."""
        reg = AgentRegistry()
        reg.register(CalendarExpertAgent())
        reg.register(CodeExpertAgent())
        reg.register(ResearchExpertAgent())
        reg.register(CreativeExpertAgent())
        return reg

    @pytest.fixture
    def router(self, registry):
        """Create router with populated registry."""
        return AgentRouter(registry)

    @pytest.mark.anyio
    async def test_route_calendar_task(self, router):
        """Test routing a calendar task."""
        result = await router.route_task(
            "Create a meeting for next Tuesday",
            min_score=0.05,  # Lower threshold for unit tests
        )

        assert result["success"] is True
        assert "calendar_expert" in result["agents_used"]
        assert "calendar_expert" in result["scores"]

    @pytest.mark.asyncio
    async def test_route_code_task(self, router):
        """Test routing a code task."""
        result = await router.route_task(
            "Write a function to sort a list", min_score=0.05
        )

        assert result["success"] is True
        assert "code_expert" in result["agents_used"]

    @pytest.mark.asyncio
    async def test_route_research_task(self, router):
        """Test routing a research task."""
        result = await router.route_task(
            "Find information about Python", min_score=0.05
        )

        assert result["success"] is True
        assert "research_expert" in result["agents_used"]

    @pytest.mark.asyncio
    async def test_route_creative_task(self, router):
        """Test routing a creative task."""
        result = await router.route_task(
            "Write a story about a robot", min_score=0.05
        )

        assert result["success"] is True
        assert "creative_expert" in result["agents_used"]

    @pytest.mark.asyncio
    async def test_route_task_no_match(self, router):
        """Test routing a task with no matching agents."""
        result = await router.route_task(
            "Extremely specific task with no keywords",
            min_score=0.99,  # Very high threshold
        )

        assert result["success"] is False
        assert "error" in result
        assert len(result["agents_used"]) == 0

    @pytest.mark.asyncio
    async def test_route_task_with_context(self, router):
        """Test routing with context."""
        context = {"user_preference": "calendar"}
        result = await router.route_task(
            "Handle my schedule", context=context, min_score=0.05
        )

        assert result["success"] is True
        assert "result" in result

    @pytest.mark.asyncio
    async def test_route_task_max_agents(self, router):
        """Test routing with max agents limit."""
        result = await router.route_task(
            "Write code to schedule events",  # Could match multiple
            max_agents=2,
            min_score=0.05,
        )

    @pytest.mark.asyncio
    async def test_route_task_max_agents(self, router):
        """Test routing with max agents limit."""
        result = await router.route_task(
            "Write code to schedule events",  # Could match multiple
            max_agents=2,
            min_score=0.1,
        )

        assert result["success"] is True
        assert len(result["agents_used"]) <= 2

    @pytest.mark.asyncio
    async def test_collaborate(self, router):
        """Test agent collaboration."""
        result = await router.collaborate(
            "Plan and write a technical blog post",
            required_agents=["research_expert", "creative_expert"],
        )

        assert result["success"] is True
        assert result["collaboration"] is True
        assert "research_expert" in result["agents_used"]
        assert "creative_expert" in result["agents_used"]

    @pytest.mark.asyncio
    async def test_collaborate_with_nonexistent_agent(self, router):
        """Test collaboration with non-existent agent."""
        result = await router.collaborate(
            "Test task",
            required_agents=["calendar_expert", "nonexistent_agent"],
        )

        # Should still succeed with available agent
        assert "calendar_expert" in result["agents_used"]
        assert "nonexistent_agent" not in result["agents_used"]


class TestExpertAgents:
    """Integration tests for specific expert agents."""

    @pytest.mark.asyncio
    async def test_calendar_agent_create_event(self):
        """Test calendar agent event creation."""
        agent = CalendarExpertAgent()
        result = await agent.execute_task("Create a meeting tomorrow at 2pm")

        assert result["success"] is True
        assert result["result"]["action"] == "create_event"
        assert "metadata" in result

    @pytest.mark.asyncio
    async def test_calendar_agent_query_events(self):
        """Test calendar agent event query."""
        agent = CalendarExpertAgent()
        result = await agent.execute_task("What meetings do I have today?")

        assert result["success"] is True
        assert result["result"]["action"] == "query_events"

    @pytest.mark.asyncio
    async def test_code_agent_generate_code(self):
        """Test code agent code generation."""
        agent = CodeExpertAgent()
        result = await agent.execute_task(
            "Write a function to calculate fibonacci"
        )

        assert result["success"] is True
        assert result["result"]["action"] == "generate_code"

    @pytest.mark.asyncio
    async def test_code_agent_review_code(self):
        """Test code agent code review."""
        agent = CodeExpertAgent()
        result = await agent.execute_task("Review this code for issues")

        assert result["success"] is True
        assert result["result"]["action"] == "review_code"

    @pytest.mark.asyncio
    async def test_research_agent_search(self):
        """Test research agent information search."""
        agent = ResearchExpertAgent()
        result = await agent.execute_task("Find information about AI")

        assert result["success"] is True
        assert result["result"]["action"] == "search_information"

    @pytest.mark.asyncio
    async def test_research_agent_summarize(self):
        """Test research agent summarization."""
        agent = ResearchExpertAgent()
        result = await agent.execute_task("Summarize this document")

        assert result["success"] is True
        assert result["result"]["action"] == "summarize_content"

    @pytest.mark.asyncio
    async def test_creative_agent_write(self):
        """Test creative agent writing."""
        agent = CreativeExpertAgent()
        result = await agent.execute_task("Write a blog post about Python")

        assert result["success"] is True
        assert result["result"]["action"] == "generate_creative_content"

    @pytest.mark.asyncio
    async def test_creative_agent_brainstorm(self):
        """Test creative agent brainstorming."""
        agent = CreativeExpertAgent()
        result = await agent.execute_task("Brainstorm ideas for a new feature")

        assert result["success"] is True
        assert result["result"]["action"] == "brainstorm_ideas"


class TestEndToEndAgentSystem:
    """End-to-end integration tests for the complete agent system."""

    @pytest.fixture
    def full_system(self):
        """Set up complete agent system."""
        registry = AgentRegistry()
        registry.register(CalendarExpertAgent())
        registry.register(CodeExpertAgent())
        registry.register(ResearchExpertAgent())
        registry.register(CreativeExpertAgent())
        router = AgentRouter(registry)
        return registry, router

    @pytest.mark.asyncio
    async def test_end_to_end_routing(self, full_system):
        """Test end-to-end task routing."""
        registry, router = full_system

        # Test various tasks get routed correctly
        tasks = [
            ("Schedule a meeting", "calendar_expert"),
            ("Write a Python function", "code_expert"),
            ("Research quantum computing", "research_expert"),
            ("Write a creative story", "creative_expert"),
        ]

        for task, expected_agent in tasks:
            result = await router.route_task(task, min_score=0.05)
            assert result["success"] is True
            assert expected_agent in result["agents_used"]

    @pytest.mark.asyncio
    async def test_multi_agent_collaboration(self, full_system):
        """Test multiple agents collaborating on complex task."""
        registry, router = full_system

        result = await router.collaborate(
            "Research AI topics, then write a technical blog post",
            required_agents=["research_expert", "creative_expert"],
        )

        assert result["success"] is True
        assert result["collaboration"] is True
        assert len(result["agents_used"]) == 2

    @pytest.mark.asyncio
    async def test_agent_discovery(self, full_system):
        """Test agent discovery based on capabilities."""
        registry, router = full_system

        # Find all agents that can help with writing
        agents = registry.find_agents_for_task(
            "Write something", min_score=0.05
        )

    @pytest.mark.asyncio
    async def test_agent_discovery(self, full_system):
        """Test agent discovery based on capabilities."""
        registry, router = full_system

        # Find all agents that can help with writing
        agents = registry.find_agents_for_task(
            "Write something", min_score=0.05
        )

        assert len(agents) > 0
        # Both creative and code agents should match
        agent_names = [name for name, score in agents]
        assert any(
            "creative" in name or "code" in name for name in agent_names
        )
