#!/usr/bin/env python3
"""
Run comprehensive math tests across all levels and compile results.

This script runs individual test methods for each math level and compiles
the results into a comprehensive report card.
"""

import subprocess
import sys
import json
from pathlib import Path
from typing import Dict, List, Any

# Test methods to run (in order)
TESTS = [
    ("GSM8K Baseline", "test_gsm8k_baseline"),
    ("GSM8K With Tools", "test_gsm8k_with_tools"),
    ("Level 1 Baseline", "test_level1_baseline"),
    ("Level 1 With Tools", "test_level1_with_tools"),
    ("Level 2 Baseline", "test_level2_baseline"),
    ("Level 2 With Tools", "test_level2_with_tools"),
    ("Level 3 Baseline", "test_level3_baseline"),
    ("Level 3 With Tools", "test_level3_with_tools"),
    ("Level 4 Baseline", "test_level4_baseline"),
    ("Level 4 With Tools", "test_level4_with_tools"),
    ("Level 5 Baseline", "test_level5_baseline"),
    ("Level 5 With Tools", "test_level5_with_tools"),
]


def run_test(test_method: str) -> Dict[str, Any]:
    """Run a single test and extract results from output."""
    cmd = [
        "pytest",
        f"src/airunner/components/eval/tests/test_math_comprehensive.py::TestMathComprehensive::{test_method}",
        "-s",
        "-v",
        "--timeout=900",  # 15 minutes per test
    ]

    print(f"\n{'='*70}")
    print(f"Running: {test_method}")
    print(f"{'='*70}\n")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=1000,  # 16+ minutes total (includes pytest overhead)
        )

        # Parse output for results
        output = result.stdout

        # Look for the results section
        results = {
            "test": test_method,
            "passed": "PASSED" in output or "passed" in result.stdout.lower(),
            "output": output,
        }

        # Extract accuracy if present
        for line in output.split("\n"):
            if "Accuracy:" in line:
                # Extract percentage
                parts = line.split("Accuracy:")
                if len(parts) > 1:
                    acc_str = parts[1].strip().split("%")[0].strip()
                    try:
                        results["accuracy"] = float(acc_str)
                    except:
                        pass
            if "Correct:" in line:
                # Extract correct/total
                parts = line.split("Correct:")
                if len(parts) > 1:
                    counts = parts[1].strip().split()[0]  # e.g., "8/10"
                    if "/" in counts:
                        correct, total = counts.split("/")
                        results["correct"] = int(correct)
                        results["total"] = int(total)

        return results

    except subprocess.TimeoutExpired:
        print(f"⚠️  Test {test_method} timed out!")
        return {
            "test": test_method,
            "passed": False,
            "timeout": True,
        }
    except Exception as e:
        print(f"⚠️  Test {test_method} failed with error: {e}")
        return {
            "test": test_method,
            "passed": False,
            "error": str(e),
        }


