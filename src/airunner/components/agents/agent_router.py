"""Router for directing tasks to appropriate expert agents."""

from typing import Dict, List, Optional, Any
from airunner.components.agents.agent_registry import AgentRegistry
from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger


class AgentRouter:
    """Routes tasks to appropriate expert agents.

    The AgentRouter analyzes incoming tasks and selects the most suitable
    expert agent(s) to handle them. It supports single-agent routing,
    multi-agent collaboration, and result aggregation.
    """

    def __init__(self, registry: AgentRegistry):
        """Initialize agent router.

        Args:
            registry: AgentRegistry instance
        """
        self.registry = registry
        self.logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)

    async def route_task(
        self,
        task: str,
        context: Optional[Dict] = None,
        min_score: float = 0.3,
        max_agents: int = 1,
    ) -> Dict[str, Any]:
        """Route a task to the most appropriate agent(s).

        Args:
            task: Task description
            context: Optional context dictionary
            min_score: Minimum relevance score to consider agent
            max_agents: Maximum number of agents to use

        Returns:
            Dictionary containing:
                - success: Boolean indicating success
                - result: Task result (or aggregated results)
                - agents_used: List of agent names that handled the task
                - scores: Dictionary of agent_name -> relevance_score
        """
        # Find suitable agents
        candidates = self.registry.find_agents_for_task(
            task, context, min_score=min_score
        )

        if not candidates:
            self.logger.warning(f"No agents found for task: {task[:50]}...")
            return {
                "success": False,
                "result": None,
                "error": "No suitable agents found",
                "agents_used": [],
                "scores": {},
            }

        # Select top agents up to max_agents
        selected_agents = candidates[:max_agents]
        self.logger.info(f"Selected {len(selected_agents)} agent(s) for task")

        # Execute task with selected agents
        results = []
        agents_used = []
        scores = {}

        for agent_name, score in selected_agents:
            agent = self.registry.get(agent_name)
            if not agent:
                continue

            try:
                self.logger.info(
                    f"Executing task with agent '{agent_name}' "
                    f"(score: {score:.2f})"
                )
                result = await agent.execute_task(task, context)
                results.append(
                    {"agent": agent_name, "score": score, "result": result}
                )
                agents_used.append(agent_name)
                scores[agent_name] = score
            except Exception as e:
                self.logger.error(
                    f"Agent '{agent_name}' failed to execute task: {e}"
                )
                results.append(
                    {"agent": agent_name, "score": score, "error": str(e)}
                )

        # Aggregate results
        if len(results) == 1:
            # Single agent result
            final_result = results[0].get("result")
            success = (
                final_result.get("success", False) if final_result else False
            )
        else:
            # Multiple agent results - aggregate
            final_result = self._aggregate_results(results)
            success = any(
                r.get("result", {}).get("success", False) for r in results
            )

        return {
            "success": success,
            "result": final_result,
            "agents_used": agents_used,
            "scores": scores,
        }

    def _aggregate_results(
        self, results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Aggregate results from multiple agents.

        Args:
            results: List of result dictionaries from agents

        Returns:
            Aggregated result dictionary
        """
        # Simple aggregation strategy: combine all successful results
        aggregated = {"type": "multi_agent_result", "individual_results": []}

        for result_entry in results:
            agent_name = result_entry.get("agent")
            result = result_entry.get("result")
            error = result_entry.get("error")

            if error:
                aggregated["individual_results"].append(
                    {"agent": agent_name, "success": False, "error": error}
                )
            elif result:
                aggregated["individual_results"].append(
                    {
                        "agent": agent_name,
                        "success": result.get("success", False),
                        "result": result.get("result"),
                        "metadata": result.get("metadata"),
                    }
                )

        # Extract primary result from highest-scoring successful agent
        successful = [
            r for r in aggregated["individual_results"] if r.get("success")
        ]
        if successful:
            aggregated["primary_result"] = successful[0].get("result")

        return aggregated

    async def collaborate(
        self,
        task: str,
        required_agents: List[str],
        context: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Execute a task requiring collaboration of specific agents.

        Args:
            task: Task description
            required_agents: List of agent names that must participate
            context: Optional context dictionary

        Returns:
            Dictionary containing collaborative results
        """
        results = []
        agents_used = []

        for agent_name in required_agents:
            agent = self.registry.get(agent_name)
            if not agent:
                self.logger.warning(f"Required agent '{agent_name}' not found")
                continue

            try:
                self.logger.info(
                    f"Collaborating agent '{agent_name}' executing task"
                )
                result = await agent.execute_task(task, context)
                results.append({"agent": agent_name, "result": result})
                agents_used.append(agent_name)

                # Add agent's result to context for next agent
                if context is None:
                    context = {}
                if "previous_results" not in context:
                    context["previous_results"] = []
                context["previous_results"].append(
                    {"agent": agent_name, "result": result}
                )
            except Exception as e:
                self.logger.error(
                    f"Collaboration failed for agent '{agent_name}': {e}"
                )
                results.append({"agent": agent_name, "error": str(e)})

        # Aggregate collaborative results
        final_result = self._aggregate_results(results)
        success = any(
            r.get("result", {}).get("success", False) for r in results
        )

        return {
            "success": success,
            "result": final_result,
            "agents_used": agents_used,
            "collaboration": True,
        }
