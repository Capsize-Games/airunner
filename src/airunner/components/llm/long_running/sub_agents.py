"""Sub-agent system for specialized task delegation.

This module provides specialized sub-agents that handle specific types
of work within long-running projects:

- CodeSubAgent: Code writing, debugging, testing
- ResearchSubAgent: Information gathering, synthesis
- TestingSubAgent: Test creation, validation
- DocumentationSubAgent: Writing docs, comments

Sub-agents can be more focused and use specialized tools/prompts
for their domain, improving overall quality.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional, List, Dict

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from airunner.components.llm.core.tool_registry import (
    ToolRegistry,
    ToolCategory,
)
from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


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
        pass

    @abstractmethod
    def _get_system_prompt(self) -> str:
        """Get system prompt for this agent type."""
        pass

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
        feature = context.get("feature", {})
        project_context = context.get("project_context", "")
        decision_context = context.get("decision_context", "")

        # Build prompt
        prompt = f"""# Task Context

## Feature to Implement
**Name:** {feature.get('name', 'Unknown')}
**Description:** {feature.get('description', '')}
**Category:** {feature.get('category', 'functional')}

**Verification Steps:**
{chr(10).join(f'- {step}' for step in feature.get('verification_steps', []))}

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

        messages = [
            SystemMessage(content=self._get_system_prompt()),
            HumanMessage(content=prompt),
        ]

        try:
            response = self._chat_model.invoke(messages)
            return {
                "output": response.content,
                "files_changed": [],  # Would be extracted from tool calls
                "verification_steps_passed": [],
                "error": None,
            }
        except Exception as e:
            logger.error(f"{self.name} error: {e}")
            return {
                "output": None,
                "files_changed": [],
                "verification_steps_passed": [],
                "error": str(e),
            }


class CodeSubAgent(BaseSubAgent):
    """Specialized agent for coding tasks.

    Handles:
    - Writing new code
    - Debugging existing code
    - Code refactoring
    - Unit test creation
    - Code execution and validation
    """

    def __init__(self, chat_model: Any, tools: Optional[List[Any]] = None):
        """Initialize code sub-agent."""
        super().__init__(
            chat_model=chat_model,
            tools=tools,
            name="CodeSubAgent",
            description="Expert code writing and debugging",
        )

    def _get_default_tools(self) -> List[Any]:
        """Get CODE-category tools."""
        code_tools = ToolRegistry.get_by_category(ToolCategory.CODE)
        return [tool.func for tool in code_tools]

    def _get_system_prompt(self) -> str:
        """Get code-focused system prompt."""
        return """You are an expert software engineer specializing in writing high-quality code.

CAPABILITIES:
- Write clean, well-documented code in any language
- Debug and fix complex issues
- Create comprehensive unit tests
- Refactor code for maintainability
- Execute and validate code safely

BEST PRACTICES:
- Follow language-specific conventions
- Write clear, descriptive comments
- Handle errors gracefully
- Use meaningful variable/function names
- Keep functions small and focused
- Write tests alongside code

PROCESS:
1. Understand the requirement completely
2. Plan the implementation
3. Write the code incrementally
4. Test each component
5. Refactor if needed
6. Verify all requirements met

Always prefer simple, readable code over clever solutions.
Always handle edge cases and errors.
Always validate your work before declaring completion."""


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
        return """You are an expert research analyst specializing in comprehensive information gathering.

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


class TestingSubAgent(BaseSubAgent):
    """Specialized agent for testing tasks.

    Handles:
    - Unit test creation
    - Integration test design
    - Test execution
    - Coverage analysis
    - Bug reproduction
    """

    def __init__(self, chat_model: Any, tools: Optional[List[Any]] = None):
        """Initialize testing sub-agent."""
        super().__init__(
            chat_model=chat_model,
            tools=tools,
            name="TestingSubAgent",
            description="Comprehensive testing and validation",
        )

    def _get_default_tools(self) -> List[Any]:
        """Get testing-relevant tools."""
        code_tools = ToolRegistry.get_by_category(ToolCategory.CODE)
        return [tool.func for tool in code_tools]

    def _get_system_prompt(self) -> str:
        """Get testing-focused system prompt."""
        return """You are an expert QA engineer specializing in comprehensive software testing.

CAPABILITIES:
- Write thorough unit tests
- Design integration tests
- Create end-to-end test scenarios
- Analyze test coverage
- Identify edge cases and bugs

BEST PRACTICES:
- Test both happy paths and edge cases
- Use descriptive test names
- Keep tests independent
- Mock external dependencies
- Aim for high coverage
- Document test purpose

TEST CATEGORIES:
1. Unit tests: Individual functions/methods
2. Integration tests: Component interactions
3. End-to-end tests: Full user workflows
4. Edge case tests: Boundary conditions
5. Error handling tests: Failure scenarios

Always ensure tests are:
- Fast to run
- Reliable (no flaky tests)
- Readable and maintainable
- Independent of each other"""


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
        return """You are an expert technical writer specializing in clear, comprehensive documentation.

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


def create_sub_agents(
    chat_model: Any,
) -> Dict[str, BaseSubAgent]:
    """Create all sub-agents with a shared chat model.

    Args:
        chat_model: LangChain chat model

    Returns:
        Dict mapping category names to sub-agent instances
    """
    return {
        "functional": CodeSubAgent(chat_model),
        "code": CodeSubAgent(chat_model),
        "research": ResearchSubAgent(chat_model),
        "integration": ResearchSubAgent(chat_model),  # Research for APIs
        "testing": TestingSubAgent(chat_model),
        "documentation": DocumentationSubAgent(chat_model),
        "ui": CodeSubAgent(chat_model),  # UI is still code
        "performance": CodeSubAgent(chat_model),
        "security": CodeSubAgent(chat_model),
    }
