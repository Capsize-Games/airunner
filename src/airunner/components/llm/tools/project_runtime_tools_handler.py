"""Project-aware runtime, diagnostics, and workspace query helpers."""

from threading import RLock

from airunner.components.agents.runtime.agent_runtime_support import (
    utc_now_iso,
)
from airunner.components.agents.runtime.agent_tool_call_record import (
    AgentToolCallRecord,
)
from airunner.components.document_editor.project.airunner_project_service import (
    AirunnerProjectService,
)
from airunner.components.document_editor.project.airunner_project_state_service import (
    AirunnerProjectStateService,
)
from airunner.components.document_editor.project.airunner_python_workflow_service import (
    AirunnerPythonWorkflowService,
)
from airunner.components.document_editor.terminal import (
    TerminalSessionManager,
)
from airunner.components.llm.tools.project_runtime_diagnostics_support import (
    ProjectRuntimeDiagnosticsSupport,
)


class ProjectRuntimeToolsHandler:
    """Expose project-scoped command, diagnostics, and query helpers."""

    _registry_lock = RLock()
    _terminal_managers: dict[str, TerminalSessionManager] = {}
    _terminal_sessions: dict[str, dict[str, object]] = {}

    def __init__(self, project_path: str, run_id: str | None = None):
        self.project_service = AirunnerProjectService(project_path)
        if not self.project_service.exists():
            raise ValueError(
                "The target path is not an initialized .airunner project."
            )
        self.state_service = AirunnerProjectStateService(self.project_service)
        self.python_workflows = AirunnerPythonWorkflowService(
            self.project_service
        )
        self.diagnostics_support = ProjectRuntimeDiagnosticsSupport(
            self.project_service
        )
        self.run_id = run_id

    def run_command(
        self,
        command: str,
        *,
        root_name: str | None = None,
        rel_working_directory: str = "",
        environment: dict[str, str] | None = None,
    ) -> dict[str, object]:
        """Run an arbitrary shell command inside one project root."""
        root = self._default_root(root_name)
        arguments = {
            "command": command,
            "root_name": root,
            "rel_working_directory": rel_working_directory,
            "environment_keys": sorted((environment or {}).keys()),
        }
        return self._start_command(
            "project_run_command",
            arguments,
            command=command,
            root_name=root,
            rel_working_directory=rel_working_directory,
            environment=environment,
        )
    def run_python_tests(
        self,
        *,
        root_name: str | None = None,
        rel_working_directory: str = "",
        extra_args: list[str] | None = None,
    ) -> dict[str, object]:
        """Run Python tests using the selected project environment."""
        context = self.python_workflows.context(
            root_name,
            rel_working_directory,
        )
        summary = self.python_workflows.summary(
            root_name=root_name,
            rel_working_directory=rel_working_directory,
        )
        command = self.python_workflows.build_test_command(
            context,
            extra_args=extra_args,
        )
        return self._start_python_workflow(
            "project_run_python_tests",
            "tests",
            command,
            summary,
            rel_working_directory=rel_working_directory,
            extra_args=extra_args or [],
        )
    def run_python_lint(
        self,
        *,
        root_name: str | None = None,
        rel_working_directory: str = "",
    ) -> dict[str, object]:
        """Run Python linting using the selected project environment."""
        context = self.python_workflows.context(
            root_name,
            rel_working_directory,
        )
        summary = self.python_workflows.summary(
            root_name=root_name,
            rel_working_directory=rel_working_directory,
        )
        command = self.python_workflows.build_lint_command(context)
        return self._start_python_workflow(
            "project_run_python_lint",
            "lint",
            command,
            summary,
            rel_working_directory=rel_working_directory,
        )
    def run_python_format(
        self,
        *,
        root_name: str | None = None,
        rel_working_directory: str = "",
        paths: list[str] | None = None,
        check_only: bool = False,
    ) -> dict[str, object]:
        """Run Python formatting using the selected project environment."""
        context = self.python_workflows.context(
            root_name,
            rel_working_directory,
        )
        summary = self.python_workflows.summary(
            root_name=root_name,
            rel_working_directory=rel_working_directory,
        )
        command = self.python_workflows.build_format_command(
            context,
            paths=paths,
            check_only=check_only,
        )
        return self._start_python_workflow(
            "project_run_python_format",
            "format",
            command,
            summary,
            rel_working_directory=rel_working_directory,
            check_only=check_only,
            paths=paths or ["."],
        )
    def python_workflow_summary(
        self,
        *,
        root_name: str | None = None,
        rel_working_directory: str = "",
    ) -> dict[str, object]:
        """Return the resolved Python workflow commands for a project."""
        return self._result(
            "project_get_python_workflow_summary",
            True,
            python=self.python_workflows.summary(
                root_name=root_name,
                rel_working_directory=rel_working_directory,
            ),
            message="Python workflow summary ready.",
        )
    def read_terminal_output(
        self,
        session_id: str,
        *,
        offset: int = 0,
        limit: int = 4000,
    ) -> dict[str, object]:
        """Read output from one tracked terminal session."""
        if offset < 0:
            return self._error(
                "project_read_terminal_output",
                f"Invalid offset: {offset}",
            )
        try:
            session = self._session_info(session_id)
        except ValueError as exc:
            return self._error("project_read_terminal_output", str(exc))
        output = self._terminal_manager().session_output(session_id)
        chunk = output[offset: offset + limit]
        return self._result(
            "project_read_terminal_output",
            True,
            session_id=session_id,
            root_name=session["root_name"],
            is_running=self._is_running(session_id),
            exit_code=self._exit_code(session_id),
            output=chunk,
            output_length=len(output),
            next_offset=offset + len(chunk),
            message="Terminal output retrieved.",
        )
    def send_terminal_input(
        self,
        session_id: str,
        text: str,
        *,
        append_newline: bool = True,
    ) -> dict[str, object]:
        """Send interactive input to one running terminal session."""
        try:
            session = self._session_info(session_id)
        except ValueError as exc:
            return self._error("project_send_terminal_input", str(exc))
        sent = self._terminal_manager().send_input(
            session_id,
            text,
            append_newline=append_newline,
        )
        if not sent:
            return self._error(
                "project_send_terminal_input",
                f"Terminal session {session_id} is not running.",
            )
        return self._audited_result(
            "project_send_terminal_input",
            {
                "session_id": session_id,
                "root_name": session["root_name"],
                "append_newline": append_newline,
            },
            session_id=session_id,
            root_name=session["root_name"],
            is_running=True,
            exit_code=None,
            message=f"Sent input to terminal session {session_id}.",
        )
    def stop_command(
        self,
        session_id: str,
        *,
        timeout: float = 1.0,
    ) -> dict[str, object]:
        """Stop one running terminal session."""
        try:
            session = self._session_info(session_id)
        except ValueError as exc:
            return self._error("project_stop_command", str(exc))
        stopped = self._terminal_manager().stop_session(
            session_id,
            timeout=timeout,
        )
        if not stopped:
            return self._error(
                "project_stop_command",
                f"Terminal session {session_id} could not be stopped.",
            )
        return self._audited_result(
            "project_stop_command",
            {"session_id": session_id, "timeout": timeout},
            session_id=session_id,
            root_name=session["root_name"],
            is_running=self._is_running(session_id),
            exit_code=self._exit_code(session_id),
            message=f"Stopped terminal session {session_id}.",
        )
    def list_terminal_sessions(self) -> dict[str, object]:
        """List all terminal sessions that belong to this project."""
        sessions = [
            self._session_snapshot(item)
            for item in self._project_sessions()
        ]
        return self._result(
            "project_list_terminal_sessions",
            True,
            sessions=sessions,
            message=f"Found {len(sessions)} terminal session(s).",
        )
    def workspace_summary(self) -> dict[str, object]:
        """Return high-level workspace context for UI or agent planning."""
        workspace = self.project_service.load_workspace()
        roots = [self._root_summary(root.name) for root in workspace.roots]
        return self._result(
            "project_get_workspace_summary",
            True,
            project_path=str(self.project_service.project_path),
            project_name=workspace.project_name,
            primary_root=workspace.primary_root,
            roots=roots,
            validation_errors=self.project_service.validate(),
            terminal_sessions=self.list_terminal_sessions()["sessions"],
            audited_tool_calls=len(self.state_service.list_tool_calls()),
            python=self.python_workflows.summary(),
            message="Workspace summary ready.",
        )
    def diagnostics(
        self,
        *,
        rel_paths: list[str] | None = None,
        root_name: str | None = None,
        rel_dir: str = "",
        pattern: str = "*.py",
        max_files: int = 50,
    ) -> dict[str, object]:
        """Collect merged diagnostics for project files."""
        diagnostic_data = self.diagnostics_support.collect(
            rel_paths=rel_paths,
            root_name=root_name,
            rel_dir=rel_dir,
            pattern=pattern,
            max_files=max_files,
        )
        files_checked = diagnostic_data["summary"]["files_checked"]
        return self._result(
            "project_get_diagnostics",
            True,
            diagnostics=diagnostic_data["diagnostics"],
            summary=diagnostic_data["summary"],
            python=self.python_workflows.summary(
                root_name=root_name,
                rel_working_directory=rel_dir,
            ),
            message=f"Collected diagnostics for {files_checked} file(s).",
        )
    def _start_python_workflow(
        self,
        operation: str,
        workflow: str,
        command: str,
        summary: dict[str, object],
        **arguments,
    ) -> dict[str, object]:
        return self._start_command(
            operation,
            {"root_name": summary["root_name"], **arguments},
            command=command,
            root_name=str(summary["root_name"]),
            rel_working_directory=str(
                arguments.get("rel_working_directory", "")
            ),
            extra_fields={
                "workflow": workflow,
                "resolved_command": command,
                "python": summary,
            },
        )
    def _start_command(
        self,
        operation: str,
        arguments: dict[str, object],
        *,
        command: str,
        root_name: str,
        rel_working_directory: str,
        environment: dict[str, str] | None = None,
        extra_fields: dict[str, object] | None = None,
    ) -> dict[str, object]:
        try:
            working_directory = self._working_directory(
                rel_working_directory,
                root_name,
            )
        except ValueError as exc:
            return self._error(operation, str(exc))
        session_id = self._terminal_manager().start_shell_session(
            command,
            working_directory=working_directory,
            environment=environment,
        )
        self._register_session(
            session_id,
            command,
            root_name,
            working_directory,
        )
        return self._audited_result(
            operation,
            arguments,
            session_id=session_id,
            root_name=root_name,
            working_directory=working_directory,
            is_running=True,
            exit_code=None,
            output="",
            output_length=0,
            **(extra_fields or {}),
            message=f"Started command in {working_directory}.",
        )
    def _register_session(
        self,
        session_id: str,
        command: str,
        root_name: str,
        working_directory: str,
    ) -> None:
        with self._registry_lock:
            self._terminal_sessions[session_id] = {
                "session_id": session_id,
                "project_path": str(self.project_service.project_path),
                "command": command,
                "root_name": root_name,
                "working_directory": working_directory,
                "created_at": utc_now_iso(),
            }

    def _session_info(self, session_id: str) -> dict[str, object]:
        with self._registry_lock:
            session = self._terminal_sessions.get(session_id)
        if session is None or session["project_path"] != str(
            self.project_service.project_path
        ):
            raise ValueError(f"Unknown terminal session: {session_id}")
        return session

    def _project_sessions(self) -> list[dict[str, object]]:
        project_path = str(self.project_service.project_path)
        with self._registry_lock:
            sessions = list(self._terminal_sessions.values())
        return [
            item for item in sessions if item["project_path"] == project_path
        ]

    def _session_snapshot(
        self,
        session: dict[str, object],
    ) -> dict[str, object]:
        session_id = str(session["session_id"])
        output = self._terminal_manager().session_output(session_id)
        return {
            "session_id": session_id,
            "command": session["command"],
            "root_name": session["root_name"],
            "working_directory": session["working_directory"],
            "created_at": session["created_at"],
            "is_running": self._is_running(session_id),
            "exit_code": self._exit_code(session_id),
            "output_length": len(output),
        }

    def _root_summary(self, root_name: str) -> dict[str, object]:
        manager = self.project_service.get_workspace_manager(root_name)
        files = manager.list_files("", pattern="*", recursive=True)
        file_count = 0
        for rel_path in files:
            if rel_path.startswith(".airunner"):
                continue
            if not manager.get_file_info(rel_path).get("is_file"):
                continue
            file_count += 1
        return {
            "name": root_name,
            "path": self.project_service.resolve_root_path(root_name),
            "file_count": file_count,
        }

    def _working_directory(
        self,
        rel_working_directory: str,
        root_name: str,
    ) -> str:
        return self.project_service.resolve_path(
            rel_working_directory or ".",
            root_name,
        )

    def _terminal_manager(self) -> TerminalSessionManager:
        project_path = str(self.project_service.project_path)
        with self._registry_lock:
            if project_path not in self._terminal_managers:
                self._terminal_managers[project_path] = (
                    TerminalSessionManager()
                )
            return self._terminal_managers[project_path]

    def _is_running(self, session_id: str) -> bool:
        session = self._terminal_manager().get_session(session_id)
        return bool(session and session.is_running)

    def _exit_code(self, session_id: str) -> int | None:
        session = self._terminal_manager().get_session(session_id)
        return None if session is None else session.exit_code

    def _default_root(self, root_name: str | None) -> str:
        workspace = self.project_service.load_workspace()
        return root_name or workspace.primary_root

    def _record_tool_call(
        self,
        tool_name: str,
        arguments: dict[str, object],
        output: dict[str, object],
        error: str | None = None,
    ) -> str:
        tool_call = AgentToolCallRecord(
            tool_name=tool_name,
            arguments=arguments,
            output=output,
            error=error,
            finished_at=utc_now_iso(),
        )
        return self.state_service.record_tool_call(
            tool_call,
            run_id=self.run_id,
        )

    def _audited_result(
        self,
        operation: str,
        arguments: dict[str, object],
        **kwargs,
    ) -> dict[str, object]:
        result = self._result(operation, True, **kwargs)
        result["audit_record_id"] = self._record_tool_call(
            operation,
            arguments,
            result,
        )
        return result

    def _result(
        self,
        operation: str,
        success: bool,
        **kwargs,
    ) -> dict[str, object]:
        message = kwargs.pop("message", f"{operation} succeeded.")
        return {
            "operation": operation,
            "success": success,
            "message": message,
            **kwargs,
        }

    def _error(self, operation: str, message: str) -> dict[str, object]:
        result = self._result(
            operation,
            False,
            error=message,
            message=message,
        )
        result["audit_record_id"] = self._record_tool_call(
            operation,
            {},
            result,
            error=message,
        )
        return result