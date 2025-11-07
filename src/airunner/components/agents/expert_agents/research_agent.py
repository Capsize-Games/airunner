"""Research expert agent for information gathering and analysis."""

from typing import Dict, List, Optional, Any
from datetime import datetime
from airunner.components.agents.expert_agent import ExpertAgent
from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger


class ResearchExpertAgent(ExpertAgent):
    """Expert agent specialized in research and information gathering.

    This agent handles tasks related to:
    - Information retrieval and search
    - Document analysis and summarization
    - Fact-checking and verification
    - Data synthesis and reporting
    """

    def __init__(self):
        """Initialize research expert agent."""
        super().__init__(
            name="research_expert",
            description="Specialized agent for research and information gathering",
        )
        self.logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)
        self._register_capabilities()

    def _register_capabilities(self) -> None:
        """Register agent capabilities."""
        self.register_capability(
            name="information_retrieval",
            description="Search and retrieve information",
            keywords=[
                "search",
                "find",
                "look up",
                "research",
                "information",
                "data",
                "facts",
                "details",
                "what is",
                "tell me about",
            ],
            priority=9,
        )

        self.register_capability(
            name="summarization",
            description="Summarize documents and content",
            keywords=[
                "summarize",
                "summary",
                "overview",
                "brief",
                "tl;dr",
                "key points",
                "main ideas",
            ],
            priority=8,
        )

        self.register_capability(
            name="analysis",
            description="Analyze and synthesize information",
            keywords=[
                "analyze",
                "analysis",
                "compare",
                "contrast",
                "evaluate",
                "assess",
                "examine",
                "investigate",
            ],
            priority=8,
        )

        self.register_capability(
            name="fact_checking",
            description="Verify facts and information",
            keywords=[
                "verify",
                "check",
                "confirm",
                "validate",
                "is it true",
                "fact check",
                "accurate",
            ],
            priority=7,
        )

    def get_available_tools(self) -> List[str]:
        """Get list of research-related tools.

        Returns:
            List of tool names
        """
        return [
            "search_knowledge",
            "summarize_document",
            "analyze_content",
            "extract_facts",
        ]

    async def execute_task(
        self, task: str, context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Execute a research-related task.

        Args:
            task: Task description
            context: Optional context dictionary

        Returns:
            Dictionary containing task result
        """
        self.logger.info(f"Research agent executing task: {task[:50]}...")

        context = context or {}
        task_lower = task.lower()

        # Determine task type
        if any(kw in task_lower for kw in ["summarize", "summary", "tl;dr"]):
            return await self._summarization_task(task, context)
        elif any(
            kw in task_lower for kw in ["analyze", "compare", "evaluate"]
        ):
            return await self._analysis_task(task, context)
        elif any(
            kw in task_lower for kw in ["verify", "check", "confirm", "fact"]
        ):
            return await self._fact_checking_task(task, context)
        else:
            # Default to information retrieval
            return await self._information_retrieval_task(task, context)

    async def _information_retrieval_task(
        self, task: str, context: Dict
    ) -> Dict[str, Any]:
        """Handle information retrieval task.

        Args:
            task: Task description
            context: Context dictionary

        Returns:
            Result dictionary
        """
        return {
            "success": True,
            "result": {
                "action": "search_information",
                "task_description": task,
                "search_strategy": [
                    "Extract key search terms",
                    "Search knowledge base",
                    "Filter and rank results",
                    "Synthesize findings",
                ],
                "recommended_tool": "search_knowledge",
            },
            "metadata": {
                "agent": self.name,
                "capability": "information_retrieval",
                "timestamp": datetime.utcnow().isoformat(),
            },
        }

    async def _summarization_task(
        self, task: str, context: Dict
    ) -> Dict[str, Any]:
        """Handle summarization task.

        Args:
            task: Task description
            context: Context dictionary

        Returns:
            Result dictionary
        """
        return {
            "success": True,
            "result": {
                "action": "summarize_content",
                "task_description": task,
                "summarization_approach": [
                    "Identify main topics",
                    "Extract key points",
                    "Remove redundant information",
                    "Create concise summary",
                ],
                "recommended_tool": "summarize_document",
            },
            "metadata": {
                "agent": self.name,
                "capability": "summarization",
                "timestamp": datetime.utcnow().isoformat(),
            },
        }

    async def _analysis_task(self, task: str, context: Dict) -> Dict[str, Any]:
        """Handle analysis task.

        Args:
            task: Task description
            context: Context dictionary

        Returns:
            Result dictionary
        """
        return {
            "success": True,
            "result": {
                "action": "analyze_content",
                "task_description": task,
                "analysis_dimensions": [
                    "Identify patterns and trends",
                    "Compare and contrast elements",
                    "Evaluate strengths and weaknesses",
                    "Draw conclusions",
                ],
                "recommended_tool": "analyze_content",
            },
            "metadata": {
                "agent": self.name,
                "capability": "analysis",
                "timestamp": datetime.utcnow().isoformat(),
            },
        }

    async def _fact_checking_task(
        self, task: str, context: Dict
    ) -> Dict[str, Any]:
        """Handle fact-checking task.

        Args:
            task: Task description
            context: Context dictionary

        Returns:
            Result dictionary
        """
        return {
            "success": True,
            "result": {
                "action": "verify_facts",
                "task_description": task,
                "verification_steps": [
                    "Extract claims to verify",
                    "Search for authoritative sources",
                    "Cross-reference information",
                    "Assess credibility",
                    "Report findings",
                ],
                "recommended_tool": "extract_facts",
            },
            "metadata": {
                "agent": self.name,
                "capability": "fact_checking",
                "timestamp": datetime.utcnow().isoformat(),
            },
        }
