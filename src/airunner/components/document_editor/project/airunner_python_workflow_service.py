"""Resolve Python quality workflow commands for coding workspaces."""

from dataclasses import dataclass
import json
import os
from pathlib import Path
import shlex
import subprocess

from airunner.components.document_editor.project.airunner_project_service import (
    AirunnerProjectService,
)
from airunner.components.document_editor.project.airunner_python_environment_selection import (
    AirunnerPythonEnvironmentSelection,
)


@dataclass(frozen=True)
class AirunnerPythonWorkflowContext:
    """Resolved Python workflow context for one project root."""

    root_name: str
    root_path: str
    working_directory: str
    bootstrap_profile: str | None
    python_environment: AirunnerPythonEnvironmentSelection | None


class AirunnerPythonWorkflowService:
    """Build Python workflow commands compatible with project settings."""

    def __init__(self, project_service: AirunnerProjectService):
        self.project_service = project_service

    def summary(
        self,
        *,
        root_name: str | None = None,
        rel_working_directory: str = "",
    ) -> dict[str, object]:
        """Return a user-facing summary of Python workflow commands."""
        context = self.context(root_name, rel_working_directory)
        return {
            "root_name": context.root_name,
            "root_path": context.root_path,
            "working_directory": context.working_directory,
            "bootstrap_profile": context.bootstrap_profile,
            "python_environment": self._environment_dict(
                context.python_environment
            ),
            "bootstrap_command": self.bootstrap_command(context),
            "commands": {
                "tests": self.build_test_command(context),
                "lint": self.build_lint_command(context),
                "format": self.build_format_command(context),
                "diagnostics": self.build_diagnostics_command(context),
            },
        }

    def build_test_command(
        self,
        context: AirunnerPythonWorkflowContext,
        extra_args: list[str] | None = None,
    ) -> str:
        """Build a pytest command for the current project context."""
        args = " ".join(shlex.quote(arg) for arg in (extra_args or []))
        command = f"{self._python_executable(context)} -m pytest"
        if args:
            command = f"{command} {args}"
        return self._apply_activation(context, command)

    def build_lint_command(
        self,
        context: AirunnerPythonWorkflowContext,
        *,
        json_output: bool = False,
    ) -> str:
        """Build a code-quality lint command for the current context."""
        script_path = shlex.quote(str(self._quality_report_script()))
        command = (
            f"{self._python_executable(context)} {script_path} --path ."
        )
        if json_output:
            command = f"{command} --json"
        return self._apply_activation(context, command)

    def build_format_command(
        self,
        context: AirunnerPythonWorkflowContext,
        *,
        paths: list[str] | None = None,
        check_only: bool = False,
    ) -> str:
        """Build a formatting command for the current context."""
        targets = paths or ["."]
        quoted_targets = " ".join(shlex.quote(item) for item in targets)
        command = f"{self._python_executable(context)} -m ruff format"
        if check_only:
            command = f"{command} --check"
        return self._apply_activation(context, f"{command} {quoted_targets}")

    def build_diagnostics_command(
        self,
        context: AirunnerPythonWorkflowContext,
    ) -> str:
        """Build the diagnostics command for the current context."""
        return self.build_lint_command(context, json_output=True)

    def bootstrap_command(
        self,
        context: AirunnerPythonWorkflowContext,
    ) -> str:
        """Build the environment bootstrap command for Python tools."""
        command = f"{self._python_executable(context)} -m pip install -e .[dev]"
        return self._apply_activation(context, command)

    def quality_report(
        self,
        *,
        root_name: str | None = None,
        rel_working_directory: str = "",
        rel_paths: list[str] | None = None,
    ) -> dict[str, object]:
        """Run the AIRunner code-quality analyzer for a project root."""
        context = self.context(root_name, rel_working_directory)
        command = self.build_diagnostics_command(context)
        completed = subprocess.run(
            ["/bin/bash", "-lc", command],
            cwd=context.working_directory,
            capture_output=True,
            text=True,
        )
        return self._quality_report_result(
            context,
            completed.returncode,
            completed.stdout,
            completed.stderr,
            rel_paths=rel_paths,
        )

    def context(
        self,
        root_name: str | None,
        rel_working_directory: str,
    ) -> AirunnerPythonWorkflowContext:
        root = root_name or self.project_service.load_workspace().primary_root
        return AirunnerPythonWorkflowContext(
            root_name=root,
            root_path=self.project_service.resolve_root_path(root),
            working_directory=self.project_service.resolve_path(
                rel_working_directory or ".",
                root,
            ),
            bootstrap_profile=self.project_service.load_settings().bootstrap_profile,
            python_environment=self.project_service.load_settings().python_environment,
        )

    def _python_executable(
        self,
        context: AirunnerPythonWorkflowContext,
    ) -> str:
        environment = context.python_environment
        if environment and environment.interpreter_path:
            return shlex.quote(environment.interpreter_path)
        return "python"

    def _apply_activation(
        self,
        context: AirunnerPythonWorkflowContext,
        command: str,
    ) -> str:
        environment = context.python_environment
        if environment and environment.activate_command:
            return f"{environment.activate_command} && {command}"
        return command

    def _environment_dict(
        self,
        environment: AirunnerPythonEnvironmentSelection | None,
    ) -> dict[str, str | None] | None:
        if environment is None:
            return None
        return environment.to_dict()

    def _quality_report_script(self) -> Path:
        return (
            Path(__file__).resolve().parents[4]
            / "airunner"
            / "bin"
            / "code_quality_report.py"
        )

    def _quality_report_result(
        self,
        context: AirunnerPythonWorkflowContext,
        return_code: int,
        stdout: str,
        stderr: str,
        *,
        rel_paths: list[str] | None,
    ) -> dict[str, object]:
        data = self._parse_quality_report(stdout, stderr)
        issues = self._normalized_quality_issues(
            context,
            data.get("issues", []),
            rel_paths=rel_paths,
        )
        return {
            "success": bool(data),
            "return_code": return_code,
            "summary": data.get("summary", {}),
            "issues": issues,
            "stdout": stdout,
            "stderr": stderr,
        }

    def _parse_quality_report(
        self,
        stdout: str,
        stderr: str,
    ) -> dict[str, object]:
        payload = stdout.strip()
        if not payload:
            return {}
        try:
            return json.loads(payload)
        except json.JSONDecodeError:
            return {
                "summary": {"parse_error": True},
                "issues": [
                    {
                        "file": "<quality-report>",
                        "line": 1,
                        "category": "quality_report_error",
                        "severity": "error",
                        "message": stderr.strip() or payload,
                    }
                ],
            }

    def _normalized_quality_issues(
        self,
        context: AirunnerPythonWorkflowContext,
        issues: list[dict[str, object]],
        *,
        rel_paths: list[str] | None,
    ) -> list[dict[str, object]]:
        allowed = {os.path.normpath(item) for item in rel_paths or []}
        normalized: list[dict[str, object]] = []
        for issue in issues:
            rel_path = self._quality_issue_rel_path(context, str(issue["file"]))
            if allowed and rel_path not in allowed:
                continue
            normalized.append(
                {
                    "root_name": context.root_name,
                    "rel_path": rel_path,
                    "line": int(issue.get("line", 1)),
                    "column": 1,
                    "severity": str(issue.get("severity", "warning")),
                    "code": str(issue.get("category", "quality")),
                    "message": str(issue.get("message", "")),
                    "tool": "airunner-quality-report",
                }
            )
        return normalized

    def _quality_issue_rel_path(
        self,
        context: AirunnerPythonWorkflowContext,
        issue_file: str,
    ) -> str:
        if os.path.isabs(issue_file):
            return os.path.normpath(
                os.path.relpath(issue_file, context.root_path)
            )
        abs_path = os.path.normpath(
            os.path.join(context.working_directory, issue_file)
        )
        return os.path.normpath(os.path.relpath(abs_path, context.root_path))