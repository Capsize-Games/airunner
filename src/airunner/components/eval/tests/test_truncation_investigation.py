"""
Test to investigate truncation issues in LLM responses.

This test specifically examines why some MATH Level 5 problems are getting
truncated responses (score 0.80) instead of complete answers (score 1.00).

Problems with truncation (from test results):
- Problem 1: Score 0.80 (extracted 'a)' - garbage)
- Problem 4: Score 0.80 (extracted wrong vector - truncated)
- Problem 7: Score 0.80 (extracted '102' instead of '18')
- Problem 9: Score 0.80 (extracted '3' instead of tuple)
"""

import pytest
import time
from airunner.components.eval.benchmark_datasets.math_dataset import load_math
from airunner.components.eval.benchmark_datasets import (
    extract_numeric_answer,
    normalize_answer,
)


pytestmark = [
    pytest.mark.benchmark,
    pytest.mark.timeout(600),  # 10 minutes for investigation
]


@pytest.mark.benchmark
class TestTruncationInvestigation:
    """Investigate why certain problems get truncated responses."""

    @pytest.fixture(scope="class")
    def math_samples(self):
        """Load MATH Level 5 samples."""
        return load_math(
            num_samples=10, level="Level 5", split="test", seed=42
        )

    def test_problem_1_with_increasing_tokens(
        self, airunner_client, math_samples
    ):
        """
        Problem 1: Vector orthogonality problem.

        Test with progressively larger max_tokens to find if truncation
        is purely a token limit issue or something else.
        """
        problem = math_samples[0]  # Problem 1

        print(f"\n{'='*70}")
        print(f"PROBLEM 1 TRUNCATION ANALYSIS")
        print(f"{'='*70}")
        print(f"Question: {problem.prompt[:200]}...")
        print(f"Expected answer: {problem.answer}")

        # Test with increasing token limits
        token_limits = [4096, 8192, 16384, 32768]

        for max_tokens in token_limits:
            print(f"\n{'-'*70}")
            print(f"Testing with max_tokens={max_tokens}")
            print(f"{'-'*70}")

            start = time.time()

            # Use the with_tools approach from test_math_level5
            prompt_with_tools = (
                f"{problem.prompt}\n\n"
                "You have access to these computational tools:\n"
                "- polya_reasoning: Break down the problem step-by-step\n"
                "- sympy_compute: Symbolic mathematics (algebra, calculus, etc.)\n"
                "- numpy_compute: Numerical computations\n"
                "- python_compute: General Python code execution\n"
                "\n"
                "CRITICAL: Use tools to verify your answer. "
                "End your response with: #### final_answer"
            )

            response = airunner_client.generate(
                prompt_with_tools,
                temperature=0.1,
                max_new_tokens=max_tokens,
                tool_categories=["math"],
            )

            elapsed = time.time() - start

            # Extract text from response dict
            response_text = response.get("text") or response.get("message", "")
            response_len = len(response_text)
            extracted = extract_numeric_answer(response_text)
            expected = problem.answer

            # Check if response ends abruptly (truncation indicator)
            has_final_marker = any(
                marker in response_text.lower()
                for marker in ["####", "\\boxed", "final answer", "therefore"]
            )
            ends_complete = response_text.rstrip().endswith(
                (".", ")", "]", "}", "\\end{pmatrix}", "\\end{bmatrix}")
            )

            print(f"Response length: {response_len} characters")
            print(f"Time: {elapsed:.1f}s")
            print(f"Extracted answer: {extracted}")
            print(f"Expected answer: {expected}")
            print(f"Has final marker: {has_final_marker}")
            print(f"Ends complete: {ends_complete}")

            # Show last 200 chars
            print(f"\nLast 200 chars of response:")
            print(f"...{response_text[-200:]}")

            # Check if answers match
            if extracted:
                extracted_norm = normalize_answer(extracted)
                expected_norm = normalize_answer(expected)
                matches = extracted_norm == expected_norm
                print(f"\nAnswer matches: {matches}")

                if matches:
                    print(f"\n✅ SOLUTION FOUND: max_tokens={max_tokens}")
                    break

            if not has_final_marker and not ends_complete:
                print(f"\n⚠️  Response appears TRUNCATED")
            elif not extracted:
                print(f"\n❌ No answer extracted")

    def test_all_truncated_problems_side_by_side(
        self, airunner_client, math_samples
    ):
        """
        Compare all 4 truncated problems to find common patterns.
        """
        # Problems with score 0.80: indices 0, 3, 6, 8
        truncated_indices = [0, 3, 6, 8]
        descriptions = [
            "Problem 1: Vector orthogonality",
            "Problem 4: Reflection matrix",
            "Problem 7: Cosine equation",
            "Problem 9: Arctan/arccos equation",
        ]

        print(f"\n{'='*70}")
        print(f"COMPARING ALL TRUNCATED PROBLEMS")
        print(f"{'='*70}")

        results = []

        for idx, description in zip(truncated_indices, descriptions):
            problem = math_samples[idx]

            print(f"\n{'-'*70}")
            print(f"{description}")
            print(f"{'-'*70}")

            start = time.time()

            prompt_with_tools = (
                f"{problem.prompt}\n\n"
                "Use computational tools to solve this step-by-step.\n"
                "End with: #### final_answer"
            )

            response = airunner_client.generate(
                prompt_with_tools,
                temperature=0.1,
                max_new_tokens=8192,  # Use consistent high limit
                tool_categories=["math"],
            )

            elapsed = time.time() - start

            # Extract text from response dict
            response_text = response.get("text") or response.get("message", "")
            extracted = extract_numeric_answer(response_text)

            has_final_marker = (
                "####" in response_text or "\\boxed" in response_text
            )
            ends_complete = response_text.rstrip().endswith(
                (".", ")", "]", "}", "\\end{pmatrix}")
            )

            result = {
                "description": description,
                "length": len(response_text),
                "time": elapsed,
                "extracted": extracted or "NONE",
                "expected": problem.answer,
                "has_marker": has_final_marker,
                "ends_complete": ends_complete,
                "truncated": not has_final_marker and not ends_complete,
            }
            results.append(result)

            print(f"Length: {result['length']} chars")
            print(f"Time: {result['time']:.1f}s")
            print(f"Extracted: {result['extracted']}")
            print(f"Expected: {result['expected']}")
            print(f"Truncated: {result['truncated']}")

        # Summary
        print(f"\n{'='*70}")
        print(f"SUMMARY")
        print(f"{'='*70}")
        for r in results:
            status = "⚠️  TRUNCATED" if r["truncated"] else "✅ Complete"
            print(f"{r['description']}: {status}")
            print(f"  Length: {r['length']} | Time: {r['time']:.1f}s")
            print(
                f"  {r['extracted'][:50]}... (expected: {r['expected'][:50]}...)"
            )
