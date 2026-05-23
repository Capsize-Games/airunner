"""Base class for specialized expert agents."""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass


@dataclass
class AgentCapability:
    """Describes a capability that an expert agent possesses.

    Attributes:
        name: Unique identifier for the capability
        description: Human-readable description
        keywords: Keywords that trigger this capability
        priority: Higher values indicate stronger match (0-10)
    """

    name: str
    description: str
    keywords: List[str]
    priority: int = 5


class ExpertAgent(ABC):
    """Abstract base class for specialized expert agents.

    Expert agents are specialized AI assistants that excel at specific
    tasks or domains (e.g., calendar management, code generation, research).
    They provide capabilities, evaluate task relevance, and execute tasks
    within their domain of expertise.
    """

    def __init__(self, name: str, description: str):
        """Initialize expert agent.

        Args:
            name: Unique identifier for the agent
            description: Human-readable description of agent's purpose
        """
        self.name = name
        self.description = description
        self._capabilities: List[AgentCapability] = []

    @property
    def capabilities(self) -> List[AgentCapability]:
        """Get list of agent capabilities.

        Returns:
            List of AgentCapability objects
        """
        return self._capabilities

    def register_capability(
        self,
        name: str,
        description: str,
        keywords: List[str],
        priority: int = 5,
    ) -> None:
        """Register a new capability for this agent.

        Args:
            name: Capability identifier
            description: Human-readable description
            keywords: Keywords that trigger this capability
            priority: Priority level (0-10)
        """
        capability = AgentCapability(
            name=name,
            description=description,
            keywords=keywords,
            priority=priority,
        )
        self._capabilities.append(capability)

    def evaluate_task(
        self, task: str, context: Optional[Dict] = None
    ) -> float:
        """Evaluate how well this agent can handle the given task.

        Analyzes the task and context to determine relevance score.
        Higher scores indicate better suitability for the task.

        Args:
            task: Task description
            context: Optional context dictionary

        Returns:
            Relevance score (0.0 to 1.0)
        """
        task_lower = task.lower()
        context = context or {}

        # Check for keyword matches across all capabilities
        max_score = 0.0
        for capability in self.capabilities:
            keyword_matches = sum(
                1
                for keyword in capability.keywords
                if keyword.lower() in task_lower
            )
            if keyword_matches > 0:
                # Score based on keyword matches and priority
                score = (keyword_matches / len(capability.keywords)) * (
                    capability.priority / 10.0
                )
                max_score = max(max_score, score)

        return min(max_score, 1.0)

    @abstractmethod
    async def execute_task(
        self, task: str, context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Execute the given task.

        Args:
            task: Task description
            context: Optional context dictionary

        Returns:
            Dictionary containing:
                - result: Task result
                - success: Boolean indicating success
                - metadata: Optional metadata about execution
        """

    def get_available_tools(self) -> List[str]:
        """Get list of available tool names for this agent.

        Returns:
            List of tool names
        """
        return []

    def __repr__(self) -> str:
        """String representation of the agent.

        Returns:
            String representation
        """
        return f"<ExpertAgent: {self.name}>"
