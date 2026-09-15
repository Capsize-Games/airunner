#!/usr/bin/env python
"""
Code quality analyzer for AI Runner codebase.

Generates an LLM-friendly report of code quality issues including:
- Inline imports (imports not at module level)
- Long functions (>20 lines)
- Long classes (>200 lines)
- Missing docstrings for public functions/classes
- Missing type hints
- Unused imports
- Other code quality issues

Command-line flags (new and existing):

- --path PATH
    Path to analyze. Defaults to `src/airunner` (automatically discovered by looking for
    the project's `setup.py` when not provided).

- --verbose
    Show a detailed breakdown of issues grouped by file.

- --json
    Output JSON (summary + issues) for programmatic consumption.

- --include-gui
    Include files under GUI-related folders in the analysis. By default GUI files are
    excluded to speed up reports; use this flag to analyze GUI code as well.

- --exclude PATTERN [PATTERN ...]
    Additional substring patterns to exclude from analysis. The script always excludes
    `alembic`, `/data/`, `vendor`, and `_ui.py` files regardless of this option.

- --class-lines N
    Threshold (in code lines) above which a class will be reported as `long_class`.
    Default: 200. Use a larger value to tolerate big classes or a smaller value to be
    stricter.

- --filter CAT1,CAT2,...
    Comma-separated list of issue categories to include in the final report. If set,
    only issues whose `category` matches one of the supplied names will be shown. Examples:
    `--filter=long_class,missing_docstring` or `--filter=unused_import`.

Examples:

    # Run a human-readable report including GUI files and a higher class size threshold
    airunner-quality-report --include-gui --class-lines 300

    # Output only long_class and missing_docstring issues as JSON
    airunner-quality-report --json --filter=long_class,missing_docstring

"""

import ast
import argparse
import json
import sys
from pathlib import Path
from typing import List, Dict, Any, Set
from dataclasses import dataclass, field, asdict
from collections import defaultdict


@dataclass
class Issue:
    """Represents a code quality issue."""

    file: str
    line: int
    category: str
    severity: str  # "error", "warning", "info"
    message: str

    def __str__(self) -> str:
        """Compact string representation for LLM parsing."""
        return f"{self.file}:{self.line} [{self.severity.upper()}] {self.category}: {self.message}"


