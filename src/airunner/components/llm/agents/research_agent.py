"""
Research Agent - Specialized subgraph for information gathering tasks.

This agent handles:
- Searching for information
- Synthesizing multiple sources
- Comparing viewpoints
- Organizing research findings
- Citation management
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


class ResearchState(TypedDict):
    """
    State schema for Research agent.

    Attributes:
        messages: Conversation messages
        research_topic: Main topic being researched
        source_count: Number of sources to gather
        citation_style: Citation format (APA, MLA, Chicago)
    """

    messages: Annotated[list[BaseMessage], add_messages]
    research_topic: str
    source_count: int
    citation_style: str


class ResearchAgent:
    """
    Research Agent for information gathering tasks.

    Uses RESEARCH-category tools to help with:
    - Information synthesis
    - Source citation
    - Research organization
    - Key point extraction
    - Source comparison
    """

    def __init__(
        self,
        chat_model: Any,
        system_prompt: str = None,
    ):
        """
        Initialize Research Agent.

        Args:
            chat_model: LangChain chat model
            system_prompt: Optional custom system prompt
        """
        self._chat_model = chat_model
        self._system_prompt = system_prompt or self._default_system_prompt()
        self._tools = self._get_research_tools()

        # Bind tools to model
        if self._tools and hasattr(self._chat_model, "bind_tools"):
            self._chat_model = self._chat_model.bind_tools(self._tools)
            logger.info(f"Research agent bound {len(self._tools)} tools")

    def _default_system_prompt(self) -> str:
        """Get default system prompt for research mode."""
        return """You are a research assistant specializing in helping users with:

- Finding and gathering information
- Synthesizing multiple sources
- Comparing different viewpoints
- Organizing research findings
- Creating proper citations

Focus on accuracy, thoroughness, and credible sources. Use your tools to:
- Synthesize information from multiple sources
- Generate proper citations in APA, MLA, or Chicago format
- Organize research findings into coherent structures
- Extract key points from complex information
- Compare and contrast different sources

Always verify information and cite sources properly."""

    def _get_research_tools(self) -> List[Callable]:
        """Get RESEARCH-category tools from registry."""
        research_tools = ToolRegistry.get_by_category(ToolCategory.RESEARCH)
        logger.info(f"Retrieved {len(research_tools)} RESEARCH tools")

        # Convert ToolInfo to actual callable functions
        tools = [tool.func for tool in research_tools]
        return tools

    def _plan_research(self, state: ResearchState) -> dict:
        """
        Plan the research approach based on the request.

        Args:
            state: Current research state

        Returns:
            Updated state with topic, source_count, citation_style
        """
        messages = state.get("messages", [])
        if not messages:
            return {
                "research_topic": "general",
                "source_count": 3,
                "citation_style": "APA",
            }

        # Get last user message
        last_msg = None
        for msg in reversed(messages):
            if hasattr(msg, "type") and msg.type == "human":
                last_msg = msg
                break

        if not last_msg:
            return {
                "research_topic": "general",
                "source_count": 3,
                "citation_style": "APA",
            }

        content = str(last_msg.content).lower()

        # Extract topic (simplified - just use first few words)
        words = content.split()[:10]
        topic = " ".join(words) if words else "general"

        # Detect desired source count
        source_count = 3  # default
        if "many sources" in content or "comprehensive" in content:
            source_count = 5
        elif "few sources" in content or "quick" in content:
            source_count = 2

        # Detect citation style
        citation_style = "APA"  # default
        if "mla" in content:
            citation_style = "MLA"
        elif "chicago" in content:
            citation_style = "Chicago"

        logger.info(
            f"Research plan: topic='{topic[:50]}...', "
            f"sources={source_count}, style={citation_style}"
        )

        return {
            "research_topic": topic,
            "source_count": source_count,
            "citation_style": citation_style,
        }

    def _call_model(self, state: ResearchState) -> dict:
        """
        Call the LLM with research-specific context.

        Args:
            state: Current research state

        Returns:
            Updated state with new AI message
        """
        messages = state.get("messages", [])
        topic = state.get("research_topic", "general")
        source_count = state.get("source_count", 3)
        citation_style = state.get("citation_style", "APA")

        # Build prompt with research context
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", self._system_prompt),
                (
                    "system",
                    f"Research task: '{topic}' with {source_count} sources, "
                    f"using {citation_style} citations",
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        chain = prompt | self._chat_model
        response = chain.invoke({"messages": messages})

        return {"messages": [response]}

    def _route_after_model(self, state: ResearchState) -> str:
        """
        Determine next step after model call.

        Args:
            state: Current research state

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
        Build the Research agent graph.

        Returns:
            StateGraph for research mode
        """
        logger.info("Building Research agent graph")

        graph = StateGraph(ResearchState)

        # Add nodes
        graph.add_node("plan_research", self._plan_research)
        graph.add_node("model", self._call_model)

        if self._tools:
            tool_node = ToolNode(self._tools)
            graph.add_node("tools", tool_node)

        # Add edges
        graph.add_edge(START, "plan_research")
        graph.add_edge("plan_research", "model")

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

        logger.info("Research agent graph built successfully")
        return graph

    def compile(self) -> Any:
        """
        Build and compile the Research agent graph.

        Returns:
            Compiled graph ready for invocation
        """
        graph = self.build_graph()
        compiled = graph.compile()
        logger.info("Research agent compiled successfully")
        return compiled
