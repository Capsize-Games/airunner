"""Code expert agent for code generation and analysis."""

from typing import Dict, List, Optional, Any
from datetime import datetime
from airunner.components.agents.expert_agent import ExpertAgent
from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger


class CodeExpertAgent(ExpertAgent):
    """Expert agent specialized in code generation and analysis.

    This agent handles tasks related to:
    - Code generation
    - Code review and analysis
    - Debugging assistance
    - Refactoring suggestions
    - Documentation generation
    """

    def __init__(self):
        """Initialize code expert agent."""
        super().__init__(
            name="code_expert",
            description="Specialized agent for code generation and analysis",
        )
        self.logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)
        self._register_capabilities()

    def _register_capabilities(self) -> None:
        """Register agent capabilities."""
        self.register_capability(
            name="code_generation",
            description="Generate code from specifications",
            keywords=[
                "code",
                "function",
                "class",
                "implement",
                "write",
                "create",
                "generate",
                "program",
                "script",
                "module",
            ],
            priority=9,
        )

        self.register_capability(
            name="code_review",
            description="Review and analyze code for issues",
            keywords=[
                "review",
                "analyze",
                "check",
                "improve",
                "optimize",
                "refactor",
                "clean up",
                "best practices",
            ],
            priority=8,
        )

        self.register_capability(
            name="debugging",
            description="Help debug code issues",
            keywords=[
                "debug",
                "fix",
                "error",
                "bug",
                "issue",
                "problem",
                "not working",
                "broken",
            ],
            priority=8,
        )

        self.register_capability(
            name="documentation",
            description="Generate code documentation",
            keywords=[
                "document",
                "docstring",
                "comment",
                "explain",
                "describe",
                "documentation",
            ],
            priority=7,
        )

    def get_available_tools(self) -> List[str]:
        """Get list of code-related tools.

        Returns:
            List of tool names
        """
        return [
            "generate_code",
            "review_code",
            "refactor_code",
            "generate_docstring",
            "analyze_complexity",
        ]

    async def execute_task(
        self, task: str, context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Execute a code-related task.

        Args:
            task: Task description
            context: Optional context dictionary

        Returns:
            Dictionary containing task result
        """
        self.logger.info(f"Code agent executing task: {task[:50]}...")

        context = context or {}
        task_lower = task.lower()

        # Determine task type
        if any(
            kw in task_lower
            for kw in ["generate", "create", "write", "implement"]
        ):
            return await self._code_generation_task(task, context)
        elif any(kw in task_lower for kw in ["review", "analyze", "check"]):
            return await self._code_review_task(task, context)
        elif any(kw in task_lower for kw in ["debug", "fix", "error", "bug"]):
            return await self._debugging_task(task, context)
        elif any(
            kw in task_lower for kw in ["document", "docstring", "comment"]
        ):
            return await self._documentation_task(task, context)
        elif any(
            kw in task_lower for kw in ["refactor", "optimize", "improve"]
        ):
            return await self._refactoring_task(task, context)
        else:
            # Default to code generation
            return await self._code_generation_task(task, context)

    async def _code_generation_task(
        self, task: str, context: Dict
    ) -> Dict[str, Any]:
        """Handle code generation task.

        Args:
            task: Task description
            context: Context dictionary

        Returns:
            Result dictionary
        """
        return {
            "success": True,
            "result": {
                "action": "generate_code",
                "task_description": task,
                "recommended_approach": "Generate code following best practices",
                "considerations": [
                    "Follow project coding standards",
                    "Include appropriate error handling",
                    "Add type hints where applicable",
                    "Write clear, self-documenting code",
                ],
            },
            "metadata": {
                "agent": self.name,
                "capability": "code_generation",
                "timestamp": datetime.utcnow().isoformat(),
            },
        }

    async def _code_review_task(
        self, task: str, context: Dict
    ) -> Dict[str, Any]:
        """Handle code review task.

        Args:
            task: Task description
            context: Context dictionary

        Returns:
            Result dictionary
        """
        return {
            "success": True,
            "result": {
                "action": "review_code",
                "task_description": task,
                "review_areas": [
                    "Code correctness",
                    "Performance optimization",
                    "Security considerations",
                    "Best practices adherence",
                    "Code maintainability",
                ],
            },
            "metadata": {
                "agent": self.name,
                "capability": "code_review",
                "timestamp": datetime.utcnow().isoformat(),
            },
        }

    async def _debugging_task(
        self, task: str, context: Dict
    ) -> Dict[str, Any]:
        """Handle debugging task.

        Args:
            task: Task description
            context: Context dictionary

        Returns:
            Result dictionary
        """
        return {
            "success": True,
            "result": {
                "action": "debug_code",
                "task_description": task,
                "debugging_steps": [
                    "Identify error location",
                    "Analyze error message/traceback",
                    "Review relevant code context",
                    "Suggest fixes",
                    "Recommend testing approaches",
                ],
            },
            "metadata": {
                "agent": self.name,
                "capability": "debugging",
                "timestamp": datetime.utcnow().isoformat(),
            },
        }

    async def _documentation_task(
        self, task: str, context: Dict
    ) -> Dict[str, Any]:
        """Handle documentation generation task.

        Args:
            task: Task description
            context: Context dictionary

        Returns:
            Result dictionary
        """
        return {
            "success": True,
            "result": {
                "action": "generate_documentation",
                "task_description": task,
                "documentation_style": "Google Python Style Guide",
                "includes": [
                    "Function/method descriptions",
                    "Parameter documentation",
                    "Return value documentation",
                    "Usage examples where appropriate",
                ],
            },
            "metadata": {
                "agent": self.name,
                "capability": "documentation",
                "timestamp": datetime.utcnow().isoformat(),
            },
        }

    async def _refactoring_task(
        self, task: str, context: Dict
    ) -> Dict[str, Any]:
        """Handle code refactoring task.

        Args:
            task: Task description
            context: Context dictionary

        Returns:
            Result dictionary
        """
        return {
            "success": True,
            "result": {
                "action": "refactor_code",
                "task_description": task,
                "refactoring_goals": [
                    "Improve code readability",
                    "Reduce complexity",
                    "Eliminate duplication",
                    "Enhance maintainability",
                    "Follow SOLID principles",
                ],
            },
            "metadata": {
                "agent": self.name,
                "capability": "code_review",
                "timestamp": datetime.utcnow().isoformat(),
            },
        }
