"""Tests for the specialized code agent."""

from types import SimpleNamespace
from unittest.mock import patch

from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)

from airunner.components.llm.agents.code_agent import CodeAgent
from airunner.components.llm.core.tool_registry import ToolCategory


def _dummy_tool() -> str:
    """Return a dummy tool value."""
    return "ok"


def _workflow_tool() -> str:
    """Return a dummy workflow tool value."""
    return "workflow"


class FakeCodeChatModel:
    """Minimal chat model for CodeAgent unit tests."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []
        self.bound_tools = None
        self.bound_tool_choice = None
        self.n_ctx = None

    def bind_tools(self, tools, tool_choice=None):
        self.bound_tools = list(tools)
        self.bound_tool_choice = tool_choice
        return self

    def invoke(self, messages):
        self.calls.append(messages)
        return self._responses[len(self.calls) - 1]


def test_code_agent_uses_single_system_prompt_with_tool_guidance():
    """CodeAgent should send one consolidated prompt to the model."""
    chat_model = FakeCodeChatModel([AIMessage(content="done")])

    with patch.object(CodeAgent, "_get_code_tools", return_value=[_dummy_tool]):
        agent = CodeAgent(chat_model=chat_model, system_prompt="Custom prompt")

    state = {
        "messages": [HumanMessage(content="create main.py")],
        "programming_language": "python",
        "task_type": "write",
        "execution_context": {},
    }
    agent._call_model(state)

    sent_messages = chat_model.calls[0]
    system_messages = [
        message for message in sent_messages if isinstance(message, SystemMessage)
    ]

    assert len(system_messages) == 1
    assert "Current task: writing new code in python." in (
        system_messages[0].content
    )
    assert "Use the available code tools directly" in (
        system_messages[0].content
    )
    assert "add or strengthen focused tests" in (
        system_messages[0].content
    )
    assert "Syntax-only checks such as validate_code" in (
        system_messages[0].content
    )
    assert "not just a successful exit code" in (
        system_messages[0].content
    )
    assert "Existing smoke tests that only verify imports or exports" in (
        system_messages[0].content
    )
    assert "Treat the user's request as the acceptance criteria" in (
        system_messages[0].content
    )


def test_code_agent_binds_workflow_tools_with_code_tools():
    """CodeAgent should expose workflow helpers in code mode."""
    chat_model = FakeCodeChatModel([])
    code_tool = SimpleNamespace(name="create_code_file", func=_dummy_tool)
    workflow_tool = SimpleNamespace(
        name="start_workflow",
        func=_workflow_tool,
    )

    with patch(
        "airunner.components.llm.agents.code_agent.ToolRegistry"
        ".get_by_category",
        side_effect=[[code_tool], [workflow_tool]],
    ) as get_by_category:
        CodeAgent(chat_model=chat_model, system_prompt="Custom prompt")

    assert get_by_category.call_args_list[0].args == (ToolCategory.CODE,)
    assert get_by_category.call_args_list[1].args == (
        ToolCategory.WORKFLOW,
    )
    assert chat_model.bound_tools == [_dummy_tool, _workflow_tool]


def test_code_agent_retries_empty_response_once():
    """CodeAgent should retry once when the model returns an empty turn."""
    chat_model = FakeCodeChatModel(
        [
            AIMessage(
                content="",
                additional_kwargs={"thinking_content": "Need to inspect."},
            ),
            AIMessage(content="Created the requested file."),
        ]
    )

    with patch.object(CodeAgent, "_get_code_tools", return_value=[_dummy_tool]):
        agent = CodeAgent(chat_model=chat_model, system_prompt="Custom prompt")

    state = {
        "messages": [HumanMessage(content="create main.py")],
        "programming_language": "python",
        "task_type": "write",
        "execution_context": {},
    }
    result = agent._call_model(state)

    assert len(chat_model.calls) == 2
    retry_system = chat_model.calls[1][0]
    assert isinstance(retry_system, SystemMessage)
    assert "previous attempt produced no visible answer" in (
        retry_system.content
    )
    assert result["messages"][0].content == "Created the requested file."


def test_code_agent_retries_analysis_only_harmony_response():
    """CodeAgent should retry when GPT-OSS only returns hidden analysis."""
    chat_model = FakeCodeChatModel(
        [
            AIMessage(
                content=(
                    "<|channel|>analysis<|message|>Need to inspect."
                    "<|return|>"
                )
            ),
            AIMessage(content="Created the requested file."),
        ]
    )

    with patch.object(CodeAgent, "_get_code_tools", return_value=[_dummy_tool]):
        agent = CodeAgent(chat_model=chat_model, system_prompt="Custom prompt")

    state = {
        "messages": [HumanMessage(content="create main.py")],
        "programming_language": "python",
        "task_type": "write",
        "execution_context": {},
    }
    result = agent._call_model(state)

    assert len(chat_model.calls) == 2
    assert result["messages"][0].content == "Created the requested file."


def test_code_agent_synthesizes_visible_reply_after_tool_only_finish():
    """CodeAgent should surface tool results when the final turn stays hidden."""
    chat_model = FakeCodeChatModel(
        [
            AIMessage(
                content=(
                    "<|channel|>analysis<|message|>Need a final answer."
                    "<|return|>"
                )
            ),
            AIMessage(
                content=(
                    "<|channel|>analysis<|message|>Still thinking."
                    "<|return|>"
                )
            ),
            AIMessage(
                content=(
                    "<|channel|>analysis<|message|>Still no visible "
                    "validation result.<|return|>"
                )
            ),
            AIMessage(
                content=(
                    "<|channel|>analysis<|message|>Still no usable "
                    "validation tool call.<|return|>"
                )
            ),
        ]
    )

    with patch.object(CodeAgent, "_get_code_tools", return_value=[_dummy_tool]):
        agent = CodeAgent(chat_model=chat_model, system_prompt="Custom prompt")

    agent._executed_tools = ["create_code_file"]
    state = {
        "messages": [
            HumanMessage(content="create main.py"),
            ToolMessage(
                content="✓ Created file: maze_generator.py",
                tool_call_id="tool-1",
                name="create_code_file",
            ),
        ],
        "programming_language": "python",
        "task_type": "write",
        "execution_context": {},
    }
    result = agent._call_model(state)

    assert len(chat_model.calls) == 4
    assert "create_code_file" in result["messages"][0].content
    assert "Created file: maze_generator.py" in result["messages"][0].content
    assert result["messages"][0].additional_kwargs["executed_tools"] == [
        "create_code_file"
    ]


def test_code_agent_synthesized_reply_handles_mutating_tool_history():
    """CodeAgent should summarize the changed file without crashing."""
    chat_model = FakeCodeChatModel(
        [
            AIMessage(
                content=(
                    "<|channel|>analysis<|message|>Need a final answer."
                    "<|return|>"
                )
            ),
            AIMessage(
                content=(
                    "<|channel|>analysis<|message|>Still thinking."
                    "<|return|>"
                )
            ),
            AIMessage(
                content=(
                    "<|channel|>analysis<|message|>Still no visible "
                    "validation result.<|return|>"
                )
            ),
            AIMessage(
                content=(
                    "<|channel|>analysis<|message|>Still no usable "
                    "validation tool call.<|return|>"
                )
            ),
        ]
    )

    with patch.object(CodeAgent, "_get_code_tools", return_value=[_dummy_tool]):
        agent = CodeAgent(chat_model=chat_model, system_prompt="Custom prompt")

    agent._executed_tools = ["edit_code_file"]
    state = {
        "messages": [
            HumanMessage(content="implement the maze generator"),
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "id": "tool-1",
                        "name": "edit_code_file",
                        "args": {"file_path": "src/mazes/__main__.py"},
                        "type": "tool_call",
                    }
                ],
            ),
            ToolMessage(
                content="✓ Edited file: src/mazes/__main__.py",
                tool_call_id="tool-1",
                name="edit_code_file",
            ),
        ],
        "programming_language": "python",
        "task_type": "write",
        "execution_context": {},
    }

    result = agent._call_model(state)

    assert "Modified src/mazes/__main__.py" in result["messages"][0].content
    assert "Edited file: src/mazes/__main__.py" in result["messages"][0].content


def test_code_agent_retries_after_read_only_tools_in_write_task():
    """CodeAgent should force a write-oriented retry after exploration."""
    chat_model = FakeCodeChatModel(
        [
            AIMessage(
                content=(
                    "<|channel|>analysis<|message|>Need more inspection."
                    "<|return|>"
                )
            ),
            AIMessage(
                content=(
                    "<|channel|>analysis<|message|>Still planning."
                    "<|return|>"
                )
            ),
            AIMessage(content="Created maze_generator.py."),
        ]
    )

    with patch.object(CodeAgent, "_get_code_tools", return_value=[_dummy_tool]):
        agent = CodeAgent(chat_model=chat_model, system_prompt="Custom prompt")

    agent._executed_tools = ["list_workspace_files", "read_code_file"]
    state = {
        "messages": [HumanMessage(content="create main.py")],
        "programming_language": "python",
        "task_type": "write",
        "execution_context": {},
    }
    result = agent._call_model(state)

    assert len(chat_model.calls) == 3
    assert "only used read-only tools" in chat_model.calls[1][0].content
    assert "inspection is complete" in chat_model.calls[2][0].content
    assert result["messages"][0].content == "Created maze_generator.py."


def test_code_agent_reports_no_file_changes_for_read_only_finish():
    """CodeAgent should not imply writes when only inspection happened."""
    chat_model = FakeCodeChatModel(
        [
            AIMessage(
                content=(
                    "<|channel|>analysis<|message|>Need a final answer."
                    "<|return|>"
                )
            ),
            AIMessage(
                content=(
                    "<|channel|>analysis<|message|>Still thinking."
                    "<|return|>"
                )
            ),
            AIMessage(
                content=(
                    "<|channel|>analysis<|message|>No visible reply."
                    "<|return|>"
                )
            ),
            AIMessage(
                content=(
                    "<|channel|>analysis<|message|>Still no tool call."
                    "<|return|>"
                )
            ),
        ]
    )

    with patch.object(CodeAgent, "_get_code_tools", return_value=[_dummy_tool]):
        agent = CodeAgent(chat_model=chat_model, system_prompt="Custom prompt")

    agent._executed_tools = ["list_workspace_files", "read_code_file"]
    state = {
        "messages": [
            HumanMessage(content="create main.py"),
            ToolMessage(
                content='"""Smoke tests for mazes."""',
                tool_call_id="tool-1",
                name="read_code_file",
            ),
        ],
        "programming_language": "python",
        "task_type": "write",
        "execution_context": {},
    }
    result = agent._call_model(state)

    assert "read-only tools" in result["messages"][0].content
    assert "no file modifications were applied" in result["messages"][0].content


def test_code_agent_retries_after_non_mutating_tools_in_write_task():
    """CodeAgent should keep pushing until a write tool runs."""
    chat_model = FakeCodeChatModel(
        [
            AIMessage(
                content=(
                    "<|channel|>analysis<|message|>Need workflow setup."
                    "<|return|>"
                )
            ),
            AIMessage(
                content=(
                    "<|channel|>analysis<|message|>Still planning."
                    "<|return|>"
                )
            ),
            AIMessage(content="Edited src/mazes/__main__.py."),
        ]
    )

    with patch.object(CodeAgent, "_get_code_tools", return_value=[_dummy_tool]):
        agent = CodeAgent(chat_model=chat_model, system_prompt="Custom prompt")

    agent._executed_tools = ["start_workflow", "transition_phase"]
    state = {
        "messages": [HumanMessage(content="create main.py")],
        "programming_language": "python",
        "task_type": "write",
        "execution_context": {},
    }
    result = agent._call_model(state)

    assert len(chat_model.calls) == 3
    assert "none of them modified files" in chat_model.calls[1][0].content
    assert "non-mutating tools" in chat_model.calls[2][0].content
    assert result["messages"][0].content == "Edited src/mazes/__main__.py."


def test_code_agent_execution_retry_uses_narrowed_write_tools():
    """Execution retry should narrow the tool set to write-capable tools."""
    chat_model = FakeCodeChatModel(
        [
            AIMessage(
                content=(
                    "<|channel|>analysis<|message|>Need more inspection."
                    "<|return|>"
                )
            ),
            AIMessage(
                content=(
                    "<|channel|>analysis<|message|>Still planning."
                    "<|return|>"
                )
            ),
        ]
    )

    with patch.object(CodeAgent, "_get_code_tools", return_value=[_dummy_tool]):
        agent = CodeAgent(chat_model=chat_model, system_prompt="Custom prompt")

    agent._executed_tools = ["list_workspace_files", "read_code_file"]
    state = {
        "messages": [HumanMessage(content="create main.py")],
        "programming_language": "python",
        "task_type": "write",
        "execution_context": {},
    }

    with patch.object(
        agent,
        "_invoke_model_with_tool_subset",
        return_value=AIMessage(content="Created maze_generator.py."),
    ) as subset_invoke:
        result = agent._call_model(state)

    subset_args = subset_invoke.call_args.args
    assert subset_args[2] == {
        "create_code_file",
        "edit_code_file",
        "replace_in_document",
        "edit_document_lines",
        "insert_document_lines",
        "save_document",
    }
    assert result["messages"][0].content == "Created maze_generator.py."


def test_code_agent_forces_single_write_tool_after_empty_narrowed_retry():
    """CodeAgent should force one write tool if narrowed retry stays empty."""
    chat_model = FakeCodeChatModel([])

    with patch.object(CodeAgent, "_get_code_tools", return_value=[_dummy_tool]):
        agent = CodeAgent(chat_model=chat_model, system_prompt="Custom prompt")

    agent._executed_tools = ["list_workspace_files", "read_code_file"]
    state = {
        "messages": [
            HumanMessage(content="create main.py"),
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "id": "tool-1",
                        "name": "read_code_file",
                        "args": {"file_path": "src/mazes/__main__.py"},
                    }
                ],
            ),
        ],
        "programming_language": "python",
        "task_type": "write",
        "execution_context": {},
    }

    with patch.object(
        agent,
        "_invoke_model",
        side_effect=[
            AIMessage(
                content=(
                    "<|channel|>analysis<|message|>Need more inspection."
                    "<|return|>"
                )
            ),
            AIMessage(
                content=(
                    "<|channel|>analysis<|message|>Still planning."
                    "<|return|>"
                )
            ),
        ],
    ), patch.object(
        agent,
        "_invoke_model_with_tool_subset",
        side_effect=[
            AIMessage(
                content=(
                    "<|channel|>analysis<|message|>No tool call yet."
                    "<|return|>"
                )
            ),
            AIMessage(content="Edited src/mazes/__main__.py."),
        ],
    ) as subset_invoke:
        result = agent._call_model(state)

    assert subset_invoke.call_args_list[0].args[2] == {
        "create_code_file",
        "edit_code_file",
        "replace_in_document",
        "edit_document_lines",
        "insert_document_lines",
        "save_document",
    }
    assert subset_invoke.call_args_list[1].args[2] == {"edit_code_file"}
    assert "src/mazes/__main__.py" in subset_invoke.call_args_list[1].args[1]
    assert "source of truth for this edit" in subset_invoke.call_args_list[1].args[1]
    assert result["messages"][0].content == "Edited src/mazes/__main__.py."


def test_code_agent_requires_post_write_validation_after_edit():
    """CodeAgent should require validation after finishing an edit."""
    chat_model = FakeCodeChatModel([])

    with patch.object(CodeAgent, "_get_code_tools", return_value=[_dummy_tool]):
        agent = CodeAgent(chat_model=chat_model, system_prompt="Custom prompt")

    agent._executed_tools = ["edit_code_file"]
    state = {
        "messages": [
            HumanMessage(
                content=(
                    "Create a maze generator using the perfect tree "
                    "algorithm and print it from __main__."
                )
            ),
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "id": "tool-1",
                        "name": "edit_code_file",
                        "args": {"file_path": "src/mazes/__main__.py"},
                    }
                ],
            ),
            ToolMessage(
                content="✓ Edited file: src/mazes/__main__.py",
                tool_call_id="tool-1",
                name="edit_code_file",
            ),
        ],
        "programming_language": "python",
        "task_type": "write",
        "execution_context": {},
    }

    with patch.object(
        agent,
        "_invoke_model",
        return_value=AIMessage(content="Implemented the maze generator."),
    ), patch.object(
        agent,
        "_invoke_model_with_tool_subset",
        return_value=AIMessage(content="Added focused tests and ran them."),
    ) as subset_invoke:
        result = agent._call_model(state)

    assert subset_invoke.call_count == 1
    assert subset_invoke.call_args.args[2] == {
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
    validation_prompt = subset_invoke.call_args.args[1]
    assert "modified src/mazes/__main__.py" in validation_prompt
    assert "tests are missing or too weak" in validation_prompt
    assert "terminal-output requirements" in validation_prompt
    assert result["messages"][0].content == "Added focused tests and ran them."


def test_code_agent_retries_malformed_forced_write_tool_payload():
    """CodeAgent should retry a forced write tool after raw JSON junk."""
    chat_model = FakeCodeChatModel([])

    with patch.object(CodeAgent, "_get_code_tools", return_value=[_dummy_tool]):
        agent = CodeAgent(chat_model=chat_model, system_prompt="Custom prompt")

    agent._executed_tools = ["list_workspace_files", "read_code_file"]
    state = {
        "messages": [
            HumanMessage(
                content="Create src/mazes/__main__.py and print the maze."
            )
        ],
        "programming_language": "python",
        "task_type": "write",
        "execution_context": {},
    }

    with patch.object(
        agent,
        "_invoke_model",
        return_value=AIMessage(content=""),
    ), patch.object(
        agent,
        "_preferred_forced_write_tool",
        return_value="edit_code_file",
    ), patch.object(
        agent,
        "_invoke_model_with_tool_subset",
        side_effect=[
            AIMessage(content=""),
            AIMessage(
                content=(
                    '{"file_path":"src/mazes/__main__.py",'
                    '"content":"print'
                )
            ),
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "id": "tool-3",
                        "name": "edit_code_file",
                        "args": {"file_path": "src/mazes/__main__.py"},
                    }
                ],
            ),
        ],
    ) as subset_invoke:
        result = agent._call_model(state)

    assert subset_invoke.call_count == 3
    assert subset_invoke.call_args_list[1].args[2] == {"edit_code_file"}
    assert subset_invoke.call_args_list[2].args[2] == {"edit_code_file"}
    assert result["messages"][0].tool_calls[0]["name"] == "edit_code_file"


def test_code_agent_requires_behavior_validation_after_syntax_check():
    """CodeAgent should reject syntax-only validation for algorithms."""
    chat_model = FakeCodeChatModel([])

    with patch.object(CodeAgent, "_get_code_tools", return_value=[_dummy_tool]):
        agent = CodeAgent(chat_model=chat_model, system_prompt="Custom prompt")

    agent._executed_tools = ["edit_code_file", "validate_code"]
    state = {
        "messages": [
            HumanMessage(
                content=(
                    "Create a maze generator using the perfect tree "
                    "algorithm and print it from __main__."
                )
            ),
            ToolMessage(
                content="✓ Edited file: src/mazes/__main__.py",
                tool_call_id="tool-1",
                name="edit_code_file",
            ),
            ToolMessage(
                content="✓ src/mazes/__main__.py is valid",
                tool_call_id="tool-2",
                name="validate_code",
            ),
        ],
        "programming_language": "python",
        "task_type": "write",
        "execution_context": {},
    }

    with patch.object(
        agent,
        "_invoke_model",
        return_value=AIMessage(content="Done."),
    ), patch.object(
        agent,
        "_invoke_model_with_tool_subset",
        return_value=AIMessage(content="Added focused tests and ran them."),
    ) as subset_invoke:
        result = agent._call_model(state)

    assert subset_invoke.call_count == 1
    assert subset_invoke.call_args.args[2] == {
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
    behavior_prompt = subset_invoke.call_args.args[1]
    assert "zero-test runs are not enough" in behavior_prompt
    assert "perfect tree algorithm" in behavior_prompt
    assert result["messages"][0].content == "Added focused tests and ran them."


def test_code_agent_forces_validation_tool_after_json_stub_reply():
    """CodeAgent should not surface raw validation arg JSON as final text."""
    chat_model = FakeCodeChatModel([])

    with patch.object(CodeAgent, "_get_code_tools", return_value=[_dummy_tool]):
        agent = CodeAgent(chat_model=chat_model, system_prompt="Custom prompt")

    agent._executed_tools = ["edit_code_file"]
    state = {
        "messages": [
            HumanMessage(
                content=(
                    "Create a maze generator using the perfect tree "
                    "algorithm and print it from __main__."
                )
            ),
            ToolMessage(
                content="✓ Edited file: src/mazes/__main__.py",
                tool_call_id="tool-1",
                name="edit_code_file",
            ),
        ],
        "programming_language": "python",
        "task_type": "write",
        "execution_context": {},
    }

    with patch.object(
        agent,
        "_invoke_model",
        return_value=AIMessage(content="Implemented the maze generator."),
    ), patch.object(
        agent,
        "_invoke_model_with_tool_subset",
        side_effect=[
            AIMessage(content='{"file_path": "tests/test_mazes.py"}'),
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "id": "tool-2",
                        "name": "run_tests",
                        "args": {"file_path": "src/mazes/__main__.py"},
                    }
                ],
            ),
        ],
    ) as subset_invoke:
        result = agent._call_model(state)

    assert subset_invoke.call_count == 2
    assert subset_invoke.call_args_list[1].args[2] == {"execute_python"}
    forced_prompt = subset_invoke.call_args_list[1].args[1]
    assert "not a usable tool call" in forced_prompt
    assert result["messages"][0].tool_calls[0]["name"] == "run_tests"


def test_code_agent_forces_behavior_validation_tool_after_json_stub_reply():
    """CodeAgent should force execute_python after weak behavior checks."""
    chat_model = FakeCodeChatModel([])

    with patch.object(CodeAgent, "_get_code_tools", return_value=[_dummy_tool]):
        agent = CodeAgent(chat_model=chat_model, system_prompt="Custom prompt")

    agent._executed_tools = ["edit_code_file", "run_tests"]
    state = {
        "messages": [
            HumanMessage(
                content=(
                    "Create a maze generator using the perfect tree "
                    "algorithm and print it from __main__."
                )
            ),
            ToolMessage(
                content="✓ Edited file: src/mazes/__main__.py",
                tool_call_id="tool-1",
                name="edit_code_file",
            ),
            ToolMessage(
                content=(
                    "Tests for src/mazes/__main__.py:\n"
                    "  Total: 0\n"
                    "  Passed: 0\n"
                    "  Failed: 0\n"
                    "  Duration: 0.00s"
                ),
                tool_call_id="tool-2",
                name="run_tests",
            ),
        ],
        "programming_language": "python",
        "task_type": "write",
        "execution_context": {},
    }

    with patch.object(
        agent,
        "_invoke_model",
        return_value=AIMessage(content="Done."),
    ), patch.object(
        agent,
        "_invoke_model_with_tool_subset",
        side_effect=[
            AIMessage(content='{"code": "print(1)"}'),
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "id": "tool-3",
                        "name": "execute_python",
                        "args": {"code": "assert True"},
                    }
                ],
            ),
        ],
    ) as subset_invoke:
        result = agent._call_model(state)

    assert subset_invoke.call_count == 2
    assert subset_invoke.call_args_list[0].args[2] == {
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
    assert subset_invoke.call_args_list[1].args[2] == {"execute_python"}
    forced_prompt = subset_invoke.call_args_list[1].args[1]
    assert "not just confirm exit code 0" in forced_prompt
    assert result["messages"][0].tool_calls[0]["name"] == "execute_python"


def test_code_agent_requires_behavior_validation_after_zero_tests():
    """CodeAgent should reject zero discovered tests for CLI behavior."""
    chat_model = FakeCodeChatModel([])

    with patch.object(CodeAgent, "_get_code_tools", return_value=[_dummy_tool]):
        agent = CodeAgent(chat_model=chat_model, system_prompt="Custom prompt")

    agent._executed_tools = ["edit_code_file", "run_tests"]
    state = {
        "messages": [
            HumanMessage(
                content=(
                    "Create a maze generator using the perfect tree "
                    "algorithm and print it from __main__."
                )
            ),
            ToolMessage(
                content="✓ Edited file: src/mazes/__main__.py",
                tool_call_id="tool-1",
                name="edit_code_file",
            ),
            ToolMessage(
                content=(
                    "Tests for src/mazes/__main__.py:\n"
                    "  Total: 0\n"
                    "  Passed: 0\n"
                    "  Failed: 0\n"
                    "  Duration: 0.00s"
                ),
                tool_call_id="tool-2",
                name="run_tests",
            ),
        ],
        "programming_language": "python",
        "task_type": "write",
        "execution_context": {},
    }

    with patch.object(
        agent,
        "_invoke_model",
        return_value=AIMessage(content="Done."),
    ), patch.object(
        agent,
        "_invoke_model_with_tool_subset",
        return_value=AIMessage(content="Ran a targeted behavior check."),
    ) as subset_invoke:
        result = agent._call_model(state)

    assert subset_invoke.call_count == 1
    behavior_prompt = subset_invoke.call_args.args[1]
    assert "zero-test runs are not enough" in behavior_prompt
    assert result["messages"][0].content == "Ran a targeted behavior check."


def test_code_agent_requires_behavior_validation_after_unchanged_smoke_tests():
    """CodeAgent should not accept untouched smoke tests for CLI output."""
    chat_model = FakeCodeChatModel([])

    with patch.object(CodeAgent, "_get_code_tools", return_value=[_dummy_tool]):
        agent = CodeAgent(chat_model=chat_model, system_prompt="Custom prompt")

    agent._executed_tools = ["edit_code_file", "run_tests"]
    state = {
        "messages": [
            HumanMessage(
                content=(
                    "Create a maze generator using the perfect tree "
                    "algorithm and print it from __main__."
                )
            ),
            ToolMessage(
                content="✓ Edited file: src/mazes/__main__.py",
                tool_call_id="tool-1",
                name="edit_code_file",
            ),
            ToolMessage(
                content=(
                    "Tests for tests/test_mazes.py:\n"
                    "  Total: 1\n"
                    "  Passed: 1\n"
                    "  Failed: 0\n"
                    "  Duration: 0.02s"
                ),
                tool_call_id="tool-2",
                name="run_tests",
            ),
        ],
        "programming_language": "python",
        "task_type": "write",
        "execution_context": {},
    }

    with patch.object(
        agent,
        "_invoke_model",
        return_value=AIMessage(content="Done."),
    ), patch.object(
        agent,
        "_invoke_model_with_tool_subset",
        return_value=AIMessage(content="Ran stronger CLI validation."),
    ) as subset_invoke:
        result = agent._call_model(state)

    assert subset_invoke.call_count == 1
    assert subset_invoke.call_args.args[2] == {
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
    assert result["messages"][0].content == "Ran stronger CLI validation."


def test_code_agent_requires_behavior_validation_after_execute_python_without_asserts():
    """CodeAgent should not accept execute_python that only runs code."""
    chat_model = FakeCodeChatModel([])

    with patch.object(CodeAgent, "_get_code_tools", return_value=[_dummy_tool]):
        agent = CodeAgent(chat_model=chat_model, system_prompt="Custom prompt")

    agent._executed_tools = ["edit_code_file", "execute_python"]
    state = {
        "messages": [
            HumanMessage(
                content=(
                    "Create a maze generator using the perfect tree "
                    "algorithm and print it from __main__."
                )
            ),
            ToolMessage(
                content="✓ Edited file: src/mazes/__main__.py",
                tool_call_id="tool-1",
                name="edit_code_file",
            ),
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "id": "tool-2",
                        "name": "execute_python",
                        "args": {"code": "from mazes.__main__ import main\nmain()"},
                    }
                ],
            ),
            ToolMessage(
                content="STDOUT:\nmaze\n\nExit code: 0",
                tool_call_id="tool-2",
                name="execute_python",
            ),
        ],
        "programming_language": "python",
        "task_type": "write",
        "execution_context": {},
    }

    with patch.object(
        agent,
        "_invoke_model",
        return_value=AIMessage(content="Done."),
    ), patch.object(
        agent,
        "_invoke_model_with_tool_subset",
        return_value=AIMessage(content="Ran stronger behavior assertions."),
    ) as subset_invoke:
        result = agent._call_model(state)

    assert subset_invoke.call_count == 1
    assert result["messages"][0].content == "Ran stronger behavior assertions."


def test_code_agent_accepts_asserting_execute_python_validation():
    """CodeAgent should accept assertion-based CLI validation."""
    chat_model = FakeCodeChatModel([])

    with patch.object(CodeAgent, "_get_code_tools", return_value=[_dummy_tool]):
        agent = CodeAgent(chat_model=chat_model, system_prompt="Custom prompt")

    agent._executed_tools = ["edit_code_file", "execute_python"]
    state = {
        "messages": [
            HumanMessage(
                content=(
                    "Create a maze generator using the perfect tree "
                    "algorithm and print it from __main__."
                )
            ),
            ToolMessage(
                content="✓ Edited file: src/mazes/__main__.py",
                tool_call_id="tool-1",
                name="edit_code_file",
            ),
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "id": "tool-2",
                        "name": "execute_python",
                        "args": {
                            "code": (
                                "import io\n"
                                "from contextlib import redirect_stdout\n"
                                "from mazes.__main__ import main\n"
                                "buffer = io.StringIO()\n"
                                "with redirect_stdout(buffer):\n"
                                "    main()\n"
                                "output = buffer.getvalue()\n"
                                "assert output.strip()\n"
                                "assert \"#\" in output or \"█\" in output\n"
                            )
                        },
                    }
                ],
            ),
            ToolMessage(
                content="Exit code: 0",
                tool_call_id="tool-2",
                name="execute_python",
            ),
        ],
        "programming_language": "python",
        "task_type": "write",
        "execution_context": {},
    }

    with patch.object(
        agent,
        "_invoke_model",
        return_value=AIMessage(content="Done."),
    ), patch.object(agent, "_invoke_model_with_tool_subset") as subset_invoke:
        result = agent._call_model(state)

    subset_invoke.assert_not_called()
    assert result["messages"][0].content == "Done."


def test_code_agent_skips_validation_retry_after_tests_ran():
    """CodeAgent should not force another validation pass after tests."""
    chat_model = FakeCodeChatModel([])

    with patch.object(CodeAgent, "_get_code_tools", return_value=[_dummy_tool]):
        agent = CodeAgent(chat_model=chat_model, system_prompt="Custom prompt")

    agent._executed_tools = ["edit_code_file", "run_tests"]
    state = {
        "messages": [HumanMessage(content="create main.py")],
        "programming_language": "python",
        "task_type": "write",
        "execution_context": {},
    }

    with patch.object(
        agent,
        "_invoke_model",
        return_value=AIMessage(content="Done."),
    ), patch.object(agent, "_invoke_model_with_tool_subset") as subset_invoke:
        result = agent._call_model(state)

    subset_invoke.assert_not_called()
    assert result["messages"][0].content == "Done."


def test_code_agent_uses_tool_choice_for_single_tool_retry():
    """CodeAgent should pass a specific tool choice for one-tool retries."""
    chat_model = FakeCodeChatModel([AIMessage(content="Edited main.py")])

    with patch.object(CodeAgent, "_get_code_tools", return_value=[_dummy_tool]):
        agent = CodeAgent(chat_model=chat_model, system_prompt="Custom prompt")

    agent._invoke_model_with_tool_subset(
        [HumanMessage(content="edit main.py")],
        "Custom prompt",
        {"_dummy_tool"},
    )

    assert chat_model.bound_tool_choice == "_dummy_tool"


def test_code_agent_records_executed_tools_via_callback():
    """CodeAgent should record tool names from specialized subgraph runs."""
    callback_calls = []
    chat_model = FakeCodeChatModel([AIMessage(content="done")])

    with patch.object(CodeAgent, "_get_code_tools", return_value=[_dummy_tool]):
        agent = CodeAgent(
            chat_model=chat_model,
            system_prompt="Custom prompt",
            tool_event_callback=callback_calls.extend,
        )

    with patch(
        "airunner.components.llm.agents.code_agent.ToolNode"
    ) as mock_tool_node:
        mock_tool_node.return_value.invoke.return_value = {"messages": []}
        state = {
            "messages": [
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "id": "tool-1",
                            "name": "create_code_file",
                            "args": {},
                        }
                    ],
                )
            ]
        }

        agent._execute_tools(state)

    assert agent._executed_tools == ["create_code_file"]
    assert callback_calls == ["create_code_file"]


def test_code_agent_trims_history_to_model_context():
    """CodeAgent should trim long history before invoking small-context models."""
    chat_model = FakeCodeChatModel([AIMessage(content="Created main.py")])
    chat_model.n_ctx = 256

    with patch.object(CodeAgent, "_get_code_tools", return_value=[_dummy_tool]):
        agent = CodeAgent(chat_model=chat_model, system_prompt="Custom prompt")

    messages = [
        HumanMessage(content="old request " * 80),
        AIMessage(content="old answer " * 80),
        HumanMessage(content="older request " * 80),
        AIMessage(content="older answer " * 80),
        HumanMessage(content="create main.py"),
    ]
    state = {
        "messages": messages,
        "programming_language": "python",
        "task_type": "write",
        "execution_context": {},
    }

    agent._call_model(state)

    sent_messages = chat_model.calls[0]
    assert len(sent_messages) < len(messages) + 1
    assert sent_messages[-1].content == "create main.py"


def test_code_agent_preserves_latest_request_when_trim_would_drop_all():
    """CodeAgent should keep the latest user request even under tiny budgets."""
    chat_model = FakeCodeChatModel([AIMessage(content="Created main.py")])

    with patch.object(CodeAgent, "_get_code_tools", return_value=[_dummy_tool]):
        agent = CodeAgent(chat_model=chat_model, system_prompt="Custom prompt")

    messages = [
        HumanMessage(content="old request " * 80),
        AIMessage(content="old answer " * 80),
        HumanMessage(content="create main.py"),
        ToolMessage(
            content="workspace contents",
            tool_call_id="tool-1",
            name="list_workspace_files",
        ),
    ]
    state = {
        "messages": messages,
        "programming_language": "python",
        "task_type": "write",
        "execution_context": {},
    }

    with patch.object(agent, "_history_token_budget", return_value=4):
        agent._call_model(state)

    sent_messages = chat_model.calls[0]
    assert len(sent_messages) >= 2
    assert sent_messages[1].content == "create main.py"


def test_code_agent_stops_repeated_non_mutating_tool_loop():
    """CodeAgent should stop before LangGraph recursion is exhausted."""
    looping_tool_call = [
        {
            "id": "tool-1",
            "name": "list_workspace_files",
            "args": {"pattern": "*"},
        }
    ]
    chat_model = FakeCodeChatModel(
        [
            AIMessage(content="", tool_calls=looping_tool_call),
            AIMessage(content="", tool_calls=looping_tool_call),
        ]
    )

    with patch.object(CodeAgent, "_get_code_tools", return_value=[_dummy_tool]):
        agent = CodeAgent(chat_model=chat_model, system_prompt="Custom prompt")

    agent._executed_tools = ["list_workspace_files"] * 8
    state = {
        "messages": [HumanMessage(content="create main.py")],
        "programming_language": "python",
        "task_type": "write",
        "execution_context": {},
    }
    result = agent._call_model(state)

    assert len(chat_model.calls) == 2
    assert "repeating non-mutating tool calls" in result["messages"][0].content
    assert "No changes were applied" in result["messages"][0].content