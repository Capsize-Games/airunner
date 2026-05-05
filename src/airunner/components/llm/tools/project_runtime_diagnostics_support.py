"""Diagnostics collection helpers for project runtime tools."""

import ast
import os

from airunner.components.document_editor.project.airunner_project_service import (
    AirunnerProjectService,
)
from airunner.components.document_editor.project.airunner_python_workflow_service import (
    AirunnerPythonWorkflowService,
)
from airunner.components.llm.tools.code_validator import CodeValidator


class ProjectRuntimeDiagnosticsSupport:
    """Collect Python diagnostics for one AIRunner project."""

    def __init__(self, project_service: AirunnerProjectService):
        self.project_service = project_service
        self.python_workflows = AirunnerPythonWorkflowService(project_service)

    def collect(
        self,
        *,
        rel_paths: list[str] | None = None,
        root_name: str | None = None,
        rel_dir: str = "",
        pattern: str = "*.py",
        max_files: int = 50,
    ) -> dict[str, object]:
        """Collect merged validator, syntax, and quality-report diagnostics."""
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
        quality_report = self.python_workflows.quality_report(
            root_name=root_name,
            rel_working_directory=rel_dir,
            rel_paths=rel_paths,
        )
        diagnostics = self._merged_diagnostics(
            files,
            validation,
            quality_report.get("issues", []),
        )
        return {
            "diagnostics": diagnostics,
            "summary": self._diagnostic_summary(
                files,
                diagnostics,
                validator,
                quality_report,
            ),
        }

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
        quality_report_issues: list[dict[str, object]],
    ) -> list[dict[str, object]]:
        merged: dict[tuple[object, ...], dict[str, object]] = {}
        for item in self._validator_diagnostics(validation_results):
            merged[self._diagnostic_key(item)] = item
        for item in quality_report_issues:
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
        quality_report: dict[str, object],
    ) -> dict[str, object]:
        return {
            "files_checked": len(files),
            "issue_count": len(diagnostics),
            "error_count": self._severity_count(diagnostics, "error"),
            "warning_count": self._severity_count(diagnostics, "warning"),
            "info_count": self._severity_count(diagnostics, "info"),
            "flake8_enabled": validator.enable_flake8,
            "mypy_enabled": validator.enable_mypy,
            "quality_report_enabled": True,
            "quality_report_issue_count": len(
                quality_report.get("issues", [])
            ),
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

    def _default_root(self, root_name: str | None) -> str:
        workspace = self.project_service.load_workspace()
        return root_name or workspace.primary_root

    def _scan_roots(self, root_name: str | None) -> list[str]:
        if root_name:
            return [self._default_root(root_name)]
        return [root.name for root in self.project_service.list_roots()]