"""
Deep Research Agent - Comprehensive multi-stage research workflow.

This agent conducts Google Deep Research-style comprehensive analysis:
- Broad multi-query searches (10-15 results per query)
- Scrapes and analyzes multiple sources
- Synthesizes findings into structured markdown documents
- Saves research papers to disk for future reference
"""

from pathlib import Path
from typing import Any, Annotated, List, Dict
from typing_extensions import TypedDict

from langchain_core.messages import (
    BaseMessage,
    HumanMessage,
)
from langgraph.graph import add_messages

from airunner.components.llm.agents.deep_research.mixins import (
    ContentValidationMixin,
    ContentParsingMixin,
    SectionSynthesisMixin,
    PlanningPhaseMixin,
    SearchGatherMixin,
    CuriosityResearchMixin,
    AnalysisPhaseMixin,
    WritingPhaseMixin,
    ReviewPhaseMixin,
    FactCheckingMixin,
    DocumentFormattingMixin,
    ToolExecutionMixin,
    ToolNormalizationMixin,
    PhaseExecutionMixin,
    GraphBuildingMixin,
)

# Import tools to ensure they're registered
from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


class DeepResearchState(TypedDict):
    """
    State schema for Deep Research agent.

    Attributes:
        messages: Conversation messages
        research_topic: Professional title for document (display only)
        clean_topic: Clean search term extracted from user prompt
        current_phase: Current workflow phase (phase0, phase1a, phase1b, etc.)
        search_queries: List of search queries to execute
        collected_sources: URLs and content from scraped sources
        notes_path: Path to temporary research notes file
        outline: Document outline structure
        document_path: Path where final document will be saved
        rag_loaded: Whether RAG documents have been loaded
        sources_scraped: Number of sources scraped
        scraped_urls: List of URLs already scraped (prevents duplicates)
        sections_written: List of section names written
        thesis_statement: Central thesis/argument for the paper
        previous_sections: Dict mapping section names to their content
        error: Error message if research failed (e.g., no sources found)
    """

    messages: Annotated[list[BaseMessage], add_messages]
    research_topic: str
    clean_topic: str
    current_phase: str
    search_queries: List[str]
    collected_sources: List[Dict[str, str]]
    notes_path: str
    outline: str
    document_path: str
    rag_loaded: bool
    sources_scraped: int
    scraped_urls: List[str]
    sections_written: List[str]
    thesis_statement: str
    previous_sections: Dict[str, str]
    error: str


class DeepResearchAgent(
    ContentValidationMixin,
    ContentParsingMixin,
    SectionSynthesisMixin,
    PlanningPhaseMixin,
    SearchGatherMixin,
    CuriosityResearchMixin,
    AnalysisPhaseMixin,
    WritingPhaseMixin,
    ReviewPhaseMixin,
    FactCheckingMixin,
    DocumentFormattingMixin,
    ToolExecutionMixin,
    ToolNormalizationMixin,
    PhaseExecutionMixin,
    GraphBuildingMixin,
):
    """Deep Research Agent for comprehensive multi-stage research.

    Produces Google Deep Research-style comprehensive documents:
    - 10-20 pages of structured content
    - Multiple sections with headers
    - Extensive citations and sources
    - Markdown formatted for readability
    - Saved to research folder
    """

    def __init__(
        self,
        chat_model: Any,
        research_path: str,
        system_prompt: str = None,
        api: Any = None,
    ):
        """
        Initialize Deep Research Agent.

        Args:
            chat_model: LangChain chat model
            research_path: Base path for saving research documents
            system_prompt: Optional custom system prompt
            api: Optional API instance for tool access
        """
        self._research_path = Path(research_path)
        self._research_path.mkdir(parents=True, exist_ok=True)
        self._system_prompt = system_prompt or self._default_system_prompt()
        self._api = api
        self._tools = self._get_research_tools()

        # Keep reference to base model WITHOUT tools (for synthesis)
        self._base_model = chat_model

        # CRITICAL: Create a NEW instance of the chat model with tools bound
        # DO NOT modify the original chat_model instance (it has conversation history)
        if self._tools and hasattr(chat_model, "bind_tools"):
            self._chat_model = chat_model.bind_tools(self._tools)
            logger.info(
                f"Deep Research agent bound {len(self._tools)} tools to NEW model instance"
            )
        else:
            self._chat_model = chat_model

    def _initialize_phase_messages(self, topic: str) -> list:
        """Initialize fresh conversation messages for a phase.

        Args:
            topic: Research topic

        Returns:
            List of initial messages
        """
        if not topic:
            return []

        return [
            HumanMessage(
                content=f"""TASK: Research the following topic: {topic}

IMPORTANT INSTRUCTIONS:
- You MUST respond with ONLY JSON tool calls
- Do NOT write any explanatory text
- Do NOT write any conversational responses
- Call the tools listed in the next system message
- Use the EXACT topic: {topic}"""
            )
        ]

    def _default_system_prompt(self) -> str:
        """Get base system prompt for deep research mode."""
        return """You are a research AI assistant. You complete tasks by calling the available tools.

IMPORTANT: Respond ONLY with tool calls. Do not include any explanatory text."""