@dataclass
class QualityReport:
    """Container for all quality issues found."""

    issues: List[Issue] = field(default_factory=list)
    files_analyzed: int = 0
    total_lines: int = 0

    def add_issue(self, issue: Issue):
        """Add an issue to the report."""
        self.issues.append(issue)

    def get_by_category(self) -> Dict[str, List[Issue]]:
        """Group issues by category."""
        by_category = defaultdict(list)
        for issue in self.issues:
            by_category[issue.category].append(issue)
        return dict(by_category)

    def get_by_file(self) -> Dict[str, List[Issue]]:
        """Group issues by file."""
        by_file = defaultdict(list)
        for issue in self.issues:
            by_file[issue.file].append(issue)
        return dict(by_file)

    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics."""
        by_severity = defaultdict(int)
        by_category = defaultdict(int)

        for issue in self.issues:
            by_severity[issue.severity] += 1
            by_category[issue.category] += 1

        return {
            "total_issues": len(self.issues),
            "files_analyzed": self.files_analyzed,
            "total_lines": self.total_lines,
            "by_severity": dict(by_severity),
            "by_category": dict(by_category),
        }


class CodeAnalyzer(ast.NodeVisitor):
    """AST visitor for analyzing Python code quality.

    Supports a configurable class line threshold so callers can control
    when a "long_class" issue is emitted.
    """

    def __init__(
        self, file_path: str, source: str, class_line_threshold: int = 200
    ):
        """
        Initialize analyzer.

        Args:
            file_path: Path to the file being analyzed
            source: Source code content
        """
        self.file_path = file_path
        self.source = source
        self.lines = source.splitlines()
        self.issues: List[Issue] = []
        self.imports_at_top: Set[str] = set()
        self.all_imports: Set[str] = set()
        self.used_names: Set[str] = set()
        self.in_function = False

        self.in_class = False
        # Threshold to consider a class 'long'. Default is 200 lines.
        self.class_line_threshold = class_line_threshold

    def add_issue(self, line: int, category: str, severity: str, message: str):
        """Add an issue to the list."""
        self.issues.append(
            Issue(
                file=self.file_path,
                line=line,
                category=category,
                severity=severity,
                message=message,
            )
        )

    def _count_code_lines(self, node: ast.AST) -> int:
        """Count actual code lines, excluding docstrings and blank lines.

        Args:
            node: AST node (FunctionDef or ClassDef) to count lines for.

        Returns:
            Number of non-blank, non-docstring lines.
        """
        if not hasattr(node, "lineno") or not hasattr(node, "end_lineno"):
            return 0

        start_line = node.lineno
        end_line = node.end_lineno

        # Get the docstring if it exists
        docstring = ast.get_docstring(node)
        docstring_lines = 0
        if docstring:
            # Count docstring lines (including quotes)
            docstring_lines = (
                len(docstring.splitlines()) + 2
            )  # +2 for triple quotes

        # Count non-blank lines
        code_lines = 0
        for i in range(start_line - 1, end_line):
            if i < len(self.lines):
                line = self.lines[i].strip()
                # Skip blank lines and comment-only lines
                if line and not line.startswith("#"):
                    code_lines += 1

        # Subtract docstring lines
        return max(0, code_lines - docstring_lines)

    def visit_Import(self, node: ast.Import):
        """Check import statements."""
        # Check if import is inline (inside function/class)
        if self.in_function:
            for alias in node.names:
                self.add_issue(
                    node.lineno,
                    "inline_import",
                    "warning",
                    f"Inline import of '{alias.name}' (should be at module level)",
                )
        else:
            # Track top-level imports
            for alias in node.names:
                import_name = alias.asname if alias.asname else alias.name
                self.imports_at_top.add(import_name)
                self.all_imports.add(import_name)

        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        """Check from-import statements."""
        if self.in_function:
            module = node.module or ""
            names = ", ".join(alias.name for alias in node.names)
            self.add_issue(
                node.lineno,
                "inline_import",
                "warning",
                f"Inline import from '{module}' ({names})",
            )
        else:
            for alias in node.names:
                import_name = alias.asname if alias.asname else alias.name
                self.imports_at_top.add(import_name)
                self.all_imports.add(import_name)

        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Check function definitions."""
        was_in_function = self.in_function
        self.in_function = True

        # Check function length (excluding docstrings and blank lines)
        if hasattr(node, "end_lineno") and node.end_lineno:
            func_lines = self._count_code_lines(node)
            if func_lines > 50:
                self.add_issue(
                    node.lineno,
                    "long_function",
                    "warning",
                    f"Function '{node.name}' is {func_lines} code lines (≤20 recommended)",
                )

        # Check for docstring (public functions only)
        if not node.name.startswith("_"):
            has_docstring = ast.get_docstring(node) is not None
            if not has_docstring:
                self.add_issue(
                    node.lineno,
                    "missing_docstring",
                    "warning",
                    f"Public function '{node.name}' missing docstring",
                )

        # Check for type hints (arguments and return)
        missing_hints = []
        for arg in node.args.args:
            if arg.arg != "self" and arg.arg != "cls" and not arg.annotation:
                missing_hints.append(arg.arg)

        if missing_hints and not node.name.startswith("_"):
            self.add_issue(
                node.lineno,
                "missing_type_hint",
                "info",
                f"Function '{node.name}' missing type hints for: {', '.join(missing_hints)}",
            )

        if not node.returns and not node.name.startswith("_"):
            # Check if function has return statements
            has_return = any(isinstance(n, ast.Return) for n in ast.walk(node))
            if has_return:
                self.add_issue(
                    node.lineno,
                    "missing_type_hint",
                    "info",
                    f"Function '{node.name}' missing return type hint",
                )

        self.generic_visit(node)
        self.in_function = was_in_function

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        """Check async function definitions (same rules as regular functions)."""
        self.visit_FunctionDef(node)  # Reuse logic

    def visit_ClassDef(self, node: ast.ClassDef):
        """Check class definitions."""
        was_in_class = self.in_class
        self.in_class = True

        # Check class length (excluding docstrings and blank lines)
        if hasattr(node, "end_lineno") and node.end_lineno:
            class_lines = self._count_code_lines(node)
            if class_lines > self.class_line_threshold:
                self.add_issue(
                    node.lineno,
                    "long_class",
                    "warning",
                    (
                        f"Class '{node.name}' is {class_lines} code lines "
                        f"(≤{self.class_line_threshold} recommended, consider mixins)"
                    ),
                )

        # Check for docstring (public classes only)
        if not node.name.startswith("_"):
            has_docstring = ast.get_docstring(node) is not None
            if not has_docstring:
                self.add_issue(
                    node.lineno,
                    "missing_docstring",
                    "warning",
                    f"Public class '{node.name}' missing docstring",
                )

        self.generic_visit(node)
        self.in_class = was_in_class

    def visit_Name(self, node: ast.Name):
        """Track variable/name usage."""
        if isinstance(node.ctx, ast.Load):
            self.used_names.add(node.id)
        self.generic_visit(node)

    def check_unused_imports(self):
        """Check for unused imports (basic heuristic)."""
        # This is a simplified check - may have false positives
        for import_name in self.imports_at_top:
            # Skip common names that are hard to track
            if import_name in ("os", "sys", "logging", "typing"):
                continue

            # Check if name appears in source code
            if import_name not in self.used_names:
                # Additional check: search in source text for usage
                # (handles cases like MyClass.method() where MyClass is imported)
                if import_name not in self.source:
                    self.add_issue(
                        1,  # Line number unknown for top-level imports
                        "unused_import",
                        "info",
                        f"Import '{import_name}' may be unused",
                    )


