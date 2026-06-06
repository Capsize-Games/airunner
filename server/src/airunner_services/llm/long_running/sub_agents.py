"""Sub-agent system for specialized task delegation.

This module provides specialized sub-agents that handle specific types
of work within long-running projects:

- ResearchSubAgent: Information gathering, synthesis
- DocumentationSubAgent: Writing docs, comments

Sub-agents can be more focused and use specialized tools/prompts
for their domain, improving overall quality.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional, List, Dict

from langchain_core.messages import HumanMessage, SystemMessage

from airunner_services.llm.core.tool_registry import (
    ToolRegistry,
    ToolCategory,
)
from airunner_services.settings import AIRUNNER_LOG_LEVEL
from airunner_services.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


RESEARCH_SYSTEM_PROMPT = """You are an expert research analyst specializing in comprehensive information gathering.

CAPABILITIES:
- Search and synthesize multiple sources
- Verify facts and cross-reference
- Analyze APIs and documentation
- Compare and contrast options
- Create comprehensive summaries

BEST PRACTICES:
- Always cite your sources
- Cross-reference multiple sources
- Note confidence levels
- Highlight uncertainties
- Provide actionable conclusions

PROCESS:
1. Understand the research question
2. Identify relevant sources
3. Gather information systematically
4. Synthesize findings
5. Verify key facts
6. Present clear conclusions

Always be thorough but focused.
Always distinguish facts from opinions.
Always provide source attribution."""


DOCUMENTATION_SYSTEM_PROMPT = """You are an expert technical writer specializing in clear, comprehensive documentation.

CAPABILITIES:
- Write clear API documentation
- Create user-friendly guides
- Document code thoroughly
- Write helpful README files
- Create architecture documents

BEST PRACTICES:
- Write for your audience
- Use clear, concise language
- Include examples
- Keep documentation updated
- Use consistent formatting
- Structure content logically

DOCUMENTATION TYPES:
1. Code comments: Explain why, not what
2. Docstrings: Function/class documentation
3. README: Project overview and setup
4. API docs: Endpoint/function references
5. Guides: Step-by-step instructions
6. Architecture: System design docs

Always make documentation:
- Accurate and up-to-date
- Easy to navigate
- Example-rich
- Searchable"""


TASK_CONTEXT_TEMPLATE = """# Task Context

## Feature to Implement
**Name:** {name}
**Description:** {description}
**Category:** {category}

**Verification Steps:**
{verification_steps}

## Project Context
{project_context}

## Past Decisions
{decision_context}

---

Implement this feature completely. Use your tools to:
1. Make necessary code changes
2. Create any new files needed
3. Test your changes
4. Verify all verification steps pass

