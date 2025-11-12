"""
Deep Research Agent - Comprehensive multi-stage research workflow.

This agent conducts Google Deep Research-style comprehensive analysis:
- Broad multi-query searches (10-15 results per query)
- Scrapes and analyzes multiple sources
- Synthesizes findings into structured markdown documents
- Saves research papers to disk for future reference
"""

import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Annotated, List, Callable, Dict
from typing_extensions import TypedDict

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.graph import START, END, StateGraph, add_messages
from langgraph.prebuilt import ToolNode

from airunner.components.llm.core.tool_registry import (
    ToolRegistry,
    ToolCategory,
)

# Import tools to ensure they're registered
import airunner.components.llm.tools
from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


class DeepResearchState(TypedDict):
    """
    State schema for Deep Research agent.

    Attributes:
        messages: Conversation messages
        research_topic: Main research topic
        current_phase: Current workflow phase (phase0, phase1a, phase1b, etc.)
        search_queries: List of search queries to execute
        collected_sources: URLs and content from scraped sources
        notes_path: Path to temporary research notes file
        outline: Document outline structure
        document_path: Path where final document will be saved
        rag_loaded: Whether RAG documents have been loaded
        sources_scraped: Number of sources scraped
        sections_written: List of section names written
    """

    messages: Annotated[list[BaseMessage], add_messages]
    research_topic: str
    current_phase: str
    search_queries: List[str]
    collected_sources: List[Dict[str, str]]
    notes_path: str
    outline: str
    document_path: str
    rag_loaded: bool
    sources_scraped: int
    sections_written: List[str]


