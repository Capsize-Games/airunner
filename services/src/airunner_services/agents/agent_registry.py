"""Registry for managing expert agents."""

import threading
from typing import Dict, List, Optional
from airunner_services.agents.expert_agent import ExpertAgent


class AgentRegistry:
    """Registry for managing and discovering expert agents.

    The AgentRegistry maintains a collection of expert agents and provides
    methods for registering, discovering, and retrieving agents based on
    their capabilities.
    """

    def __init__(self):
        """Initialize agent registry."""
        self._agents: Dict[str, ExpertAgent] = {}
        self._lock = threading.Lock()

    def register(self, agent: ExpertAgent) -> None:
        """Register an expert agent.

        Args:
            agent: ExpertAgent instance to register

        Raises:
            ValueError: If agent with same name already registered
        """
        with self._lock:
            if agent.name in self._agents:
                raise ValueError(
                    f"Agent '{agent.name}' is already registered"
                )
            self._agents[agent.name] = agent

    def unregister(self, agent_name: str) -> None:
        """Unregister an expert agent.

        Args:
            agent_name: Name of agent to unregister

        Raises:
            KeyError: If agent not found
        """
        with self._lock:
            if agent_name not in self._agents:
                raise KeyError(f"Agent '{agent_name}' not found")
            del self._agents[agent_name]

    def get(self, agent_name: str) -> Optional[ExpertAgent]:
        """Get agent by name.

        Args:
            agent_name: Name of agent to retrieve

        Returns:
            ExpertAgent instance or None if not found
        """
        with self._lock:
            return self._agents.get(agent_name)

    def list_agents(self) -> List[str]:
        """List all registered agent names.

        Returns:
            List of agent names
        """
        with self._lock:
            return list(self._agents.keys())

    def list_agents_by_capability(self, capability_name: str) -> List[str]:
        """List agents that have a specific capability.

        Args:
            capability_name: Name of capability to search for

        Returns:
            List of agent names that have the capability
        """
        matching_agents = []
        with self._lock:
            agents = list(self._agents.items())
        for agent_name, agent in agents:
            for capability in agent.capabilities:
                if capability.name == capability_name:
                    matching_agents.append(agent_name)
                    break
        return matching_agents

    def find_agents_for_task(
        self, task: str, context: Optional[Dict] = None, min_score: float = 0.1
    ) -> List[tuple[str, float]]:
        """Find agents suitable for a task, ranked by relevance.

        Args:
            task: Task description
            context: Optional context dictionary
            min_score: Minimum relevance score to include (0.0 to 1.0)

        Returns:
            List of (agent_name, score) tuples, sorted by score descending
        """
        scores = []
        with self._lock:
            agents = list(self._agents.items())
        for agent_name, agent in agents:
            score = agent.evaluate_task(task, context)
            if score >= min_score:
                scores.append((agent_name, score))

        # Sort by score descending
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores

    def get_agent_info(self, agent_name: str) -> Optional[Dict]:
        """Get detailed information about an agent.

        Args:
            agent_name: Name of agent

        Returns:
            Dictionary with agent info or None if not found
        """
        agent = self.get(agent_name)
        if not agent:
            return None

        return {
            "name": agent.name,
            "description": agent.description,
            "capabilities": [
                {
                    "name": cap.name,
                    "description": cap.description,
                    "keywords": cap.keywords,
                    "priority": cap.priority,
                }
                for cap in agent.capabilities
            ],
            "tools": agent.get_available_tools(),
        }

    def clear(self) -> None:
        """Clear all registered agents."""
        with self._lock:
            self._agents.clear()

    def __len__(self) -> int:
        """Get number of registered agents.

        Returns:
            Number of registered agents
        """
        with self._lock:
            return len(self._agents)

    def __contains__(self, agent_name: str) -> bool:
        """Check if agent is registered.

        Args:
            agent_name: Name of agent to check

        Returns:
            True if agent is registered
        """
        with self._lock:
            return agent_name in self._agents
