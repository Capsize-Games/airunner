"""
Code Agent - Specialized subgraph for programming tasks.

This agent handles:
- Writing code in any language
- Debugging and testing
- Code review and analysis
- Explaining code concepts
- File operations related to code
"""

import json
import re
from typing import Any, Annotated, Callable, List, Optional
from typing_extensions import TypedDict

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    SystemMessage,
    ToolMessage,
    trim_messages,
)
from langchain_core.messages.utils import count_tokens_approximately
from langgraph.graph import START, END, StateGraph, add_messages
from langgraph.prebuilt import ToolNode

from airunner.components.llm.core.tool_registry import (
    ToolRegistry,
    ToolCategory,
)
from airunner.components.llm.utils.gpt_oss_parser import (
    has_gpt_oss_markup,
    looks_like_tool_argument_payload,
    parse_gpt_oss_response,
)
from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)

READ_ONLY_CODE_TOOLS = {
    "list_workspace_files",
    "read_code_file",
    "get_document_content",
    "get_document_info",
    "search_document",
    "goto_document_line",
    "validate_code",
    "run_tests",
    "lint_code",
    "analyze_code_complexity",
    "execute_python",
}

MUTATING_CODE_TOOLS = {
    "create_code_file",
    "edit_code_file",
    "delete_code_file",
    "format_code_file",
    "format_code",
    "edit_document_lines",
    "insert_document_lines",
    "delete_document_lines",
    "replace_in_document",
    "save_document",
}

EXECUTION_RETRY_TOOL_NAMES = {
    "create_code_file",
    "edit_code_file",
    "replace_in_document",
    "edit_document_lines",
    "insert_document_lines",
    "save_document",
}

VALIDATION_CODE_TOOLS = {
    "validate_code",
    "run_tests",
    "execute_python",
}

BEHAVIOR_VALIDATION_CODE_TOOLS = {
    "run_tests",
    "execute_python",
}

POST_WRITE_VALIDATION_TOOL_NAMES = {
    "list_workspace_files",
    "read_code_file",
    "create_code_file",
    "edit_code_file",
    "replace_in_document",
    "edit_document_lines",
    "insert_document_lines",
    "validate_code",
    "run_tests",
    "execute_python",
}

BEHAVIOR_VALIDATION_TOOL_NAMES = {
    "list_workspace_files",
    "read_code_file",
    "create_code_file",
    "edit_code_file",
    "replace_in_document",
    "edit_document_lines",
    "insert_document_lines",
    "run_tests",
    "execute_python",
}

BEHAVIOR_VALIDATION_HINTS = (
    "algorithm",
    "cli",
    "command line",
    "command-line",
    "stdout",
    "stderr",
    "terminal",
    "__main__",
    "print",
    "output",
)

TERMINAL_OUTPUT_VALIDATION_HINTS = (
    "cli",
    "command line",
    "command-line",
    "stdout",
    "stderr",
    "terminal",
    "__main__",
    "print",
    "output",
)

ASSERTION_SIGNAL_PATTERNS = (
    r"\bassert\b",
    r"AssertionError",
    r"pytest\.fail\(",
    r"self\.assert[A-Za-z]+\(",
)

OUTPUT_CAPTURE_SIGNAL_PATTERNS = (
    r"redirect_stdout",
    r"StringIO",
    r"getvalue\(",
    r"stdout",
    r"subprocess\.",
    r"capsys",
)

