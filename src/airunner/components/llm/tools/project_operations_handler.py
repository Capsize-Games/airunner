"""Project-aware file and search operations for coding agents."""

import os
import re
import shutil

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
from airunner.components.llm.tools.project_tool_result import (
    ProjectToolResult,
)


class ProjectOperationsHandler:
    """Execute project-scoped file and search operations with auditing."""

    def __init__(self, project_path: str, run_id: str | None = None):
        self.project_service = AirunnerProjectService(project_path)
        if not self.project_service.exists():
            raise ValueError(
                "The target path is not an initialized .airunner project."
            )
        self.state_service = AirunnerProjectStateService(self.project_service)
        self.run_id = run_id

    def list_files(
        self,
        rel_dir: str = "",
        *,
        root_name: str | None = None,
        pattern: str = "*",
        recursive: bool = True,
    ) -> ProjectToolResult:
        files = self._listed_files(rel_dir, pattern, recursive, root_name)
        return self._result("project_list_files", True, files=files)

    def read_file(
        self,
        rel_path: str,
        *,
        root_name: str | None = None,
    ) -> ProjectToolResult:
        root = self._default_root(root_name)
        manager = self.project_service.get_workspace_manager(root)
        if not manager.exists(rel_path):
            return self._error(
                "project_read_file",
                rel_path,
                "File does not exist.",
                root,
            )
        content = self.project_service.read_file(rel_path, root)
        abs_path = self.project_service.resolve_path(rel_path, root)
        return self._result(
            "project_read_file",
            True,
            root_name=root,
            rel_path=rel_path,
            abs_path=abs_path,
            content=content,
        )

    def search_files(
        self,
        query: str,
        *,
        root_name: str | None = None,
        rel_dir: str = "",
        include_pattern: str = "*",
        is_regex: bool = False,
        case_sensitive: bool = False,
        max_results: int = 20,
        recursive: bool = True,
    ) -> ProjectToolResult:
        try:
            matcher = self._compile_pattern(query, is_regex, case_sensitive)
        except re.error as exc:
            return self._error(
                "project_search_files",
                rel_dir or None,
                f"Invalid search pattern: {exc}",
                root_name,
            )
        matches = self._search_matches(
            matcher,
            rel_dir,
            include_pattern,
            recursive,
            root_name,
            max_results,
        )
        return self._result("project_search_files", True, matches=matches)

    def create_file(
        self,
        rel_path: str,
        content: str,
        *,
        root_name: str | None = None,
        overwrite: bool = False,
    ) -> ProjectToolResult:
        root = self._default_root(root_name)
        manager = self.project_service.get_workspace_manager(root)
        if manager.exists(rel_path) and not overwrite:
            return self._error(
                "project_create_file",
                rel_path,
                "File already exists.",
                root,
            )
        abs_path = self.project_service.write_file(
            rel_path,
            content,
            root,
            backup=True,
        )
        arguments = {
            "root_name": root,
            "rel_path": rel_path,
            "overwrite": overwrite,
        }
        return self._audited_result(
            "project_create_file",
            arguments,
            root_name=root,
            rel_path=rel_path,
            abs_path=abs_path,
            content=content,
            message=f"Created {rel_path}.",
        )

    def edit_file(
        self,
        rel_path: str,
        content: str,
        *,
        root_name: str | None = None,
        backup: bool = True,
    ) -> ProjectToolResult:
        root = self._default_root(root_name)
        manager = self.project_service.get_workspace_manager(root)
        if not manager.exists(rel_path):
            return self._error(
                "project_edit_file",
                rel_path,
                "File does not exist.",
                root,
            )
        abs_path = self.project_service.write_file(
            rel_path,
            content,
            root,
            backup=backup,
        )
        arguments = {
            "root_name": root,
            "rel_path": rel_path,
            "backup": backup,
        }
        return self._audited_result(
            "project_edit_file",
            arguments,
            root_name=root,
            rel_path=rel_path,
            abs_path=abs_path,
            content=content,
            message=f"Edited {rel_path}.",
        )

    def patch_file(
        self,
        rel_path: str,
        old_text: str,
        new_text: str,
        *,
        root_name: str | None = None,
        expected_occurrences: int = 1,
        backup: bool = True,
    ) -> ProjectToolResult:
        root = self._default_root(root_name)
        manager = self.project_service.get_workspace_manager(root)
        if not manager.exists(rel_path):
            return self._error(
                "project_patch_file",
                rel_path,
                "File does not exist.",
                root,
            )
        current_content = self.project_service.read_file(rel_path, root)
        occurrences = current_content.count(old_text)
        error = self._patch_error(occurrences, expected_occurrences)
        if error:
            return self._error("project_patch_file", rel_path, error, root)
        updated = self._patched_content(
            current_content,
            old_text,
            new_text,
            expected_occurrences,
        )
        abs_path = self.project_service.write_file(
            rel_path,
            updated,
            root,
            backup=backup,
        )
        arguments = {
            "root_name": root,
            "rel_path": rel_path,
            "expected_occurrences": expected_occurrences,
            "backup": backup,
        }
        return self._audited_result(
            "project_patch_file",
            arguments,
            root_name=root,
            rel_path=rel_path,
            abs_path=abs_path,
            content=updated,
            message=f"Patched {rel_path}.",
        )

    def rename_file(
        self,
        rel_path: str,
        new_rel_path: str,
        *,
        root_name: str | None = None,
        new_root_name: str | None = None,
    ) -> ProjectToolResult:
        source_root = self._default_root(root_name)
        target_root = self._default_root(new_root_name or source_root)
        try:
            abs_path = self._rename_path(
                rel_path,
                new_rel_path,
                source_root,
                target_root,
            )
        except FileNotFoundError:
            return self._error(
                "project_rename_file",
                rel_path,
                "File does not exist.",
                source_root,
            )
        arguments = {
            "root_name": source_root,
            "new_root_name": target_root,
            "rel_path": rel_path,
            "new_rel_path": new_rel_path,
        }
        return self._audited_result(
            "project_rename_file",
            arguments,
            root_name=target_root,
            rel_path=new_rel_path,
            abs_path=abs_path,
            message=f"Renamed {rel_path} to {new_rel_path}.",
        )

    def delete_file(
        self,
        rel_path: str,
        *,
        root_name: str | None = None,
        backup: bool = True,
    ) -> ProjectToolResult:
        root = self._default_root(root_name)
        manager = self.project_service.get_workspace_manager(root)
        if not manager.exists(rel_path):
            return self._error(
                "project_delete_file",
                rel_path,
                "File does not exist.",
                root,
            )
        abs_path = self.project_service.resolve_path(rel_path, root)
        manager.delete(rel_path, backup=backup)
        arguments = {
            "root_name": root,
            "rel_path": rel_path,
            "backup": backup,
        }
        return self._audited_result(
            "project_delete_file",
            arguments,
            root_name=root,
            rel_path=rel_path,
            abs_path=abs_path,
            message=f"Deleted {rel_path}.",
        )

    def _listed_files(
        self,
        rel_dir: str,
        pattern: str,
        recursive: bool,
        root_name: str | None,
    ) -> list[dict[str, str]]:
        files: list[dict[str, str]] = []
        for root in self._scan_roots(root_name):
            manager = self.project_service.get_workspace_manager(root)
            for rel_path in sorted(manager.list_files(rel_dir, pattern, recursive)):
                if not manager.get_file_info(rel_path).get("is_file"):
                    continue
                files.append({"root_name": root, "rel_path": rel_path})
        return files

    def _search_matches(
        self,
        matcher: re.Pattern[str],
        rel_dir: str,
        include_pattern: str,
        recursive: bool,
        root_name: str | None,
        max_results: int,
    ) -> list[dict[str, object]]:
        matches: list[dict[str, object]] = []
        for file_info in self._listed_files(
            rel_dir,
            include_pattern,
            recursive,
            root_name,
        ):
            content = self._safe_read(
                file_info["rel_path"],
                file_info["root_name"],
            )
            if content is None:
                continue
            matches.extend(
                self._matches_in_content(
                    content,
                    file_info,
                    matcher,
                    max_results - len(matches),
                )
            )
            if len(matches) >= max_results:
                return matches[:max_results]
        return matches

    def _matches_in_content(
        self,
        content: str,
        file_info: dict[str, str],
        matcher: re.Pattern[str],
        max_results: int,
    ) -> list[dict[str, object]]:
        matches: list[dict[str, object]] = []
        for line_number, line in enumerate(content.splitlines(), 1):
            for matched in matcher.finditer(line):
                matches.append(
                    {
                        "root_name": file_info["root_name"],
                        "rel_path": file_info["rel_path"],
                        "line_number": line_number,
                        "line": line,
                        "match": matched.group(0),
                    }
                )
                if len(matches) >= max_results:
                    return matches
        return matches

    def _safe_read(self, rel_path: str, root_name: str) -> str | None:
        try:
            return self.project_service.read_file(rel_path, root_name)
        except UnicodeDecodeError:
            return None
        except OSError:
            return None

    def _rename_path(
        self,
        rel_path: str,
        new_rel_path: str,
        source_root: str,
        target_root: str,
    ) -> str:
        if source_root == target_root:
            manager = self.project_service.get_workspace_manager(source_root)
            return manager.rename(rel_path, new_rel_path)
        old_abs = self.project_service.resolve_path(rel_path, source_root)
        new_abs = self.project_service.resolve_path(new_rel_path, target_root)
        if not os.path.exists(old_abs):
            raise FileNotFoundError(rel_path)
        os.makedirs(os.path.dirname(new_abs), exist_ok=True)
        shutil.move(old_abs, new_abs)
        return new_abs

    def _compile_pattern(
        self,
        query: str,
        is_regex: bool,
        case_sensitive: bool,
    ) -> re.Pattern[str]:
        flags = 0 if case_sensitive else re.IGNORECASE
        pattern = query if is_regex else re.escape(query)
        return re.compile(pattern, flags)

    def _default_root(self, root_name: str | None) -> str:
        workspace = self.project_service.load_workspace()
        return root_name or workspace.primary_root

    def _scan_roots(self, root_name: str | None) -> list[str]:
        if root_name:
            return [self._default_root(root_name)]
        return [root.name for root in self.project_service.list_roots()]

    def _patch_error(
        self,
        occurrences: int,
        expected_occurrences: int,
    ) -> str | None:
        if occurrences == 0:
            return "Patch target text was not found."
        if expected_occurrences > 0 and occurrences != expected_occurrences:
            return (
                "Patch target matched "
                f"{occurrences} time(s); expected {expected_occurrences}."
            )
        return None

    def _patched_content(
        self,
        content: str,
        old_text: str,
        new_text: str,
        expected_occurrences: int,
    ) -> str:
        count = 1 if expected_occurrences == 1 else -1
        return content.replace(old_text, new_text, count)

    def _audited_result(
        self,
        tool_name: str,
        arguments: dict[str, object],
        **kwargs,
    ) -> ProjectToolResult:
        result = self._result(tool_name, True, **kwargs)
        result.audit_record_id = self._record_tool_call(
            tool_name,
            arguments,
            result.to_dict(),
        )
        return result

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

    def _result(
        self,
        operation: str,
        success: bool,
        **kwargs,
    ) -> ProjectToolResult:
        message = kwargs.pop("message", f"{operation} succeeded.")
        return ProjectToolResult(
            operation=operation,
            success=success,
            message=message,
            **kwargs,
        )

    def _error(
        self,
        operation: str,
        rel_path: str | None,
        error: str,
        root_name: str | None,
    ) -> ProjectToolResult:
        result = self._result(
            operation,
            False,
            rel_path=rel_path,
            root_name=root_name,
            error=error,
            message=error,
        )
        result.audit_record_id = self._record_tool_call(
            operation,
            {"root_name": root_name, "rel_path": rel_path},
            result.to_dict(),
            error=error,
        )
        return result