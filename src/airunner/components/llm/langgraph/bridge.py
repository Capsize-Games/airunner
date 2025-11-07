"""Bridge between LangGraph and existing LlamaIndex functionality.

This module provides wrappers that allow LangGraph nodes to use
existing LlamaIndex components (RAG, chat engines, tools).
"""

from typing import Any, Dict, List, Optional, Callable
from llama_index.core import VectorStoreIndex
from llama_index.core.chat_engine.types import BaseChatEngine
from airunner.components.llm.core.tool_registry import (
    ToolRegistry,
    ToolCategory,
)
from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger


logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


class LlamaIndexBridge:
    """Bridge between LangGraph nodes and LlamaIndex functionality.

    This class provides static methods that create LangGraph-compatible
    node functions from LlamaIndex components.
    """

    @staticmethod
    def create_rag_node(
        rag_index: VectorStoreIndex,
        state_query_key: str = "query",
        state_context_key: str = "rag_context",
        state_docs_key: str = "retrieved_docs",
        top_k: int = 5,
    ) -> Callable:
        """Create a LangGraph node that uses LlamaIndex RAG.

        Args:
            rag_index: LlamaIndex vector store index
            state_query_key: Key in state dict for query
            state_context_key: Key to store retrieved context
            state_docs_key: Key to store retrieved documents
            top_k: Number of documents to retrieve

        Returns:
            Function that can be used as a LangGraph node
        """

        def rag_search(state: Dict[str, Any]) -> Dict[str, Any]:
            """Retrieve relevant documents using RAG."""
            try:
                # Get query from state
                query = state.get(
                    state_query_key,
                    state.get("messages", [""])[-1],
                )

                if not query:
                    logger.warning("No query found in state for RAG search")
                    return state

                logger.debug(f"RAG search for: {query[:100]}")

                # Retrieve documents
                retriever = rag_index.as_retriever(similarity_top_k=top_k)
                nodes = retriever.retrieve(query)

                # Extract context and metadata
                context_parts = []
                doc_metadata = []

                for node in nodes:
                    context_parts.append(node.text)
                    doc_metadata.append(
                        {
                            "text": node.text[:200] + "...",
                            "score": node.score,
                            "metadata": node.metadata,
                        }
                    )

                # Update state
                state[state_context_key] = "\n\n".join(context_parts)
                state[state_docs_key] = doc_metadata

                logger.info(f"Retrieved {len(nodes)} documents")

            except Exception as e:
                logger.error(f"RAG search error: {e}", exc_info=True)
                state["error"] = f"RAG search failed: {str(e)}"

            return state

        return rag_search

    @staticmethod
    def create_chat_engine_node(
        chat_engine: BaseChatEngine,
        state_message_key: str = "messages",
        state_response_key: str = "response",
    ) -> Callable:
        """Create a LangGraph node that uses LlamaIndex chat engine.

        Args:
            chat_engine: LlamaIndex chat engine
            state_message_key: Key in state dict for messages
            state_response_key: Key to store response

        Returns:
            Function that can be used as a LangGraph node
        """

        def chat_node(state: Dict[str, Any]) -> Dict[str, Any]:
            """Process message through chat engine."""
            try:
                # Get latest message
                messages = state.get(state_message_key, [])
                if not messages:
                    logger.warning("No messages found in state")
                    return state

                message = (
                    messages[-1] if isinstance(messages, list) else messages
                )

                logger.debug(f"Chat engine processing: {message[:100]}")

                # Get response
                response = chat_engine.chat(message)

                # Update state
                state[state_response_key] = str(response)
                state[state_message_key].append(str(response))

                logger.info("Chat engine response generated")

            except Exception as e:
                logger.error(f"Chat engine error: {e}", exc_info=True)
                state["error"] = f"Chat engine failed: {str(e)}"

            return state

        return chat_node

    @staticmethod
    def create_tool_node(
        tool_name: str,
        state_input_key: str = "tool_input",
        state_output_key: str = "tool_output",
    ) -> Callable:
        """Create a LangGraph node that executes a registered tool.

        Args:
            tool_name: Name of tool in ToolRegistry
            state_input_key: Key in state dict for tool input
            state_output_key: Key to store tool output

        Returns:
            Function that can be used as a LangGraph node
        """

        def tool_node(state: Dict[str, Any]) -> Dict[str, Any]:
            """Execute registered tool."""
            try:
                # Get tool from registry
                tool_info = ToolRegistry.get(tool_name)
                if not tool_info:
                    raise ValueError(f"Tool '{tool_name}' not found")

                # Get input
                tool_input = state.get(state_input_key)

                logger.debug(f"Executing tool: {tool_name}")

                # Execute tool
                if isinstance(tool_input, dict):
                    result = tool_info.func(**tool_input)
                elif isinstance(tool_input, (list, tuple)):
                    result = tool_info.func(*tool_input)
                else:
                    result = tool_info.func(tool_input)

                # Update state
                state[state_output_key] = result

                logger.info(f"Tool '{tool_name}' executed successfully")

            except Exception as e:
                logger.error(f"Tool execution error: {e}", exc_info=True)
                state["error"] = f"Tool '{tool_name}' failed: {str(e)}"

            return state

        return tool_node

    @staticmethod
    def create_multi_tool_node(
        categories: Optional[List[ToolCategory]] = None,
        state_calls_key: str = "tool_calls",
        state_results_key: str = "tool_results",
    ) -> Callable:
        """Create a node that can execute multiple tools.

        Args:
            categories: Optional list of tool categories to include
            state_calls_key: Key in state dict for tool calls
            state_results_key: Key to store results

        Returns:
            Function that can be used as a LangGraph node
        """

        def multi_tool_node(state: Dict[str, Any]) -> Dict[str, Any]:
            """Execute multiple tools from state."""
            try:
                tool_calls = state.get(state_calls_key, [])
                results = []

                for call in tool_calls:
                    tool_name = call.get("name")
                    tool_args = call.get("args", {})

                    # Get tool
                    tool_info = ToolRegistry.get(tool_name)
                    if not tool_info:
                        logger.warning(f"Tool '{tool_name}' not found")
                        results.append(
                            {"error": f"Tool '{tool_name}' not found"}
                        )
                        continue

                    # Check category filter
                    if categories and tool_info.category not in categories:
                        logger.warning(
                            f"Tool '{tool_name}' category {tool_info.category} not allowed"
                        )
                        results.append({"error": "Tool category not allowed"})
                        continue

                    # Execute
                    try:
                        result = tool_info.func(**tool_args)
                        results.append(result)
                        logger.debug(f"Executed tool: {tool_name}")
                    except Exception as e:
                        logger.error(
                            f"Tool '{tool_name}' error: {e}",
                            exc_info=True,
                        )
                        results.append({"error": str(e)})

                # Update state
                state[state_results_key] = results

            except Exception as e:
                logger.error(f"Multi-tool execution error: {e}", exc_info=True)
                state["error"] = f"Multi-tool execution failed: {str(e)}"

            return state

        return multi_tool_node
