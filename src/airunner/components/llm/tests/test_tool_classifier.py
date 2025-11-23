#!/usr/bin/env python3
"""
Test the intelligent tool classifier in Auto mode.

This script tests:
1. Simple "hello" prompt → Should select no tools ([] or empty)
2. Web scraping prompt → Should select ["web"]
3. Math prompt → Should select ["math"]
"""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from airunner.components.llm.managers.llm_model_manager import LLMModelManager


def test_classifier():
    """Test the _classify_prompt_for_tools method."""

    # Create a minimal manager instance (don't need full initialization)
    manager = LLMModelManager()

    print("=" * 80)
    print("Testing Tool Classifier")
    print("=" * 80)

    test_cases = [
        ("hello", []),
        ("hi there", []),
        ("how are you?", []),
        (
            "scrape example.com",
            ["search"],
        ),  # search category contains web scraping tools
        ("fetch content from https://example.com", ["search"]),
        ("download the webpage at site.com", ["search"]),
        ("what is 2+2", ["math"]),
        ("calculate 15 * 23", ["math"]),
        ("solve the equation x + 5 = 10", ["math"]),
        ("read file.txt", ["file"]),
        ("save to output.json", ["file"]),
        ("what time is it", ["time"]),
        ("what day is tomorrow", ["time"]),
        ("search for information about Python", ["search"]),
        ("tell me about machine learning", ["search"]),
        ("what is mindwar?", ["search"]),
        ("clear my conversation history", ["conversation"]),
        ("scrape site.com and calculate the sum", ["search", "math"]),
    ]

    print("\nTest Results:")
    print("-" * 80)

    passed = 0
    failed = 0

    for prompt, expected_categories in test_cases:
        result = manager._classify_prompt_for_tools(prompt)

        # Debug the failing case
        if prompt == "fetch content from https://example.com":
            prompt_lower = prompt.lower()
            print(f"\nDEBUG: '{prompt}'")
            print(f"  Lowercased: '{prompt_lower}'")
            print(f"  Contains '-': {'-' in prompt_lower}")
            print(f"  Contains 'http': {'http' in prompt_lower}")

            # Check each math keyword
            math_keywords = [
                "calculate",
                "compute",
                "solve",
                " what is ",
                "how much",
                "equation",
                " math",
                "addition",
                "subtract",
                "multiply",
                "divide",
                " sum ",
                "total",
            ]
            for kw in math_keywords:
                if kw in prompt_lower:
                    print(f"  MATCHED MATH KEYWORD: '{kw}'")

            math_ops = ["+", "*", "/", "="]
            for op in math_ops:
                if op in prompt_lower:
                    print(f"  MATCHED MATH OPERATOR: '{op}'")

            print(f"  Result: {result}\n")

        # Check if all expected categories are present (order doesn't matter)
        matches = set(result) == set(expected_categories)
        status = "✅ PASS" if matches else "❌ FAIL"

        if matches:
            passed += 1
        else:
            failed += 1

        print(f"{status} | Prompt: '{prompt}'")
        print(f"       | Expected: {expected_categories}")
        print(f"       | Got: {result}")
        print()

    print("=" * 80)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 80)

    return failed == 0


if __name__ == "__main__":
    success = test_classifier()
    sys.exit(0 if success else 1)