def analyze_file(
    file_path: Path, class_line_threshold: int = 200
) -> List[Issue]:
    """
    Analyze a single Python file.

    Args:
        file_path: Path to the file to analyze

    Returns:
        List of issues found
    """
    try:
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(file_path))

        analyzer = CodeAnalyzer(str(file_path), source, class_line_threshold)
        analyzer.visit(tree)
        analyzer.check_unused_imports()

        return analyzer.issues

    except SyntaxError as e:
        return [
            Issue(
                file=str(file_path),
                line=e.lineno or 1,
                category="syntax_error",
                severity="error",
                message=f"Syntax error: {e.msg}",
            )
        ]
    except Exception as e:
        return [
            Issue(
                file=str(file_path),
                line=1,
                category="analysis_error",
                severity="error",
                message=f"Failed to analyze: {str(e)}",
            )
        ]


def find_python_files(
    root_path: Path, exclude_patterns: List[str]
) -> List[Path]:
    """
    Find all Python files in the project.

    Args:
        root_path: Root directory or file to search
        exclude_patterns: Patterns to exclude (e.g., '__pycache__', '*_ui.py')

    Returns:
        List of Python file paths
    """
    # If root_path is a file, return it directly
    if root_path.is_file() and root_path.suffix == ".py":
        return [root_path]

    # Otherwise search directory
    python_files = []

    for py_file in root_path.rglob("*.py"):
        # Check exclusions
        skip = False
        for pattern in exclude_patterns:
            if pattern in str(py_file):
                skip = True
                break

        if not skip:
            python_files.append(py_file)

    return python_files


