"""
code_quality_manager.py

Manager for orchestrating code quality operations (formatting, validation, testing).

Provides high-level API for applying formatting, running validators, and executing tests
on generated code files.
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from airunner.components.llm.tools.code_operations_handler import (
    CodeOperationsHandler,
    CodeOperationResult,
)
from airunner.components.llm.tools.code_validator import (
    CodeValidator,
    ValidationResult,
)
from airunner.components.llm.tools.test_runner import (
    TestRunner,
    TestResult,
)
from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


@dataclass
class CodeQualityResult:
    """
    Result of code quality checks.

    Includes formatting, validation, and test results.
    """

    file_path: str
    formatted: bool
    format_result: Optional[CodeOperationResult]
    validated: bool
    validation_result: Optional[ValidationResult]
    tested: bool
    test_result: Optional[TestResult]

    @property
    def success(self) -> bool:
        """Check if all quality checks passed."""
        validation_ok = not self.validated or (
            self.validation_result and self.validation_result.success
        )
        test_ok = not self.tested or (
            self.test_result and self.test_result.success
        )

        return validation_ok and test_ok

    def __str__(self):
        status = "✓" if self.success else "✗"
        parts = [f"{status} {self.file_path}"]

        if self.formatted:
            parts.append("formatted")

        if self.validated and self.validation_result:
            vr = self.validation_result
            parts.append(f"{vr.error_count}E/{vr.warning_count}W")

        if self.tested and self.test_result:
            tr = self.test_result
            parts.append(f"{tr.passed}/{tr.total} tests")

        return " | ".join(parts)


class CodeQualityManager:
    """
    Manages code quality operations.

    Orchestrates formatting, validation, and testing of code files
    with configurable options for each step.
    """

    def __init__(
        self,
        operations_handler: CodeOperationsHandler,
        workspace_root: str,
        enable_formatting: bool = True,
        enable_validation: bool = True,
        enable_testing: bool = True,
        validator: Optional[CodeValidator] = None,
        test_runner: Optional[TestRunner] = None,
    ):
        """
        Initialize code quality manager.

        Args:
            operations_handler: Handler for file operations
            workspace_root: Root directory of workspace
            enable_formatting: Enable auto-formatting with black/isort
            enable_validation: Enable flake8/mypy validation
            enable_testing: Enable auto-running tests
            validator: Custom CodeValidator (optional)
            test_runner: Custom TestRunner (optional)
        """
        self.operations_handler = operations_handler
        self.workspace_root = workspace_root
        self.enable_formatting = enable_formatting
        self.enable_validation = enable_validation
        self.enable_testing = enable_testing

        self.validator = validator or CodeValidator(
            enable_flake8=True, enable_mypy=True
        )

        self.test_runner = test_runner or TestRunner(
            workspace_root=workspace_root, test_dir="tests"
        )

        logger.info(
            f"CodeQualityManager initialized "
            f"(format={enable_formatting}, validate={enable_validation}, test={enable_testing})"
        )

    def process_file(
        self,
        file_path: str,
        format_code: Optional[bool] = None,
        validate_code: Optional[bool] = None,
        run_tests: Optional[bool] = None,
    ) -> CodeQualityResult:
        """
        Process a file with formatting, validation, and testing.

        Args:
            file_path: Absolute path to file
            format_code: Enable formatting (overrides default)
            validate_code: Enable validation (overrides default)
            run_tests: Enable testing (overrides default)

        Returns:
            CodeQualityResult with all results
        """
        # Determine which operations to perform
        do_format = (
            format_code if format_code is not None else self.enable_formatting
        )
        do_validate = (
            validate_code
            if validate_code is not None
            else self.enable_validation
        )
        do_test = run_tests if run_tests is not None else self.enable_testing

        logger.info(
            f"Processing {file_path} "
            f"(format={do_format}, validate={do_validate}, test={do_test})"
        )

        # Format code
        format_result = None
        if do_format:
            logger.debug(f"Formatting {file_path}")
            format_result = self.operations_handler.format_file(file_path)

            if not format_result.success:
                logger.warning(f"Formatting failed: {format_result.error}")

        # Validate code
        validation_result = None
        if do_validate:
            logger.debug(f"Validating {file_path}")
            validation_result = self.validator.validate_file(file_path)

            if validation_result.has_errors:
                logger.warning(
                    f"Validation found {validation_result.error_count} error(s)"
                )

            if validation_result.has_warnings:
                logger.info(
                    f"Validation found {validation_result.warning_count} warning(s)"
                )

        # Run tests
        test_result = None
        if do_test:
            logger.debug(f"Running tests for {file_path}")
            test_result = self.test_runner.run_tests_for_file(file_path)

            if not test_result.success:
                logger.warning(
                    f"Tests failed: {test_result.failed}/{test_result.total}"
                )
            elif test_result.total > 0:
                logger.info(
                    f"Tests passed: {test_result.passed}/{test_result.total}"
                )

        return CodeQualityResult(
            file_path=file_path,
            formatted=do_format,
            format_result=format_result,
            validated=do_validate,
            validation_result=validation_result,
            tested=do_test,
            test_result=test_result,
        )

    def process_files(
        self,
        file_paths: List[str],
        format_code: Optional[bool] = None,
        validate_code: Optional[bool] = None,
        run_tests: Optional[bool] = None,
    ) -> List[CodeQualityResult]:
        """
        Process multiple files with formatting, validation, and testing.

        Args:
            file_paths: List of absolute paths to files
            format_code: Enable formatting (overrides default)
            validate_code: Enable validation (overrides default)
            run_tests: Enable testing (overrides default)

        Returns:
            List of CodeQualityResult objects
        """
        results = []

        for file_path in file_paths:
            result = self.process_file(
                file_path,
                format_code=format_code,
                validate_code=validate_code,
                run_tests=run_tests,
            )
            results.append(result)

        return results

    def get_summary(self, results: List[CodeQualityResult]) -> Dict[str, Any]:
        """
        Get summary statistics for quality check results.

        Args:
            results: List of CodeQualityResult objects

        Returns:
            Dictionary with summary stats
        """
        total_files = len(results)
        files_formatted = sum(1 for r in results if r.formatted)
        files_validated = sum(1 for r in results if r.validated)
        files_tested = sum(1 for r in results if r.tested)

        total_errors = sum(
            r.validation_result.error_count
            for r in results
            if r.validation_result
        )

        total_warnings = sum(
            r.validation_result.warning_count
            for r in results
            if r.validation_result
        )

        test_results = [r.test_result for r in results if r.test_result]
        total_tests = sum(tr.total for tr in test_results)
        tests_passed = sum(tr.passed for tr in test_results)
        tests_failed = sum(tr.failed for tr in test_results)

        files_with_errors = sum(
            1
            for r in results
            if r.validation_result and r.validation_result.has_errors
        )

        files_with_test_failures = sum(
            1 for r in results if r.test_result and not r.test_result.success
        )

        all_success = all(r.success for r in results)

        return {
            "total_files": total_files,
            "files_formatted": files_formatted,
            "files_validated": files_validated,
            "files_tested": files_tested,
            "total_errors": total_errors,
            "total_warnings": total_warnings,
            "files_with_errors": files_with_errors,
            "total_tests": total_tests,
            "tests_passed": tests_passed,
            "tests_failed": tests_failed,
            "files_with_test_failures": files_with_test_failures,
            "success": all_success,
        }

    def format_summary(self, summary: Dict[str, Any]) -> str:
        """
        Format summary as human-readable string.

        Args:
            summary: Summary dictionary from get_summary()

        Returns:
            Formatted summary string
        """
        lines = [
            "Code Quality Summary:",
            f"  Files processed: {summary['total_files']}",
        ]

        if summary["files_formatted"] > 0:
            lines.append(f"  Formatted: {summary['files_formatted']}")

        if summary["files_validated"] > 0:
            lines.append(
                f"  Validated: {summary['files_validated']} "
                f"({summary['total_errors']} errors, {summary['total_warnings']} warnings)"
            )

            if summary["files_with_errors"] > 0:
                lines.append(
                    f"  Files with errors: {summary['files_with_errors']}"
                )

        if summary["files_tested"] > 0:
            lines.append(
                f"  Tests: {summary['tests_passed']}/{summary['total_tests']} passed"
            )

            if summary["files_with_test_failures"] > 0:
                lines.append(
                    f"  Files with test failures: {summary['files_with_test_failures']}"
                )

        status = (
            "✓ All checks passed"
            if summary["success"]
            else "✗ Some checks failed"
        )
        lines.append(f"\n  {status}")

        return "\n".join(lines)
