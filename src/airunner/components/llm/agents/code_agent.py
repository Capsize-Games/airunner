"""
Code Agent - Specialized subgraph for programming tasks.

This agent handles:
- Writing code in any language
- Debugging and testing
- Code review and analysis
- Explaining code concepts
- File operations related to code
"""

from typing import Any, Annotated, List, Callable
from typing_extensions import TypedDict

from langchain_core.messages import BaseMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.graph import START, END, StateGraph, add_messages
from langgraph.prebuilt import ToolNode

from airunner.components.llm.core.tool_registry import (
    ToolRegistry,
    ToolCategory,
)
from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


class CodeState(TypedDict):
    """
    State schema for Code agent.

    Attributes:
        messages: Conversation messages
        programming_language: Detected programming language
        task_type: Type of coding task (write, debug, review, etc.)
        execution_context: Context for code execution safety
    """

    messages: Annotated[list[BaseMessage], add_messages]
    programming_language: str
    task_type: str
    execution_context: dict


class CodeAgent:
    """
    Code Agent for programming tasks.

    Uses CODE-category tools to help with:
    - Code writing and generation
    - Code execution and testing
    - Code formatting and linting
    - Complexity analysis
    - File operations
    """

    def __init__(
        self,
        chat_model: Any,
        system_prompt: str = None,
    ):
        """
        Initialize Code Agent.

        Args:
            chat_model: LangChain chat model
            system_prompt: Optional custom system prompt
        """
        self._chat_model = chat_model
        self._system_prompt = system_prompt or self._default_system_prompt()
        self._tools = self._get_code_tools()

        # Bind tools to model
        if self._tools and hasattr(self._chat_model, "bind_tools"):
            self._chat_model = self._chat_model.bind_tools(self._tools)
            logger.info(f"Code agent bound {len(self._tools)} tools")

    def _default_system_prompt(self) -> str:
        """Get default system prompt for code mode."""
        return """You are a programming assistant specializing in helping users with:

- Writing code in any programming language
- Debugging and fixing code issues
- Code review and best practices
- Explaining code concepts
- Testing and validation

Focus on correctness, efficiency, and maintainability. Use your tools to:
- Execute code safely to verify it works
- Format code according to style guidelines
- Analyze code complexity and suggest improvements
- Create and manage code files

Always prioritize code safety and security. Never execute untrusted code without review."""

    def _get_code_tools(self) -> List[Callable]:
        """Get CODE-category tools from registry."""
        code_tools = ToolRegistry.get_by_category(ToolCategory.CODE)
        logger.info(f"Retrieved {len(code_tools)} CODE tools")

        # Convert ToolInfo to actual callable functions
        tools = [tool.func for tool in code_tools]
        return tools

    def _analyze_code_request(self, state: CodeState) -> dict:
        """
        Analyze the code request to determine language and task type.

        Args:
            state: Current code state

        Returns:
            Updated state with language, task_type, execution_context
        """
        messages = state.get("messages", [])
        if not messages:
            return {
                "programming_language": "unknown",
                "task_type": "general",
                "execution_context": {"safe_mode": True},
            }

        # Get last user message
        last_msg = None
        for msg in reversed(messages):
            if hasattr(msg, "type") and msg.type == "human":
                last_msg = msg
                break

        if not last_msg:
            return {
                "programming_language": "unknown",
                "task_type": "general",
                "execution_context": {"safe_mode": True},
            }

        content = str(last_msg.content).lower()

        # Detect programming language
        language = "unknown"
        language_keywords = {
            "python": ["python", "py", "django", "flask", "pandas"],
            "javascript": ["javascript", "js", "node", "react", "vue"],
            "typescript": ["typescript", "ts"],
            "java": ["java"],
            "c++": ["c++", "cpp"],
            "c": ["c programming"],
            "rust": ["rust"],
            "go": ["golang", "go"],
            "ruby": ["ruby", "rails"],
            "php": ["php"],
            "sql": ["sql", "database query"],
        }

        for lang, keywords in language_keywords.items():
            if any(keyword in content for keyword in keywords):
                language = lang
                break

        # Detect task type
        task_type = "general"
        if any(
            word in content
            for word in ["write", "create", "generate", "implement"]
        ):
            task_type = "write"
        elif any(word in content for word in ["debug", "fix", "error"]):
            task_type = "debug"
        elif any(word in content for word in ["review", "analyze", "check"]):
            task_type = "review"
        elif any(word in content for word in ["explain", "understand", "how"]):
            task_type = "explain"
        elif any(word in content for word in ["test", "verify"]):
            task_type = "test"

        # Execution context
        execution_context = {
            "safe_mode": True,
            "allow_file_ops": task_type in ["write", "test"],
            "timeout": 10,  # seconds
        }

        logger.info(
            f"Detected code request: lang={language}, task={task_type}"
        )

        return {
            "programming_language": language,
            "task_type": task_type,
            "execution_context": execution_context,
        }

    def _call_model(self, state: CodeState) -> dict:
        """
        Call the LLM with code-specific context.

        Args:
            state: Current code state

        Returns:
            Updated state with new AI message
        """
        messages = state.get("messages", [])
        language = state.get("programming_language", "unknown")
        task_type = state.get("task_type", "general")

        # Build prompt with code context
        task_description = {
            "write": "writing new code",
            "debug": "debugging and fixing code",
            "review": "reviewing and analyzing code",
            "explain": "explaining code concepts",
            "test": "testing and verifying code",
            "general": "general programming assistance",
        }.get(task_type, "general programming assistance")

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", self._system_prompt),
                (
                    "system",
                    f"Current task: {task_description} in {language}",
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        chain = prompt | self._chat_model
        response = chain.invoke({"messages": messages})

        return {"messages": [response]}

    def _route_after_model(self, state: CodeState) -> str:
        """
        Determine next step after model call.

        Args:
            state: Current code state

        Returns:
            Next node name ("tools" or "end")
        """
        messages = state.get("messages", [])
        if not messages:
            return "end"

        last_message = messages[-1]

        # Check if model wants to use tools
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            logger.info(
                f"Model requested {len(last_message.tool_calls)} tool calls"
            )
            return "tools"

        return "end"

    def build_graph(self) -> StateGraph:
        """
        Build the Code agent graph.

        Returns:
            StateGraph for code mode
        """
        logger.info("Building Code agent graph")

        graph = StateGraph(CodeState)

        # Add nodes
        graph.add_node("analyze_request", self._analyze_code_request)
        graph.add_node("model", self._call_model)

        if self._tools:
            tool_node = ToolNode(self._tools)
            graph.add_node("tools", tool_node)

        # Add edges
        graph.add_edge(START, "analyze_request")
        graph.add_edge("analyze_request", "model")

        if self._tools:
            graph.add_conditional_edges(
                "model",
                self._route_after_model,
                {
                    "tools": "tools",
                    "end": END,
                },
            )
            graph.add_edge("tools", "model")
        else:
            graph.add_edge("model", END)

        logger.info("Code agent graph built successfully")
        return graph

    def compile(self) -> Any:
        """
        Build and compile the Code agent graph.

        Returns:
            Compiled graph ready for invocation
        """
        graph = self.build_graph()
        compiled = graph.compile()
        logger.info("Code agent compiled successfully")
        return compiled