class DeepResearchAgent:
    """
    Deep Research Agent for comprehensive multi-stage research.

    Produces Google Deep Research-style comprehensive documents:
    - 10-20 pages of structured content
    - Multiple sections with headers
    - Extensive citations and sources
    - Markdown formatted for readability
    - Saved to research folder
    """

    # Domain blacklist for sites that consistently block scraping
    # This prevents wasting time on 403/paywall sites
    BLACKLISTED_DOMAINS = {
        "nytimes.com",
        "wsj.com",
        "ft.com",  # Financial Times
        "economist.com",
        "bloomberg.com",
        "bakerinstitute.org",  # Consistently returns 403
    }

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

    def _execute_phase_with_tools(
        self,
        phase_name: str,
        task_prompt: str,
        state: DeepResearchState,
        max_tool_calls: int = 5,
    ) -> dict:
        """
        Execute a phase by calling the model and handling tool calls internally.

        This allows each phase to loop with tools without needing graph edges.

        Args:
            phase_name: Name of the current phase for logging
            task_prompt: The specific task instructions for this phase
            state: Current state
            max_tool_calls: Maximum number of tool call iterations (default 5)

        Returns:
            Updated state with new messages
        """
        from langchain_core.messages import ToolMessage, HumanMessage

        self._emit_progress(phase_name, "Starting phase execution")

        state_updates: Dict[str, Any] = {}
        required_tools = self._extract_required_tools(task_prompt)

        # CRITICAL: Create a FRESH conversation with NO prior context
        # Add the research topic explicitly as a new user message
        topic = state.get("research_topic", "")
        messages = []

        # Add explicit user message demanding JSON tool calls
        if topic:
            messages.append(
                HumanMessage(
                    content=f"""TASK: Research the following topic: {topic}

IMPORTANT INSTRUCTIONS:
- You MUST respond with ONLY JSON tool calls
- Do NOT write any explanatory text
- Do NOT write any conversational responses
- Call the tools listed in the next system message
- Use the EXACT topic: {topic}"""
                )
            )

        iterations = 0

        while iterations < max_tool_calls:
            iterations += 1

            # Build prompt for this iteration
            prompt = ChatPromptTemplate.from_messages(
                [
                    ("system", self._system_prompt),
                    ("system", task_prompt),
                    MessagesPlaceholder(variable_name="messages"),
                ]
            )

            # DEBUG: Log what we're sending to the model
            logger.debug(
                f"[{phase_name}] Iteration {iterations} - Sending to model:"
            )
            logger.debug(f"  System prompt: {self._system_prompt[:100]}...")
            logger.debug(f"  Task prompt: {task_prompt[:100]}...")
            logger.debug(f"  Messages count: {len(messages)}")
            if messages:
                logger.debug(
                    f"  First message: {messages[0].content[:100] if hasattr(messages[0], 'content') else str(messages[0])[:100]}..."
                )

            # Call model
            chain = prompt | self._chat_model
            response = chain.invoke({"messages": messages})
            messages.append(response)

            # DEBUG: Log model response
            logger.debug(
                f"[{phase_name}] Model response type: {type(response)}"
            )
            if hasattr(response, "content"):
                logger.debug(
                    f"[{phase_name}] Model response content: {response.content[:200] if response.content else '(empty)'}..."
                )
            if hasattr(response, "tool_calls"):
                logger.debug(
                    f"[{phase_name}] Model tool_calls: {response.tool_calls}"
                )

            # Check if model wants to call tools
            if not hasattr(response, "tool_calls") or not response.tool_calls:
                if iterations >= max_tool_calls:
                    logger.warning(
                        f"[{phase_name}] No tool calls after {iterations} attempts"
                    )
                    break

                logger.warning(
                    f"[{phase_name}] Model response lacked tool calls (attempt {iterations}); reinforcing instructions"
                )
                retry_prompt = self._build_tool_retry_prompt(
                    topic=topic, required_tools=required_tools
                )
                messages.append(HumanMessage(content=retry_prompt))
                continue

            logger.info(
                f"[{phase_name}] Iteration {iterations}: Executing {len(response.tool_calls)} tool call(s)"
            )

            # Execute tools
            tool_results = []
            for tool_call in response.tool_calls:
                tool_name = tool_call.get("name")
                tool_args = tool_call.get("args", {})
                tool_args = self._normalize_tool_args(
                    tool_name, tool_args, state
                )
                tool_id = tool_call.get("id")

                # Find and execute tool
                tool_obj = None
                for tool in self._tools:
                    if hasattr(tool, "name") and tool.name == tool_name:
                        tool_obj = tool
                        break

                if tool_obj:
                    # Avoid duplicate document/note creation if already present
                    if tool_name == "create_research_document" and state.get(
                        "document_path"
                    ):
                        existing_path = state["document_path"]
                        tool_results.append(
                            ToolMessage(
                                content=str(existing_path),
                                tool_call_id=tool_id,
                            )
                        )
                        logger.info(
                            f"[{phase_name}] Reusing existing document path"
                        )
                        continue

                    if tool_name == "create_research_notes" and state.get(
                        "notes_path"
                    ):
                        existing_notes = state["notes_path"]
                        tool_results.append(
                            ToolMessage(
                                content=str(existing_notes),
                                tool_call_id=tool_id,
                            )
                        )
                        logger.info(
                            f"[{phase_name}] Reusing existing notes path"
                        )
                        continue

                    try:
                        # Inject API if needed
                        import inspect

                        func = (
                            tool_obj.func
                            if hasattr(tool_obj, "func")
                            else tool_obj.run
                        )
                        sig = inspect.signature(func)
                        if "api" in sig.parameters and self._api:
                            tool_args["api"] = self._api

                        # Execute
                        result = tool_obj.invoke(tool_args)
                        tool_results.append(
                            ToolMessage(
                                content=str(result), tool_call_id=tool_id
                            )
                        )
                        self._apply_tool_side_effects(
                            tool_name, result, state_updates, state
                        )
                        logger.debug(
                            f"[{phase_name}] Tool {tool_name} executed successfully"
                        )
                    except Exception as e:
                        logger.error(
                            f"[{phase_name}] Tool {tool_name} failed: {e}",
                            exc_info=True,
                        )
                        tool_results.append(
                            ToolMessage(
                                content=f"Error: {str(e)}",
                                tool_call_id=tool_id,
                            )
                        )
                else:
                    logger.warning(
                        f"[{phase_name}] Tool {tool_name} not found"
                    )
                    tool_results.append(
                        ToolMessage(
                            content=f"Error: Tool {tool_name} not found",
                            tool_call_id=tool_id,
                        )
                    )

            # Add tool results to messages
            messages.extend(tool_results)

        if iterations >= max_tool_calls:
            logger.warning(
                f"[{phase_name}] Reached max tool call limit ({max_tool_calls})"
            )

        self._emit_progress(
            phase_name, f"Completed after {iterations} iteration(s)"
        )

        return {"messages": messages, "state_updates": state_updates}

    def _normalize_tool_args(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
        state: DeepResearchState,
    ) -> Dict[str, Any]:
        """Ensure critical tool arguments align with current research topic."""
        normalized = dict(tool_args or {})
        topic = state.get("research_topic", "").strip()
        document_path = state.get("document_path", "")
        notes_path = state.get("notes_path", "")
        queries = state.get("search_queries", []) or ([topic] if topic else [])

        if tool_name in {"create_research_document", "create_research_notes"}:
            if topic:
                normalized["topic"] = topic

        if tool_name == "append_research_notes" and notes_path:
            normalized.setdefault("notes_path", notes_path)

        if tool_name in {
            "update_research_section",
            "add_source_citation",
            "finalize_research_document",
        }:
            if document_path:
                normalized["document_path"] = document_path

        if tool_name in {
            "search_web",
            "search_news",
            "search_knowledge_base_documents",
        }:
            desired_query = None
            if queries:
                if tool_name == "search_news" and len(queries) > 1:
                    desired_query = queries[1]
                else:
                    desired_query = queries[0]

            current_query = normalized.get("query")
            if not current_query and desired_query:
                normalized["query"] = desired_query
            elif (
                topic
                and current_query
                and topic.lower() not in current_query.lower()
            ):
                normalized["query"] = f"{topic} {current_query}".strip()

        if (
            tool_name
            in {
                "organize_research",
                "extract_key_points",
                "compare_sources",
                "synthesize_sources",
            }
            and topic
        ):
            for key in ("findings", "text", "topic"):
                if key in normalized:
                    if topic.lower() not in str(normalized[key]).lower():
                        normalized[key] = topic
                    break

        if tool_name in {"update_research_section", "append_research_notes"}:
            # Ensure content fields are strings
            if "content" in normalized and normalized["content"] is None:
                normalized["content"] = ""

        return normalized

    def _apply_tool_side_effects(
        self,
        tool_name: str,
        result: Any,
        state_updates: Dict[str, Any],
        state: DeepResearchState,
    ) -> None:
        """Capture tool outputs that should update agent state."""

        if tool_name == "create_research_document" and isinstance(result, str):
            state_updates["document_path"] = result
            state["document_path"] = result

        elif tool_name == "create_research_notes" and isinstance(result, str):
            state_updates["notes_path"] = result
            state["notes_path"] = result

        elif tool_name == "search_knowledge_base_documents":
            # RAG check - mark as loaded if we found docs
            if result and "No documents found" not in str(result):
                state_updates["rag_loaded"] = True

        elif tool_name == "append_research_notes":
            # keep existing notes path if we already have one
            if state.get("notes_path"):
                state_updates.setdefault("notes_path", state["notes_path"])

        elif tool_name == "update_research_section" and isinstance(
            result, str
        ):
            if "Successfully updated" in result:
                sections = list(state.get("sections_written", []))
                section_name = result.replace(
                    "Successfully updated", ""
                ).strip()
                if section_name:
                    sections.append(section_name)
                    state_updates["sections_written"] = sections

        elif tool_name == "search_web" and isinstance(result, dict):
            hits = result.get("results") or []
            if hits:
                collected = list(state.get("collected_sources", []))
                collected.extend(hits)
                state_updates["collected_sources"] = collected

        elif tool_name == "search_news" and isinstance(result, dict):
            hits = result.get("results") or []
            if hits:
                collected = list(state.get("collected_sources", []))
                collected.extend(hits)
                state_updates["collected_sources"] = collected

    def _default_system_prompt(self) -> str:
        """Get base system prompt for deep research mode."""
        return """You are a research AI assistant. You complete tasks by calling the available tools.

IMPORTANT: Respond ONLY with tool calls. Do not include any explanatory text."""

    def _extract_required_tools(self, task_prompt: str) -> List[str]:
        """Infer which tools the task prompt explicitly asked the model to call."""

        if not task_prompt:
            return []

        task_lower = task_prompt.lower()
        available_names = []
        for tool in self._tools:
            if hasattr(tool, "name") and tool.name:
                available_names.append(tool.name)

        required: List[str] = []
        for name in available_names:
            name_lower = name.lower()
            if (
                f"call {name_lower}" in task_lower
                or f"{name_lower}(" in task_lower
                or f"{name_lower}:" in task_lower
            ):
                required.append(name)

        # Preserve order but remove duplicates
        seen = set()
        ordered_required = []
        for tool_name in required:
            if tool_name not in seen:
                ordered_required.append(tool_name)
                seen.add(tool_name)

        return ordered_required

    def _build_tool_retry_prompt(
        self, topic: str, required_tools: List[str]
    ) -> str:
        """Construct a direct instruction reminding the model to emit a tool call."""

        tool_hint = (
            "Call one of these tools immediately: " + ", ".join(required_tools)
            if required_tools
            else "Call one of the allowed tools provided in the system instructions."
        )

        topic_hint = (
            f"Use the exact research topic: {topic}."
            if topic
            else "Use the exact topic from the task prompt."
        )

        return (
            "You failed to call a tool. Respond NOW with a single JSON object.\n"
            '{"tool": "tool_name", "arguments": { ... }}\n'
            f"{tool_hint}\n"
            f"{topic_hint}\n"
            "Do not write prose or mention any other subject."
        )

    def _get_research_tools(self) -> List[Any]:
        """Get RESEARCH and SEARCH category tools from registry."""
        from langchain_core.tools import StructuredTool
        from inspect import signature

        research_tools = ToolRegistry.get_by_category(ToolCategory.RESEARCH)
        search_tools = ToolRegistry.get_by_category(ToolCategory.SEARCH)

        all_tools = research_tools + search_tools
        logger.info(
            f"Deep Research: {len(research_tools)} RESEARCH + "
            f"{len(search_tools)} SEARCH = {len(all_tools)} tools"
        )

        # Log individual tool names for debugging
        logger.debug(f"RESEARCH tools: {[t.name for t in research_tools]}")
        logger.debug(f"SEARCH tools: {[t.name for t in search_tools]}")

        # Convert ToolInfo to LangChain StructuredTool objects
        langchain_tools = []
        for tool_info in all_tools:
            # Create a StructuredTool with proper schema
            structured_tool = StructuredTool.from_function(
                func=tool_info.func,
                name=tool_info.name,
                description=tool_info.description,
                return_direct=tool_info.return_direct,
            )
            langchain_tools.append(structured_tool)

        logger.info(
            f"Converted {len(langchain_tools)} tools to LangChain format"
        )
        logger.debug(
            f"Available tool names: {[t.name for t in langchain_tools]}"
        )
        return langchain_tools

    @staticmethod
    def _is_domain_blacklisted(url: str) -> bool:
        """Check if a URL's domain is blacklisted.

        Args:
            url: Full URL to check

        Returns:
            True if domain is blacklisted, False otherwise
        """
        from urllib.parse import urlparse

        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()

            # Remove www. prefix for comparison
            if domain.startswith("www."):
                domain = domain[4:]

            # Check if any blacklisted domain matches
            for blacklisted in DeepResearchAgent.BLACKLISTED_DOMAINS:
                if domain == blacklisted or domain.endswith("." + blacklisted):
                    return True

            return False
        except Exception as e:
            logger.warning(f"Error parsing URL {url}: {e}")
            return False

    @staticmethod
    def _is_url_irrelevant_path(url: str) -> bool:
        """
        Check if URL path contains irrelevant sections.

        Filters out:
        - Games, puzzles, crosswords
        - Account/login pages
        - Shopping/products
        - Jobs/careers
        - General navigation (about, contact, etc.)

        Args:
            url: URL to check

        Returns:
            True if URL should be skipped
        """
        from urllib.parse import urlparse

        try:
            parsed = urlparse(url)
            path = parsed.path.lower()

            # Irrelevant path segments
            irrelevant_segments = [
                "/games/",
                "/game/",
                "/puzzle/",
                "/crossword/",
                "/sudoku/",
                "/login/",
                "/signin/",
                "/signup/",
                "/register/",
                "/account/",
                "/shop/",
                "/store/",
                "/product/",
                "/cart/",
                "/checkout/",
                "/jobs/",
                "/careers/",
                "/apply/",
                "/about/",
                "/contact/",
                "/privacy/",
                "/terms/",
                "/help/",
                "/subscribe/",
                "/newsletter/",
                "/podcast/",
                "/video/",
                "/videos/",
                "/gallery/",
                "/photos/",
                "/events/",
                "/calendar/",
            ]

            # Check if any irrelevant segment is in the path
            for segment in irrelevant_segments:
                if segment in path:
                    return True

            return False
        except Exception:
            return False

    @staticmethod
    def _is_content_quality_acceptable(content: str) -> bool:
        """Check if scraped content has acceptable quality for research.

        Rejects content that is:
        - Too short (< 200 chars)
        - Access-blocked pages (CAPTCHA, paywall, login required)
        - Too repetitive (many duplicate lines)
        - Mostly navigation/boilerplate (high ratio of common web words)
        - Contains too many symbols/numbers (like Wikipedia citations: [1][2][3])

        Args:
            content: Scraped content to validate

        Returns:
            True if content quality is acceptable, False otherwise
        """
        if not content or len(content) < 200:
            return False

        import re

        # Check for common scraper-blocking / access-denied content
        # These are telltale signs of paywalls, CAPTCHAs, or blocked access
        block_phrases = [
            "request access",
            "access denied",
            "captcha",
            "bot test",
            "cloudflare",
            "please verify you are human",
            "verify you are not a robot",
            "automated scraping",
            "programmatic access",
            "complete the captcha",
            "subscription required",
            "subscribe to continue",
            "sign in to continue",
            "login to view",
            "paywall",
            "this content is premium",
            "members only",
            "404 not found",
            "page not found",
            "403 forbidden",
            "enable javascript",
            "javascript is required",
            "cookie consent",
        ]

        content_lower = content.lower()
        blocked_count = sum(
            1 for phrase in block_phrases if phrase in content_lower
        )

        if blocked_count >= 2:  # Two or more blocking phrases = likely blocked
            logger.debug(
                f"Content contains {blocked_count} access-blocking phrases - likely CAPTCHA/paywall/blocked"
            )
            return False

        # Check for excessive citation markers (Wikipedia lists often have tons of [1][2][3])
        citation_count = len(re.findall(r"\[\d+\]", content))
        if (
            citation_count > 20
        ):  # More than 20 citation markers suggests a reference list
            logger.debug(
                f"Content has {citation_count} citation markers - likely a list/index page"
            )
            return False

        # Check for Wikipedia-style reference markers in sequence (e.g., "[56][57][58]")
        sequential_refs = len(re.findall(r"\[\d+\]\[\d+\]\[\d+\]", content))
        if sequential_refs > 5:
            logger.debug(
                f"Content has {sequential_refs} sequential reference markers - likely Wikipedia citations"
            )
            return False

        # Check for list-style content (lines starting with "- " or numbers)
        lines = content.split("\n")
        list_lines = [
            line
            for line in lines
            if re.match(r"^\s*[-•*]\s+", line.strip())
            or re.match(r"^\s*\d+\.\s+", line.strip())
        ]
        if len(lines) > 10 and len(list_lines) / len(lines) > 0.6:
            logger.debug(
                f"Content is {len(list_lines)/len(lines)*100:.0f}% list items - likely an index/list page"
            )
            return False

        # Check for repetitive content (many duplicate lines)
        lines = content.split("\n")
        unique_lines = set(
            line.strip() for line in lines if len(line.strip()) > 10
        )
        if len(lines) > 10 and len(unique_lines) / len(lines) < 0.5:
            logger.debug("Content is too repetitive (< 50% unique lines)")
            return False

        # Check for navigation boilerplate
        nav_words = [
            "home",
            "about",
            "contact",
            "privacy",
            "terms",
            "login",
            "sign in",
            "subscribe",
        ]
        nav_count = sum(1 for word in nav_words if word in content.lower())
        if nav_count > 5:  # Too many navigation keywords
            logger.debug(
                f"Content has {nav_count} navigation keywords - likely boilerplate"
            )
            return False

        # Check sentence structure (real articles have proper sentences)
        sentences = re.split(r"[.!?]+", content)
        long_sentences = [s for s in sentences if len(s.strip().split()) > 5]
        if len(long_sentences) < 3:
            logger.debug("Content lacks proper sentence structure")
            return False

        return True

    def _parse_research_notes(self, notes_content: str) -> dict:
        """
        Parse research notes to extract structured information.

        Extracts:
        - Individual sources with their content
        - Key entities, dates, locations mentioned
        - Main themes and topics
        - Curiosity deep-dive sections

        Args:
            notes_content: Raw notes content from file

        Returns:
            Structured dict with parsed information
        """
        parsed = {
            "sources": [],
            "entities": set(),
            "dates": set(),
            "themes": {},
            "curiosity_topics": [],
        }

        # Split by source markers (### URL format in actual notes)
        source_sections = re.split(r"\n(?=###\s+https?://)", notes_content)

        for section in source_sections:
            if not section.strip():
                continue

            # Check if this is a curiosity deep-dive
            curiosity_match = re.search(
                r"\*\*CURIOSITY DEEP-DIVE: (.+?)\*\*", section
            )
            is_curiosity = curiosity_match is not None
            curiosity_topic = (
                curiosity_match.group(1) if is_curiosity else None
            )

            # Extract URL from ### header or URL: line
            url_match = re.search(r"###\s+(https?://\S+)", section)
            if not url_match:
                url_match = re.search(r"URL:\s+(https?://\S+)", section)
            url = url_match.group(1) if url_match else "Unknown"

            # Extract title from Title: line
            title_match = re.search(r"Title:\s+(.+?)(?:\n|$)", section)
            title = title_match.group(1).strip() if title_match else None

            # Extract content from "Extract:" section (this is where the actual content is)
            extract_match = re.search(
                r"Extract:\s+(.+?)(?:\n---|\n###|$)", section, re.DOTALL
            )
            if extract_match:
                content = extract_match.group(1).strip()
            else:
                # Fallback: everything after URL line
                lines = section.split("\n")
                content_start = (
                    next(
                        (
                            i
                            for i, line in enumerate(lines)
                            if line.startswith("URL:")
                        ),
                        -1,
                    )
                    + 1
                )
                content = (
                    "\n".join(lines[content_start:]).strip()
                    if content_start > 0
                    else section.strip()
                )

            source_info = {
                "url": url,
                "title": title,  # Store the page title
                "content": content,
                "is_curiosity": is_curiosity,
                "curiosity_topic": curiosity_topic,
            }
            parsed["sources"].append(source_info)

            # Extract entities (capitalized multi-word phrases)
            entities = re.findall(
                r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b", content
            )
            parsed["entities"].update(entities)

            # Extract dates
            dates = re.findall(
                r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b",
                content,
            )
            dates += re.findall(r"\b\d{4}\b", content)  # Just years
            parsed["dates"].update(dates)

            # Track themes by word frequency in this source
            words = re.findall(r"\b[a-z]{4,}\b", content.lower())
            for word in words:
                if word not in [
                    "that",
                    "this",
                    "with",
                    "from",
                    "have",
                    "been",
                    "were",
                    "will",
                ]:
                    parsed["themes"][word] = parsed["themes"].get(word, 0) + 1

        # Identify curiosity topics
        for source in parsed["sources"]:
            if source["is_curiosity"] and source["curiosity_topic"]:
                parsed["curiosity_topics"].append(source["curiosity_topic"])

        # Get top themes
        top_themes = sorted(
            parsed["themes"].items(), key=lambda x: x[1], reverse=True
        )[:10]
        parsed["top_themes"] = [theme for theme, _ in top_themes]

        return parsed

    def _synthesize_introduction(self, topic: str, parsed_notes: dict) -> str:
        """
        Generate introduction section using LLM with research context.

        Uses low temperature (0.2) and repetition penalty (1.2) to produce
        factual, well-written academic prose without copying source text.

        Args:
            topic: Research topic
            parsed_notes: Parsed notes with sources, findings, entities

        Returns:
            Introduction section markdown
        """
        num_sources = len(parsed_notes["sources"])
        num_curiosity = len(parsed_notes["curiosity_topics"])
        key_entities = list(parsed_notes["entities"])[:5]

        # Collect brief context from sources (for LLM understanding, not for copying)
        context_snippets = []
        main_sources = [
            s for s in parsed_notes["sources"] if not s["is_curiosity"]
        ][:3]
        for source in main_sources:
            content = source.get("content", "")
            # Extract first few sentences for context
            lines = [l for l in content.split("\n") if len(l.strip()) > 30]
            if lines:
                context_snippets.append(lines[0][:300])

        context_text = (
            "\n\n".join(context_snippets)
            if context_snippets
            else "General research on the topic."
        )

        # Build prompt for LLM
        prompt = f"""You are an expert academic research writer. You are writing the INTRODUCTION section (opening section) of a research paper.

RESEARCH PAPER TOPIC: {topic}

NUMBER OF SOURCES ANALYZED: {num_sources} (including {num_curiosity} specialized investigations)

KEY ENTITIES/ACTORS: {', '.join(key_entities) if key_entities else 'various stakeholders'}

CONTEXT FROM SOURCES (for understanding only - DO NOT copy this text):
{context_text}

YOUR TASK: Write the Introduction section that opens this research paper. This should:
1. Establish the significance and relevance of studying {topic}
2. Provide context for why this topic matters in current affairs
3. State the research scope: systematic review of {num_sources} authoritative sources
4. Identify key actors/entities: {', '.join(key_entities[:3]) if key_entities else 'relevant stakeholders'}
5. Outline what the paper will examine and analyze
6. Use formal academic style with clear, engaging prose
7. DO NOT copy text from context - write original analysis
8. DO NOT use repetitive phrases or clichés
9. DO NOT say "the introduction of" or similar meta-references
10. Length: 400-600 words (comprehensive but focused)

Write the Introduction section content now (start directly with substantive content):"""

        try:
            # CRITICAL: Use BASE model WITHOUT tools for synthesis (not tool-bound version)
            # The tool-bound model is in JSON mode and will generate garbage
            response = self._base_model.invoke(
                [HumanMessage(content=prompt)],
                temperature=0.2,  # Low temperature for factual consistency
                max_new_tokens=2048,  # Allow comprehensive content generation
                repetition_penalty=1.2,  # Prevent repetitive phrases
            )

            if hasattr(response, "content") and response.content:
                intro_content = response.content.strip()
                logger.info(
                    f"[Synthesis] Generated introduction via LLM: {len(intro_content)} chars"
                )
                # Ensure it doesn't start with a heading (we add that elsewhere)
                intro_content = re.sub(
                    r"^#+\s*Introduction\s*\n+",
                    "",
                    intro_content,
                    flags=re.IGNORECASE,
                )
                return intro_content
            else:
                logger.warning(
                    "[Synthesis] LLM response empty, using fallback"
                )
                return self._fallback_introduction(
                    topic, num_sources, key_entities
                )

        except Exception as e:
            logger.error(f"[Synthesis] LLM synthesis failed: {e}")
            return self._fallback_introduction(
                topic, num_sources, key_entities
            )

    def _fallback_introduction(
        self, topic: str, num_sources: int, key_entities: List[str]
    ) -> str:
        """Fallback introduction if LLM fails (simple but clean)."""
        entities_str = (
            f" involving {', '.join(key_entities[:3])}" if key_entities else ""
        )
        return f"""This research examines {topic}{entities_str}, drawing on {num_sources} authoritative sources to provide comprehensive analysis.

The investigation systematically reviews policy developments, expert commentary, and analytical perspectives to synthesize current understanding and identify key implications.

This document presents findings organized thematically, with attention to both immediate developments and broader strategic significance."""

    @staticmethod
    def _normalize_temporal_references(text: str) -> str:
        """Remove or normalize temporal references that don't make sense in a research paper."""
        # Remove references to "yesterday", "today", "earlier today", etc.
        text = re.sub(r"\byesterday\b", "recently", text, flags=re.IGNORECASE)
        text = re.sub(
            r"\bearlier today\b", "recently", text, flags=re.IGNORECASE
        )
        text = re.sub(r"\btoday\b", "currently", text, flags=re.IGNORECASE)
        text = re.sub(
            r"\bthis morning\b", "recently", text, flags=re.IGNORECASE
        )
        text = re.sub(
            r"\bthis afternoon\b", "recently", text, flags=re.IGNORECASE
        )
        text = re.sub(
            r"\bthis evening\b", "recently", text, flags=re.IGNORECASE
        )
        text = re.sub(r"\blast night\b", "recently", text, flags=re.IGNORECASE)
        return text

    def _synthesize_background(self, topic: str, parsed_notes: dict) -> str:
        """
        Generate background section using LLM.

        Args:
            topic: Research topic
            parsed_notes: Parsed notes

        Returns:
            Background section markdown
        """
        main_sources = [
            s for s in parsed_notes["sources"] if not s["is_curiosity"]
        ]

        if not main_sources:
            return "Background information is being compiled from research sources.\n\n"

        # Collect context from first 4 sources
        context_snippets = []
        for source in main_sources[:4]:
            content = source.get("content", "")
            lines = [
                l.strip()
                for l in content.split("\n")
                if len(l.strip()) > 40 and not l.strip().startswith("#")
            ]
            if lines:
                context_snippets.append(" ".join(lines[:3])[:500])

        context_text = (
            "\n\n".join(context_snippets)
            if context_snippets
            else "Background context from sources."
        )

        prompt = f"""You are an expert academic research writer. Write the BACKGROUND section for a research paper.

RESEARCH PAPER TOPIC: {topic}

CONTEXT FROM SOURCES (for understanding only - DO NOT copy):
{context_text}

YOUR TASK: Write a comprehensive Background section that:
1. Provides historical context and evolution of events related to {topic}
2. Explains relevant background information needed to understand current developments
3. Describes key policies, decisions, or events that led to the current situation
4. Identifies major turning points or shifts in approach
5. Establishes the foundation for later analysis
6. Uses formal academic style with clear chronological or thematic organization
7. DO NOT copy text from sources - synthesize original historical narrative
8. DO NOT repeat phrases or use filler language
9. Length: 600-900 words (detailed and comprehensive)

Write the Background section content now (start directly with substantive content):"""

        try:
            # CRITICAL: Use BASE model WITHOUT tools for synthesis (not tool-bound version)
            response = self._base_model.invoke(
                [HumanMessage(content=prompt)],
                temperature=0.2,
                max_new_tokens=2048,  # Allow comprehensive, detailed background
                repetition_penalty=1.2,
            )

            if hasattr(response, "content") and response.content:
                content = response.content.strip()
                logger.info(
                    f"[Synthesis] Generated background via LLM: {len(content)} chars"
                )
                content = re.sub(
                    r"^#+\s*Background\s*\n+", "", content, flags=re.IGNORECASE
                )
                return content
            else:
                logger.warning(
                    "[Synthesis] LLM background response empty, using fallback"
                )
                return f"Background information on {topic} was compiled from {len(main_sources)} sources.\n\n"

        except Exception as e:
            logger.error(f"[Synthesis] LLM background synthesis failed: {e}")
            return f"Background information on {topic} was compiled from {len(main_sources)} sources.\n\n"

    def _synthesize_analysis(self, topic: str, parsed_notes: dict) -> str:
        """
        Generate analysis section using LLM.

        Args:
            topic: Research topic
            parsed_notes: Parsed notes

        Returns:
            Analysis section markdown
        """
        main_sources = [
            s for s in parsed_notes["sources"] if not s["is_curiosity"]
        ]
        curiosity_sources = [
            s for s in parsed_notes["sources"] if s["is_curiosity"]
        ]

        # Collect key findings from sources
        findings_snippets = []
        for source in main_sources[:5]:
            content = source.get("content", "")
            lines = [
                l.strip()
                for l in content.split("\n")
                if len(l.strip()) > 40 and not l.strip().startswith("#")
            ]
            if lines:
                findings_snippets.append(" ".join(lines[:2])[:400])

        findings_text = (
            "\n\n".join(findings_snippets)
            if findings_snippets
            else "Key findings from sources."
        )

        # Include curiosity topics if any
        curiosity_text = ""
        if curiosity_sources:
            topics = list(
                set(
                    [
                        s.get("curiosity_topic", "Unknown")
                        for s in curiosity_sources
                    ]
                )
            )
            curiosity_text = f"\n\nDeep-dive investigations were conducted on: {', '.join(topics)}"

        prompt = f"""You are an expert academic research writer. Write the ANALYSIS section for a research paper.

RESEARCH PAPER TOPIC: {topic}

KEY FINDINGS FROM SOURCES (for understanding only - DO NOT copy):
{findings_text}{curiosity_text}

YOUR TASK: Write a comprehensive Analysis section that:
1. Analyzes key findings, patterns, and trends discovered in the research
2. Synthesizes information across multiple sources to reveal insights
3. Examines cause-and-effect relationships and interconnections
4. Identifies significant developments, shifts, or turning points
5. Evaluates the implications of findings in broader context
6. Compares different perspectives or approaches when relevant
7. Applies critical thinking to assess the significance of evidence
8. Uses formal academic style with clear analytical reasoning
9. DO NOT copy text from sources - develop original analytical interpretation
10. DO NOT use repetitive transitions like "the analysis shows" repeatedly
11. Length: 800-1200 words (thorough, multi-layered analysis)

Write the Analysis section content now (start directly with substantive analysis):"""

        try:
            # CRITICAL: Use BASE model WITHOUT tools for synthesis (not tool-bound version)
            response = self._base_model.invoke(
                [HumanMessage(content=prompt)],
                temperature=0.2,
                max_new_tokens=3072,  # Significantly increased for deep, multi-layered analysis
                repetition_penalty=1.2,
            )

            if hasattr(response, "content") and response.content:
                content = response.content.strip()
                logger.info(
                    f"[Synthesis] Generated analysis via LLM: {len(content)} chars"
                )
                content = re.sub(
                    r"^#+\s*Analysis\s*\n+", "", content, flags=re.IGNORECASE
                )
                return content
            else:
                logger.warning(
                    "[Synthesis] LLM analysis response empty, using fallback"
                )
                return f"Analysis of {topic} based on {len(main_sources)} sources.\n\n"

        except Exception as e:
            logger.error(f"[Synthesis] LLM analysis synthesis failed: {e}")
            return f"Analysis of {topic} based on {len(main_sources)} sources.\n\n"

    def _synthesize_implications(self, topic: str, parsed_notes: dict) -> str:
        """
        Generate implications section using LLM.

        Args:
            topic: Research topic
            parsed_notes: Parsed notes

        Returns:
            Implications section markdown
        """
        # Extract sentences mentioning implications/impacts
        relevant_snippets = []
        keywords = [
            "implication",
            "impact",
            "consequence",
            "result",
            "effect",
            "significant",
            "important",
        ]

        for source in parsed_notes["sources"][:5]:
            content = source.get("content", "")
            sentences = [
                s.strip()
                for s in content.split(".")
                if len(s.strip().split()) > 8
            ]
            for sentence in sentences:
                if any(kw in sentence.lower() for kw in keywords):
                    relevant_snippets.append(sentence[:300])
                    if len(relevant_snippets) >= 5:
                        break

        context_text = (
            ". ".join(relevant_snippets[:5])
            if relevant_snippets
            else "Implications discussed in sources."
        )

        prompt = f"""You are an expert academic research writer. Write the IMPLICATIONS section for a research paper.

RESEARCH PAPER TOPIC: {topic}

RELEVANT CONTEXT (for understanding only - DO NOT copy):
{context_text}

YOUR TASK: Write a comprehensive Implications section that:
1. Discusses policy implications - what should policymakers consider or do?
2. Analyzes strategic implications - how does this affect broader strategies?
3. Examines practical implications - real-world effects on stakeholders
4. Considers short-term consequences and long-term ramifications
5. Identifies implications for different groups: governments, organizations, citizens
6. Explores potential risks, challenges, and opportunities
7. Discusses how findings might influence future decision-making
8. Uses formal academic style with clear, logical progression
9. DO NOT copy text from sources - develop original implication analysis
10. DO NOT repeat phrases or use generic statements
11. Length: 600-800 words (thorough examination of implications)

Write the Implications section content now (start directly with substantive discussion):"""

        try:
            # CRITICAL: Use BASE model WITHOUT tools for synthesis (not tool-bound version)
            response = self._base_model.invoke(
                [HumanMessage(content=prompt)],
                temperature=0.2,
                max_new_tokens=2048,  # Allow thorough implications discussion
                repetition_penalty=1.2,
            )

            if hasattr(response, "content") and response.content:
                content = response.content.strip()
                logger.info(
                    f"[Synthesis] Generated implications via LLM: {len(content)} chars"
                )
                content = re.sub(
                    r"^#+\s*Implications\s*\n+",
                    "",
                    content,
                    flags=re.IGNORECASE,
                )
                return content
            else:
                logger.warning(
                    "[Synthesis] LLM implications response empty, using fallback"
                )
                return f"The developments examined regarding {topic} have significant implications for policy and practice.\n\n"

        except Exception as e:
            logger.error(f"[Synthesis] LLM implications synthesis failed: {e}")
            return f"The developments examined regarding {topic} have significant implications for policy and practice.\n\n"

    def _synthesize_conclusion(self, topic: str, parsed_notes: dict) -> str:
        """
        Generate conclusion section using LLM.

        Args:
            topic: Research topic
            parsed_notes: Parsed notes

        Returns:
            Conclusion section markdown
        """
        num_sources = len(parsed_notes["sources"])
        num_curiosity = len(parsed_notes["curiosity_topics"])
        key_entities = list(parsed_notes["entities"])[:3]

        entities_str = (
            ", ".join(key_entities) if key_entities else "various stakeholders"
        )

        prompt = f"""You are an expert academic research writer. Write the CONCLUSION section for a research paper.

RESEARCH PAPER TOPIC: {topic}

RESEARCH SCOPE:
- Sources analyzed: {num_sources} (including {num_curiosity} deep-dive investigations)
- Key entities examined: {entities_str}

YOUR TASK: Write a comprehensive Conclusion section that:
1. Synthesizes the main findings from the research without simply repeating them
2. Reflects on the broader significance and importance of this research
3. Discusses what we now understand better about {topic}
4. Considers the contribution this research makes to existing knowledge
5. Identifies limitations of the current study if applicable
6. Suggests specific areas for future research and investigation
7. Ends with a strong closing statement about the topic's importance
8. Uses formal academic style with reflective, synthesizing language
9. DO NOT introduce new factual information not covered earlier
10. DO NOT repeat exact phrases from Introduction, Background, or Analysis
11. Length: 500-700 words (thoughtful, comprehensive conclusion)

Write the Conclusion section content now (start directly with synthesizing content):"""

        try:
            # CRITICAL: Use BASE model WITHOUT tools for synthesis (not tool-bound version)
            response = self._base_model.invoke(
                [HumanMessage(content=prompt)],
                temperature=0.2,
                max_new_tokens=2048,  # Allow comprehensive, thoughtful conclusion
                repetition_penalty=1.2,
            )

            if hasattr(response, "content") and response.content:
                content = response.content.strip()
                logger.info(
                    f"[Synthesis] Generated conclusion via LLM: {len(content)} chars"
                )
                content = re.sub(
                    r"^#+\s*Conclusion\s*\n+", "", content, flags=re.IGNORECASE
                )
                return content
            else:
                logger.warning(
                    "[Synthesis] LLM conclusion response empty, using fallback"
                )
                return f"This research examined {topic} through analysis of {num_sources} sources, providing comprehensive insights and identifying key implications for future consideration.\n\n"

        except Exception as e:
            logger.error(f"[Synthesis] LLM conclusion synthesis failed: {e}")
            return f"This research examined {topic} through analysis of {num_sources} sources, providing comprehensive insights and identifying key implications for future consideration.\n\n"

    def _synthesize_sources(self, parsed_notes: dict) -> str:
        """Generate sources/bibliography section."""
        sources_section = ""

        # Get all sources
        all_sources = parsed_notes["sources"]

        if not all_sources:
            sources_section += "No sources available.\n\n"
            return sources_section

        sources_section += "### Bibliography\n\n"
        sources_section += (
            "The following sources were consulted for this research:\n\n"
        )

        # Number sources sequentially
        for i, source in enumerate(all_sources, 1):
            url = source["url"]
            title = source.get("title")

            # Use the scraped page title if available, otherwise fall back to domain name
            if title and title.strip():
                display_name = title.strip()
            else:
                domain = self._get_domain_name(url)
                display_name = domain

            # Format: 1. Title/Domain - URL
            sources_section += f"{i}. **{display_name}** - {url}\n"

            # Add curiosity marker if applicable
            if source["is_curiosity"]:
                curiosity_topic = source.get("curiosity_topic", "Unknown")
                sources_section += (
                    f"   *(Deep-dive investigation: {curiosity_topic})*\n"
                )

            sources_section += "\n"

        # Add access date
        from datetime import datetime

        access_date = datetime.now().strftime("%B %d, %Y")
        sources_section += f"\n*All sources accessed on {access_date}*\n\n"

        return sources_section

    def _get_source_name(self, source: dict) -> str:
        """Get display name for a source - prefer title, fallback to domain."""
        title = source.get("title")
        if title and title.strip():
            return title.strip()
        return self._get_domain_name(source["url"])

    @staticmethod
    def _get_domain_name(url: str) -> str:
        """Extract readable domain name from URL as fallback."""
        from urllib.parse import urlparse

        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path

        # Remove www. prefix
        domain = re.sub(r"^www\.", "", domain)

        # Remove TLD for cleaner name
        domain = domain.split(".")[0] if "." in domain else domain
        return domain.title()

    @staticmethod
    def _generate_professional_title(user_prompt: str) -> str:
        """
        Generate a professional research title from user prompt.

        Args:
            user_prompt: Raw user prompt (e.g., "research trump and his recent decisions on syria")

        Returns:
            Professional title (e.g., "Trump Administration Policy on Syria: Recent Developments and Decisions")
        """
        # Remove common research-related words
        prompt_lower = user_prompt.lower()
        for prefix in [
            "research ",
            "analyze ",
            "investigate ",
            "study ",
            "examine ",
        ]:
            if prompt_lower.startswith(prefix):
                prompt_lower = prompt_lower[len(prefix) :]
                break

        # Identify key entities and topics
        words = prompt_lower.split()

        # Capitalize important words (skip articles, conjunctions, prepositions unless first word)
        skip_words = {
            "a",
            "an",
            "the",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "from",
        }
        title_words = []

        for i, word in enumerate(words):
            # Always capitalize first word, proper nouns, and important words
            if i == 0 or word not in skip_words or len(word) > 4:
                title_words.append(word.capitalize())
            else:
                title_words.append(word)

        # Join and add professional framing
        base_title = " ".join(title_words)

        # Add context if it seems to be about policy/decisions
        if any(
            keyword in prompt_lower
            for keyword in [
                "decision",
                "policy",
                "action",
                "order",
                "sanctions",
            ]
        ):
            # It's about policy/decisions
            return f"{base_title}: Recent Developments and Policy Analysis"
        elif any(
            keyword in prompt_lower
            for keyword in ["impact", "effect", "consequence", "implication"]
        ):
            # It's about impacts
            return f"{base_title}: Analysis and Implications"
        else:
            # General research
            return f"{base_title}: A Research Analysis"

    def _plan_research(self, state: DeepResearchState) -> dict:
        """
        Generate comprehensive research plan with multiple search queries.

        Args:
            state: Current research state

        Returns:
            Updated state with topic, queries, document path
        """
        messages = state.get("messages", [])
        if not messages:
            return {}

        # Get last user message
        last_msg = None
        for msg in reversed(messages):
            if hasattr(msg, "type") and msg.type == "human":
                last_msg = msg
                break

        if not last_msg:
            return {}

        # Get user's raw prompt
        user_prompt = str(last_msg.content)

        # Generate professional title for the document
        professional_title = self._generate_professional_title(user_prompt)
        logger.info(f"[Plan] Generated title: {professional_title}")

        # Create the actual research document file
        from airunner.components.llm.tools.research_document_tools import (
            create_research_document,
        )

        document_path = None
        try:
            document_path = create_research_document(
                topic=professional_title, api=self._api
            )
            logger.info(f"[Plan] Created research document: {document_path}")
        except Exception as e:
            logger.error(
                f"[Plan] Failed to create research document: {e}",
                exc_info=True,
            )
            # Fallback: generate path but DON'T create file yet (will be created in Phase 1D)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_topic = "".join(
                c if c.isalnum() or c in (" ", "_") else "_"
                for c in professional_title[:50]
            )
            safe_topic = "_".join(safe_topic.split())
            filename = f"{timestamp}_{safe_topic}.md"
            document_path = str(self._research_path / filename)
            logger.warning(f"[Plan] Using fallback path: {document_path}")

        if not document_path:
            raise RuntimeError("Failed to create or generate document path")

        # Generate diverse search queries using the original user prompt
        # (searches should use user's natural language, not formal title)
        search_queries = [
            user_prompt,  # Original query
            f"{user_prompt} overview background",  # Context query
            f"{user_prompt} recent news developments",  # News query
            f"{user_prompt} analysis expert opinion",  # Analysis query
        ]

        logger.info(
            f"Deep research plan: title='{professional_title}', "
            f"prompt='{user_prompt[:40]}...', queries={len(search_queries)}, path={document_path}"
        )

        # Emit progress
        if self._api:
            self._emit_progress(
                "Planning Complete",
                f"Prepared {len(search_queries)} search queries",
            )

        return {
            "research_topic": professional_title,  # Use professional title in state
            "user_prompt": user_prompt,  # Keep original for reference
            "search_queries": search_queries,
            "collected_sources": [],
            "current_phase": "phase0",
            "rag_loaded": False,
            "sources_scraped": 0,
            "sections_written": [],
            "notes_path": "",
            "outline": "",
            "document_path": document_path,
        }

    def _emit_progress(self, phase: str, message: str):
        """Emit progress update signal to UI."""
        if self._api and hasattr(self._api, "emit_signal"):
            try:
                from airunner.enums import SignalCode
                from airunner.components.llm.managers.llm_response import (
                    LLMResponse,
                )

                response = LLMResponse(
                    message=f"**📍 {phase}:** {message}",
                    is_first_message=False,
                    is_end_of_message=True,
                    action=None,
                    request_id=None,
                )
                self._api.emit_signal(
                    SignalCode.LLM_TEXT_STREAMED_SIGNAL,
                    {"response": response},
                )
            except Exception as e:
                logger.warning(f"Failed to emit progress: {e}")

    # ==================================================================
    # PHASE 0: RAG CHECK
    # ==================================================================

    def _phase0_rag_check(self, state: DeepResearchState) -> dict:
        """
        Phase 0: Check for relevant RAG documents in knowledge base.

        Returns:
            Updated state with rag_loaded flag
        """
        topic = state.get("research_topic", "")

        logger.info(f"[Phase 0] Checking for relevant RAG documents")

        # DIRECTLY execute tool to check for indexed docs
        from airunner.components.llm.tools.rag_tools import (
            search_knowledge_base_documents,
        )

        rag_loaded = False
        try:
            result = search_knowledge_base_documents(query=topic, k=5)
            rag_loaded = bool(result and "No documents found" not in result)
            if rag_loaded:
                logger.info(
                    f"[Phase 0] Found relevant docs: {result[:200]}..."
                )
            else:
                logger.info(f"[Phase 0] No relevant indexed documents found")
        except Exception as e:
            logger.warning(f"[Phase 0] RAG check failed: {e}")

        self._emit_progress("Phase 0", "RAG check complete")

        return {
            "messages": state.get("messages", []),
            "rag_loaded": rag_loaded,
            "current_phase": "phase1a",
        }

    # ==================================================================
    # PHASE 1A: GATHER SOURCES
    # ==================================================================

    def _phase1a_gather(self, state: DeepResearchState) -> dict:
        """
        Phase 1A: Create documents, generate queries, search web.

        Returns:
            Updated state with messages
        """
        topic = state.get("research_topic", "")
        document_path = state.get("document_path", "")
        queries = state.get("search_queries", [])

        logger.info(
            f"[Phase 1A] DIRECTLY executing tools (model refuses to cooperate)"
        )

        # DIRECTLY execute tools since model won't cooperate
        state_updates = {}

        # Create document
        if not document_path:
            from airunner.components.llm.tools.research_document_tools import (
                create_research_document,
            )

            try:
                doc_path = create_research_document(topic=topic, api=self._api)
                state_updates["document_path"] = doc_path
                state["document_path"] = doc_path
                logger.info(f"[Phase 1A] Created document: {doc_path}")
            except Exception as e:
                logger.error(f"[Phase 1A] Failed to create document: {e}")

        # Create notes
        if not state.get("notes_path"):
            from airunner.components.llm.tools.research_document_tools import (
                create_research_notes,
            )

            try:
                notes_path = create_research_notes(topic=topic, api=self._api)
                state_updates["notes_path"] = notes_path
                state["notes_path"] = notes_path
                logger.info(f"[Phase 1A] Created notes: {notes_path}")
            except Exception as e:
                logger.error(f"[Phase 1A] Failed to create notes: {e}")

        # Search web
        from airunner.components.llm.tools.web_tools import (
            search_web,
            search_news,
            scrape_website,
        )
        from airunner.components.llm.tools.research_document_tools import (
            append_research_notes,
        )

        query = queries[0] if queries else topic

        collected = list(state.get("collected_sources", []))

        # Run web search (DuckDuckGo) and collect structured results
        try:
            web_results = search_web(query=query)
            if isinstance(web_results, dict) and web_results.get("results"):
                collected.extend(web_results["results"])
                logger.info(
                    f"[Phase 1A] Found {len(web_results['results'])} web results"
                )
        except Exception as e:
            logger.error(f"[Phase 1A] Web search failed: {e}")

        # Run news search (DuckDuckGo news) and collect structured results
        try:
            news_results = search_news(query=query)
            if isinstance(news_results, dict) and news_results.get("results"):
                collected.extend(news_results["results"])
                logger.info(
                    f"[Phase 1A] Found {len(news_results['results'])} news results"
                )
        except Exception as e:
            logger.error(f"[Phase 1A] News search failed: {e}")

        # Deduplicate by URL and filter for relevance (topic in title/snippet/url)
        seen = set()
        filtered = []
        topic_lower = topic.lower()
        for item in collected:
            url = item.get("link") or item.get("url") or item.get("link")
            if not url:
                continue
            if url in seen:
                continue

            # Skip blacklisted domains (403 errors, paywalls, etc.)
            if self._is_domain_blacklisted(url):
                logger.info(f"[Phase 1A] Skipping blacklisted domain: {url}")
                continue

            # Skip irrelevant URL paths (games, login, shop, etc.)
            if self._is_url_irrelevant_path(url):
                logger.info(f"[Phase 1A] Skipping irrelevant URL path: {url}")
                continue

            seen.add(url)

            title = (item.get("title") or "").lower()
            snippet = (item.get("snippet") or "").lower()

            # Consider relevant if topic words appear in title/snippet or url
            is_relevant = (
                topic_lower in title
                or topic_lower in snippet
                or topic_lower.replace(" ", "-") in url.lower()
            )

            # Keep relevant items as high priority, otherwise keep as fallback
            item["_relevant"] = is_relevant
            filtered.append(item)

        # Sort with relevant items first
        filtered.sort(key=lambda x: (not x.get("_relevant", False)))

        # Persist collected sources to state
        if filtered:
            state_updates["collected_sources"] = filtered

        # For the top N relevant results, scrape and append notes incrementally
        # Keep trying URLs until we get enough successful scrapes
        max_scrape = 8
        scraped = 0
        attempted = 0
        max_attempts = min(
            len(filtered), 20
        )  # Try up to 20 URLs to get 8 successful scrapes

        for item in filtered:
            if scraped >= max_scrape:
                break
            if attempted >= max_attempts:
                logger.warning(
                    f"[Phase 1A] Reached max attempts ({max_attempts}), "
                    f"got {scraped}/{max_scrape} successful scrapes"
                )
                break

            url = item.get("link") or item.get("url")
            if not url:
                continue

            # Only scrape if flagged relevant or we still need to fill quota
            if not item.get("_relevant") and scraped >= 3:
                # keep a few non-relevant fallbacks but prefer relevant
                continue

            attempted += 1

            try:
                result = scrape_website(url)

                # Check if we got an error
                if not result.get("content") or result.get("error"):
                    error_msg = result.get("error", "Unknown error")
                    logger.warning(
                        f"[Phase 1A] Scraper returned error for {url}: {error_msg}, trying next URL"
                    )
                    continue

                content = result["content"]
                page_title = result.get("title")

                # Validate content quality before saving
                if not self._is_content_quality_acceptable(content):
                    logger.warning(
                        f"[Phase 1A] Content quality too low for {url} - adding to blocklist"
                    )
                    # Add to blocklist to avoid this domain in the future
                    from airunner.components.tools.web_content_extractor import (
                        WebContentExtractor,
                    )

                    WebContentExtractor._add_to_blocklist(url)
                    continue

            except Exception as e:
                logger.warning(
                    f"[Phase 1A] Scrape failed for {url}: {e}, trying next URL"
                )
                continue

            # Append a note for this source (incremental progress)
            try:
                # Use page title if available, fallback to search result title
                title = page_title or item.get("title", "")

                # Store MORE content for research - up to 3000 chars instead of 1000
                # Include the scraped page title for proper citation
                findings = (
                    f"Title: {title}\nURL: {url}\n\nExtract: {content[:3000]}"
                )
                append_research_notes(
                    notes_path=state.get("notes_path", ""),
                    source_url=url,
                    findings=findings,
                )
                scraped += 1
                state_updates.setdefault("sources_scraped", 0)
                state_updates["sources_scraped"] = (
                    state.get("sources_scraped", 0) + scraped
                )
                # Emit progress so user sees notes being added
                self._emit_progress(
                    "Phase 1A",
                    f"Scraped and noted: {title or url} ({scraped}/{max_scrape})",
                )
            except Exception as e:
                logger.error(
                    f"[Phase 1A] Failed to append notes for {url}: {e}"
                )

        self._emit_progress("Phase 1A", "Completed data gathering")

        return {
            "messages": state.get("messages", []),
            "current_phase": "phase1a_curiosity",  # Go to curiosity phase next
            **state_updates,
        }

    # ==================================================================
    # PHASE 1A-CURIOSITY: DEEP DIVE INTO INTERESTING TOPICS
    # ==================================================================

    def _phase1a_curiosity(self, state: DeepResearchState) -> dict:
        """
        Phase 1A-Curiosity: Extract interesting topics from initial notes and research them deeper.

        This phase reads the initial notes, identifies key topics/entities/concepts that warrant
        deeper investigation, generates follow-up search queries, and scrapes additional sources.

        This transforms the agent from a search aggregator into a true researcher.

        Args:
            state: Current research state

        Returns:
            Updated state with additional notes
        """
        notes_path = state.get("notes_path", "")
        topic = state.get("research_topic", "")

        logger.info(
            "[Phase 1A-Curiosity] Analyzing notes for interesting topics"
        )

        # Read initial notes
        notes_content = ""
        if notes_path and Path(notes_path).exists():
            try:
                with open(notes_path, "r", encoding="utf-8") as f:
                    notes_content = f.read()
                logger.info(
                    f"[Phase 1A-Curiosity] Read {len(notes_content)} chars from initial notes"
                )
            except Exception as e:
                logger.error(f"[Phase 1A-Curiosity] Failed to read notes: {e}")
                # Skip curiosity phase if we can't read notes
                return {
                    "messages": state.get("messages", []),
                    "current_phase": "phase1b",
                }

        if not notes_content:
            logger.warning(
                "[Phase 1A-Curiosity] No notes content, skipping curiosity phase"
            )
            return {
                "messages": state.get("messages", []),
                "current_phase": "phase1b",
            }

        # Extract interesting topics/entities from notes using simple keyword extraction
        # Look for proper nouns, quoted terms, and important concepts
        curiosity_topics = self._extract_curiosity_topics(notes_content, topic)

        if not curiosity_topics:
            logger.info(
                "[Phase 1A-Curiosity] No curiosity topics found, moving to next phase"
            )
            return {
                "messages": state.get("messages", []),
                "current_phase": "phase1b",
            }

        logger.info(
            f"[Phase 1A-Curiosity] Identified {len(curiosity_topics)} topics for deeper research: {curiosity_topics}"
        )
        self._emit_progress(
            "Phase 1A-Curiosity",
            f"Researching {len(curiosity_topics)} deeper topics",
        )

        # Import search/scrape tools
        from airunner.components.llm.tools.web_tools import (
            search_web,
            search_news,
            scrape_website,
        )
        from airunner.components.llm.tools.research_document_tools import (
            append_research_notes,
        )

        # For each curiosity topic, do a focused search
        state_updates = {}
        total_curiosity_scrapes = 0
        max_curiosity_scrapes_per_topic = 2  # 2 sources per curiosity topic

        for curiosity_topic in curiosity_topics[
            :5
        ]:  # Limit to top 5 curiosity topics
            logger.info(f"[Phase 1A-Curiosity] Deep dive: {curiosity_topic}")
            self._emit_progress(
                "Phase 1A-Curiosity", f"Deep dive: {curiosity_topic}"
            )

            # Search for this specific topic
            collected = []
            try:
                web_results = search_web(query=curiosity_topic)
                if isinstance(web_results, dict) and web_results.get(
                    "results"
                ):
                    collected.extend(web_results["results"])
            except Exception as e:
                logger.error(
                    f"[Phase 1A-Curiosity] Web search failed for '{curiosity_topic}': {e}"
                )

            # Filter and scrape
            scraped_for_topic = 0
            for item in collected:
                if scraped_for_topic >= max_curiosity_scrapes_per_topic:
                    break

                url = item.get("link") or item.get("url")
                if not url or self._is_domain_blacklisted(url):
                    continue

                # Skip irrelevant URL paths
                if self._is_url_irrelevant_path(url):
                    logger.info(
                        f"[Phase 1A-Curiosity] Skipping irrelevant URL path: {url}"
                    )
                    continue

                try:
                    result = scrape_website(url)

                    # Check if we got an error
                    if not result.get("content") or result.get("error"):
                        logger.warning(
                            f"[Phase 1A-Curiosity] Scraper error for {url}: {result.get('error', 'Unknown')}"
                        )
                        continue

                    content = result["content"]
                    page_title = result.get("title")

                    # Validate content quality
                    if not self._is_content_quality_acceptable(content):
                        logger.warning(
                            f"[Phase 1A-Curiosity] Content quality too low for {url} - adding to blocklist"
                        )
                        # Add to blocklist to avoid this domain in the future
                        from airunner.components.tools.web_content_extractor import (
                            WebContentExtractor,
                        )

                        WebContentExtractor._add_to_blocklist(url)
                        continue

                    # Use page title if available, fallback to search result title
                    title = page_title or item.get("title", "")

                    # Append to notes with curiosity marker
                    findings = f"**CURIOSITY DEEP-DIVE: {curiosity_topic}**\n\nTitle: {title}\nURL: {url}\n\nExtract: {content[:3000]}"
                    append_research_notes(
                        notes_path=notes_path,
                        source_url=url,
                        findings=findings,
                    )
                    scraped_for_topic += 1
                    total_curiosity_scrapes += 1

                    self._emit_progress(
                        "Phase 1A-Curiosity",
                        f"Found: {curiosity_topic} ({total_curiosity_scrapes} curiosity sources)",
                    )

                except Exception as e:
                    logger.warning(
                        f"[Phase 1A-Curiosity] Scrape failed for {url}: {e}"
                    )
                    continue

        logger.info(
            f"[Phase 1A-Curiosity] Completed {total_curiosity_scrapes} curiosity scrapes"
        )
        self._emit_progress(
            "Phase 1A-Curiosity",
            f"Completed deep dive ({total_curiosity_scrapes} additional sources)",
        )

        return {
            "messages": state.get("messages", []),
            "current_phase": "phase1b",
            **state_updates,
        }

    @staticmethod
    def _extract_curiosity_topics(
        notes_content: str, original_topic: str
    ) -> List[str]:
        """Extract interesting topics from notes that warrant deeper research.

        Uses simple heuristics:
        - Capitalized phrases (proper nouns, entities)
        - Quoted terms
        - Important policy/technical terms
        - Names of organizations, people, places

        Args:
            notes_content: The research notes content
            original_topic: Original research topic (to avoid redundancy)

        Returns:
            List of curiosity topics to research deeper
        """
        import re

        curiosity_topics = set()

        # Extract quoted terms (often important concepts)
        quoted = re.findall(r'"([^"]+)"', notes_content)
        for q in quoted:
            if (
                len(q.split()) >= 2 and len(q) < 60
            ):  # Multi-word phrases, not too long
                curiosity_topics.add(q)

        # Extract capitalized multi-word phrases (entities, organizations, places)
        # Look for sequences like "United Nations", "European Union", "Barack Obama"
        capitalized_phrases = re.findall(
            r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b", notes_content
        )
        for phrase in capitalized_phrases:
            if (
                len(phrase.split()) <= 4 and len(phrase) < 50
            ):  # Reasonable length
                # Skip common words
                if phrase.lower() not in {
                    "the united states",
                    "united states",
                    "the white house",
                    "white house",
                }:
                    curiosity_topics.add(phrase)

        # Extract specific policy/technical terms that appear frequently
        # Look for terms that appear multiple times (indicates importance)
        words = notes_content.lower().split()
        word_freq = {}
        for word in words:
            cleaned = re.sub(r"[^a-z]", "", word)
            if len(cleaned) > 5:  # Longer words tend to be more specific
                word_freq[cleaned] = word_freq.get(cleaned, 0) + 1

        # Get frequently mentioned terms (but not too common)
        for word, freq in word_freq.items():
            if (
                3 <= freq <= 10 and word not in original_topic.lower()
            ):  # Mentioned multiple times but not everywhere
                curiosity_topics.add(word.capitalize())

        # Convert to list and filter out the original topic
        filtered_topics = []
        original_lower = original_topic.lower()
        for topic in curiosity_topics:
            topic_lower = topic.lower()
            # Skip if it's basically the original topic
            if (
                topic_lower not in original_lower
                and original_lower not in topic_lower
            ):
                # Skip single words (prefer multi-word concepts)
                if " " in topic or len(topic) > 8:
                    filtered_topics.append(topic)

        # Sort by potential interest (prefer multi-word phrases)
        filtered_topics.sort(
            key=lambda x: (len(x.split()), len(x)), reverse=True
        )

        return filtered_topics[:10]  # Top 10 curiosity topics

    # ==================================================================
    # PHASE 1B: ANALYZE SOURCES
    # ==================================================================

    def _phase1b_analyze(self, state: DeepResearchState) -> dict:
        """
        Phase 1B: Read notes file and create structured outline.

        Phase 1A already scraped and appended notes, so Phase 1B just
        reads the accumulated notes and prepares for outlining.

        Returns:
            Updated state
        """
        logger.info(f"[Phase 1B] Analyzing collected notes")

        notes_path = state.get("notes_path", "")

        # Just verify notes exist
        if notes_path and Path(notes_path).exists():
            notes_size = Path(notes_path).stat().st_size
            logger.info(f"[Phase 1B] Notes file size: {notes_size} bytes")
            self._emit_progress(
                "Phase 1B", f"Analyzed {notes_size} bytes of research notes"
            )
        else:
            logger.warning(f"[Phase 1B] Notes file not found: {notes_path}")

        # Phase 1B is now just a pass-through since Phase 1A does the scraping
        return {
            "messages": state.get("messages", []),
            "current_phase": "phase1c",
        }

    # ==================================================================
    # PHASE 1C: CREATE OUTLINE
    # ==================================================================

    def _phase1c_outline(self, state: DeepResearchState) -> dict:
        """
        Phase 1C: Generate basic outline structure.

        Returns:
            Updated state with outline
        """
        topic = state.get("research_topic", "")

        logger.info(f"[Phase 1C] Creating outline for: {topic}")

        # Create a basic outline structure programmatically
        outline = f"""# {topic}

## Abstract
(To be written)

## Introduction
Overview of {topic}

## Background
Historical context and current situation

## Analysis
Key findings and developments

## Implications
Consequences and future outlook

## Conclusion
Summary of findings

## Sources
(Citations to be added)
"""

        logger.info(
            f"[Phase 1C] Created outline with {len(outline)} characters"
        )
        self._emit_progress("Phase 1C", "Created document outline")

        return {
            "messages": state.get("messages", []),
            "outline": outline,
            "current_phase": "phase1d",
        }

    # ==================================================================
    # PHASE 1D: WRITE DOCUMENT
    # ==================================================================

    def _phase1d_write(self, state: DeepResearchState) -> dict:
        """
        Phase 1D: Synthesize notes into a proper research document.

        This phase distills the raw notes into structured sections with:
        - Clear narratives
        - Proper organization
        - Key insights highlighted
        - Professional writing

        Returns:
            Updated state with messages
        """
        topic = state.get("research_topic", "")
        document_path = state.get("document_path", "")
        notes_path = state.get("notes_path", "")

        logger.info(f"[Phase 1D] Synthesizing research document from notes")

        from airunner.components.llm.tools.research_document_tools import (
            update_research_section,
        )

        # Read notes file
        notes_content = ""
        if notes_path and Path(notes_path).exists():
            try:
                with open(notes_path, "r", encoding="utf-8") as f:
                    notes_content = f.read()
                logger.info(
                    f"[Phase 1D] Read {len(notes_content)} chars from notes"
                )
            except Exception as e:
                logger.error(f"[Phase 1D] Failed to read notes: {e}")

        if not notes_content:
            logger.error("[Phase 1D] No notes content available to synthesize")
            return {
                "messages": state.get("messages", []),
                "current_phase": "phase1e",
            }

        # Parse notes to extract sources and key information
        parsed_notes = self._parse_research_notes(notes_content)

        # Write Introduction section
        sections_written = []
        try:
            intro_content = self._synthesize_introduction(topic, parsed_notes)
            update_research_section(
                document_path=document_path,
                section_name="Introduction",
                content=intro_content,
            )
            sections_written.append("Introduction")
            logger.info(f"[Phase 1D] Wrote Introduction section")
            self._emit_progress("Phase 1D", "Wrote Introduction")
        except Exception as e:
            logger.error(f"[Phase 1D] Failed to write Introduction: {e}")

        # Write Background section
        try:
            background_content = self._synthesize_background(
                topic, parsed_notes
            )
            update_research_section(
                document_path=document_path,
                section_name="Background",
                content=background_content,
            )
            sections_written.append("Background")
            logger.info(f"[Phase 1D] Wrote Background section")
            self._emit_progress("Phase 1D", "Wrote Background")
        except Exception as e:
            logger.error(f"[Phase 1D] Failed to write Background: {e}")

        # Write Analysis section with synthesized findings
        try:
            analysis_content = self._synthesize_analysis(topic, parsed_notes)
            update_research_section(
                document_path=document_path,
                section_name="Analysis",
                content=analysis_content,
            )
            sections_written.append("Analysis")
            logger.info(f"[Phase 1D] Wrote Analysis section")
            self._emit_progress("Phase 1D", "Wrote Analysis")
        except Exception as e:
            logger.error(f"[Phase 1D] Failed to write Analysis: {e}")

        # Write Implications section
        try:
            implications_content = self._synthesize_implications(
                topic, parsed_notes
            )
            update_research_section(
                document_path=document_path,
                section_name="Implications",
                content=implications_content,
            )
            sections_written.append("Implications")
            logger.info(f"[Phase 1D] Wrote Implications section")
            self._emit_progress("Phase 1D", "Wrote Implications")
        except Exception as e:
            logger.error(f"[Phase 1D] Failed to write Implications: {e}")

        # Write Conclusion section
        try:
            conclusion_content = self._synthesize_conclusion(
                topic, parsed_notes
            )
            update_research_section(
                document_path=document_path,
                section_name="Conclusion",
                content=conclusion_content,
            )
            sections_written.append("Conclusion")
            logger.info(f"[Phase 1D] Wrote Conclusion section")
            self._emit_progress("Phase 1D", "Wrote Conclusion")
        except Exception as e:
            logger.error(f"[Phase 1D] Failed to write Conclusion: {e}")

        # Write Sources section
        try:
            sources_content = self._synthesize_sources(parsed_notes)
            update_research_section(
                document_path=document_path,
                section_name="Sources",
                content=sources_content,
            )
            sections_written.append("Sources")
            logger.info(f"[Phase 1D] Wrote Sources section")
            self._emit_progress("Phase 1D", "Wrote Sources bibliography")
        except Exception as e:
            logger.error(f"[Phase 1D] Failed to write Sources: {e}")

        logger.info(
            f"[Phase 1D] Completed synthesis: {len(sections_written)} sections"
        )
        self._emit_progress(
            "Phase 1D", f"Synthesized {len(sections_written)} sections"
        )

        return {
            "messages": state.get("messages", []),
            "sections_written": sections_written,
            "current_phase": "phase1e",
        }

        return {
            "messages": state.get("messages", []),
            "sections_written": sections_written,
            "current_phase": "phase1e",
        }

    # ==================================================================
    # PHASE 1E: REVIEW
    # ==================================================================

    def _phase1e_review(self, state: DeepResearchState) -> dict:
        """
        Phase 1E: Review and validate document quality.

        Checks:
        - All sections are present
        - Citations are included
        - Content is substantial
        - No raw notes remain

        Returns:
            Updated state with review notes
        """
        document_path = state.get("document_path", "")

        logger.info(f"[Phase 1E] Reviewing document for quality")
        self._emit_progress("Phase 1E", "Reviewing document quality")

        if not document_path or not Path(document_path).exists():
            logger.error(f"[Phase 1E] Document not found: {document_path}")
            return {
                "messages": state.get("messages", []),
                "current_phase": "phase1f",
            }

        # Read document
        try:
            with open(document_path, "r", encoding="utf-8") as f:
                doc_content = f.read()
        except Exception as e:
            logger.error(f"[Phase 1E] Failed to read document: {e}")
            return {
                "messages": state.get("messages", []),
                "current_phase": "phase1f",
            }

        # Review checks
        review_notes = []

        # Check for required sections
        required_sections = [
            "Introduction",
            "Background",
            "Analysis",
            "Implications",
            "Conclusion",
        ]
        for section in required_sections:
            if f"## {section}" not in doc_content:
                review_notes.append(f"Missing section: {section}")
                logger.warning(f"[Phase 1E] Missing section: {section}")

        # Check for substance
        if len(doc_content) < 1000:
            review_notes.append("Document is too short")
            logger.warning(
                f"[Phase 1E] Document only {len(doc_content)} chars"
            )

        # Check for source references (look for **Source N** format)
        source_count = len(re.findall(r"\*\*Source \d+\*\*", doc_content))
        if source_count < 3:
            review_notes.append(
                f"Only {source_count} sources cited - expected more"
            )
            logger.warning(f"[Phase 1E] Only {source_count} sources found")

        # Check for unprocessed notes markers (shouldn't have ### URLs anymore)
        if re.search(r"###\s+https?://", doc_content):
            review_notes.append("Document may contain unprocessed raw notes")
            logger.warning(f"[Phase 1E] Found potential raw notes markers")

        if review_notes:
            logger.info(
                f"[Phase 1E] Review found {len(review_notes)} issues to address"
            )
            for note in review_notes:
                logger.info(f"  - {note}")
        else:
            logger.info(f"[Phase 1E] Document passed all quality checks")

        self._emit_progress(
            "Phase 1E",
            (
                f"Review complete - {len(review_notes)} issues found"
                if review_notes
                else "Review complete - quality approved"
            ),
        )

        return {
            "messages": state.get("messages", []),
            "review_notes": review_notes,
            "current_phase": "phase1f",
        }

    # ==================================================================
    # PHASE 1F: REVISE
    # ==================================================================

    def _phase1f_revise(self, state: DeepResearchState) -> dict:
        """
        Phase 1F: Apply final polishing and improvements.

        Improvements:
        - Add transitions between sections
        - Ensure proper formatting
        - Add executive summary if missing
        - Finalize citations

        Returns:
            Updated state
        """
        document_path = state.get("document_path", "")
        review_notes = state.get("review_notes", [])

        logger.info(f"[Phase 1F] Applying final revisions")
        self._emit_progress("Phase 1F", "Polishing document")

        if not document_path or not Path(document_path).exists():
            logger.error(f"[Phase 1F] Document not found: {document_path}")
            return {
                "messages": state.get("messages", []),
                "current_phase": "finalize",
            }

        # Read current document
        try:
            with open(document_path, "r", encoding="utf-8") as f:
                doc_content = f.read()
        except Exception as e:
            logger.error(f"[Phase 1F] Failed to read document: {e}")
            return {
                "messages": state.get("messages", []),
                "current_phase": "finalize",
            }

        # Apply revisions
        revisions_applied = []

        # 1. Generate and add Abstract at the beginning (after title and status)
        if "## Abstract" not in doc_content:
            # Find position after title and status lines
            lines = doc_content.split("\n")
            insert_pos = 0
            for i, line in enumerate(lines):
                if line.startswith("**Status:**"):
                    insert_pos = i + 1
                    break

            if insert_pos > 0:
                # Extract Introduction and Conclusion for context
                intro_match = re.search(
                    r"## Introduction\n\n(.+?)(?:\n##|$)",
                    doc_content,
                    re.DOTALL,
                )
                conclusion_match = re.search(
                    r"## Conclusion\n\n(.+?)(?:\n##|$)", doc_content, re.DOTALL
                )

                if intro_match and conclusion_match:
                    intro_text = intro_match.group(1).strip()[:800]
                    conclusion_text = conclusion_match.group(1).strip()[:600]

                    # Use LLM to generate a professional abstract
                    prompt = f"""Write a concise academic abstract (150-200 words) for this research paper.

INTRODUCTION EXCERPT:
{intro_text}

CONCLUSION EXCERPT:
{conclusion_text}

REQUIREMENTS:
1. Summarize the paper's scope, methods, and key findings
2. Use formal academic language
3. Be complete and coherent (no cut-off sentences)
4. Start directly with the content (no heading)
5. Length: 150-200 words

Write the abstract now:"""

                    try:
                        response = self._base_model.invoke(
                            [HumanMessage(content=prompt)],
                            temperature=0.2,
                            max_new_tokens=512,  # Allow full abstract generation
                            repetition_penalty=1.2,
                        )

                        if hasattr(response, "content") and response.content:
                            abstract_text = response.content.strip()
                            abstract = (
                                f"\n\n---\n\n## Abstract\n\n{abstract_text}\n"
                            )
                            lines.insert(insert_pos, abstract)
                            doc_content = "\n".join(lines)
                            revisions_applied.append("Generated abstract")
                            logger.info(
                                f"[Phase 1F] Generated abstract via LLM: {len(abstract_text)} chars"
                            )
                    except Exception as e:
                        logger.warning(
                            f"[Phase 1F] Failed to generate abstract via LLM: {e}"
                        )

        # 2. Generate and add Table of Contents
        if "## Table of Contents" not in doc_content:
            # Find all section headers
            section_headers = re.findall(
                r"^## (.+)$", doc_content, re.MULTILINE
            )

            # Filter out Abstract and ToC itself
            sections = [
                s
                for s in section_headers
                if s not in ["Abstract", "Table of Contents"]
            ]

            if sections:
                # Find position after Abstract (or after Status if no Abstract)
                lines = doc_content.split("\n")
                insert_pos = 0
                for i, line in enumerate(lines):
                    if line.startswith("## Abstract"):
                        # Find end of abstract section
                        for j in range(i + 1, len(lines)):
                            if lines[j].startswith("##") or lines[
                                j
                            ].startswith("---"):
                                insert_pos = j
                                break
                        break
                    elif line.startswith("**Status:**") and insert_pos == 0:
                        insert_pos = i + 1

                if insert_pos > 0:
                    toc = "\n\n---\n\n## Table of Contents\n\n"
                    for idx, section in enumerate(sections, 1):
                        toc += f"{idx}. {section}\n"
                    toc += "\n"

                    lines.insert(insert_pos, toc)
                    doc_content = "\n".join(lines)
                    revisions_applied.append("Generated table of contents")
                    logger.info(f"[Phase 1F] Generated table of contents")

        # 3. Ensure proper spacing between sections
        doc_content = re.sub(r"\n(## [A-Z])", r"\n\n\1", doc_content)
        doc_content = re.sub(r"\n{3,}", "\n\n", doc_content)  # Max 2 newlines
        revisions_applied.append("Normalized section spacing")

        # 3. Add source count to title if not present
        source_count = len(re.findall(r"\*\*Source \d+\*\*", doc_content))
        if source_count > 0:
            # Find title line
            title_match = re.search(r"(# .+)", doc_content)
            if (
                title_match
                and f"({source_count} sources)" not in title_match.group(1)
            ):
                new_title = (
                    title_match.group(1).rstrip()
                    + f" ({source_count} sources analyzed)"
                )
                doc_content = doc_content.replace(
                    title_match.group(1), new_title, 1
                )
                revisions_applied.append(
                    f"Added source count to title ({source_count} sources)"
                )
                logger.info(f"[Phase 1F] Added source count to title")

        # Write revised document
        try:
            with open(document_path, "w", encoding="utf-8") as f:
                f.write(doc_content)
            logger.info(
                f"[Phase 1F] Applied {len(revisions_applied)} revisions"
            )
            for revision in revisions_applied:
                logger.info(f"  - {revision}")
        except Exception as e:
            logger.error(f"[Phase 1F] Failed to write revisions: {e}")

        self._emit_progress(
            "Phase 1F", f"Applied {len(revisions_applied)} improvements"
        )

        return {
            "messages": state.get("messages", []),
            "revisions_applied": revisions_applied,
            "current_phase": "finalize",
        }

    # ==================================================================
    # FINALIZATION
    # ==================================================================

    def _finalize_document(self, state: DeepResearchState) -> dict:
        """
        Finalize the research document.

        Args:
            state: Current research state

        Returns:
            Updated state
        """
        document_path = state.get("document_path", "")

        logger.info(f"[Finalize] Finalizing document: {document_path}")

        from airunner.components.llm.tools.research_document_tools import (
            finalize_research_document,
        )

        try:
            result = finalize_research_document(document_path=document_path)
            logger.info(f"[Finalize] {result}")
            self._emit_progress("Finalize", f"Document ready: {document_path}")
        except Exception as e:
            logger.error(f"[Finalize] Failed to finalize: {e}")

        logger.info(f"✓ Research workflow completed for: {document_path}")

        return {
            "messages": state.get("messages", []),
            "current_phase": "complete",
        }

    def build_graph(self) -> StateGraph:
        """
        Build the Deep Research agent graph with explicit phases.

        Each phase handles its own tool loops internally via _execute_phase_with_tools(),
        so the graph is purely linear.

        Returns:
            StateGraph for deep research mode
        """
        logger.info(
            "Building Deep Research agent graph (phase-based workflow)"
        )

        graph = StateGraph(DeepResearchState)

        # Add all phase nodes
        graph.add_node("plan", self._plan_research)
        graph.add_node("phase0", self._phase0_rag_check)
        graph.add_node("phase1a", self._phase1a_gather)
        graph.add_node(
            "phase1a_curiosity", self._phase1a_curiosity
        )  # NEW: Curiosity phase
        graph.add_node("phase1b", self._phase1b_analyze)
        graph.add_node("phase1c", self._phase1c_outline)
        graph.add_node("phase1d", self._phase1d_write)
        graph.add_node("phase1e", self._phase1e_review)
        graph.add_node("phase1f", self._phase1f_revise)
        graph.add_node("finalize", self._finalize_document)

        # Pure linear progression - no conditional edges needed
        # Each phase handles tools internally
        graph.add_edge(START, "plan")
        graph.add_edge("plan", "phase0")
        graph.add_edge("phase0", "phase1a")
        graph.add_edge(
            "phase1a", "phase1a_curiosity"
        )  # NEW: Go to curiosity after initial gather
        graph.add_edge("phase1a_curiosity", "phase1b")  # Curiosity -> analyze
        graph.add_edge("phase1b", "phase1c")
        graph.add_edge("phase1c", "phase1d")
        graph.add_edge("phase1d", "phase1e")
        graph.add_edge("phase1e", "phase1f")
        graph.add_edge("phase1f", "finalize")
        graph.add_edge("finalize", END)

        logger.info(
            "Deep Research agent graph built successfully (8 phases with curiosity, linear flow)"
        )
        return graph

    def compile(self) -> Any:
        """
        Build and compile the Deep Research agent graph.

        Returns:
            Compiled graph ready for invocation
        """
        graph = self.build_graph()
        compiled = graph.compile()
        logger.info("Deep Research agent compiled successfully")
        return compiled
