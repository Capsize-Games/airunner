"""
test_runner.py

Service for discovering and running relevant tests after code changes.

Finds test files related to modified code and executes them with pytest.
"""

import subprocess
import re
from typing import List, Optional
from pathlib import Path
from dataclasses import dataclass

from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


@dataclass
class TestResult:
    """Result of running tests."""

    success: bool
    total: int
    passed: int
    failed: int
    skipped: int
    errors: int
    duration: float
    output: str
    test_files: List[str]

    def __str__(self):
        status = "✓" if self.success else "✗"
        return f"{status} {self.passed}/{self.total} passed, {self.failed} failed, {self.skipped} skipped ({self.duration:.2f}s)"


class TestRunner:
    """
    Discovers and runs Python tests with pytest.

    Intelligently finds test files related to modified source files
    and executes them.
    """

    def __init__(
        self,
        workspace_root: str,
        test_dir: str = "tests",
        pytest_args: Optional[List[str]] = None,
    ):
        """
        Initialize test runner.

        Args:
            workspace_root: Root directory of workspace
            test_dir: Directory containing tests (relative to workspace_root)
            pytest_args: Additional arguments to pass to pytest
        """
        self.workspace_root = Path(workspace_root)
        self.test_dir = self.workspace_root / test_dir
        self.pytest_args = pytest_args or []

        self._check_pytest_available()

        logger.info(
            f"TestRunner initialized (workspace={workspace_root}, test_dir={test_dir})"
        )

    def _check_pytest_available(self):
        """Check if pytest is installed."""
        try:
            subprocess.run(
                ["pytest", "--version"],
                capture_output=True,
                check=True,
                timeout=5,
            )
            logger.debug("pytest available")
            self.pytest_available = True
        except (
            subprocess.CalledProcessError,
            FileNotFoundError,
            subprocess.TimeoutExpired,
        ):
            logger.warning("pytest not available")
            self.pytest_available = False

    def discover_tests_for_file(self, file_path: str) -> List[str]:
        """
        Discover test files related to a source file.

        Uses common patterns to find corresponding test files:
        - src/module/file.py -> tests/module/test_file.py
        - src/package/module.py -> tests/package/test_module.py

        Args:
            file_path: Absolute path to source file

        Returns:
            List of absolute paths to test files
        """
        file_path = Path(file_path)

        if not file_path.exists():
            logger.warning(f"File does not exist: {file_path}")
            return []

        # Make path relative to workspace root
        try:
            rel_path = file_path.relative_to(self.workspace_root)
        except ValueError:
            logger.warning(f"File not in workspace: {file_path}")
            return []

        test_files = set()

        # Pattern 1: Direct mapping (src/module/file.py -> tests/module/test_file.py)
        if rel_path.parts[0] == "src":
            # Remove 'src' prefix and add test_ prefix to filename
            test_parts = list(rel_path.parts[1:])
            test_parts[-1] = f"test_{test_parts[-1]}"

            test_path = self.test_dir / Path(*test_parts)
            if test_path.exists():
                test_files.add(str(test_path))
                logger.debug(f"Found direct test mapping: {test_path}")

        # Pattern 2: Search for any test file containing the module name
        module_name = file_path.stem

        if self.test_dir.exists():
            for test_file in self.test_dir.rglob(f"test_*{module_name}*.py"):
                test_files.add(str(test_file))
                logger.debug(f"Found test file by name: {test_file}")

            for test_file in self.test_dir.rglob(f"*{module_name}*_test.py"):
                test_files.add(str(test_file))
                logger.debug(f"Found test file by name: {test_file}")

        # Pattern 3: If file is in a package, look for package tests
        if len(rel_path.parts) > 2:  # e.g., src/package/module.py
            package_name = rel_path.parts[1]
            package_test_dir = self.test_dir / package_name

            if package_test_dir.exists():
                for test_file in package_test_dir.rglob("test_*.py"):
                    test_files.add(str(test_file))

        return sorted(test_files)

    def discover_tests_for_files(self, file_paths: List[str]) -> List[str]:
        """
        Discover test files for multiple source files.

        Args:
            file_paths: List of absolute paths to source files

        Returns:
            List of absolute paths to unique test files
        """
        all_tests = set()

        for file_path in file_paths:
            tests = self.discover_tests_for_file(file_path)
            all_tests.update(tests)

        return sorted(all_tests)

    def run_tests(
        self,
        test_files: Optional[List[str]] = None,
        verbose: bool = False,
        capture_output: bool = True,
    ) -> TestResult:
        """
        Run tests with pytest.

        Args:
            test_files: List of test files to run (None = run all tests)
            verbose: Enable verbose output
            capture_output: Capture test output

        Returns:
            TestResult with test execution results
        """
        if not self.pytest_available:
            logger.error("pytest not available")
            return TestResult(
                success=False,
                total=0,
                passed=0,
                failed=0,
                skipped=0,
                errors=0,
                duration=0.0,
                output="pytest not available",
                test_files=[],
            )

        cmd = ["pytest"]

        # Add test files or default to test directory
        if test_files:
            cmd.extend(test_files)
        elif self.test_dir.exists():
            cmd.append(str(self.test_dir))
        else:
            logger.error(f"Test directory not found: {self.test_dir}")
            return TestResult(
                success=False,
                total=0,
                passed=0,
                failed=0,
                skipped=0,
                errors=0,
                duration=0.0,
                output=f"Test directory not found: {self.test_dir}",
                test_files=[],
            )

        # Add verbosity
        if verbose:
            cmd.append("-v")

        # Add custom args
        cmd.extend(self.pytest_args)

        # Always add --tb=short for concise output
        if "--tb" not in " ".join(self.pytest_args):
            cmd.append("--tb=short")

        logger.info(f"Running tests: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                cwd=str(self.workspace_root),
                capture_output=capture_output,
                text=True,
                timeout=300,  # 5 minute timeout
            )

            output = result.stdout + result.stderr

            # Parse pytest output
            parsed_result = self._parse_pytest_output(output)
            parsed_result.test_files = test_files or []

            return parsed_result

        except subprocess.TimeoutExpired:
            logger.error("Test execution timed out")
            return TestResult(
                success=False,
                total=0,
                passed=0,
                failed=0,
                skipped=0,
                errors=0,
                duration=0.0,
                output="Test execution timed out (5 minutes)",
                test_files=test_files or [],
            )

        except Exception as e:
            logger.error(f"Error running tests: {e}")
            return TestResult(
                success=False,
                total=0,
                passed=0,
                failed=0,
                skipped=0,
                errors=0,
                duration=0.0,
                output=str(e),
                test_files=test_files or [],
            )

    def _parse_pytest_output(self, output: str) -> TestResult:
        """
        Parse pytest output to extract test results.

        Args:
            output: pytest stdout/stderr

        Returns:
            TestResult object
        """
        # Default values
        success = False
        total = 0
        passed = 0
        failed = 0
        skipped = 0
        errors = 0
        duration = 0.0

        # Parse summary line: "===== 5 passed, 2 failed in 1.23s ====="
        summary_pattern = (
            r"=+\s*(\d+\s+\w+(?:,\s*\d+\s+\w+)*)\s+in\s+([\d.]+)s?\s*=+"
        )

        match = re.search(summary_pattern, output)
        if match:
            counts_str = match.group(1)
            duration = float(match.group(2))

            # Parse individual counts
            for count_match in re.finditer(r"(\d+)\s+(\w+)", counts_str):
                count = int(count_match.group(1))
                status = count_match.group(2)

                if "pass" in status.lower():
                    passed = count
                elif "fail" in status.lower():
                    failed = count
                elif "skip" in status.lower():
                    skipped = count
                elif "error" in status.lower():
                    errors = count

            total = passed + failed + skipped + errors
            success = failed == 0 and errors == 0

        return TestResult(
            success=success,
            total=total,
            passed=passed,
            failed=failed,
            skipped=skipped,
            errors=errors,
            duration=duration,
            output=output,
            test_files=[],  # Will be set by caller
        )

    def run_tests_for_file(
        self,
        file_path: str,
        verbose: bool = False,
    ) -> TestResult:
        """
        Discover and run tests for a specific file.

        Args:
            file_path: Absolute path to source file
            verbose: Enable verbose output

        Returns:
            TestResult with test execution results
        """
        test_files = self.discover_tests_for_file(file_path)

        if not test_files:
            logger.warning(f"No tests found for {file_path}")
            return TestResult(
                success=True,
                total=0,
                passed=0,
                failed=0,
                skipped=0,
                errors=0,
                duration=0.0,
                output=f"No tests found for {file_path}",
                test_files=[],
            )

        logger.info(f"Running {len(test_files)} test file(s) for {file_path}")

        return self.run_tests(test_files=test_files, verbose=verbose)

    def run_tests_for_files(
        self,
        file_paths: List[str],
        verbose: bool = False,
    ) -> TestResult:
        """
        Discover and run tests for multiple files.

        Args:
            file_paths: List of absolute paths to source files
            verbose: Enable verbose output

        Returns:
            TestResult with test execution results
        """
        test_files = self.discover_tests_for_files(file_paths)

        if not test_files:
            logger.warning(f"No tests found for {len(file_paths)} file(s)")
            return TestResult(
                success=True,
                total=0,
                passed=0,
                failed=0,
                skipped=0,
                errors=0,
                duration=0.0,
                output=f"No tests found for {len(file_paths)} file(s)",
                test_files=[],
            )

        logger.info(
            f"Running {len(test_files)} test file(s) for {len(file_paths)} source file(s)"
        )

        return self.run_tests(test_files=test_files, verbose=verbose)
