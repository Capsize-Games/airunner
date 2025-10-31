#!/usr/bin/env python3
"""
Update wiki with latest evaluation test results.

This script:
1. Runs comprehensive evaluation tests
2. Parses the results
3. Generates a markdown table
4. Updates the wiki Evaluation-Results.md page

Usage:
    python -m airunner.scripts.update_eval_wiki
    python -m airunner.scripts.update_eval_wiki --wiki-path /custom/path/to/wiki
"""

import argparse
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


def run_eval_tests() -> tuple[str, int]:
    """Run comprehensive evaluation tests and capture output.

    Returns:
        Tuple of (output_text, exit_code)
    """
    print("🔄 Running comprehensive evaluation tests...")
    print("   This may take 20-30 minutes...\n")

    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "-xvs",
        "src/airunner/components/eval/tests/test_benchmark_eval.py::TestMATH::test_math_comprehensive_summary",
        "-m",
        "benchmark",
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=3600,  # 1 hour timeout
        )
        return result.stdout + result.stderr, result.returncode
    except subprocess.TimeoutExpired:
        return "ERROR: Test execution timed out after 1 hour", 1


def parse_test_results(output: str) -> Optional[Dict]:
    """Parse test output and extract results.

    Args:
        output: Raw test output text

    Returns:
        Dict with parsed results or None if parsing failed
    """
    results = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_time": None,
        "categories": [],
        "total_problems": 0,
        "total_passed": 0,
        "overall_score": 0.0,
        "grade": "F",
    }

    # Extract total time
    time_match = re.search(r"Total Time: ([\d.]+) minutes", output)
    if time_match:
        results["total_time"] = float(time_match.group(1))

    # Extract category results from table
    # Format: | Category Name | 5 | 5/5 (100%) | 0.95 |
    table_pattern = r"\|\s*([^|]+?)\s*\|\s*(\d+)\s*\|\s*(\d+)/(\d+)\s*\((\d+)%\)\s*\|\s*([\d.]+)\s*\|"

    for match in re.finditer(table_pattern, output):
        category = match.group(1).strip()
        problems_tested = int(match.group(2))
        passed = int(match.group(3))
        total = int(match.group(4))
        pass_rate = int(match.group(5))
        avg_score = float(match.group(6))

        results["categories"].append(
            {
                "name": category,
                "problems_tested": problems_tested,
                "passed": passed,
                "total": total,
                "pass_rate": pass_rate,
                "avg_score": avg_score,
            }
        )

        results["total_problems"] += problems_tested
        results["total_passed"] += passed

    # Extract overall stats
    overall_match = re.search(
        r"Overall:\s*(\d+)\s*problems,\s*(\d+)\s*passed.*?([\d.]+)%.*?average score:\s*([\d.]+)",
        output,
        re.DOTALL,
    )
    if overall_match:
        results["total_problems"] = int(overall_match.group(1))
        results["total_passed"] = int(overall_match.group(2))
        results["overall_score"] = float(overall_match.group(4))

    # Extract grade
    grade_match = re.search(r"Grade:\s*([A-F])", output)
    if grade_match:
        results["grade"] = grade_match.group(1)

    return results if results["categories"] else None


