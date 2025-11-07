"""Creative expert agent for content generation."""

from typing import Dict, List, Optional, Any
from datetime import datetime
from airunner.components.agents.expert_agent import ExpertAgent
from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger


class CreativeExpertAgent(ExpertAgent):
    """Expert agent specialized in creative content generation.

    This agent handles tasks related to:
    - Creative writing (stories, articles, etc.)
    - Brainstorming and ideation
    - Content rephrasing and rewriting
    - Style adaptation
    """

    def __init__(self):
        """Initialize creative expert agent."""
        super().__init__(
            name="creative_expert",
            description="Specialized agent for creative content generation",
        )
        self.logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)
        self._register_capabilities()

    def _register_capabilities(self) -> None:
        """Register agent capabilities."""
        self.register_capability(
            name="creative_writing",
            description="Generate creative written content",
            keywords=[
                "write",
                "story",
                "article",
                "blog",
                "content",
                "compose",
                "draft",
                "creative",
                "narrative",
                "fiction",
            ],
            priority=9,
        )

        self.register_capability(
            name="brainstorming",
            description="Generate ideas and concepts",
            keywords=[
                "brainstorm",
                "ideas",
                "suggest",
                "propose",
                "come up with",
                "think of",
                "generate ideas",
                "creative ideas",
            ],
            priority=8,
        )

        self.register_capability(
            name="rewriting",
            description="Rephrase and rewrite content",
            keywords=[
                "rephrase",
                "rewrite",
                "paraphrase",
                "different way",
                "another way",
                "reword",
                "improve",
                "polish",
            ],
            priority=7,
        )

        self.register_capability(
            name="style_adaptation",
            description="Adapt content to different styles",
            keywords=[
                "style",
                "tone",
                "voice",
                "formal",
                "casual",
                "professional",
                "friendly",
                "technical",
                "simple",
            ],
            priority=7,
        )

    def get_available_tools(self) -> List[str]:
        """Get list of creative-related tools.

        Returns:
            List of tool names
        """
        return [
            "generate_content",
            "brainstorm_ideas",
            "rephrase_text",
            "adapt_style",
        ]

    async def execute_task(
        self, task: str, context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Execute a creative task.

        Args:
            task: Task description
            context: Optional context dictionary

        Returns:
            Dictionary containing task result
        """
        self.logger.info(f"Creative agent executing task: {task[:50]}...")

        context = context or {}
        task_lower = task.lower()

        # Determine task type
        if any(kw in task_lower for kw in ["brainstorm", "ideas", "suggest"]):
            return await self._brainstorming_task(task, context)
        elif any(
            kw in task_lower for kw in ["rephrase", "rewrite", "paraphrase"]
        ):
            return await self._rewriting_task(task, context)
        elif any(
            kw in task_lower for kw in ["style", "tone", "formal", "casual"]
        ):
            return await self._style_adaptation_task(task, context)
        else:
            # Default to creative writing
            return await self._creative_writing_task(task, context)

    async def _creative_writing_task(
        self, task: str, context: Dict
    ) -> Dict[str, Any]:
        """Handle creative writing task.

        Args:
            task: Task description
            context: Context dictionary

        Returns:
            Result dictionary
        """
        return {
            "success": True,
            "result": {
                "action": "generate_creative_content",
                "task_description": task,
                "writing_approach": [
                    "Understand topic and requirements",
                    "Develop creative angle",
                    "Structure content effectively",
                    "Use engaging language",
                    "Maintain consistent voice",
                ],
                "recommended_tool": "generate_content",
            },
            "metadata": {
                "agent": self.name,
                "capability": "creative_writing",
                "timestamp": datetime.utcnow().isoformat(),
            },
        }

    async def _brainstorming_task(
        self, task: str, context: Dict
    ) -> Dict[str, Any]:
        """Handle brainstorming task.

        Args:
            task: Task description
            context: Context dictionary

        Returns:
            Result dictionary
        """
        return {
            "success": True,
            "result": {
                "action": "brainstorm_ideas",
                "task_description": task,
                "ideation_approach": [
                    "Free association",
                    "Different perspectives",
                    "Novel combinations",
                    "Challenge assumptions",
                    "Build on concepts",
                ],
                "recommended_tool": "brainstorm_ideas",
            },
            "metadata": {
                "agent": self.name,
                "capability": "brainstorming",
                "timestamp": datetime.utcnow().isoformat(),
            },
        }

    async def _rewriting_task(
        self, task: str, context: Dict
    ) -> Dict[str, Any]:
        """Handle rewriting task.

        Args:
            task: Task description
            context: Context dictionary

        Returns:
            Result dictionary
        """
        return {
            "success": True,
            "result": {
                "action": "rephrase_content",
                "task_description": task,
                "rewriting_strategies": [
                    "Preserve core meaning",
                    "Use synonyms and varied structure",
                    "Improve clarity",
                    "Enhance readability",
                    "Maintain appropriate tone",
                ],
                "recommended_tool": "rephrase_text",
            },
            "metadata": {
                "agent": self.name,
                "capability": "rewriting",
                "timestamp": datetime.utcnow().isoformat(),
            },
        }

    async def _style_adaptation_task(
        self, task: str, context: Dict
    ) -> Dict[str, Any]:
        """Handle style adaptation task.

        Args:
            task: Task description
            context: Context dictionary

        Returns:
            Result dictionary
        """
        return {
            "success": True,
            "result": {
                "action": "adapt_style",
                "task_description": task,
                "adaptation_considerations": [
                    "Identify target style",
                    "Adjust vocabulary",
                    "Modify sentence structure",
                    "Adapt tone and voice",
                    "Maintain message integrity",
                ],
                "recommended_tool": "adapt_style",
            },
            "metadata": {
                "agent": self.name,
                "capability": "style_adaptation",
                "timestamp": datetime.utcnow().isoformat(),
            },
        }