def _contains_language_keyword(content: str, keyword: str) -> bool:
    """Return True when one language keyword is present in the prompt."""
    if not keyword:
        return False
    if re.fullmatch(r"[a-z0-9]+", keyword):
        pattern = rf"\b{re.escape(keyword)}\b"
        return re.search(pattern, content) is not None
    return keyword in content


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
        tool_event_callback: Optional[Callable[[List[str]], None]] = None,
    ):
        """
        Initialize Code Agent.

        Args:
            chat_model: LangChain chat model
            system_prompt: Optional custom system prompt
        """
        self._chat_model = chat_model
        self._system_prompt = system_prompt or self._default_system_prompt()
        self._tool_event_callback = tool_event_callback
        self._executed_tools: List[str] = []
        self._tool_result_summaries: List[tuple[str, str]] = []
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
        """Get code-mode tools from the registry."""
        code_tools = ToolRegistry.get_by_category(ToolCategory.CODE)
        workflow_tools = ToolRegistry.get_by_category(
            ToolCategory.WORKFLOW
        )
        logger.info(
            "Retrieved %s CODE tools and %s WORKFLOW tools",
            len(code_tools),
            len(workflow_tools),
        )

        tools_by_name = {
            tool.name: tool.func for tool in [*code_tools, *workflow_tools]
        }
        tools = list(tools_by_name.values())
        return tools

    def _analyze_code_request(self, state: CodeState) -> dict:
        """
        Analyze the code request to determine language and task type.

        Args:
            state: Current code state

        Returns:
            Updated state with language, task_type, execution_context
        """
        self._executed_tools = []
        self._tool_result_summaries = []
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
            if any(
                _contains_language_keyword(content, keyword)
                for keyword in keywords
            ):
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

        system_prompt = self._build_model_system_prompt(language, task_type)
        response = self._invoke_model(messages, system_prompt)
        forced_write_tool_name: str | None = None
        forced_write_retry_attempted = False

        if self._should_retry_empty_response(response):
            logger.info("Retrying empty code-agent model response")
            retry_prompt = self._build_retry_system_prompt(
                system_prompt,
                task_type,
            )
            response = self._invoke_model(messages, retry_prompt)

        if self._needs_write_execution_retry(task_type, response):
            logger.info(
                "Retrying code-agent response after non-mutating progress"
            )
            execution_prompt = self._build_execution_retry_prompt(
                system_prompt,
            )
            response = self._invoke_model_with_tool_subset(
                messages,
                execution_prompt,
                EXECUTION_RETRY_TOOL_NAMES,
            )

        if self._needs_forced_write_tool_retry(task_type, response):
            forced_tool_name = self._preferred_forced_write_tool(messages)
            forced_write_tool_name = forced_tool_name
            forced_write_retry_attempted = True
            logger.info(
                "Retrying code-agent with forced write tool: %s",
                forced_tool_name,
            )
            forced_prompt = self._build_forced_write_tool_prompt(
                system_prompt,
                forced_tool_name,
                messages,
            )
            response = self._invoke_model_with_tool_subset(
                messages,
                forced_prompt,
                {forced_tool_name},
            )

        if self._needs_follow_up_forced_write_tool_retry(
            task_type,
            response,
            forced_write_retry_attempted,
        ):
            forced_tool_name = (
                forced_write_tool_name
                or self._preferred_forced_write_tool(messages)
            )
            logger.info(
                "Retrying malformed forced write tool payload: %s",
                forced_tool_name,
            )
            forced_prompt = self._build_forced_write_tool_prompt(
                system_prompt,
                forced_tool_name,
                messages,
            )
            response = self._invoke_model_with_tool_subset(
                messages,
                forced_prompt,
                {forced_tool_name},
            )

        if self._needs_post_write_validation_retry(task_type, response):
            logger.info(
                "Retrying code-agent response to require post-write "
                "validation"
            )
            validation_prompt = self._build_post_write_validation_prompt(
                system_prompt,
                messages,
            )
            response = self._invoke_model_with_tool_subset(
                messages,
                validation_prompt,
                POST_WRITE_VALIDATION_TOOL_NAMES,
            )

        if self._needs_forced_validation_tool_retry(
            task_type,
            response,
            messages,
        ):
            forced_validation_tool = self._preferred_validation_tool(
                messages,
            )
            logger.info(
                "Retrying code-agent with forced validation tool: %s",
                forced_validation_tool,
            )
            forced_validation_prompt = (
                self._build_forced_validation_tool_prompt(
                    system_prompt,
                    messages,
                    forced_validation_tool,
                )
            )
            response = self._invoke_model_with_tool_subset(
                messages,
                forced_validation_prompt,
                {forced_validation_tool},
            )

        if self._needs_behavior_validation_retry(
            task_type,
            response,
            messages,
        ):
            logger.info(
                "Retrying code-agent response to require stronger "
                "behavior validation"
            )
            behavior_prompt = self._build_behavior_validation_prompt(
                system_prompt,
                messages,
            )
            response = self._invoke_model_with_tool_subset(
                messages,
                behavior_prompt,
                BEHAVIOR_VALIDATION_TOOL_NAMES,
            )

        if self._needs_forced_behavior_validation_tool_retry(
            task_type,
            response,
            messages,
        ):
            logger.info(
                "Retrying code-agent with forced behavior validation tool"
            )
            forced_behavior_prompt = (
                self._build_forced_behavior_validation_tool_prompt(
                    system_prompt,
                    messages,
                )
            )
            response = self._invoke_model_with_tool_subset(
                messages,
                forced_behavior_prompt,
                {"execute_python"},
            )

        if self._should_abort_repeating_tool_loop(task_type, response):
            logger.warning(
                "Stopping code-agent after repeated non-mutating tool loop"
            )
            response = AIMessage(content=self._repeating_tool_loop_reply())

        response = self._finalize_response(messages, response)

        return {"messages": [response]}

    def _finalize_response(
        self,
        messages: List[BaseMessage],
        response: BaseMessage,
    ) -> BaseMessage:
        """Attach tool metadata or synthesize a fallback final response."""
        if not isinstance(response, AIMessage):
            return response

        additional_kwargs = dict(response.additional_kwargs or {})
        if self._executed_tools:
            additional_kwargs["executed_tools"] = self._executed_tools.copy()

        if self._should_retry_empty_response(response) and self._executed_tools:
            return AIMessage(
                content=self._synthesized_final_reply(messages),
                additional_kwargs=additional_kwargs,
            )

        response.additional_kwargs = additional_kwargs
        return response

    def _synthesized_final_reply(self, messages: List[BaseMessage]) -> str:
        """Build a visible fallback when tools ran but the model stayed hidden."""
        tool_names = ", ".join(dict.fromkeys(self._executed_tools))
        if self._only_read_only_tools_used():
            return (
                "Inspected the workspace using read-only tools "
                f"({tool_names}), but no file modifications were applied."
            )
        if self._used_only_non_mutating_tools():
            return (
                "Used non-mutating tools "
                f"({tool_names}), but no file modifications were applied."
            )
        last_result = self._last_tool_result_summary(messages)
        changed_file = self._latest_mutating_file_path(messages)
        if changed_file:
            if last_result:
                return (
                    f"Modified {changed_file} using {tool_names}, but the "
                    "model did not verify that the result satisfies the "
                    f"request. Last tool result: {last_result}"
                )
            return (
                f"Modified {changed_file} using {tool_names}, but the model "
                "did not provide a final verification summary."
            )
        if last_result:
            return (
                f"Completed tool actions ({tool_names}). "
                f"Last tool result: {last_result}"
            )
        return (
            f"Completed tool actions ({tool_names}), but the model did "
            "not provide a visible final reply."
        )

    def _last_tool_result_summary(self, messages: List[BaseMessage]) -> str:
        """Return one compact summary from the latest tool result."""
        for _tool_name, summary in reversed(self._tool_result_summaries):
            if summary:
                return summary
        for message in reversed(messages):
            if not isinstance(message, ToolMessage):
                continue
            content = str(message.content or "").strip()
            if not content:
                continue
            for line in content.splitlines():
                line = line.strip()
                if line:
                    return line[:200]
        return ""

    def _invoke_model(
        self,
        messages: List[BaseMessage],
        system_prompt: str,
    ) -> BaseMessage:
        """Invoke the bound chat model with one consolidated system prompt."""
        return self._invoke_model_with_model(
            self._chat_model,
            messages,
            system_prompt,
        )

    def _invoke_model_with_model(
        self,
        model: Any,
        messages: List[BaseMessage],
        system_prompt: str,
    ) -> BaseMessage:
        """Invoke one specific model binding with trimmed context."""
        trimmed_messages = self._trim_messages_for_context(
            messages,
            system_prompt,
            model,
        )
        prompt_messages = [SystemMessage(content=system_prompt), *trimmed_messages]
        return model.invoke(prompt_messages)

    def _invoke_model_with_tool_subset(
        self,
        messages: List[BaseMessage],
        system_prompt: str,
        allowed_tool_names: set[str],
    ) -> BaseMessage:
        """Invoke the model with a narrowed set of tools for this turn."""
        if not self._tools or not hasattr(self._chat_model, "bind_tools"):
            return self._invoke_model(messages, system_prompt)

        subset_tools = [
            tool
            for tool in self._tools
            if getattr(tool, "__name__", "") in allowed_tool_names
        ]
        if not subset_tools:
            return self._invoke_model(messages, system_prompt)

        logger.info(
            "Invoking code-agent retry with narrowed tools: %s",
            ", ".join(getattr(tool, "__name__", "unknown") for tool in subset_tools),
        )
        bind_kwargs: dict[str, str] = {}
        if len(subset_tools) == 1:
            tool_name = getattr(subset_tools[0], "__name__", "")
            if tool_name:
                bind_kwargs["tool_choice"] = tool_name
        try:
            narrowed_model = self._chat_model.bind_tools(
                subset_tools,
                **bind_kwargs,
            )
        except TypeError:
            narrowed_model = self._chat_model.bind_tools(subset_tools)
        return self._invoke_model_with_model(
            narrowed_model,
            messages,
            system_prompt,
        )

    def _trim_messages_for_context(
        self,
        messages: List[BaseMessage],
        system_prompt: str,
        model: Any | None = None,
    ) -> List[BaseMessage]:
        """Trim code-mode history to fit the active model context."""
        budget = self._history_token_budget(system_prompt, model)
        if budget is None:
            return messages

        trimmed = trim_messages(
            messages,
            max_tokens=budget,
            strategy="last",
            token_counter=count_tokens_approximately,
            allow_partial=False,
            start_on="human",
        )
        trimmed = self._preserve_latest_request_context(
            messages,
            trimmed,
            budget,
        )
        if len(trimmed) != len(messages):
            logger.info(
                "Trimmed code-agent history from %s to %s messages "
                "for %s-token budget",
                len(messages),
                len(trimmed),
                budget,
            )
        return trimmed

    def _preserve_latest_request_context(
        self,
        messages: List[BaseMessage],
        trimmed: List[BaseMessage],
        budget: int,
    ) -> List[BaseMessage]:
        """Recover the latest user turn when automatic trimming drops it."""
        if not messages:
            return trimmed
        if trimmed and any(getattr(msg, "type", "") == "human" for msg in trimmed):
            return trimmed
        last_human_index = self._last_human_index(messages)
        if last_human_index is None:
            return trimmed or messages[-1:]
        recovered = self._recover_request_tail(
            messages[last_human_index:],
            budget,
        )
        if recovered != trimmed:
            logger.info(
                "Recovered %s code-agent messages to preserve the latest "
                "request",
                len(recovered),
            )
        return recovered

    def _last_human_index(self, messages: List[BaseMessage]) -> int | None:
        """Return the index of the latest human message when present."""
        for index in range(len(messages) - 1, -1, -1):
            if getattr(messages[index], "type", "") == "human":
                return index
        return None

    def _recover_request_tail(
        self,
        tail_messages: List[BaseMessage],
        budget: int,
    ) -> List[BaseMessage]:
        """Return the latest request plus as much trailing context as fits."""
        request_message = tail_messages[0]
        if count_tokens_approximately([request_message]) >= budget:
            return [request_message]

        recovered: List[BaseMessage] = []
        for message in reversed(tail_messages[1:]):
            candidate = [request_message, message, *recovered]
            if count_tokens_approximately(candidate) <= budget:
                recovered.insert(0, message)
        return [request_message, *recovered]

    def _history_token_budget(self, system_prompt: str) -> int | None:
        """Return the history budget after reserving prompt and reply space."""
    def _history_token_budget(
        self,
        system_prompt: str,
        model: Any | None = None,
    ) -> int | None:
        """Return the history budget after reserving prompt and reply space."""
        target_ctx = self._model_context_limit(model)
        if not target_ctx:
            return None

        prompt_tokens = count_tokens_approximately(
            [
                SystemMessage(
                    content=self._effective_system_prompt(
                        system_prompt,
                        model,
                    )
                )
            ]
        )
        reply_reserve = max(256, min(2048, target_ctx // 4))
        history_budget = target_ctx - prompt_tokens - reply_reserve
        return max(128, history_budget)

    def _model_context_limit(self, model: Any | None = None) -> int | None:
        """Return the active chat-model context limit when available."""
        active_model = model or self._chat_model
        for attr in ("n_ctx", "_target_context_length"):
            value = getattr(active_model, attr, None)
            if isinstance(value, int) and value > 0:
                return value
        return None

    def _effective_system_prompt(
        self,
        system_prompt: str,
        model: Any | None = None,
    ) -> str:
        """Approximate the full system prompt after tool injection."""
        prompt = system_prompt
        active_model = model or self._chat_model
        if not getattr(active_model, "tools", None):
            return prompt
        if getattr(active_model, "tool_calling_mode", None) != "react":
            return prompt
        if getattr(active_model, "_uses_gpt_oss_parser", lambda: False)():
            return active_model._inject_gpt_oss_tool_instructions(prompt)
        if hasattr(active_model, "_inject_tool_instructions"):
            return active_model._inject_tool_instructions(prompt)
        return prompt

    def _build_model_system_prompt(
        self,
        language: str,
        task_type: str,
    ) -> str:
        """Build one system prompt with task context and tool guidance."""
        parts = [
            self._system_prompt,
            f"Current task: {self._describe_task(task_type)} in {language}.",
        ]

        if self._tools:
            parts.append(self._tool_execution_guidance())

        return "\n\n".join(part for part in parts if part)

    def _describe_task(self, task_type: str) -> str:
        """Return one short description for the current coding task."""
        return {
            "write": "writing new code",
            "debug": "debugging and fixing code",
            "review": "reviewing and analyzing code",
            "explain": "explaining code concepts",
            "test": "testing and verifying code",
            "general": "general programming assistance",
        }.get(task_type, "general programming assistance")

    def _tool_execution_guidance(self) -> str:
        """Return the direct-action guidance used for tool-backed code turns."""
        return (
            "Use the available code tools directly when the request needs "
            "workspace changes or validation. Inspect relevant files before "
            "editing, including nearby tests or entry points when they "
            "exist, then create or edit the required files instead of "
            "stopping after planning. Preferred actions are reading relevant "
            "files, creating or editing the target file, and running the "
            "relevant validation tool. When behavior changes, add or "
            "strengthen focused tests instead of relying on trivial smoke "
            "coverage. For algorithmic or CLI requirements, prefer tests "
            "that would fail if the core behavior is semantically wrong. "
            "Syntax-only checks such as validate_code do not prove "
            "semantic correctness. If run_tests finds zero tests for an "
            "algorithmic or CLI task, treat that as unvalidated behavior. "
            "For terminal-output tasks, verify the output content or "
            "invariants, not just a successful exit code. "
            "Existing smoke tests that only verify imports or exports do "
            "not satisfy algorithmic or CLI acceptance criteria. "
            "Do not end the turn with hidden "
            "reasoning only. Do not stop after scaffolding or placeholder "
            "code when the user requested a specific implementation. "
            "Read-only inspection alone does not satisfy a write request. "
            "Treat the user's request as the acceptance criteria; weak or "
            "incomplete smoke tests are not enough by themselves. "
            "The create_code_file and edit_code_file tools can be called "
            "directly once you know the required changes. "
            "Either call the next appropriate tool now or provide a "
            "user-visible final answer."
        )

    def _build_retry_system_prompt(
        self,
        system_prompt: str,
        task_type: str,
    ) -> str:
        """Return the retry prompt for an empty assistant turn."""
        retry_suffix = ""
        if task_type == "write" and self._used_only_non_mutating_tools():
            explored_tools = ", ".join(dict.fromkeys(self._executed_tools))
            if self._only_read_only_tools_used():
                retry_suffix = (
                    " You have only used read-only tools so far "
                    f"({explored_tools}). The request requires code "
                    "changes, so your next step must be a "
                    "file-modifying tool such as create_code_file, "
                    "edit_code_file, replace_in_document, "
                    "edit_document_lines, insert_document_lines, "
                    "or save_document."
                )
            else:
                retry_suffix = (
                    " You have used tools already "
                    f"({explored_tools}), but none of them modified files. "
                    "The request requires code changes, so your next step "
                    "must be a file-modifying tool such as "
                    "create_code_file, edit_code_file, "
                    "replace_in_document, edit_document_lines, "
                    "insert_document_lines, or save_document."
                )
        return (
            f"{system_prompt}\n\n"
            "Your previous attempt produced no visible answer and no tool "
            "call. For this turn, either call the next appropriate tool "
            "immediately or provide a user-visible final answer. Do not "
            "return an empty response or hidden reasoning by itself. If the "
            "user asked for a specific implementation, do not stop at "
            f"scaffolding or placeholder code.{retry_suffix}"
        )

    def _build_execution_retry_prompt(self, system_prompt: str) -> str:
        """Return a targeted retry prompt after non-mutating progress."""
        explored_tools = ", ".join(dict.fromkeys(self._executed_tools))
        progress_summary = "non-mutating tools"
        next_step = "planning is complete"
        if self._only_read_only_tools_used():
            progress_summary = "read-only tools"
            next_step = "inspection is complete"
        return (
            f"{system_prompt}\n\n"
            f"You have already used {progress_summary} "
            f"({explored_tools}). The user asked you to implement code, so "
            f"{next_step}. On this turn, call a file-modifying tool "
            "that creates or edits the required implementation. Only write "
            "tools are available for this retry. Do not reply "
            "with more planning, more read-only inspection, or hidden "
            "reasoning only. Do not repeat list_workspace_files or "
            "read_code_file unless that directly enables the next file edit."
        )

    def _build_forced_write_tool_prompt(
        self,
        system_prompt: str,
        tool_name: str,
        messages: List[BaseMessage],
    ) -> str:
        """Return a final retry prompt that requires one write tool call."""
        inspected_files = self._recent_read_file_paths(messages)
        file_hint = ""
        if inspected_files:
            file_hint = (
                " You have already inspected these files: "
                f"{', '.join(inspected_files)}."
            )
        return (
            f"{system_prompt}\n\n"
            "Your previous retries did not modify any files. You must now "
            "emit exactly one commentary tool call with JSON arguments and "
            "no final answer text for this turn. "
            f"Call functions.{tool_name} now.{file_hint} "
            "Use the user's stated requirements as the source of truth for "
            "this edit, and do not optimize for the smallest change that only "
            "passes weak smoke tests. "
            "Do not use analysis-only output. Do not call read-only tools."
        )

    def _build_post_write_validation_prompt(
        self,
        system_prompt: str,
        messages: List[BaseMessage],
    ) -> str:
        """Return a retry prompt that requires post-write validation."""
        changed_file = self._latest_mutating_file_path(messages)
        file_hint = ""
        if changed_file:
            file_hint = f" You already modified {changed_file}."
        return (
            f"{system_prompt}\n\n"
            "You have already modified files but have not validated the "
            f"result yet.{file_hint} Before finalizing, use validation "
            "tools. Run validate_code or run_tests for the affected code. "
            "If the change affects behavior and tests are missing or too "
            "weak, add or strengthen a focused test first, then run it. "
            "For algorithmic or terminal-output requirements, prefer tests "
            "that would fail if the core behavior is semantically wrong. "
            "Syntax-only validation alone does not prove the behavior is "
            "correct. Existing import/export smoke tests are not enough. "
            "Do not stop with a completion summary until you have either "
            "run relevant validation or clearly established that no "
            "validation tool applies."
        )

    def _build_behavior_validation_prompt(
        self,
        system_prompt: str,
        messages: List[BaseMessage],
    ) -> str:
        """Return a retry prompt for stronger algorithmic validation."""
        changed_file = self._latest_mutating_file_path(messages)
        request = self._latest_human_content(messages)
        file_hint = ""
        if changed_file:
            file_hint = f" You already modified {changed_file}."
        request_hint = ""
        if request:
            request_hint = f" Validate against this request: {request[:220]}."
        return (
            f"{system_prompt}\n\n"
            "The task includes behavioral acceptance criteria. "
            f"{file_hint}{request_hint} Syntax-only checks and zero-test "
            "runs are not enough here. Re-read the changed code, then "
            "either add or strengthen a focused test and run it, or use "
            "execute_python with assertions that would fail if the core "
            "algorithm or CLI output is wrong. For rendered or terminal "
            "output, assert content invariants instead of checking exit "
            "status alone, and do not rely on unchanged smoke tests. "
            "Do not finalize until one of those checks "
            "succeeds or you can clearly explain why it cannot be run."
        )

    def _build_forced_validation_tool_prompt(
        self,
        system_prompt: str,
        messages: List[BaseMessage],
        tool_name: str,
    ) -> str:
        """Return a prompt that forces one validation tool call."""
        changed_file = self._latest_mutating_file_path(messages)
        file_hint = ""
        if changed_file:
            file_hint = f" Validate {changed_file}."
        return (
            f"{system_prompt}\n\n"
            "Your previous validation reply was not a usable tool call or "
            "user-facing verification summary. Emit exactly one commentary "
            "tool call with JSON arguments and no final answer text. "
            f"Call functions.{tool_name} now.{file_hint} "
            "If run_tests finds zero tests, that does not count as "
            "validated behavior."
        )

    def _build_forced_behavior_validation_tool_prompt(
        self,
        system_prompt: str,
        messages: List[BaseMessage],
    ) -> str:
        """Return a prompt that forces one execute_python behavior check."""
        changed_file = self._latest_mutating_file_path(messages)
        request = self._latest_human_content(messages)
        file_hint = ""
        if changed_file:
            file_hint = f" Inspect and validate {changed_file}."
        return (
            f"{system_prompt}\n\n"
            "You still owe a behavior check. Emit exactly one commentary "
            "tool call with JSON arguments and no final answer text. Call "
            "functions.execute_python now. The code must include assertions "
            "that would fail if the algorithm or terminal output is wrong, "
            "not just confirm exit code 0."
            f"{file_hint} Request: {request[:220]}."
        )

    def _should_retry_empty_response(self, response: BaseMessage) -> bool:
        """Return True when one code-mode retry should be attempted."""
        if not isinstance(response, AIMessage):
            return False
        if getattr(response, "tool_calls", None):
            return False
        return not self._has_visible_response_content(response)

    def _has_visible_response_content(self, response: AIMessage) -> bool:
        """Return True when an AI message contains user-visible content."""
        content = str(response.content or "").strip()
        if not content:
            return False
        if has_gpt_oss_markup(content):
            parsed = parse_gpt_oss_response(content)
            return bool(parsed.content)
        if self._looks_like_tool_argument_payload(content):
            return False
        return True

    def _response_needs_tool_retry(self, response: BaseMessage) -> bool:
        """Return True when a response is empty or just tool arguments."""
        if self._should_retry_empty_response(response):
            return True
        if not isinstance(response, AIMessage):
            return False
        return self._looks_like_tool_argument_payload(
            str(response.content or "").strip()
        )

    def _needs_write_execution_retry(
        self,
        task_type: str,
        response: BaseMessage,
    ) -> bool:
        """Return True when a write task stalled before any file edits."""
        return (
            task_type == "write"
            and self._used_only_non_mutating_tools()
            and (
                self._should_retry_empty_response(response)
                or self._is_repeating_non_mutating_tool_loop(response)
            )
        )

    def _needs_forced_write_tool_retry(
        self,
        task_type: str,
        response: BaseMessage,
    ) -> bool:
        """Return True when the narrowed write retry still stayed empty."""
        return (
            task_type == "write"
            and self._used_only_non_mutating_tools()
            and self._should_retry_empty_response(response)
        )

    def _needs_post_write_validation_retry(
        self,
        task_type: str,
        response: BaseMessage,
    ) -> bool:
        """Return True when a write finished without any validation step."""
        return (
            task_type == "write"
            and self._has_used_mutating_tool()
            and not self._has_used_validation_tool()
            and isinstance(response, AIMessage)
            and not getattr(response, "tool_calls", None)
        )

    def _needs_follow_up_forced_write_tool_retry(
        self,
        task_type: str,
        response: BaseMessage,
        forced_write_retry_attempted: bool,
    ) -> bool:
        """Return True when the forced write tool still emitted junk."""
        if not (
            forced_write_retry_attempted
            and task_type == "write"
            and self._used_only_non_mutating_tools()
            and isinstance(response, AIMessage)
            and not getattr(response, "tool_calls", None)
        ):
            return False

        if response.additional_kwargs.get(
            "suppressed_malformed_tool_payload"
        ):
            return True

        return (
            self._looks_like_tool_argument_payload(
                str(response.content or "").strip()
            )
        )

    def _needs_behavior_validation_retry(
        self,
        task_type: str,
        response: BaseMessage,
        messages: List[BaseMessage],
    ) -> bool:
        """Return True when behavior-heavy work only had weak validation."""
        return (
            task_type == "write"
            and self._has_used_mutating_tool()
            and self._has_used_validation_tool()
            and self._request_needs_behavior_validation(messages)
            and not self._has_meaningful_behavior_validation(messages)
            and isinstance(response, AIMessage)
            and not getattr(response, "tool_calls", None)
        )

    def _needs_forced_validation_tool_retry(
        self,
        task_type: str,
        response: BaseMessage,
        messages: List[BaseMessage],
    ) -> bool:
        """Return True when validation guidance still produced junk."""
        return (
            task_type == "write"
            and self._has_used_mutating_tool()
            and not self._has_used_validation_tool()
            and self._response_needs_tool_retry(response)
            and not getattr(response, "tool_calls", None)
            and bool(messages)
        )

    def _needs_forced_behavior_validation_tool_retry(
        self,
        task_type: str,
        response: BaseMessage,
        messages: List[BaseMessage],
    ) -> bool:
        """Return True when behavior validation still produced junk."""
        return (
            task_type == "write"
            and self._has_used_mutating_tool()
            and self._request_needs_behavior_validation(messages)
            and self._has_used_validation_tool()
            and not self._has_meaningful_behavior_validation(messages)
            and self._response_needs_tool_retry(response)
            and not getattr(response, "tool_calls", None)
        )

    def _preferred_forced_write_tool(
        self,
        messages: List[BaseMessage],
    ) -> str:
        """Return the best single write tool to force on the final retry."""
        if self._recent_read_file_paths(messages):
            return "edit_code_file"
        return "create_code_file"

    def _preferred_validation_tool(
        self,
        messages: List[BaseMessage],
    ) -> str:
        """Return the best first validation tool for the current request."""
        if self._request_needs_terminal_output_validation(messages):
            return "execute_python"
        if self._request_needs_behavior_validation(messages):
            return "run_tests"
        return "validate_code"

    def _recent_read_file_paths(
        self,
        messages: List[BaseMessage],
    ) -> List[str]:
        """Return recently inspected file paths from tool-call history."""
        file_paths: List[str] = []
        for message in reversed(messages):
            if not isinstance(message, AIMessage):
                continue
            for tool_call in getattr(message, "tool_calls", None) or []:
                if tool_call.get("name") != "read_code_file":
                    continue
                args = tool_call.get("args") or {}
                file_path = args.get("file_path")
                if not isinstance(file_path, str) or not file_path:
                    continue
                if file_path in file_paths:
                    continue
                file_paths.append(file_path)
            if len(file_paths) >= 3:
                break
        file_paths.reverse()
        return file_paths

    def _latest_mutating_file_path(
        self,
        messages: List[BaseMessage],
    ) -> str | None:
        """Return the latest file path targeted by a mutating tool call."""
        for message in reversed(messages):
            if not isinstance(message, AIMessage):
                continue
            for tool_call in reversed(getattr(message, "tool_calls", None) or []):
                if tool_call.get("name") not in MUTATING_CODE_TOOLS:
                    continue
                file_path = self._tool_call_file_path(tool_call)
                if file_path:
                    return file_path
        return None

    def _tool_call_file_path(
        self,
        tool_call: dict[str, Any],
    ) -> str | None:
        """Return the file path argument from one tool call when present."""
        args = tool_call.get("args") or {}
        for key in ("file_path", "path", "document_path"):
            value = args.get(key)
            if isinstance(value, str) and value:
                return value
        return None

    def _should_abort_repeating_tool_loop(
        self,
        task_type: str,
        response: BaseMessage,
    ) -> bool:
        """Return True when the model still loops after a targeted retry."""
        return (
            task_type == "write"
            and self._used_only_non_mutating_tools()
            and self._is_repeating_non_mutating_tool_loop(response)
        )

    def _is_repeating_non_mutating_tool_loop(
        self,
        response: BaseMessage,
    ) -> bool:
        """Return True when the model is stuck repeating safe tools."""
        tool_names = self._current_tool_call_names(response)
        if not tool_names or any(name in MUTATING_CODE_TOOLS for name in tool_names):
            return False
        if self._non_mutating_tool_streak() >= 8:
            return True
        if len(set(tool_names)) != 1:
            return False
        return self._matching_tool_streak(tool_names[0]) >= 3

    def _current_tool_call_names(self, response: BaseMessage) -> List[str]:
        """Return one list of tool names requested by an AI response."""
        if not isinstance(response, AIMessage):
            return []
        return [
            tool_call.get("name")
            for tool_call in getattr(response, "tool_calls", None) or []
            if tool_call.get("name")
        ]

    def _non_mutating_tool_streak(self) -> int:
        """Return the current streak of tool calls without file edits."""
        streak = 0
        for tool_name in reversed(self._executed_tools):
            if tool_name in MUTATING_CODE_TOOLS:
                break
            streak += 1
        return streak

    def _matching_tool_streak(self, tool_name: str) -> int:
        """Return how many times one tool name repeats at the end."""
        streak = 0
        for executed_tool in reversed(self._executed_tools):
            if executed_tool != tool_name:
                break
            streak += 1
        return streak

    def _repeating_tool_loop_reply(self) -> str:
        """Return a visible failure when the model repeats safe tools."""
        tool_names = ", ".join(dict.fromkeys(self._executed_tools))
        return (
            "The model got stuck repeating non-mutating tool calls "
            f"({tool_names}) without making file changes. No changes were "
            "applied."
        )

    def _used_only_non_mutating_tools(self) -> bool:
        """Return True when tools ran but none of them changed files."""
        return bool(self._executed_tools) and not self._has_used_mutating_tool()

    def _has_used_mutating_tool(self) -> bool:
        """Return True when a file-modifying tool already ran."""
        return bool(set(self._executed_tools) & MUTATING_CODE_TOOLS)

    def _has_used_validation_tool(self) -> bool:
        """Return True when validation or tests already ran."""
        return bool(set(self._executed_tools) & VALIDATION_CODE_TOOLS)

    def _request_needs_behavior_validation(
        self,
        messages: List[BaseMessage],
    ) -> bool:
        """Return True when the request describes algorithmic behavior."""
        request = self._latest_human_content(messages).lower()
        return any(hint in request for hint in BEHAVIOR_VALIDATION_HINTS)

    def _request_needs_terminal_output_validation(
        self,
        messages: List[BaseMessage],
    ) -> bool:
        """Return True when the request explicitly cares about output."""
        request = self._latest_human_content(messages).lower()
        return any(
            hint in request for hint in TERMINAL_OUTPUT_VALIDATION_HINTS
        )

    def _latest_human_content(self, messages: List[BaseMessage]) -> str:
        """Return the latest human request content."""
        for message in reversed(messages):
            if getattr(message, "type", "") == "human":
                return str(message.content or "").replace("\n", " ")
        return ""

    def _has_meaningful_behavior_validation(
        self,
        messages: List[BaseMessage],
    ) -> bool:
        """Return True when recent validation checks behavior, not syntax."""
        interactions = self._tool_interactions_since_last_mutation(messages)
        if self._request_needs_terminal_output_validation(messages):
            return self._has_meaningful_execute_python_validation(
                interactions,
                require_output_checks=True,
            )
        if self._has_meaningful_execute_python_validation(
            interactions,
            require_output_checks=False,
        ):
            return True
        if not self._has_changed_test_file(messages):
            return False
        return self._has_meaningful_run_tests_validation(interactions)

    def _tool_messages_since_last_mutation(
        self,
        messages: List[BaseMessage],
    ) -> List[ToolMessage]:
        """Return tool results emitted after the latest file edit."""
        recent: List[ToolMessage] = []
        for message in reversed(messages):
            if not isinstance(message, ToolMessage):
                continue
            if message.name in MUTATING_CODE_TOOLS:
                break
            recent.append(message)
        recent.reverse()
        return recent

    def _tool_interactions_since_last_mutation(
        self,
        messages: List[BaseMessage],
    ) -> List[dict[str, Any]]:
        """Return executed tool calls and results after the latest edit."""
        start_index = 0
        for index in range(len(messages) - 1, -1, -1):
            message = messages[index]
            if isinstance(message, ToolMessage):
                if message.name in MUTATING_CODE_TOOLS:
                    start_index = index + 1
                    break

        interactions: List[dict[str, Any]] = []
        pending_calls: dict[str, dict[str, Any]] = {}
        for message in messages[start_index:]:
            if isinstance(message, AIMessage):
                for tool_call in getattr(message, "tool_calls", None) or []:
                    tool_call_id = tool_call.get("id")
                    if isinstance(tool_call_id, str) and tool_call_id:
                        pending_calls[tool_call_id] = tool_call
                continue
            if not isinstance(message, ToolMessage):
                continue
            tool_call = pending_calls.get(message.tool_call_id or "", {})
            interactions.append(
                {
                    "name": message.name,
                    "args": tool_call.get("args") or {},
                    "content": str(message.content or ""),
                    "tool_call_id": message.tool_call_id,
                }
            )
        return interactions

    def _has_meaningful_run_tests_validation(
        self,
        interactions: List[dict[str, Any]],
    ) -> bool:
        """Return True when focused tests ran after test edits."""
        return any(
            interaction.get("name") == "run_tests"
            and self._run_tests_output_is_meaningful(
                str(interaction.get("content") or "")
            )
            for interaction in interactions
        )

    def _has_meaningful_execute_python_validation(
        self,
        interactions: List[dict[str, Any]],
        require_output_checks: bool,
    ) -> bool:
        """Return True when execute_python contains real assertions."""
        for interaction in interactions:
            if interaction.get("name") != "execute_python":
                continue
            content = str(interaction.get("content") or "")
            if not self._execute_python_output_is_meaningful(content):
                continue
            args = interaction.get("args") or {}
            code = str(args.get("code") or "")
            if self._execute_python_code_is_meaningful(
                code,
                require_output_checks,
            ):
                return True
        return False

    def _execute_python_code_is_meaningful(
        self,
        code: str,
        require_output_checks: bool,
    ) -> bool:
        """Return True when execute_python code checks behavior."""
        if not any(
            re.search(pattern, code) for pattern in ASSERTION_SIGNAL_PATTERNS
        ):
            return False
        if not require_output_checks:
            return True
        return any(
            re.search(pattern, code)
            for pattern in OUTPUT_CAPTURE_SIGNAL_PATTERNS
        )

    def _run_tests_output_is_meaningful(self, content: str) -> bool:
        """Return True when test output shows real passing coverage."""
        if "No tests found" in content:
            return False
        total = self._extract_result_count(content, "Total")
        failed = self._extract_result_count(content, "Failed") or 0
        errors = self._extract_result_count(content, "Errors") or 0
        if total is None or total <= 0:
            return False
        return failed == 0 and errors == 0

    def _execute_python_output_is_meaningful(self, content: str) -> bool:
        """Return True when execute_python finished without an error."""
        return "Exit code: 0" in content and "Error:" not in content

    def _has_changed_test_file(
        self,
        messages: List[BaseMessage],
    ) -> bool:
        """Return True when this request changed at least one test file."""
        for message in messages:
            if not isinstance(message, AIMessage):
                continue
            for tool_call in getattr(message, "tool_calls", None) or []:
                if tool_call.get("name") not in MUTATING_CODE_TOOLS:
                    continue
                file_path = self._tool_call_file_path(tool_call)
                if file_path and self._is_test_file_path(file_path):
                    return True
        return False

    def _is_test_file_path(self, file_path: str) -> bool:
        """Return True when a path looks like a test module."""
        normalized = file_path.replace("\\", "/")
        file_name = normalized.rsplit("/", 1)[-1]
        return (
            "/tests/" in f"/{normalized}"
            or file_name.startswith("test_")
            or file_name.endswith("_test.py")
        )

    def _extract_result_count(
        self,
        content: str,
        label: str,
    ) -> int | None:
        """Return one integer count from tool output when present."""
        match = re.search(rf"{re.escape(label)}:\s*(\d+)", content)
        if not match:
            return None
        return int(match.group(1))

    def _looks_like_tool_argument_payload(self, content: str) -> bool:
        """Return True when the response looks like raw tool arguments."""
        return looks_like_tool_argument_payload(content)

    def _only_read_only_tools_used(self) -> bool:
        """Return True when only non-mutating code tools ran so far."""
        if not self._executed_tools:
            return False
        normalized_tools = set(self._executed_tools)
        if self._has_used_mutating_tool():
            return False
        return normalized_tools <= READ_ONLY_CODE_TOOLS

    def _execute_tools(self, state: CodeState) -> dict:
        """Run code tools while recording the executed tool names."""
        messages = state.get("messages", [])
        last_message = messages[-1] if messages else None
        tool_calls = getattr(last_message, "tool_calls", None) or []
        tool_names = [
            tool_call.get("name")
            for tool_call in tool_calls
            if tool_call.get("name")
        ]
        if tool_names:
            logger.info(
                "Executing code-agent tools: %s",
                ", ".join(tool_names),
            )
            self._executed_tools.extend(tool_names)
            if self._tool_event_callback:
                self._tool_event_callback(tool_names)

        tool_node = ToolNode(self._tools)
        result = tool_node.invoke(state)
        self._record_tool_result_summaries(result)
        return result

    def _record_tool_result_summaries(self, result: dict[str, Any]) -> None:
        """Capture one-line summaries from the latest tool execution."""
        if not isinstance(result, dict):
            return
        for message in result.get("messages") or []:
            if not isinstance(message, ToolMessage):
                continue
            summary = self._first_nonempty_tool_line(
                str(message.content or "")
            )
            if summary:
                self._tool_result_summaries.append(
                    (str(message.name or ""), summary)
                )

    def _first_nonempty_tool_line(self, content: str) -> str:
        """Return the first non-empty line from a tool result."""
        for line in (content or "").splitlines():
            stripped = line.strip()
            if stripped:
                return stripped[:200]
        return ""

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
            graph.add_node("tools", self._execute_tools)

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