Report what you did and the results."""


def _verification_steps(feature: Dict[str, Any]) -> str:
    """Return formatted verification steps for one feature."""
    return "\n".join(
        f"- {step}" for step in feature.get("verification_steps", [])
    )


def _context_prompt(context: Dict[str, Any]) -> str:
    """Build the task prompt for one sub-agent invocation."""
    feature = context.get("feature", {})
    return TASK_CONTEXT_TEMPLATE.format(
        name=feature.get("name", "Unknown"),
        description=feature.get("description", ""),
        category=feature.get("category", "functional"),
        verification_steps=_verification_steps(feature),
        project_context=context.get("project_context", ""),
        decision_context=context.get("decision_context", ""),
    )


def _invoke_result(response: Any) -> Dict[str, Any]:
    """Return the success payload for one sub-agent response."""
    return {
        "output": response.content,
        "files_changed": [],
        "verification_steps_passed": [],
        "error": None,
    }


def _invoke_error(name: str, error: Exception) -> Dict[str, Any]:
    """Return the failure payload for one sub-agent invocation."""
    logger.error("%s error: %s", name, error)
    return {
        "output": None,
        "files_changed": [],
        "verification_steps_passed": [],
        "error": str(error),
    }


class BaseSubAgent(ABC):
    """Base class for specialized sub-agents.

    Sub-agents handle specific types of work within projects,
    using domain-specific tools and prompts.

    Attributes:
        chat_model: LangChain chat model
        tools: List of tools available to this agent
        name: Agent name
        description: What this agent does
    """

    def __init__(
        self,
        chat_model: Any,
        tools: Optional[List[Any]] = None,
        name: str = "BaseSubAgent",
        description: str = "Base sub-agent",
    ):
        """Initialize sub-agent.

        Args:
            chat_model: LangChain chat model
            tools: Optional list of tools
            name: Agent name
            description: Agent description
        """
        self._chat_model = chat_model
        self._tools = tools or self._get_default_tools()
        self.name = name
        self.description = description

        # Bind tools to model
        if self._tools and hasattr(self._chat_model, "bind_tools"):
            self._chat_model = self._chat_model.bind_tools(self._tools)

        logger.info(f"Initialized {name} with {len(self._tools)} tools")

    @abstractmethod
    def _get_default_tools(self) -> List[Any]:
        """Get default tools for this agent type."""

    @abstractmethod
    def _get_system_prompt(self) -> str:
        """Get system prompt for this agent type."""

    def invoke(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke the sub-agent with context.

        Args:
            context: Dict with:
                - feature: Feature dict to work on
                - project_context: Progress log content
                - decision_context: Past decisions

        Returns:
            Dict with:
                - output: Agent's work output
                - files_changed: List of files modified
                - verification_steps_passed: List of passed steps
                - error: Any error encountered
        """
        messages = [
            SystemMessage(content=self._get_system_prompt()),
            HumanMessage(content=_context_prompt(context)),
        ]

        try:
            response = self._chat_model.invoke(messages)
            return _invoke_result(response)
        except Exception as error:
            return _invoke_error(self.name, error)


class ResearchSubAgent(BaseSubAgent):
    """Specialized agent for research tasks.

    Handles:
    - Information gathering
    - Source synthesis
    - Fact verification
    - Documentation research
    - API/library exploration
    """

    def __init__(self, chat_model: Any, tools: Optional[List[Any]] = None):
        """Initialize research sub-agent."""
        super().__init__(
            chat_model=chat_model,
            tools=tools,
            name="ResearchSubAgent",
            description="Deep research and information synthesis",
        )

    def _get_default_tools(self) -> List[Any]:
        """Get RESEARCH-category tools."""
        research_tools = ToolRegistry.get_by_category(ToolCategory.RESEARCH)
        return [tool.func for tool in research_tools]

    def _get_system_prompt(self) -> str:
        """Get research-focused system prompt."""
        return RESEARCH_SYSTEM_PROMPT


class DocumentationSubAgent(BaseSubAgent):
    """Specialized agent for documentation tasks.

    Handles:
    - Code documentation
    - API documentation
    - User guides
    - README creation
    - Comment writing
    """

    def __init__(self, chat_model: Any, tools: Optional[List[Any]] = None):
        """Initialize documentation sub-agent."""
        super().__init__(
            chat_model=chat_model,
            tools=tools,
            name="DocumentationSubAgent",
            description="Technical documentation and guides",
        )

    def _get_default_tools(self) -> List[Any]:
        """Get file/writing tools."""
        file_tools = ToolRegistry.get_by_category(ToolCategory.FILE)
        return [tool.func for tool in file_tools]

    def _get_system_prompt(self) -> str:
        """Get documentation-focused system prompt."""
        return DOCUMENTATION_SYSTEM_PROMPT


def create_sub_agents(
    chat_model: Any,
) -> Dict[str, BaseSubAgent]:
    """Create all sub-agents with a shared chat model.

    Args:
        chat_model: LangChain chat model

    Returns:
        Dict mapping category names to sub-agent instances
    """
    research_agent = ResearchSubAgent(chat_model)
    documentation_agent = DocumentationSubAgent(chat_model)

    return {
        "functional": documentation_agent,
        "research": research_agent,
        "integration": research_agent,
        "testing": documentation_agent,
        "documentation": documentation_agent,
        "ui": documentation_agent,
        "performance": research_agent,
        "security": research_agent,
    }