def print_summary(results: List[Dict[str, Any]]):
    """Print comprehensive summary of all test results."""
    print(f"\n{'#'*70}")
    print("📋 COMPREHENSIVE TEST SUMMARY - REPORT CARD")
    print(f"{'#'*70}\n")

    # Group by baseline vs tools
    baseline_results = [
        r
        for r in results
        if "Baseline" in r["test"] or "baseline" in r["test"]
    ]
    tools_results = [
        r for r in results if "Tools" in r["test"] or "tools" in r["test"]
    ]

    # Print baseline summary
    print(f"{'='*70}")
    print("🔹 BASELINE (No Tools) RESULTS")
    print(f"{'='*70}")
    print(f"{'Test':<30} {'Correct':<12} {'Accuracy':<12} {'Status'}")
    print(f"{'-'*70}")

    baseline_accuracies = []
    for result in baseline_results:
        test_name = (
            result["test"].replace("test_", "").replace("_baseline", "")
        )
        correct = f"{result.get('correct', '?')}/{result.get('total', '?')}"
        accuracy = f"{result.get('accuracy', 0):.1f}%"
        status = "✅ PASS" if result.get("passed") else "❌ FAIL"
        print(f"{test_name:<30} {correct:<12} {accuracy:<12} {status}")
        if "accuracy" in result:
            baseline_accuracies.append(result["accuracy"])

    baseline_avg = (
        sum(baseline_accuracies) / len(baseline_accuracies)
        if baseline_accuracies
        else 0
    )
    print(f"{'-'*70}")
    print(f"{'OVERALL BASELINE':<30} {'':<12} {baseline_avg:.1f}%")
    print()

    # Print tool-enabled summary
    print(f"{'='*70}")
    print("🔧 WITH TOOLS (Reasoning + Computation) RESULTS")
    print(f"{'='*70}")
    print(f"{'Test':<30} {'Correct':<12} {'Accuracy':<12} {'Status'}")
    print(f"{'-'*70}")

    tools_accuracies = []
    for result in tools_results:
        test_name = (
            result["test"].replace("test_", "").replace("_with_tools", "")
        )
        correct = f"{result.get('correct', '?')}/{result.get('total', '?')}"
        accuracy = f"{result.get('accuracy', 0):.1f}%"
        status = "✅ PASS" if result.get("passed") else "❌ FAIL"
        print(f"{test_name:<30} {correct:<12} {accuracy:<12} {status}")
        if "accuracy" in result:
            tools_accuracies.append(result["accuracy"])

    tools_avg = (
        sum(tools_accuracies) / len(tools_accuracies)
        if tools_accuracies
        else 0
    )
    print(f"{'-'*70}")
    print(f"{'OVERALL WITH TOOLS':<30} {'':<12} {tools_avg:.1f}%")
    print()

    # Print grade
    print(f"{'='*70}")
    print("🎓 FINAL GRADE")
    print(f"{'='*70}")

    # Determine grade based on overall accuracy with tools
    if tools_avg >= 90:
        grade = "A"
        comment = "Excellent! Outstanding performance across all levels."
    elif tools_avg >= 80:
        grade = "B"
        comment = "Very Good! Strong performance with room for improvement."
    elif tools_avg >= 70:
        grade = "C"
        comment = (
            "Good. Solid foundation but needs more work on harder problems."
        )
    elif tools_avg >= 60:
        grade = "D"
        comment = "Fair. Struggles with competition math, needs significant improvement."
    else:
        grade = "F"
        comment = "Needs Work. Major improvements needed across all levels."

    print(f"Overall Baseline Accuracy: {baseline_avg:.1f}%")
    print(f"Overall Tool-Enabled Accuracy: {tools_avg:.1f}%")
    print(f"Improvement from Tools: {tools_avg - baseline_avg:+.1f}%")
    print(f"\nGrade: {grade}")
    print(f"Comment: {comment}")
    print(f"{'='*70}\n")


def main():
    """Run all tests and print comprehensive summary."""
    print("🎓 COMPREHENSIVE MATH TEST SUITE")
    print("Testing from Grade School through Competition Math Level 5")
    print(f"This will take approximately {len(TESTS) * 2-3} minutes\n")

    all_results = []

    for test_name, test_method in TESTS:
        print(f"\n▶️  Running {test_name}...")
        result = run_test(test_method)
        all_results.append(result)

        # Print quick status
        if result.get("passed"):
            acc = result.get("accuracy", 0)
            correct = result.get("correct", "?")
            total = result.get("total", "?")
            print(f"✅ {test_name}: {correct}/{total} = {acc:.1f}%")
        else:
            print(f"❌ {test_name}: FAILED")

    # Print comprehensive summary
    print_summary(all_results)

    # Save results to file
    output_file = Path("math_test_results.json")
    with open(output_file, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\n📝 Results saved to {output_file}")


if __name__ == "__main__":
    main()
