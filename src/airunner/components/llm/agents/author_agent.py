"""
Author Agent - Specialized subgraph for creative writing tasks.

This agent handles:
- Story writing, articles, essays, poetry
- Writing improvement (style, grammar, clarity)
- Content generation and ideation
- Editing and proofreading
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


class AuthorState(TypedDict):
    """
    State schema for Author agent.

    Attributes:
        messages: Conversation messages
        writing_style: Requested writing style (formal, casual, creative, etc.)
        content_type: Type of content (story, article, essay, etc.)
    """

    messages: Annotated[list[BaseMessage], add_messages]
    writing_style: str
    content_type: str


class AuthorAgent:
    """
    Author Agent for creative writing tasks.

    Uses AUTHOR-category tools to help with:
    - Creative writing
    - Style improvement
    - Grammar checking
    - Vocabulary enhancement
    """

    def __init__(
        self,
        chat_model: Any,
        system_prompt: str = None,
    ):
        """
        Initialize Author Agent.

        Args:
            chat_model: LangChain chat model
            system_prompt: Optional custom system prompt
        """
        self._chat_model = chat_model
        self._system_prompt = system_prompt or self._default_system_prompt()
        self._tools = self._get_author_tools()

        # Bind tools to model
        if self._tools and hasattr(self._chat_model, "bind_tools"):
            self._chat_model = self._chat_model.bind_tools(self._tools)
            logger.info(f"Author agent bound {len(self._tools)} tools")

    def _default_system_prompt(self) -> str:
        """Get default system prompt for author mode."""
        return """You are a creative writing assistant specializing in helping users with:

- Writing stories, articles, essays, and poetry
- Improving writing style, grammar, and clarity
- Generating content ideas and outlines
- Editing and proofreading

Focus on creativity, clarity, and engaging content. Use your tools to:
- Check and improve grammar
- Enhance vocabulary with better word choices
- Analyze and improve writing style
- Provide constructive feedback

Be encouraging and supportive while maintaining high quality standards."""

    def _get_author_tools(self) -> List[Callable]:
        """Get AUTHOR-category tools from registry."""
        author_tools = ToolRegistry.get_by_category(ToolCategory.AUTHOR)
        logger.info(f"Retrieved {len(author_tools)} AUTHOR tools")

        # Convert ToolInfo to actual callable functions
        tools = [tool.func for tool in author_tools]
        return tools

    def _analyze_writing_request(self, state: AuthorState) -> dict:
        """
        Analyze the writing request to determine style and content type.

        Args:
            state: Current author state

        Returns:
            Updated state with writing_style and content_type
        """
        messages = state.get("messages", [])
        if not messages:
            return {
                "writing_style": "general",
                "content_type": "general",
            }

        # Get last user message
        last_msg = None
        for msg in reversed(messages):
            if hasattr(msg, "type") and msg.type == "human":
                last_msg = msg
                break

        if not last_msg:
            return {
                "writing_style": "general",
                "content_type": "general",
            }

        content = str(last_msg.content).lower()

        # Detect writing style
        style = "general"
        if any(
            word in content for word in ["formal", "professional", "academic"]
        ):
            style = "formal"
        elif any(
            word in content
            for word in ["casual", "friendly", "conversational"]
        ):
            style = "casual"
        elif any(
            word in content for word in ["creative", "artistic", "imaginative"]
        ):
            style = "creative"

        # Detect content type
        content_type = "general"
        if any(word in content for word in ["story", "narrative", "tale"]):
            content_type = "story"
        elif any(word in content for word in ["article", "blog"]):
            content_type = "article"
        elif any(word in content for word in ["essay", "paper"]):
            content_type = "essay"
        elif any(word in content for word in ["poem", "poetry", "verse"]):
            content_type = "poetry"

        logger.info(
            f"Detected writing request: style={style}, type={content_type}"
        )

        return {
            "writing_style": style,
            "content_type": content_type,
        }

    def _call_model(self, state: AuthorState) -> dict:
        """
        Call the LLM with author-specific context.

        Args:
            state: Current author state

        Returns:
            Updated state with new AI message
        """
        messages = state.get("messages", [])
        writing_style = state.get("writing_style", "general")
        content_type = state.get("content_type", "general")

        # Build prompt with style context
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", self._system_prompt),
                (
                    "system",
                    f"Current task: {content_type} in {writing_style} style",
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        chain = prompt | self._chat_model
        response = chain.invoke({"messages": messages})

        return {"messages": [response]}

    def _route_after_model(self, state: AuthorState) -> str:
        """
        Determine next step after model call.

        Args:
            state: Current author state

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
        Build the Author agent graph.

        Returns:
            StateGraph for author mode
        """
        logger.info("Building Author agent graph")

        graph = StateGraph(AuthorState)

        # Add nodes
        graph.add_node("analyze_request", self._analyze_writing_request)
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

        logger.info("Author agent graph built successfully")
        return graph

    def compile(self) -> Any:
        """
        Build and compile the Author agent graph.

        Returns:
            Compiled graph ready for invocation
        """
        graph = self.build_graph()
        compiled = graph.compile()
        logger.info("Author agent compiled successfully")
        return compiled
