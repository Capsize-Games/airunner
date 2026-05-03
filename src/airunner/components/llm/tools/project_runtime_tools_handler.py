"""Project-aware runtime, diagnostics, and workspace query helpers."""

import ast
import os
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
from airunner.components.document_editor.terminal import (
    TerminalSessionManager,
)
from airunner.components.llm.tools.code_validator import CodeValidator


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
        self.run_id = run_id

    def run_command(
        self,
        command: str,
        *,
        root_name: str | None = None,
        rel_working_directory: str = "",
        environment: dict[str, str] | None = None,
    ) -> dict[str, object]:
        root = self._default_root(root_name)
        try:
            working_directory = self._working_directory(
                rel_working_directory,
                root,
            )
        except ValueError as exc:
            return self._error("project_run_command", str(exc))
        manager = self._terminal_manager()
        session_id = manager.start_shell_session(
            command,
            working_directory=working_directory,
            environment=environment,
        )
        self._register_session(
            session_id,
            command,
            root,
            working_directory,
        )
        arguments = {
            "command": command,
            "root_name": root,
            "rel_working_directory": rel_working_directory,
            "environment_keys": sorted((environment or {}).keys()),
        }
        return self._audited_result(
            "project_run_command",
            arguments,
            session_id=session_id,
            root_name=root,
            working_directory=working_directory,
            is_running=True,
            exit_code=None,
            output="",
            output_length=0,
            message=f"Started command in {working_directory}.",
        )

    def read_terminal_output(
        self,
        session_id: str,
        *,
        offset: int = 0,
        limit: int = 4000,
    ) -> dict[str, object]:
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
        arguments = {
            "session_id": session_id,
            "root_name": session["root_name"],
            "append_newline": append_newline,
        }
        return self._audited_result(
            "project_send_terminal_input",
            arguments,
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
        arguments = {
            "session_id": session_id,
            "timeout": timeout,
        }
        return self._audited_result(
            "project_stop_command",
            arguments,
            session_id=session_id,
            root_name=session["root_name"],
            is_running=self._is_running(session_id),
            exit_code=self._exit_code(session_id),
            message=f"Stopped terminal session {session_id}.",
        )

    def list_terminal_sessions(self) -> dict[str, object]:
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
        files = self._diagnostic_targets(
            rel_paths,
            root_name,
            rel_dir,
            pattern,
            max_files,
        )
        validator = CodeValidator()
        validation = validator.validate_files(
            [item["abs_path"] for item in files if item["rel_path"].endswith(".py")]
        )
        diagnostics = self._merged_diagnostics(files, validation)
        return self._result(
            "project_get_diagnostics",
            True,
            diagnostics=diagnostics,
            summary=self._diagnostic_summary(files, diagnostics, validator),
            message=f"Collected diagnostics for {len(files)} file(s).",
        )

    def _diagnostic_targets(
        self,
        rel_paths: list[str] | None,
        root_name: str | None,
        rel_dir: str,
        pattern: str,
        max_files: int,
    ) -> list[dict[str, str]]:
        if rel_paths:
            root = self._default_root(root_name)
            return [self._file_descriptor(item, root) for item in rel_paths]
        files: list[dict[str, str]] = []
        for root in self._scan_roots(root_name):
            manager = self.project_service.get_workspace_manager(root)
            paths = manager.list_files(rel_dir, pattern, recursive=True)
            for rel_path in sorted(paths):
                if not manager.get_file_info(rel_path).get("is_file"):
                    continue
                files.append(self._file_descriptor(rel_path, root))
                if len(files) >= max_files:
                    return files
        return files

    def _file_descriptor(
        self,
        rel_path: str,
        root_name: str,
    ) -> dict[str, str]:
        return {
            "root_name": root_name,
            "rel_path": rel_path,
            "abs_path": self.project_service.resolve_path(rel_path, root_name),
        }

    def _merged_diagnostics(
        self,
        files: list[dict[str, str]],
        validation_results: list,
    ) -> list[dict[str, object]]:
        merged: dict[tuple[object, ...], dict[str, object]] = {}
        for item in self._validator_diagnostics(validation_results):
            merged[self._diagnostic_key(item)] = item
        for item in self._syntax_diagnostics(files):
            merged[self._diagnostic_key(item)] = item
        return sorted(
            merged.values(),
            key=lambda item: (
                item["root_name"],
                item["rel_path"],
                item["line"],
                item["column"],
                item["code"],
            ),
        )

    def _validator_diagnostics(
        self,
        validation_results: list,
    ) -> list[dict[str, object]]:
        diagnostics: list[dict[str, object]] = []
        for result in validation_results:
            root_name, rel_path = self._relative_file_info(result.file_path)
            for issue in result.issues:
                diagnostics.append(
                    {
                        "root_name": root_name,
                        "rel_path": rel_path,
                        "line": issue.line,
                        "column": issue.column,
                        "severity": issue.severity.value,
                        "code": issue.code,
                        "message": issue.message,
                        "tool": issue.tool,
                    }
                )
        return diagnostics

    def _syntax_diagnostics(
        self,
        files: list[dict[str, str]],
    ) -> list[dict[str, object]]:
        diagnostics: list[dict[str, object]] = []
        for item in files:
            if not item["rel_path"].endswith(".py"):
                continue
            try:
                with open(item["abs_path"], "r", encoding="utf-8") as handle:
                    ast.parse(handle.read(), filename=item["abs_path"])
            except SyntaxError as exc:
                diagnostics.append(
                    {
                        "root_name": item["root_name"],
                        "rel_path": item["rel_path"],
                        "line": exc.lineno or 1,
                        "column": exc.offset or 1,
                        "severity": "error",
                        "code": "syntax",
                        "message": exc.msg,
                        "tool": "python-parser",
                    }
                )
            except OSError:
                continue
        return diagnostics

    def _diagnostic_summary(
        self,
        files: list[dict[str, str]],
        diagnostics: list[dict[str, object]],
        validator: CodeValidator,
    ) -> dict[str, object]:
        return {
            "files_checked": len(files),
            "issue_count": len(diagnostics),
            "error_count": self._severity_count(diagnostics, "error"),
            "warning_count": self._severity_count(diagnostics, "warning"),
            "info_count": self._severity_count(diagnostics, "info"),
            "flake8_enabled": validator.enable_flake8,
            "mypy_enabled": validator.enable_mypy,
        }

    def _severity_count(
        self,
        diagnostics: list[dict[str, object]],
        severity: str,
    ) -> int:
        return sum(1 for item in diagnostics if item["severity"] == severity)

    def _relative_file_info(self, abs_path: str) -> tuple[str, str]:
        info = self.project_service.project_relative_path(abs_path)
        if info is None:
            return self._default_root(None), os.path.basename(abs_path)
        return info

    def _diagnostic_key(
        self,
        item: dict[str, object],
    ) -> tuple[object, ...]:
        return (
            item["root_name"],
            item["rel_path"],
            item["line"],
            item["column"],
            item["code"],
            item["message"],
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
        return [item for item in sessions if item["project_path"] == project_path]

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
        count = 0
        for rel_path in files:
            if rel_path.startswith(".airunner"):
                continue
            if not manager.get_file_info(rel_path).get("is_file"):
                continue
            count += 1
        return {
            "name": root_name,
            "path": self.project_service.resolve_root_path(root_name),
            "file_count": count,
        }

    def _working_directory(
        self,
        rel_working_directory: str,
        root_name: str,
    ) -> str:
        rel_path = rel_working_directory or "."
        return self.project_service.resolve_path(rel_path, root_name)

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

    def _scan_roots(self, root_name: str | None) -> list[str]:
        if root_name:
            return [self._default_root(root_name)]
        return [root.name for root in self.project_service.list_roots()]

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