"""LangSmith evaluation tests for expert agent system.

These tests validate LLM output quality using LangSmith evaluators.
Following the pattern from ~/Projects/agent/eval_tests/test_dev_onboarding_agent.py
"""

import pytest
from langsmith import testing as t
from openevals.llm import create_llm_as_judge

from airunner.components.agents.agent_registry import AgentRegistry
from airunner.components.agents.agent_router import AgentRouter
from airunner.components.agents.expert_agents.calendar_agent import (
    CalendarExpertAgent,
)
from airunner.components.agents.expert_agents.code_agent import (
    CodeExpertAgent,
)
from airunner.components.agents.expert_agents.research_agent import (
    ResearchExpertAgent,
)
from airunner.components.agents.expert_agents.creative_agent import (
    CreativeExpertAgent,
)

# LLM-as-Judge evaluators using ollama:llama3.2
CORRECTNESS_PROMPT = """You are an expert evaluator assessing AI agent task routing decisions.

Task: {inputs[task]}
Expected Agent Type: {reference_outputs[expected_agent_type]}
Selected Agents: {outputs[agents_used]}
Agent Reasoning: {outputs[reasoning]}

Evaluate whether the agent router correctly selected the appropriate expert agent(s) for the task.

Score 1-5:
5: Perfect match - selected agent is ideal for the task
4: Good match - selected agent can handle the task well
3: Acceptable match - selected agent can handle the task adequately
2: Poor match - selected agent is suboptimal for the task
1: Wrong match - selected agent cannot handle the task properly

Provide your score and reasoning."""

CONCISENESS_PROMPT = """You are an expert evaluator assessing AI agent response quality.

Task: {inputs[task]}
Agent Response: {outputs[result]}

Evaluate whether the agent's response is concise and actionable.

Score 1-5:
5: Extremely concise with clear, actionable recommendations
4: Concise with good actionable recommendations
3: Adequately concise with reasonable recommendations
2: Somewhat verbose or vague recommendations
1: Very verbose or unclear recommendations

Provide your score and reasoning."""

# Create evaluators
correctness_evaluator = create_llm_as_judge(
    prompt=CORRECTNESS_PROMPT,
    model="ollama:llama3.2",
)

conciseness_evaluator = create_llm_as_judge(
    prompt=CONCISENESS_PROMPT,
    model="ollama:llama3.2",
)


class AgentSystemEvaluator:
    """Evaluator for agent system using real LLM."""

    def __init__(self):
        """Initialize evaluator with registry and router."""
        self.registry = AgentRegistry()
        self.router = AgentRouter(self.registry)

        # Register all expert agents
        self.calendar_agent = CalendarExpertAgent()
        self.code_agent = CodeExpertAgent()
        self.research_agent = ResearchExpertAgent()
        self.creative_agent = CreativeExpertAgent()

        self.registry.register(self.calendar_agent)
        self.registry.register(self.code_agent)
        self.registry.register(self.research_agent)
        self.registry.register(self.creative_agent)

    async def route_task(self, task: str) -> dict:
        """Route a task and return results.

        Args:
            task: Task description

        Returns:
            Dictionary with routing results
        """
        result = await self.router.route_task(task, min_score=0.05)
        return result


@pytest.fixture
def evaluator():
    """Create agent system evaluator fixture."""
    return AgentSystemEvaluator()


# Test cases with reference outputs
test_cases = [
    {
        "task": "Schedule a team meeting for next Tuesday at 2pm",
        "expected_agent_type": "calendar",
        "expected_agent_name": "calendar_expert",
    },
    {
        "task": "Write a Python function to calculate fibonacci numbers",
        "expected_agent_type": "code",
        "expected_agent_name": "code_expert",
    },
    {
        "task": "Research the latest advances in quantum computing",
        "expected_agent_type": "research",
        "expected_agent_name": "research_expert",
    },
    {
        "task": "Write a creative short story about time travel",
        "expected_agent_type": "creative",
        "expected_agent_name": "creative_expert",
    },
    {
        "task": "Create a reminder to call the dentist tomorrow",
        "expected_agent_type": "calendar",
        "expected_agent_name": "calendar_expert",
    },
    {
        "task": "Debug this Python code that's throwing an exception",
        "expected_agent_type": "code",
        "expected_agent_name": "code_expert",
    },
]


