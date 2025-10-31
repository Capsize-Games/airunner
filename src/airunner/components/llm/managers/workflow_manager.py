import logging
import uuid
from datetime import datetime
from contextlib import nullcontext
from typing import Any, Annotated, Optional, List, Callable
from typing_extensions import TypedDict

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import (
    HumanMessage,
    AIMessage,
    BaseMessage,
    trim_messages,
)
from langchain_core.messages.utils import count_tokens_approximately
from langgraph.graph import START, END, StateGraph, add_messages

from airunner.components.llm.managers.database_checkpoint_saver import (
    DatabaseCheckpointSaver,
)


class WorkflowState(TypedDict):
    """State schema for the workflow."""

    messages: Annotated[list[BaseMessage], add_messages]


class WorkflowManager:
    """Manages the LangGraph workflow for agent execution."""

    def __init__(
        self,
        system_prompt: str,
        chat_model: Any,
        tools: Optional[List[Callable]] = None,
        max_tokens: int = 2000,
        conversation_id: Optional[int] = None,
    ):
        """
        Initialize the workflow manager.

        Args:
            system_prompt: System prompt for the agent
            chat_model: LangChain ChatModel instance (ChatHuggingFaceLocal, ChatOllama, etc.)
            tools: List of LangChain tools
            max_tokens: Maximum tokens for conversation history
            conversation_id: Optional conversation ID for persistence
        """
        self._system_prompt = system_prompt
        self._original_chat_model = chat_model  # Store original unbound model
        self._chat_model = chat_model
        self._tools = tools or []
        self._max_tokens = max_tokens
        self._token_counter = lambda msgs: count_tokens_approximately(msgs)
        self._conversation_id = conversation_id
        self._memory = DatabaseCheckpointSaver(conversation_id)
        self._thread_id = (
            str(conversation_id) if conversation_id else "default"
        )
        self._workflow = None
        self._compiled_workflow = None
        self._token_callback: Optional[Callable[[str], None]] = None
        self._interrupted = False
        self.logger = logging.getLogger(__name__)

        self._initialize_model()
        self._build_and_compile_workflow()

    def _initialize_model(self):
        """
        Configure model for tool calling using ReAct pattern.

        Instead of dumping full tool schemas (which overwhelms models), we:
        1. Bind tools to chat model for native function calling (if supported)
        2. For local models, add COMPACT tool list to system prompt
        3. Let LangGraph's ToolNode handle parsing and execution
        """
        # Reset to original unbound model
        self._chat_model = self._original_chat_model

        # Skip if no tools provided
        if not self._tools or len(self._tools) == 0:
            self.logger.info("No tools provided - skipping tool binding")
            return

        # Log tool calling mode for debugging
        tool_calling_mode = getattr(
            self._chat_model, "tool_calling_mode", "react"
        )
        print(
            f"[WORKFLOW DEBUG] Model tool_calling_mode: {tool_calling_mode}",
            flush=True,
        )

        # Try to bind tools for native function calling
        if hasattr(self._chat_model, "bind_tools"):
            try:
                self._chat_model = self._chat_model.bind_tools(self._tools)
                self.logger.info(
                    f"Successfully bound {len(self._tools)} tools to chat model"
                )
                print(
                    f"[WORKFLOW DEBUG] Tools bound successfully via bind_tools()",
                    flush=True,
                )

                # NOTE: Tool instructions are added in _call_model() on each generation,
                # not here in init. This is because update_system_prompt() can overwrite
                # self._system_prompt, and we need tool instructions re-added each time.
                # See _call_model() line ~769 for the actual injection point.

            except NotImplementedError:
                self.logger.info(
                    "Model doesn't support native function calling - "
                    "using LangChain ReAct pattern"
                )
                # NOTE: Tool instructions are added in _call_model(), not here.
                # This prevents duplicate tool lists when system prompt is updated.

            except Exception as e:
                import traceback

                self.logger.warning(
                    f"Could not bind tools: {type(e).__name__}: {e}"
                )
                self.logger.debug(f"Traceback: {traceback.format_exc()}")
        elif self._tools:
            self.logger.warning(
                f"Chat model does not support bind_tools() - tools will not be available"
            )

    def _create_compact_tool_list(self) -> str:
        """
        Create a compact, readable tool list instead of verbose schemas.

        Instead of:
            ```
            @tool
            def generate_image(...):
                '''Long docstring...'''
                Args:
                    prompt (str): ...
                    width (int): ...
            ```

        We generate:
            Available tools:
            - generate_image(prompt, width, height) - Generate an image from text
            - search_documents(query, max_results) - Search knowledge base

        This is:
        - Much more compact (~50 tokens vs 500+ per tool)
        - Easier for models to parse
        - Standard ReAct pattern
        """
        if not self._tools:
            return ""

        tool_descriptions = []
        tool_descriptions.append("You have access to the following tools:")
        tool_descriptions.append("")

        for tool in self._tools:
            # Import ToolRegistry for metadata lookup
            from airunner.components.llm.core.tool_registry import ToolRegistry

            # Get tool metadata
            # StructuredTool objects have .name attribute but not .__name__
            tool_name = getattr(tool, "name", None)
            if tool_name is None:
                # Fallback for regular functions
                tool_name = getattr(tool, "__name__", "unknown_tool")

            # Try to get description from tool object first
            tool_desc = getattr(tool, "description", "")

            # If no description, try to look up in ToolRegistry
            if not tool_desc:
                tool_info = ToolRegistry.get(tool_name)
                if tool_info:
                    tool_desc = tool_info.description

            # Extract function signature
            if hasattr(tool, "func"):
                import inspect

                sig = inspect.signature(tool.func)
                params = [
                    p
                    for p in sig.parameters.keys()
                    if p not in ["api", "agent", "self"]
                ]
                param_str = ", ".join(params)
            elif hasattr(tool, "__name__"):
                # Try to get signature from the tool itself if it's a function
                import inspect

                try:
                    sig = inspect.signature(tool)
                    params = [
                        p
                        for p in sig.parameters.keys()
                        if p not in ["api", "agent", "self"]
                    ]
                    param_str = ", ".join(params)
                except (ValueError, TypeError):
                    param_str = "..."
            else:
                param_str = "..."

            # Clean description (first sentence only)
            short_desc = (
                tool_desc.split(".")[0] if tool_desc else "No description"
            )

            # Format: - tool_name(arg1, arg2) - Short description
            tool_descriptions.append(
                f"- {tool_name}({param_str}) - {short_desc}"
            )

        tool_descriptions.append("")

        # Add mode-specific instructions based on chat model's tool calling mode
        tool_calling_mode = getattr(
            self._chat_model, "tool_calling_mode", "react"
        )

        if tool_calling_mode == "json":
            # JSON mode: Clean structured output
            tool_descriptions.append(
                "To use a tool, respond with ONLY valid JSON (RFC 8259 compliant) on a SINGLE LINE:\n"
                "- Use DOUBLE QUOTES for all strings (not single quotes)\n"
                '- Escape special characters: \\n for newline, \\" for quote, \\\\ for backslash\n'
                '- Format: {"tool": "tool_name", "arguments": {"arg1": "value1"}}\n\n'
                "CRITICAL examples for code strings - note the DOUBLE QUOTES:\n"
                '{"tool": "sympy_compute", "arguments": {"code": "import sympy as sp\\nx = sp.symbols(\\"x\\")\\nresult = sp.solve(x**2 - 4, x)"}}\n'
                '{"tool": "python_compute", "arguments": {"code": "result = 2 + 2"}}\n\n'
                "More examples:\n"
                '{"tool": "search_web", "arguments": {"query": "Python tutorials"}}\n\n'
                "To use MULTIPLE tools, output multiple JSON objects, one per line:\n"
                '{"tool": "sympy_compute", "arguments": {"code": "x = 1"}}\n'
                '{"tool": "sympy_compute", "arguments": {"code": "result = x + 1"}}\n\n'
                "After tool execution, you'll receive results and can provide your final answer."
            )
        elif tool_calling_mode == "native":
            # Native mode: Minimal instructions (tokenizer handles it)
            tool_descriptions.append(
                "Use tools when needed. You can use multiple tools at once if the task requires it. "
                "The system will handle tool execution automatically."
            )
        else:
            # ReAct mode: Action/Observation format (fallback)
            tool_descriptions.append(
                "To use a tool, respond EXACTLY in this format:\n"
                "Action: tool_name\n"
                'Action Input: {"arg1": "value1", "arg2": "value2"}\n\n'
                "To use multiple tools, you can specify them sequentially:\n"
                "Action: first_tool\n"
                'Action Input: {"arg": "value"}\n'
                "Action: second_tool\n"
                'Action Input: {"arg": "value"}\n\n'
                "After using a tool, you'll receive:\n"
                "Observation: [tool result]\n\n"
                "Then continue reasoning or provide your final answer."
            )

        result = "\n".join(tool_descriptions)
        self.logger.debug(
            f"Compact tool list ({tool_calling_mode} mode): {len(result)} chars vs ~{len(self._tools) * 500} for full schemas"
        )
        return result

    def _execute_tools_with_status(
        self, state: WorkflowState
    ) -> WorkflowState:
        """Custom tool execution node that emits status signals.

        This wraps the standard ToolNode behavior but adds real-time status
        updates that can be displayed in the UI.
        """
        from langgraph.prebuilt import ToolNode
        from langchain_core.messages import ToolMessage
        from airunner.enums import SignalCode
        from airunner.components.application.api.api import API

        # Get the last AIMessage which contains tool_calls
        messages = state["messages"]
        last_message = messages[-1] if messages else None

        if not last_message or not hasattr(last_message, "tool_calls"):
            # No tool calls to execute, just pass through
            return state

        tool_calls = last_message.tool_calls or []

        # Emit "starting" status for each tool
        for tool_call in tool_calls:
            tool_name = tool_call.get("name", "unknown")
            tool_args = tool_call.get("args", {})
            tool_id = tool_call.get("id", "")

            # Extract primary argument (query, search_query, etc.)
            query = (
                tool_args.get("query")
                or tool_args.get("search_query")
                or tool_args.get("prompt")
                or str(tool_args)[:50]
            )

            self.logger.info(f"🔧 Tool starting: {tool_name} - {query}")

            # Emit "starting" status
            API().emit_signal(
                SignalCode.LLM_TOOL_STATUS_SIGNAL,
                {
                    "tool_id": tool_id,
                    "tool_name": tool_name,
                    "query": query,
                    "status": "starting",
                    "details": None,
                    "conversation_id": self._conversation_id,
                    "timestamp": str(datetime.now()),
                },
            )

        # Execute tools using standard ToolNode
        tool_node = ToolNode(self._tools)
        result_state = tool_node.invoke(state)

        # Extract tool results and emit "completed" status
        new_messages = result_state.get("messages", [])
        for msg in new_messages:
            if isinstance(msg, ToolMessage):
                # Find the corresponding tool_call
                matching_tool_call = None
                for tc in tool_calls:
                    if tc.get("id") == msg.tool_call_id:
                        matching_tool_call = tc
                        break

                if matching_tool_call:
                    tool_name = matching_tool_call.get("name", "unknown")
                    tool_args = matching_tool_call.get("args", {})
                    query = (
                        tool_args.get("query")
                        or tool_args.get("search_query")
                        or tool_args.get("prompt")
                        or str(tool_args)[:50]
                    )

                    # Extract details from result (URLs, sources, etc.)
                    details = self._extract_tool_details(
                        tool_name, msg.content
                    )

                    self.logger.info(
                        f"✅ Tool completed: {tool_name} - {details if details else 'success'}"
                    )

                    # Emit "completed" status
                    API().emit_signal(
                        SignalCode.LLM_TOOL_STATUS_SIGNAL,
                        {
                            "tool_id": msg.tool_call_id,
                            "tool_name": tool_name,
                            "query": query,
                            "status": "completed",
                            "details": details,
                            "conversation_id": self._conversation_id,
                            "timestamp": str(datetime.now()),
                        },
                    )

        return result_state

    def _extract_tool_details(
        self, tool_name: str, result_content: str
    ) -> Optional[str]:
        """Extract relevant details from tool result for status display.

        Args:
            tool_name: Name of the tool that was executed
            result_content: The result content from the tool

        Returns:
            Brief details string for display (e.g., "foxnews.com, cnn.com")
        """
        if tool_name == "search_web":
            # Extract URLs from web search results
            import re

            urls = re.findall(r"URL: (https?://[^\s]+)", result_content)
            if urls:
                # Extract domain names only
                domains = [url.split("/")[2] for url in urls[:3]]  # Top 3
                return ", ".join(domains)
        elif tool_name == "rag_search":
            # For RAG, just indicate number of results found
            if (
                "No results" in result_content
                or "couldn't find" in result_content
            ):
                return "no results"
            else:
                return "found results"

        return None

    def _build_and_compile_workflow(self):
        """Build and compile the LangGraph workflow."""
        self._workflow = self._build_graph()
        self._compiled_workflow = self._workflow.compile(
            checkpointer=self._memory
        )

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow."""
        workflow = StateGraph(WorkflowState)

        workflow.add_node("model", self._call_model)
        workflow.add_node("force_response", self._force_response_node)
        if self._tools:
            # Use custom tool node that emits status signals
            workflow.add_node("tools", self._execute_tools_with_status)

        workflow.add_edge(START, "model")

        if self._tools:
            workflow.add_conditional_edges(
                "model",
                self._route_after_model,
                {
                    "tools": "tools",
                    "force_response": "force_response",
                    "end": END,
                },
            )
            workflow.add_edge("tools", "model")
            workflow.add_edge("force_response", END)
        else:
            workflow.add_edge("model", END)

        return workflow

    def _force_response_node(self, state: WorkflowState) -> WorkflowState:
        """Node that generates forced response when redundancy detected.

        This is a proper LangGraph node (not just a router) so state updates
        are properly persisted to the checkpoint/database.
        """
        from langchain_core.messages import AIMessage

        # The last message should be the AIMessage with tool_calls that triggered redundancy
        # We'll replace it with a conversational response
        last_message = state["messages"][-1]

        if (
            not hasattr(last_message, "tool_calls")
            or not last_message.tool_calls
        ):
            self.logger.error(
                "Force response node called but last message has no tool_calls"
            )
            return state

        # Get the tool name and previous tool results
        tool_name = last_message.tool_calls[0].get("name")

        # Find ALL tool results (not just the last one)
        tool_messages = [
            msg
            for msg in state["messages"]
            if msg.__class__.__name__ == "ToolMessage"
        ]

        # Combine ALL tool results into one context
        all_tool_content = ""
        if tool_messages:
            for i, tool_msg in enumerate(tool_messages):
                all_tool_content += f"\n--- Tool Result {i+1} ---\n"
                all_tool_content += tool_msg.content
                all_tool_content += "\n"

        self.logger.info(
            f"Force response node: Generating answer from {len(all_tool_content)} chars across {len(tool_messages)} tool result(s)"
        )

        # Generate forced response based on tool results
        # Check if we have actual results to work with (> 100 chars)
        if len(all_tool_content) > 100:
            # We have actual results - force the model to answer based on them
            forced_prompt = f"""You have already used tools and received these results:

{all_tool_content}

Now provide a direct, conversational answer to the user's question based on the information above. Do NOT call any more tools. Just answer the question using what you found."""

            if tool_name == "rag_search":
                self.logger.info(
                    "Forcing model to answer based on RAG results..."
                )
            elif tool_name == "search_web":
                self.logger.info(
                    "Forcing model to answer based on web search results..."
                )
            else:
                self.logger.info(
                    f"Forcing model to answer based on {tool_name} results..."
                )

            try:
                from langchain_core.messages import HumanMessage

                response_content = ""
                # Call the model directly without going through _call_model
                # to avoid adding the post-tool instruction multiple times
                simple_prompt_text = f"""Based on the following tool results, answer the user's question:

{all_tool_content}

Provide a clear, conversational answer using only the information above."""

                # Convert to message format expected by chat model
                simple_prompt = [HumanMessage(content=simple_prompt_text)]

                for chunk in self._chat_model.stream(
                    simple_prompt, disable_tool_parsing=True
                ):
                    chunk_content = (
                        chunk.content
                        if hasattr(chunk, "content")
                        else str(chunk)
                    )
                    if chunk_content:
                        response_content += chunk_content
                        if self._token_callback:
                            self._token_callback(chunk_content)

                self.logger.info(
                    f"Model streamed {len(response_content)} char answer"
                )
            except Exception as e:
                self.logger.error(f"Failed to generate forced response: {e}")
                response_content = "I found some information but encountered an issue generating a complete response. Let me try to help with what I found."
                # Stream fallback message through callback
                if self._token_callback:
                    self._token_callback(response_content)
        else:
            # Tool failed or returned insufficient results - provide helpful message
            if tool_name == "search_web":
                response_content = "I searched the internet but couldn't find relevant information on that topic. Could you try rephrasing your question or asking about something else?"
            elif tool_name == "rag_search":
                response_content = "I searched through the available documents but couldn't find information about that. The documents may not contain details on this topic."
            else:
                response_content = "I tried to find information but wasn't able to get useful results. Could you rephrase your question or try a different approach?"
            # CRITICAL: Stream this message through callback so GUI sees it
            if self._token_callback:
                self._token_callback(response_content)

        # CRITICAL: Create AIMessage with NO tool_calls (empty list)
        # This ensures DatabaseChatMessageHistory won't skip it
        forced_message = AIMessage(
            content=response_content,
            tool_calls=[],  # Explicitly set to empty list
        )
        state["messages"][-1] = forced_message

        self.logger.info(
            f"✓ Force response node: Replaced tool call with {len(response_content)} char conversational response (tool_calls=[])"
        )

        return state

    def _route_after_model(self, state: WorkflowState) -> str:
        """Route to tools if model made tool calls, otherwise end."""
        last_message = state["messages"][-1]
        has_tool_calls = (
            hasattr(last_message, "tool_calls") and last_message.tool_calls
        )

        # DEBUG: Log the last message to see what we got
        print(
            f"[WORKFLOW DEBUG] Last message type: {type(last_message).__name__}",
            flush=True,
        )
        print(
            f"[WORKFLOW DEBUG] Has tool_calls attribute: {hasattr(last_message, 'tool_calls')}",
            flush=True,
        )
        if hasattr(last_message, "tool_calls"):
            print(
                f"[WORKFLOW DEBUG] tool_calls value: {last_message.tool_calls}",
                flush=True,
            )
        if hasattr(last_message, "content"):
            content_preview = (
                last_message.content[:300] if last_message.content else "None"
            )
            print(
                f"[WORKFLOW DEBUG] Message content preview: {content_preview}",
                flush=True,
            )

        # Log message history for debugging
        tool_messages = [
            msg
            for msg in state["messages"]
            if msg.__class__.__name__ == "ToolMessage"
        ]
        ai_messages = [
            msg
            for msg in state["messages"]
            if msg.__class__.__name__ == "AIMessage"
        ]

        self.logger.debug(
            f"Routing: has_tool_calls={has_tool_calls}, message_type={type(last_message).__name__}"
        )
        self.logger.debug(
            f"Message history: {len(ai_messages)} AI messages, {len(tool_messages)} tool results"
        )

        if has_tool_calls:
            tool_names = [tc.get("name") for tc in last_message.tool_calls]
            self.logger.info(
                f"Model requested {len(last_message.tool_calls)} tool calls: {tool_names}"
            )

            # DUPLICATE TOOL CALL DETECTION
            # Check if any of the current tool calls are duplicates of previous ones
            # This allows multiple different tools but prevents loops
            if tool_messages and len(ai_messages) >= 2:
                # Get all previous tool calls from AI messages that have corresponding results
                previous_tool_calls = []
                for i, ai_msg in enumerate(
                    ai_messages[:-1]
                ):  # Exclude current message
                    if hasattr(ai_msg, "tool_calls") and ai_msg.tool_calls:
                        for tc in ai_msg.tool_calls:
                            previous_tool_calls.append(
                                {
                                    "name": tc.get("name"),
                                    "args": tc.get("args", {}),
                                    "message_index": i,
                                }
                            )

                # Check each current tool call against previous ones
                for current_tc in last_message.tool_calls:
                    current_name = current_tc.get("name")
                    current_args = current_tc.get("args", {})

                    # Normalize arguments for comparison (convert to sorted tuple of items)
                    def normalize_args(args):
                        """Convert args dict to comparable format, handling nested structures."""
                        if not isinstance(args, dict):
                            return str(args)
                        # Sort items and convert to tuple for comparison
                        items = []
                        for k, v in sorted(args.items()):
                            if isinstance(v, dict):
                                v = normalize_args(v)
                            elif isinstance(v, list):
                                v = tuple(v)
                            items.append((k, v))
                        return tuple(items)

                    current_normalized = normalize_args(current_args)

                    # Check if this exact tool call (name + args) was made before
                    for prev_tc in previous_tool_calls:
                        if prev_tc["name"] == current_name:
                            prev_normalized = normalize_args(prev_tc["args"])

                            if current_normalized == prev_normalized:
                                self.logger.error(
                                    f"🔁 DUPLICATE TOOL CALL DETECTED!"
                                )
                                self.logger.error(f"   Tool: {current_name}")
                                self.logger.error(
                                    f"   Arguments: {current_args}"
                                )
                                self.logger.error(
                                    f"   This exact tool call was already executed in a previous turn."
                                )
                                self.logger.error(
                                    f"   Model is stuck in a loop - forcing conversational response."
                                )

                                # Log the tool result for context
                                if tool_messages:
                                    last_tool_content = (
                                        tool_messages[-1].content
                                        if tool_messages[-1].content
                                        else ""
                                    )
                                    self.logger.info(
                                        f"   Previous tool results available: {len(last_tool_content)} chars"
                                    )

                                return "force_response"

            # Log tool result for debugging
            if tool_messages:
                last_tool_result = tool_messages[-1] if tool_messages else None
                if last_tool_result and hasattr(last_tool_result, "content"):
                    result_content = last_tool_result.content
                    result_preview = (
                        result_content[:200]
                        if result_content
                        else "No content"
                    )
                    self.logger.info(
                        f"📋 Previous tool result length: {len(result_content)} chars, preview: {result_preview}..."
                    )

            return "tools"
        return "end"

    def _call_model(self, state: WorkflowState) -> dict[str, Any]:
        """Call the model with trimmed message history.

        Args:
            state: Workflow state containing messages and optional generation_kwargs

        Returns:
            Updated state with new AI message
        """
        # Extract generation kwargs from config if available
        generation_kwargs = state.get("generation_kwargs", {})

        trimmed_messages = trim_messages(
            state["messages"],
            max_tokens=self._max_tokens,
            strategy="last",
            token_counter=self._token_counter,
            include_system=True,
            allow_partial=False,
            start_on="human",
        )

        # Check if there are any ToolMessages in the conversation
        # If yes, the model should respond conversationally, not with tool JSON
        has_tool_results = any(
            msg.__class__.__name__ == "ToolMessage" for msg in trimmed_messages
        )

        # Escape curly braces in system prompt for LangChain template compatibility
        escaped_system_prompt = self._system_prompt.replace("{", "{{").replace(
            "}", "}}"
        )

        # CRITICAL: Add tool instructions if tools are available
        # This must be done here (not in _initialize_model) because update_system_prompt() can overwrite it
        if self._tools and len(self._tools) > 0:
            compact_tools = self._create_compact_tool_list()
            if compact_tools:
                # Escape curly braces for LangChain template compatibility
                compact_tools_escaped = compact_tools.replace(
                    "{", "{{"
                ).replace("}", "}}")
                escaped_system_prompt = (
                    f"{escaped_system_prompt}\n\n{compact_tools_escaped}"
                )
                print(
                    f"[WORKFLOW DEBUG] Appended tool instructions ({len(self._tools)} tools) to system prompt",
                    flush=True,
                )

        # DEBUG: Log full system prompt
        print(
            f"[WORKFLOW DEBUG] Full system prompt being sent to model:",
            flush=True,
        )
        print(f"{escaped_system_prompt[:1000]}...", flush=True)
        print(f"[WORKFLOW DEBUG] End of system prompt\n", flush=True)

        # Add context-aware instruction for JSON mode
        tool_calling_mode = getattr(
            self._chat_model, "tool_calling_mode", "react"
        )
        if has_tool_results and tool_calling_mode == "json":
            # After tool execution, instruct model to respond normally
            # Log the tool results for debugging
            tool_msgs = [
                m
                for m in trimmed_messages
                if m.__class__.__name__ == "ToolMessage"
            ]

            # Simple, natural instruction
            instruction = (
                "\n\nYou have tool results in the conversation above. "
                "Answer the user's question using that information. "
                "Respond conversationally, not in JSON."
            )
            escaped_system_prompt += instruction
            self.logger.debug(
                f"Added post-tool instruction: {instruction.strip()}"
            )

            if tool_msgs:
                self.logger.info(
                    f"Model has access to {len(tool_msgs)} tool result(s)"
                )
                for i, tool_msg in enumerate(tool_msgs):
                    result_preview = (
                        tool_msg.content[:200]
                        if hasattr(tool_msg, "content")
                        else "No content"
                    )
                    self.logger.info(
                        f"  Tool result {i+1} preview: {result_preview}..."
                    )

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", escaped_system_prompt),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )
        formatted_prompt = prompt.invoke({"messages": trimmed_messages})

        streamed_content: List[str] = []
        last_chunk_message: Optional[BaseMessage] = None
        response_message: Optional[AIMessage] = None

        if hasattr(self._chat_model, "stream"):
            try:
                # Pass generation kwargs to the chat model stream
                for chunk in self._chat_model.stream(
                    formatted_prompt, **generation_kwargs
                ):
                    if self._interrupted:
                        break

                    chunk_message = getattr(chunk, "message", chunk)
                    text = getattr(chunk_message, "content", "") or ""

                    # Always capture last chunk (might have tool_calls with no content)
                    last_chunk_message = chunk_message

                    # Skip content processing if empty, but still capture chunk for tool_calls
                    if not text:
                        continue

                    streamed_content.append(text)
                    # DON'T stream to GUI yet - wait until we know if it's a tool call or not
                    # (we'll send the complete response after parsing)

                if streamed_content:
                    additional_kwargs = {}
                    tool_calls = None
                    if last_chunk_message is not None:
                        additional_kwargs = getattr(
                            last_chunk_message, "additional_kwargs", {}
                        )
                        tool_calls = getattr(
                            last_chunk_message, "tool_calls", None
                        )

                    # LangChain automatically populates tool_calls on AIMessage
                    # when using bind_tools() - no manual parsing needed!
                    complete_content = "".join(streamed_content)

                    # Stream the content to GUI
                    # (will be empty if it was a pure tool call, so GUI won't show tool JSON)
                    if complete_content and self._token_callback:
                        try:
                            self._token_callback(complete_content)
                        except Exception as callback_error:
                            self.logger.error(
                                "Token callback failed: %s",
                                callback_error,
                                exc_info=True,
                            )

                    response_message = AIMessage(
                        content=complete_content,
                        additional_kwargs=additional_kwargs,
                        tool_calls=tool_calls or [],
                    )
                    print(
                        f"[DEBUG WORKFLOW] AIMessage content: {response_message.content[:200]}"
                    )
            except Exception as exc:
                self.logger.error(
                    "Error during streamed model call: %s", exc, exc_info=True
                )
                streamed_content = []
                response_message = None

        if response_message is None:
            response_message = self._chat_model.invoke(formatted_prompt)
            if (
                self._token_callback
                and hasattr(response_message, "content")
                and response_message.content
            ):
                try:
                    self._token_callback(response_message.content)
                except Exception as callback_error:
                    self.logger.error(
                        "Token callback failed: %s",
                        callback_error,
                        exc_info=True,
                    )

        return {"messages": [response_message]}

    def clear_memory(self):
        """Clear the conversation memory/history."""
        self._memory.message_history.clear()
        # Rebuild workflow with fresh memory
        self._build_and_compile_workflow()

    def set_conversation_id(self, conversation_id: int):
        """Set the conversation ID for persistence.

        Args:
            conversation_id: Conversation ID to use for storing messages
        """
        self._conversation_id = conversation_id
        self._thread_id = str(conversation_id)
        self._memory = DatabaseCheckpointSaver(conversation_id)
        self._build_and_compile_workflow()

    def invoke(self, user_input: str) -> dict[str, Any]:
        """Invoke the workflow with user input."""
        input_messages = [HumanMessage(user_input)]
        config = {
            "configurable": {"thread_id": self._thread_id},
            "recursion_limit": 20,  # Prevent runaway tool loops
        }
        math_context = nullcontext()

        try:
            from airunner.components.llm.tools.math_tools import (
                math_executor_session,
            )

            session_id = f"{self._thread_id}:{uuid.uuid4()}"
            math_context = math_executor_session(session_id)
        except ImportError:
            math_context = nullcontext()

        with math_context:
            return self._compiled_workflow.invoke(
                {"messages": input_messages}, config
            )

    def stream(
        self, user_input: str, generation_kwargs: Optional[dict] = None
    ):
        """Stream the workflow execution with user input, yielding messages.

        Args:
            user_input: The user's message/prompt
            generation_kwargs: Optional dict of generation parameters (max_new_tokens, temperature, etc.)
        """
        input_messages = [HumanMessage(user_input)]

        # Include generation kwargs in the initial state if provided
        initial_state = {"messages": input_messages}
        if generation_kwargs:
            initial_state["generation_kwargs"] = generation_kwargs

        config = {
            "configurable": {"thread_id": self._thread_id},
            "recursion_limit": 20,  # Prevent runaway tool loops (10-15 steps max for math)
        }

        # Use stream_mode="values" to get updates more frequently
        # This allows interrupt checking to happen more often
        math_context = nullcontext()

        try:
            from airunner.components.llm.tools.math_tools import (
                math_executor_session,
            )

            session_id = f"{self._thread_id}:{uuid.uuid4()}"
            math_context = math_executor_session(session_id)
        except ImportError:
            math_context = nullcontext()

        with math_context:
            for event in self._compiled_workflow.stream(
                initial_state,
                config,
                stream_mode="values",
            ):
                # Check interrupt flag on each event
                if self._interrupted:
                    break
                # Yield the entire state for each update
                if "messages" in event and event["messages"]:
                    last_message = event["messages"][-1]
                    if (
                        isinstance(last_message, AIMessage)
                        and last_message.content
                    ):
                        yield last_message

    def update_system_prompt(self, system_prompt: str):
        """Update the system prompt and rebuild the workflow."""
        print(
            f"[WORKFLOW DEBUG] Updating system prompt to: {system_prompt[:200]}...",
            flush=True,
        )
        self._system_prompt = system_prompt
        self._build_and_compile_workflow()

    def update_tools(self, tools: List[Callable]):
        """Update the tools and rebuild the workflow."""
        print(
            f"[WORKFLOW DEBUG] Updating tools: {len(tools)} tools provided",
            flush=True,
        )
        for tool in tools:
            print(
                f"[WORKFLOW DEBUG]   - Tool: {getattr(tool, '__name__', str(tool))}",
                flush=True,
            )
        self._tools = tools
        self._initialize_model()  # Re-bind tools
        self._build_and_compile_workflow()

    def set_token_callback(
        self, callback: Optional[Callable[[str], None]]
    ) -> None:
        """Register a callback for streaming tokens during model execution."""
        self._token_callback = callback

    def set_interrupted(self, value: bool) -> None:
        """Set the interrupted flag to stop generation."""
        self._interrupted = value
        if value:
            self.logger.info("Workflow interrupted flag set")

    def is_interrupted(self) -> bool:
        """Check if generation has been interrupted."""
        return self._interrupted
