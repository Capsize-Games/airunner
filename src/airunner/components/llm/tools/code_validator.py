"""
code_validator.py

Service for validating Python code with flake8 and mypy.

Runs static analysis tools and returns structured validation results
for display in Problems panel or feedback to LLM.
"""

import subprocess
import re
from typing import List, Optional, Dict, Any
from pathlib import Path
from enum import Enum
from dataclasses import dataclass

from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


class ValidationSeverity(Enum):
    """Severity levels for validation issues."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationIssue:
    """A single validation issue found in code."""

    file_path: str
    line: int
    column: int
    severity: ValidationSeverity
    code: str
    message: str
    tool: str

    def __str__(self):
        return f"{self.file_path}:{self.line}:{self.column}: {self.severity.value}: {self.code} {self.message}"


@dataclass
class ValidationResult:
    """Result of code validation."""

    file_path: str
    success: bool
    issues: List[ValidationIssue]
    error_count: int
    warning_count: int
    info_count: int

    @property
    def has_errors(self) -> bool:
        """Check if validation found any errors."""
        return self.error_count > 0

    @property
    def has_warnings(self) -> bool:
        """Check if validation found any warnings."""
        return self.warning_count > 0

    def __str__(self):
        status = "✓" if self.success else "✗"
        return f"{status} {self.file_path}: {self.error_count} errors, {self.warning_count} warnings"


class CodeValidator:
    """
    Validates Python code using flake8 and mypy.

    Runs static analysis tools and parses output into structured results.
    """

    def __init__(
        self,
        enable_flake8: bool = True,
        enable_mypy: bool = True,
        flake8_config: Optional[str] = None,
        mypy_config: Optional[str] = None,
    ):
        """
        Initialize code validator.

        Args:
            enable_flake8: Enable flake8 validation
            enable_mypy: Enable mypy type checking
            flake8_config: Path to flake8 config file
            mypy_config: Path to mypy config file
        """
        self.enable_flake8 = enable_flake8
        self.enable_mypy = enable_mypy
        self.flake8_config = flake8_config
        self.mypy_config = mypy_config

        self._check_tools_available()

        logger.info(
            f"CodeValidator initialized (flake8={enable_flake8}, mypy={enable_mypy})"
        )

    def _check_tools_available(self):
        """Check if validation tools are installed."""
        if self.enable_flake8:
            try:
                subprocess.run(
                    ["flake8", "--version"],
                    capture_output=True,
                    check=True,
                    timeout=5,
                )
                logger.debug("flake8 available")
            except (
                subprocess.CalledProcessError,
                FileNotFoundError,
                subprocess.TimeoutExpired,
            ):
                logger.warning(
                    "flake8 not available, disabling flake8 validation"
                )
                self.enable_flake8 = False

        if self.enable_mypy:
            try:
                subprocess.run(
                    ["mypy", "--version"],
                    capture_output=True,
                    check=True,
                    timeout=5,
                )
                logger.debug("mypy available")
            except (
                subprocess.CalledProcessError,
                FileNotFoundError,
                subprocess.TimeoutExpired,
            ):
                logger.warning("mypy not available, disabling mypy validation")
                self.enable_mypy = False

    def validate_file(self, file_path: str) -> ValidationResult:
        """
        Validate a Python file.

        Args:
            file_path: Absolute path to file to validate

        Returns:
            ValidationResult with all issues found
        """
        if not Path(file_path).exists():
            logger.error(f"File not found: {file_path}")
            return ValidationResult(
                file_path=file_path,
                success=False,
                issues=[],
                error_count=0,
                warning_count=0,
                info_count=0,
            )

        issues = []

        if self.enable_flake8:
            issues.extend(self._run_flake8(file_path))

        if self.enable_mypy:
            issues.extend(self._run_mypy(file_path))

        # Count by severity
        error_count = sum(
            1 for i in issues if i.severity == ValidationSeverity.ERROR
        )
        warning_count = sum(
            1 for i in issues if i.severity == ValidationSeverity.WARNING
        )
        info_count = sum(
            1 for i in issues if i.severity == ValidationSeverity.INFO
        )

        success = error_count == 0

        return ValidationResult(
            file_path=file_path,
            success=success,
            issues=issues,
            error_count=error_count,
            warning_count=warning_count,
            info_count=info_count,
        )

    def _run_flake8(self, file_path: str) -> List[ValidationIssue]:
        """
        Run flake8 on file.

        Args:
            file_path: Path to file

        Returns:
            List of ValidationIssue objects
        """
        issues = []

        try:
            cmd = ["flake8", file_path]

            if self.flake8_config:
                cmd.extend(["--config", self.flake8_config])

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )

            # flake8 exits with non-zero if issues found, but that's expected
            output = result.stdout + result.stderr

            issues = self._parse_flake8_output(output, file_path)

            logger.debug(f"flake8 found {len(issues)} issues in {file_path}")

        except subprocess.TimeoutExpired:
            logger.error(f"flake8 timed out on {file_path}")
        except Exception as e:
            logger.error(f"Error running flake8: {e}")

        return issues

    def _parse_flake8_output(
        self, output: str, file_path: str
    ) -> List[ValidationIssue]:
        """
        Parse flake8 output into ValidationIssue objects.

        Format: path/file.py:line:column: code message
        Example: test.py:10:5: E501 line too long (82 > 79 characters)

        Args:
            output: flake8 stdout/stderr
            file_path: Path to file being validated

        Returns:
            List of ValidationIssue objects
        """
        issues = []

        # Pattern: filename:line:column: code message
        pattern = r"^(.+?):(\d+):(\d+):\s+([A-Z]\d+)\s+(.+)$"

        for line in output.splitlines():
            match = re.match(pattern, line)
            if match:
                path, line_num, col, code, message = match.groups()

                # Determine severity based on error code
                # E/F/C = errors, W = warnings
                severity = (
                    ValidationSeverity.ERROR
                    if code[0] in ["E", "F", "C"]
                    else ValidationSeverity.WARNING
                )

                issues.append(
                    ValidationIssue(
                        file_path=file_path,
                        line=int(line_num),
                        column=int(col),
                        severity=severity,
                        code=code,
                        message=message,
                        tool="flake8",
                    )
                )

        return issues

    def _run_mypy(self, file_path: str) -> List[ValidationIssue]:
        """
        Run mypy on file.

        Args:
            file_path: Path to file

        Returns:
            List of ValidationIssue objects
        """
        issues = []

        try:
            cmd = [
                "mypy",
                file_path,
                "--no-error-summary",
                "--show-column-numbers",
            ]

            if self.mypy_config:
                cmd.extend(["--config-file", self.mypy_config])

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )

            # mypy exits with non-zero if issues found, but that's expected
            output = result.stdout + result.stderr

            issues = self._parse_mypy_output(output, file_path)

            logger.debug(f"mypy found {len(issues)} issues in {file_path}")

        except subprocess.TimeoutExpired:
            logger.error(f"mypy timed out on {file_path}")
        except Exception as e:
            logger.error(f"Error running mypy: {e}")

        return issues

    def _parse_mypy_output(
        self, output: str, file_path: str
    ) -> List[ValidationIssue]:
        """
        Parse mypy output into ValidationIssue objects.

        Format: path/file.py:line:column: severity: message [code]
        Example: test.py:10:5: error: Incompatible return value type [return-value]

        Args:
            output: mypy stdout/stderr
            file_path: Path to file being validated

        Returns:
            List of ValidationIssue objects
        """
        issues = []

        # Pattern: filename:line:column: severity: message [code]
        pattern = r"^(.+?):(\d+):(\d+):\s+(error|warning|note):\s+(.+?)(?:\s+\[(.+?)\])?$"

        for line in output.splitlines():
            match = re.match(pattern, line)
            if match:
                path, line_num, col, severity_str, message, code = (
                    match.groups()
                )

                # Map mypy severity to our enum
                if severity_str == "error":
                    severity = ValidationSeverity.ERROR
                elif severity_str == "warning":
                    severity = ValidationSeverity.WARNING
                else:  # note
                    severity = ValidationSeverity.INFO

                issues.append(
                    ValidationIssue(
                        file_path=file_path,
                        line=int(line_num),
                        column=int(col),
                        severity=severity,
                        code=code or "mypy",
                        message=message,
                        tool="mypy",
                    )
                )

        return issues

    def validate_files(self, file_paths: List[str]) -> List[ValidationResult]:
        """
        Validate multiple Python files.

        Args:
            file_paths: List of absolute paths to validate

        Returns:
            List of ValidationResult objects
        """
        results = []

        for file_path in file_paths:
            result = self.validate_file(file_path)
            results.append(result)

        return results

    def get_summary(self, results: List[ValidationResult]) -> Dict[str, Any]:
        """
        Get summary statistics for validation results.

        Args:
            results: List of ValidationResult objects

        Returns:
            Dictionary with summary stats
        """
        total_files = len(results)
        files_with_errors = sum(1 for r in results if r.has_errors)
        files_with_warnings = sum(1 for r in results if r.has_warnings)
        total_errors = sum(r.error_count for r in results)
        total_warnings = sum(r.warning_count for r in results)
        total_issues = sum(len(r.issues) for r in results)

        return {
            "total_files": total_files,
            "files_with_errors": files_with_errors,
            "files_with_warnings": files_with_warnings,
            "total_errors": total_errors,
            "total_warnings": total_warnings,
            "total_issues": total_issues,
            "success": files_with_errors == 0,
        }