def generate_markdown(results: Dict) -> str:
    """Generate markdown content for wiki page.

    Args:
        results: Parsed test results

    Returns:
        Markdown formatted string
    """
    md = []
    md.append("# Evaluation Results")
    md.append("")
    md.append(
        "Latest evaluation test results for AI Runner's LLM capabilities."
    )
    md.append("")
    md.append(f"**Last Updated:** {results['timestamp']}")
    md.append("")
    md.append("## Summary")
    md.append("")
    md.append(f"- **Total Problems Tested:** {results['total_problems']}")
    md.append(
        f"- **Problems Passed:** {results['total_passed']}/{results['total_problems']}"
    )
    md.append(
        f"- **Pass Rate:** {results['total_passed']/results['total_problems']*100:.0f}%"
    )
    md.append(f"- **Average Score:** {results['overall_score']:.2f}")
    md.append(f"- **Grade:** {results['grade']}")

    if results["total_time"]:
        md.append(
            f"- **Evaluation Time:** {results['total_time']:.1f} minutes"
        )

    md.append("")
    md.append("## Results by Category")
    md.append("")
    md.append("| Category | Problems | Pass Rate | Avg Score |")
    md.append("|----------|----------|-----------|-----------|")

    for cat in results["categories"]:
        md.append(
            f"| {cat['name']} | {cat['problems_tested']} | "
            f"{cat['passed']}/{cat['total']} ({cat['pass_rate']}%) | "
            f"{cat['avg_score']:.2f} |"
        )

    md.append("")
    md.append("## Interpretation")
    md.append("")
    md.append("### Grading Scale")
    md.append("- **A (0.90-1.00):** Excellent - Production ready")
    md.append("- **B (0.80-0.89):** Good - Minor improvements needed")
    md.append("- **C (0.70-0.79):** Acceptable - Moderate improvements needed")
    md.append("- **D (0.60-0.69):** Poor - Significant improvements needed")
    md.append("- **F (<0.60):** Failing - Major rework required")
    md.append("")
    md.append("## Test Details")
    md.append("")
    md.append("### Datasets")
    md.append(
        "- **GSM8K:** Grade school math problems (basic arithmetic, word problems)"
    )
    md.append(
        "- **MATH Levels 1-5:** Competition-level math problems (increasing difficulty)"
    )
    md.append("")
    md.append("### Evaluation Criteria")
    md.append(
        "- **Correctness:** Accuracy of the answer compared to reference solution"
    )
    md.append("- Evaluated using LLM-as-Judge with temperature=0.3")
    md.append("- Scores normalized to 0-1 scale")
    md.append("")
    md.append("## Running Evaluations")
    md.append("")
    md.append("To run evaluations yourself:")
    md.append("")
    md.append("```bash")
    md.append("# Run comprehensive math evaluation")
    md.append(
        "pytest -xvs src/airunner/components/eval/tests/test_benchmark_eval.py::TestMATH::test_math_comprehensive_summary -m benchmark"
    )
    md.append("")
    md.append("# Update wiki with results")
    md.append("python -m airunner.scripts.update_eval_wiki")
    md.append("```")

    return "\n".join(md)


def update_wiki(markdown: str, wiki_path: Path) -> bool:
    """Write markdown to wiki file.

    Args:
        markdown: Markdown content
        wiki_path: Path to wiki repository

    Returns:
        True if successful
    """
    wiki_file = wiki_path / "Evaluation-Results.md"

    try:
        wiki_file.write_text(markdown)
        print(f"✅ Wiki updated: {wiki_file}")
        return True
    except Exception as e:
        print(f"❌ Failed to write wiki file: {e}")
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run eval tests and update wiki with results"
    )
    parser.add_argument(
        "--wiki-path",
        type=Path,
        default=Path.home() / "Projects" / "airunner.wiki",
        help="Path to wiki repository (default: ~/Projects/airunner.wiki)",
    )
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="Skip running tests, use cached results from /tmp/comprehensive_eval_results.txt",
    )

    args = parser.parse_args()

    # Validate wiki path
    if not args.wiki_path.exists():
        print(f"❌ Wiki path does not exist: {args.wiki_path}")
        print("   Use --wiki-path to specify correct location")
        return 1

    # Run tests or load cached results
    if args.skip_tests:
        cache_file = Path("/tmp/comprehensive_eval_results.txt")
        if not cache_file.exists():
            print(
                "❌ No cached results found at /tmp/comprehensive_eval_results.txt"
            )
            print("   Run without --skip-tests to execute tests")
            return 1

        print(f"📂 Loading cached results from {cache_file}")
        output = cache_file.read_text()
        exit_code = 0
    else:
        output, exit_code = run_eval_tests()

    # Check test success
    if exit_code != 0:
        print(f"⚠️  Tests failed with exit code {exit_code}")
        print("   Continuing to parse available results...")

    # Parse results
    print("📊 Parsing test results...")
    results = parse_test_results(output)

    if not results:
        print("❌ Failed to parse test results")
        print("   Check test output format")
        return 1

    # Display summary
    print("\n" + "=" * 70)
    print("📊 PARSED RESULTS SUMMARY")
    print("=" * 70)
    print(f"Total Problems: {results['total_problems']}")
    print(f"Total Passed: {results['total_passed']}")
    print(f"Average Score: {results['overall_score']:.2f}")
    print(f"Grade: {results['grade']}")
    print(f"Categories: {len(results['categories'])}")
    print("=" * 70 + "\n")

    # Generate markdown
    print("📝 Generating markdown...")
    markdown = generate_markdown(results)

    # Update wiki
    print(f"💾 Updating wiki at {args.wiki_path}...")
    success = update_wiki(markdown, args.wiki_path)

    if success:
        print("\n✅ Wiki update complete!")
        print(f"   Review changes: {args.wiki_path / 'Evaluation-Results.md'}")
        print("   Commit if satisfied with results")
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())