@pytest.mark.asyncio
async def test_agent_routing_correctness(evaluator):
    """Test agent routing correctness using LLM-as-judge.

    This test validates that the agent router selects the correct
    expert agent for various tasks, using an LLM to judge correctness.
    """

    async def run_routing(inputs: dict) -> dict:
        """Run agent routing for evaluation.

        Args:
            inputs: Dictionary with 'task' key

        Returns:
            Dictionary with routing results
        """
        task = inputs["task"]
        result = await evaluator.route_task(task)

        return {
            "agents_used": result.get("agents_used", []),
            "reasoning": result.get("message", ""),
            "success": result.get("success", False),
        }

    # Run evaluation
    results = await t.aevaluate(
        run_routing,
        data=[
            {
                "inputs": {"task": case["task"]},
                "reference_outputs": {
                    "expected_agent_type": case["expected_agent_type"],
                    "expected_agent_name": case["expected_agent_name"],
                },
            }
            for case in test_cases
        ],
        evaluators=[correctness_evaluator],
        experiment_prefix="agent_routing_correctness",
    )

    # Log individual results
    for i, case in enumerate(test_cases):
        t.log_inputs({"task": case["task"]})
        t.log_reference_outputs(
            {
                "expected_agent_type": case["expected_agent_type"],
                "expected_agent_name": case["expected_agent_name"],
            }
        )

    # Assert overall correctness threshold
    # At least 80% of cases should score >= 4/5
    high_scores = sum(1 for r in results if r.get("score", 0) >= 4)
    total_cases = len(test_cases)
    success_rate = high_scores / total_cases

    assert success_rate >= 0.8, (
        f"Agent routing correctness below threshold: "
        f"{success_rate:.1%} (expected >= 80%)"
    )


@pytest.mark.asyncio
async def test_agent_response_quality(evaluator):
    """Test agent response quality using LLM-as-judge.

    This test validates that expert agents provide concise and
    actionable responses, using an LLM to judge quality.
    """

    async def run_agent_execution(inputs: dict) -> dict:
        """Run agent execution for evaluation.

        Args:
            inputs: Dictionary with 'task' key

        Returns:
            Dictionary with execution results
        """
        task = inputs["task"]
        result = await evaluator.route_task(task)

        # Extract agent result
        agent_result = ""
        if result.get("success") and result.get("results"):
            # Get first agent's result
            agent_result = str(result["results"][0])

        return {
            "result": agent_result,
            "success": result.get("success", False),
        }

    # Run evaluation
    results = await t.aevaluate(
        run_agent_execution,
        data=[
            {
                "inputs": {"task": case["task"]},
                "reference_outputs": {
                    "expected_agent_type": case["expected_agent_type"],
                },
            }
            for case in test_cases
        ],
        evaluators=[conciseness_evaluator],
        experiment_prefix="agent_response_quality",
    )

    # Log individual results
    for i, case in enumerate(test_cases):
        t.log_inputs({"task": case["task"]})

    # Assert overall quality threshold
    # At least 70% of cases should score >= 3/5
    acceptable_scores = sum(1 for r in results if r.get("score", 0) >= 3)
    total_cases = len(test_cases)
    quality_rate = acceptable_scores / total_cases

    assert quality_rate >= 0.7, (
        f"Agent response quality below threshold: "
        f"{quality_rate:.1%} (expected >= 70%)"
    )


@pytest.mark.asyncio
async def test_multi_agent_collaboration_quality(evaluator):
    """Test multi-agent collaboration quality using LLM-as-judge.

    This test validates that the agent router can effectively
    coordinate multiple agents for complex tasks.
    """
    complex_tasks = [
        {
            "task": (
                "Research Python best practices and then write example code"
            ),
            "required_agents": ["research_expert", "code_expert"],
        },
        {
            "task": (
                "Brainstorm creative ideas for a story, "
                "then schedule time to write it"
            ),
            "required_agents": ["creative_expert", "calendar_expert"],
        },
    ]

    async def run_collaboration(inputs: dict) -> dict:
        """Run multi-agent collaboration.

        Args:
            inputs: Dictionary with 'task' and 'required_agents'

        Returns:
            Dictionary with collaboration results
        """
        task = inputs["task"]
        required = inputs["required_agents"]

        result = await evaluator.router.collaborate(task, required)

        return {
            "agents_used": result.get("agents_used", []),
            "results": result.get("results", []),
            "success": result.get("success", False),
        }

    # Run evaluation
    results = await t.aevaluate(
        run_collaboration,
        data=[
            {
                "inputs": {
                    "task": case["task"],
                    "required_agents": case["required_agents"],
                },
                "reference_outputs": {
                    "required_agents": case["required_agents"],
                },
            }
            for case in complex_tasks
        ],
        evaluators=[correctness_evaluator, conciseness_evaluator],
        experiment_prefix="multi_agent_collaboration",
    )

    # Log results
    for i, case in enumerate(complex_tasks):
        t.log_inputs(
            {
                "task": case["task"],
                "required_agents": case["required_agents"],
            }
        )

    # Assert collaboration success
    # All complex tasks should succeed
    successful = sum(1 for r in results if r.get("success", False))
    total_tasks = len(complex_tasks)

    assert successful == total_tasks, (
        f"Multi-agent collaboration failed: "
        f"{successful}/{total_tasks} tasks successful"
    )