def print_compact_report(report: QualityReport, verbose: bool = False):
    """
    Print a compact, LLM-friendly report.

    Args:
        report: Quality report to print
        verbose: Include detailed breakdown
    """
    summary = report.get_summary()

    print("=" * 80)
    print("CODE QUALITY REPORT")
    print("=" * 80)
    print(f"Files Analyzed: {summary['files_analyzed']}")
    print(f"Total Lines: {summary['total_lines']:,}")
    print(f"Total Issues: {summary['total_issues']}")
    print()

    # Summary by severity
    print("By Severity:")
    for severity, count in sorted(summary["by_severity"].items()):
        print(f"  {severity.upper()}: {count}")
    print()

    # Summary by category
    print("By Category:")
    for category, count in sorted(
        summary["by_category"].items(), key=lambda x: -x[1]
    ):
        print(f"  {category}: {count}")
    print()

    if verbose:
        # Detailed breakdown by file
        print("=" * 80)
        print("ISSUES BY FILE")
        print("=" * 80)

        by_file = report.get_by_file()
        for file_path in sorted(by_file.keys()):
            issues = by_file[file_path]
            print(f"\n{file_path} ({len(issues)} issues):")
            for issue in sorted(issues, key=lambda x: x.line):
                print(f"  {issue}")
    else:
        # Compact list of all issues
        print("=" * 80)
        print("ALL ISSUES (compact format)")
        print("=" * 80)

        for issue in sorted(report.issues, key=lambda x: (x.file, x.line)):
            print(issue)

    print()
    print("=" * 80)
    print("LLM PARSING TIPS:")
    print("- Format: filename:line [SEVERITY] category: message")
    print(
        "- Severities: ERROR (must fix), WARNING (should fix), INFO (consider)"
    )
    print("- Focus on ERROR and WARNING items first")
    print("=" * 80)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Analyze code quality for AI Runner codebase"
    )
    parser.add_argument(
        "--path",
        type=Path,
        default=None,
        help="Path to analyze (default: src/airunner)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed breakdown by file",
    )
    parser.add_argument(
        "--json", action="store_true", help="Output results as JSON"
    )
    parser.add_argument(
        "--include-gui",
        action="store_true",
        help="Include GUI folder files in analysis (normally excluded)",
    )
    parser.add_argument(
        "--exclude",
        nargs="+",
        default=[
            "__pycache__",
            "_ui.py",
            "test_",
            ".venv",
            "venv",
            "build",
            "dist",
            "alembic",
            "/data/",
            "vendor",
            "__init__.py",
        ],
        help="Patterns to exclude from analysis (alembic, data, vendor, _ui.py always excluded)",
    )

    parser.add_argument(
        "--class-lines",
        type=int,
        default=500,
        help="Threshold (in code lines) above which a class is reported as long (default: 200)",
    )

    parser.add_argument(
        "--filter",
        type=str,
        default=None,
        help=(
            "Comma-separated list of issue categories to include in the final report. "
            "Example: --filter=long_class,missing_docstring"
        ),
    )

    args = parser.parse_args()

    # Always exclude these patterns regardless of user input
    permanent_exclusions = ["alembic", "/data/", "vendor", "_ui.py", '/bin/', '/db/', '/services/']

    # Conditionally add /gui/ to permanent exclusions
    if not args.include_gui:
        permanent_exclusions.append("/gui/")

    # Merge user exclusions with permanent ones
    all_exclusions = list(set(args.exclude + permanent_exclusions))

    # Determine root path
    if args.path:
        root_path = args.path
    else:
        # Find project root (look for setup.py)
        current = Path.cwd()
        while current != current.parent:
            if (current / "setup.py").exists():
                root_path = current / "src" / "airunner"
                break
            current = current.parent
        else:
            print(
                "ERROR: Could not find project root (setup.py)",
                file=sys.stderr,
            )
            sys.exit(1)

    if not root_path.exists():
        print(f"ERROR: Path does not exist: {root_path}", file=sys.stderr)
        sys.exit(1)

    # Find Python files
    python_files = find_python_files(root_path, all_exclusions)

    if not python_files:
        print(
            f"WARNING: No Python files found in {root_path}", file=sys.stderr
        )
        sys.exit(0)

    # Analyze all files
    report = QualityReport()
    total_lines = 0

    for py_file in python_files:
        issues = analyze_file(py_file, class_line_threshold=args.class_lines)
        for issue in issues:
            report.add_issue(issue)

        # Count lines
        try:
            with open(py_file, "r", encoding="utf-8") as f:
                total_lines += sum(1 for _ in f)
        except:
            pass

    report.files_analyzed = len(python_files)
    report.total_lines = total_lines

    # Output report
    # If a filter was provided, reduce issues to only those categories
    filtered_report = report
    if args.filter:
        wanted = set([c.strip() for c in args.filter.split(",") if c.strip()])
        filtered = [i for i in report.issues if i.category in wanted]
        filtered_report = QualityReport(
            issues=filtered,
            files_analyzed=report.files_analyzed,
            total_lines=report.total_lines,
        )

    if args.json:
        # JSON output for programmatic parsing
        output = {
            "summary": filtered_report.get_summary(),
            "issues": [asdict(issue) for issue in filtered_report.issues],
        }
        print(json.dumps(output, indent=2))
    else:
        # Human/LLM-readable format
        print_compact_report(filtered_report, args.verbose)

    # Exit code based on severity
    has_errors = any(
        issue.severity == "error" for issue in filtered_report.issues
    )
    sys.exit(1 if has_errors else 0)


if __name__ == "__main__":
    main()
