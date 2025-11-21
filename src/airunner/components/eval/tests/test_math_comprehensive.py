"""
Comprehensive Math Test Suite - Grade School through MATH Level 5.

Tests the agent's ability to solve math problems across all difficulty levels:
- GSM8K (Grade School Math)
- MATH Level 1 (Easiest competition math)
- MATH Level 2
- MATH Level 3 (Medium)
- MATH Level 4
- MATH Level 5 (Hardest competition math)

Each level tests with baseline (no tools) and with tools (reasoning + computation).
"""

import logging
import pytest
import sys
import time
from typing import Dict, Any, List
from airunner.components.eval.benchmark_datasets import (
    extract_numeric_answer,
    answers_are_equivalent,
)
from airunner.components.eval.benchmark_datasets.math_dataset import load_math
from airunner.components.eval.benchmark_datasets.gsm8k_dataset import (
    load_gsm8k,
)
from airunner.components.eval.evaluators import create_correctness_evaluator
from airunner.components.llm.core.tool_registry import ToolCategory
from airunner.settings import AIRUNNER_DEFAULT_LLM_HF_PATH

logger = logging.getLogger(__name__)

# Ensure print flushes immediately for live test output (pytest buffers otherwise).
import builtins as _builtins

_original_print = _builtins.print


def _flush_print(*args, **kwargs):
    if "flush" not in kwargs:
        kwargs["flush"] = True
    result = _original_print(*args, **kwargs)
    sys.stdout.flush()  # Extra flush to ensure pytest sees it
    return result


# Override module-level print to flush by default
print = _flush_print

# Mark ALL tests in this module with longer timeout
pytestmark = [
    pytest.mark.benchmark,
    pytest.mark.timeout(1800),  # 30 minutes for comprehensive suite
]


@pytest.mark.benchmark
class TestMathComprehensive:
    """Comprehensive math test suite covering all difficulty levels."""

    @pytest.fixture(scope="class")
    def gsm8k_samples(self):
        """Load GSM8K (grade school) samples."""
        return load_gsm8k(num_samples=5, split="test", seed=42)

    @pytest.fixture(scope="class")
    def math_samples_level1(self):
        """Load MATH Level 1 (easiest) samples."""
        return load_math(num_samples=5, level="Level 1", split="test", seed=42)

    @pytest.fixture(scope="class")
    def math_samples_level2(self):
        """Load MATH Level 2 samples."""
        return load_math(num_samples=5, level="Level 2", split="test", seed=42)

    @pytest.fixture(scope="class")
    def math_samples_level3(self):
        """Load MATH Level 3 (medium) samples."""
        return load_math(num_samples=5, level="Level 3", split="test", seed=42)

    @pytest.fixture(scope="class")
    def math_samples_level4(self):
        """Load MATH Level 4 samples."""
        return load_math(num_samples=5, level="Level 4", split="test", seed=42)

    @pytest.fixture(scope="class")
    def math_samples_level5(self):
        """Load MATH Level 5 (hardest) samples."""
        return load_math(num_samples=5, level="Level 5", split="test", seed=42)

    def _is_response_complete(self, response: str) -> bool:
        """
        Check if the response appears complete (has a final answer).

        Args:
            response: The LLM response text

        Returns:
            True if response has a final answer marker, False if incomplete/truncated
        """
        # Check for final answer markers
        has_final_marker = any(
            marker in response
            for marker in ["\\boxed{", "####", "final answer is", "Therefore,"]
        )

        # Check if ends properly (not mid-sentence)
        response_stripped = response.rstrip()
        ends_properly = response_stripped.endswith(
            (".", ")", "]", "}", "\\end{pmatrix}", "\\end{bmatrix}")
        )

        # Response is complete if it has a final marker OR ends properly
        return has_final_marker or ends_properly

    def _continue_response(
        self,
        airunner_client,
        original_prompt: str,
        previous_response: str,
        system_prompt: str,
        tool_categories: list,
        max_continuations: int = 10,
    ) -> str:
        """
        Continue an incomplete response until we get a final answer.

        Args:
            airunner_client: The AI Runner client
            original_prompt: The original problem/question
            previous_response: The incomplete response so far
            system_prompt: System prompt to use
            tool_categories: Tool categories to enable
            max_continuations: Maximum number of continuation attempts

        Returns:
            Complete response (original + continuations)
        """
        full_response = previous_response

        for attempt in range(max_continuations):
            if self._is_response_complete(full_response):
                print(f"✓ Response complete after {attempt} continuation(s)")
                break

            print(
                f"\n🔄 Response incomplete, requesting continuation {attempt + 1}/{max_continuations}..."
            )

            # Ask the agent to continue from where it left off
            continuation_prompt = (
                f"Original problem:\n{original_prompt}\n\n"
                f"Your work so far:\n{full_response}\n\n"
                "CONTINUE from where you left off. Complete your solution and "
                "provide the final answer in \\boxed{{}} format. Do not restart - just continue."
            )

            continuation = airunner_client.generate(
                continuation_prompt,
                temperature=0.0,
                max_tokens=4096,
                use_memory=False,
                system_prompt=system_prompt,
                tool_categories=tool_categories,
                model=AIRUNNER_DEFAULT_LLM_HF_PATH,
            )

            continuation_text = continuation.get("text", "")
            full_response += "\n\n" + continuation_text

            print(f"📝 Continuation {attempt + 1}:")
            print(
                continuation_text[:200] + "..."
                if len(continuation_text) > 200
                else continuation_text
            )
        else:
            # Hit max continuations without completing
            if not self._is_response_complete(full_response):
                print(
                    f"\n⚠️  WARNING: Hit max continuations ({max_continuations}) without completing response"
                )

        return full_response

    def _run_test_suite(
        self,
        airunner_client,
        level_name: str,
        samples: List,
        use_tools: bool = False,
    ) -> Dict[str, Any]:
        """
        Run a test suite for a given difficulty level.

        Args:
            airunner_client: The AI Runner client
            level_name: Name of the level (e.g., "GSM8K", "Level 1")
            samples: List of BenchmarkExample instances
            use_tools: Whether to enable tools (reasoning + computation)

        Returns:
            Dictionary with test results
        """
        mode = "With Tools" if use_tools else "Baseline"
        print(f"\n{'='*70}")
        print(f"📊 {level_name.upper()} - {mode.upper()}")
        print(f"{'='*70}")
        if use_tools:
            print("Method: Agent with Polya reasoning + computation tools")
            print(
                "Tools: polya_reasoning, sympy_compute, numpy_compute, python_compute"
            )
        else:
            print("Method: Simple LLM generation with correctness evaluation")
        print(f"Problems: {len(samples)}")
        print(f"{'='*70}\n")

        # System prompts - BOTH use Polya reasoning
        POLYA_BASELINE_PROMPT = """You are a mathematics expert solving problems step-by-step.

**YOUR TASK:**
Solve the problem using the Polya method:
1. Understand the problem - identify what's given and what we need to find
2. Plan the solution - choose appropriate mathematical methods
3. Execute the plan - work through calculations step-by-step
4. Verify the answer - check if the solution makes sense

**CRITICAL RULES:**
1. Work step-by-step through the problem
2. Show your work clearly at each step
3. At the very end, write your final answer in the format: \\boxed{final_answer}
4. Do NOT add any text after the \\boxed{} answer
5. Be extremely careful with calculations - double-check your arithmetic"""

        POLYA_TOOLS_PROMPT = """You are a mathematics expert solving problems step-by-step.

**YOUR TASK:**
Solve the problem using the Polya method:
1. Understand the problem - identify what's given and what we need to find
2. Plan the solution - choose appropriate mathematical methods
3. Execute the plan - work through calculations step-by-step
4. Verify the answer - check if the solution makes sense

**CRITICAL RULES:**
1. Work step-by-step through the problem
2. Use computational tools for complex calculations to ensure accuracy
3. Show your work clearly at each step
4. At the very end, write your final answer in the format: \\boxed{final_answer}
5. Do NOT add any text after the \\boxed{} answer

**NOTE:** Tool usage instructions will be provided automatically by the system."""

        evaluators = [create_correctness_evaluator(airunner_client)]
        results = []
        correct = 0
        total_time = 0

        for i, example in enumerate(samples, 1):
            print(f"\n{'─'*70}")
            print(f"Problem {i}/{len(samples)}")
            subject = example.metadata.get(
                "subject", example.metadata.get("dataset", "Unknown")
            )
            print(f"Subject: {subject}")
            print(f"Question: {example.prompt[:150]}...")
            print(f"Expected: {example.answer}")

            start = time.time()

            # Prepare prompt - BOTH modes use Polya reasoning
            if use_tools:
                prompt_with_instruction = (
                    f"Solve this math problem:\n\n{example.prompt}\n\n"
                    "Work through it step-by-step.\n"
                    "Provide your final answer in the format: \\boxed{{your answer}}"
                )
                system_prompt = POLYA_TOOLS_PROMPT
                tool_cats = [
                    ToolCategory.MATH.value,
                    ToolCategory.ANALYSIS.value,
                ]
            else:
                prompt_with_instruction = (
                    f"Solve this math problem:\n\n{example.prompt}\n\n"
                    "Work through it step-by-step.\n"
                    "Provide your final answer in the format: \\boxed{{your answer}}"
                )
                system_prompt = POLYA_BASELINE_PROMPT
                tool_cats = []

            response = airunner_client.generate(
                prompt_with_instruction,
                temperature=0.0,
                max_tokens=4096,
                use_memory=False,
                system_prompt=system_prompt,
                tool_categories=tool_cats,
                model=AIRUNNER_DEFAULT_LLM_HF_PATH,
            )

            output = response.get("text", "")

            # Check if response is complete, if not, continue it
            if not self._is_response_complete(output):
                print("\n🔄 Response incomplete, requesting continuation...")
                output = self._continue_response(
                    airunner_client=airunner_client,
                    original_prompt=example.prompt,
                    previous_response=output,
                    system_prompt=system_prompt,
                    tool_categories=tool_cats,
                    max_continuations=10,
                )

            # Print response summary
            words = len(output.split())
            chars = len(output)
            print(f"\n📝 Response: {chars} chars, ~{words} words")

            answer = extract_numeric_answer(output)
            print(f"🔍 Extracted answer: '{answer}'")

            # Evaluate
            eval_result = evaluators[0](
                inputs=example.prompt,
                outputs=output,
                reference_outputs=example.reference_output or "",
            )

            score = eval_result["score"]
            elapsed = time.time() - start
            total_time += elapsed

            # Check mathematical equivalence (PRIMARY METRIC)
            is_correct = False
            if answer and example.answer:
                is_correct = answers_are_equivalent(answer, example.answer)

            if is_correct:
                correct += 1

            status = "✅" if is_correct else "❌"
            print(f"\n{status} Answer: {answer}")
            print(f"   Expected: {example.answer}")
            print(f"   Mathematically equivalent: {is_correct}")
            print(f"   Time: {elapsed:.1f}s")

            results.append(
                {
                    "problem": i,
                    "subject": subject,
                    "answer": answer,
                    "expected": example.answer,
                    "correct": is_correct,
                    "score": score,
                    "time": elapsed,
                }
            )

        accuracy = correct / len(results) * 100 if results else 0
        avg_time = total_time / len(results) if results else 0

        print(f"\n{'='*70}")
        print(f"📊 RESULTS - {level_name.upper()} ({mode})")
        print(f"{'='*70}")
        print(f"Correct: {correct}/{len(results)}")
        print(f"Accuracy: {accuracy:.1f}%")
        print(f"Average time: {avg_time:.1f}s per problem")
        print(f"Total time: {total_time/60:.1f} minutes")
        print(f"{'='*70}\n")

        return {
            "level": level_name,
            "mode": mode,
            "accuracy": accuracy,
            "correct": correct,
            "total": len(results),
            "avg_time": avg_time,
            "total_time": total_time,
            "results": results,
        }

    # ===== GSM8K (Grade School Math) Tests =====

    def test_gsm8k_baseline(self, airunner_client, gsm8k_samples):
        """Test GSM8K (grade school math) - Baseline (no tools)."""
        return self._run_test_suite(
            airunner_client,
            "GSM8K (Grade School)",
            gsm8k_samples,
            use_tools=False,
        )

    def test_gsm8k_with_tools(self, airunner_client, gsm8k_samples):
        """Test GSM8K (grade school math) - With tools."""
        return self._run_test_suite(
            airunner_client,
            "GSM8K (Grade School)",
            gsm8k_samples,
            use_tools=True,
        )

    # ===== MATH Level 1 Tests =====

    def test_level1_baseline(self, airunner_client, math_samples_level1):
        """Test MATH Level 1 - Baseline (no tools)."""
        return self._run_test_suite(
            airunner_client,
            "MATH Level 1",
            math_samples_level1,
            use_tools=False,
        )

    def test_level1_with_tools(self, airunner_client, math_samples_level1):
        """Test MATH Level 1 - With tools."""
        return self._run_test_suite(
            airunner_client,
            "MATH Level 1",
            math_samples_level1,
            use_tools=True,
        )

    # ===== MATH Level 2 Tests =====

    def test_level2_baseline(self, airunner_client, math_samples_level2):
        """Test MATH Level 2 - Baseline (no tools)."""
        return self._run_test_suite(
            airunner_client,
            "MATH Level 2",
            math_samples_level2,
            use_tools=False,
        )

    def test_level2_with_tools(self, airunner_client, math_samples_level2):
        """Test MATH Level 2 - With tools."""
        return self._run_test_suite(
            airunner_client,
            "MATH Level 2",
            math_samples_level2,
            use_tools=True,
        )

    # ===== MATH Level 3 Tests =====

    def test_level3_baseline(self, airunner_client, math_samples_level3):
        """Test MATH Level 3 - Baseline (no tools)."""
        return self._run_test_suite(
            airunner_client,
            "MATH Level 3",
            math_samples_level3,
            use_tools=False,
        )

    def test_level3_with_tools(self, airunner_client, math_samples_level3):
        """Test MATH Level 3 - With tools."""
        return self._run_test_suite(
            airunner_client,
            "MATH Level 3",
            math_samples_level3,
            use_tools=True,
        )

    # ===== MATH Level 4 Tests =====

    def test_level4_baseline(self, airunner_client, math_samples_level4):
        """Test MATH Level 4 - Baseline (no tools)."""
        return self._run_test_suite(
            airunner_client,
            "MATH Level 4",
            math_samples_level4,
            use_tools=False,
        )

    def test_level4_with_tools(self, airunner_client, math_samples_level4):
        """Test MATH Level 4 - With tools."""
        return self._run_test_suite(
            airunner_client,
            "MATH Level 4",
            math_samples_level4,
            use_tools=True,
        )

    # ===== MATH Level 5 Tests =====

    def test_level5_baseline(self, airunner_client, math_samples_level5):
        """Test MATH Level 5 - Baseline (no tools)."""
        return self._run_test_suite(
            airunner_client,
            "MATH Level 5",
            math_samples_level5,
            use_tools=False,
        )

    def test_level5_with_tools(self, airunner_client, math_samples_level5):
        """Test MATH Level 5 - With tools."""
        return self._run_test_suite(
            airunner_client,
            "MATH Level 5",
            math_samples_level5,
            use_tools=True,
        )

    # ===== Summary Test (Run all levels) =====

    def test_all_levels_summary(
        self,
        airunner_client,
        gsm8k_samples,
        math_samples_level1,
        math_samples_level2,
        math_samples_level3,
        math_samples_level4,
        math_samples_level5,
    ):
        """
        Run all difficulty levels and print comprehensive summary.

        This test runs both baseline and tool-enabled tests for all levels:
        - GSM8K (Grade School)
        - MATH Levels 1-5

        Prints a comprehensive report card at the end.
        """
        print(f"\n{'#'*70}")
        print("🎓 COMPREHENSIVE MATH TEST SUITE")
        print("Testing from Grade School through Competition Math Level 5")
        print(f"{'#'*70}\n")

        all_results = []

        # Define all test levels
        test_configs = [
            ("GSM8K (Grade School)", gsm8k_samples),
            ("MATH Level 1", math_samples_level1),
            ("MATH Level 2", math_samples_level2),
            ("MATH Level 3", math_samples_level3),
            ("MATH Level 4", math_samples_level4),
            ("MATH Level 5", math_samples_level5),
        ]

        # Run baseline tests
        print(f"\n{'='*70}")
        print("🔹 PHASE 1: BASELINE TESTS (No Tools)")
        print(f"{'='*70}\n")

        for level_name, samples in test_configs:
            result = self._run_test_suite(
                airunner_client, level_name, samples, use_tools=False
            )
            all_results.append(result)

        # Run tool-enabled tests
        print(f"\n{'='*70}")
        print("🔹 PHASE 2: TOOL-ENABLED TESTS (Reasoning + Computation)")
        print(f"{'='*70}\n")

        for level_name, samples in test_configs:
            result = self._run_test_suite(
                airunner_client, level_name, samples, use_tools=True
            )
            all_results.append(result)

        # Print comprehensive summary
        self._print_comprehensive_summary(all_results)

    def _print_comprehensive_summary(self, all_results: List[Dict[str, Any]]):
        """Print comprehensive summary of all test results."""
        print(f"\n{'#'*70}")
        print("📋 COMPREHENSIVE TEST SUMMARY - REPORT CARD")
        print(f"{'#'*70}\n")

        # Group by level
        baseline_results = [r for r in all_results if r["mode"] == "Baseline"]
        tools_results = [r for r in all_results if r["mode"] == "With Tools"]

        # Print baseline summary
        print(f"{'='*70}")
        print("🔹 BASELINE (No Tools) RESULTS")
        print(f"{'='*70}")
        print(f"{'Level':<25} {'Correct':<12} {'Accuracy':<12} {'Avg Time'}")
        print(f"{'-'*70}")

        for result in baseline_results:
            level = result["level"]
            correct = f"{result['correct']}/{result['total']}"
            accuracy = f"{result['accuracy']:.1f}%"
            avg_time = f"{result['avg_time']:.1f}s"
            print(f"{level:<25} {correct:<12} {accuracy:<12} {avg_time}")

        baseline_avg = sum(r["accuracy"] for r in baseline_results) / len(
            baseline_results
        )
        print(f"{'-'*70}")
        print(f"{'OVERALL BASELINE':<25} {'':<12} {baseline_avg:.1f}%")
        print()

        # Print tool-enabled summary
        print(f"{'='*70}")
        print("🔧 WITH TOOLS (Reasoning + Computation) RESULTS")
        print(f"{'='*70}")
        print(f"{'Level':<25} {'Correct':<12} {'Accuracy':<12} {'Avg Time'}")
        print(f"{'-'*70}")

        for result in tools_results:
            level = result["level"]
            correct = f"{result['correct']}/{result['total']}"
            accuracy = f"{result['accuracy']:.1f}%"
            avg_time = f"{result['avg_time']:.1f}s"
            print(f"{level:<25} {correct:<12} {accuracy:<12} {avg_time}")

        tools_avg = sum(r["accuracy"] for r in tools_results) / len(
            tools_results
        )
        print(f"{'-'*70}")
        print(f"{'OVERALL WITH TOOLS':<25} {'':<12} {tools_avg:.1f}%")
        print()

        # Print improvement
        print(f"{'='*70}")
        print("📈 IMPROVEMENT WITH TOOLS")
        print(f"{'='*70}")
        print(
            f"{'Level':<25} {'Baseline':<12} {'With Tools':<12} {'Improvement'}"
        )
        print(f"{'-'*70}")

        for baseline, tools in zip(baseline_results, tools_results):
            level = baseline["level"]
            baseline_acc = f"{baseline['accuracy']:.1f}%"
            tools_acc = f"{tools['accuracy']:.1f}%"
            improvement = tools["accuracy"] - baseline["accuracy"]
            improvement_str = f"{improvement:+.1f}%"
            print(
                f"{level:<25} {baseline_acc:<12} {tools_acc:<12} {improvement_str}"
            )

        overall_improvement = tools_avg - baseline_avg
        print(f"{'-'*70}")
        print(
            f"{'OVERALL':<25} {baseline_avg:.1f}%{'':<6} {tools_avg:.1f}%{'':<6} {overall_improvement:+.1f}%"
        )

        # Print grade
        print(f"\n{'='*70}")
        print("🎓 FINAL GRADE")
        print(f"{'='*70}")

        # Determine grade based on overall accuracy with tools
        if tools_avg >= 90:
            grade = "A"
            comment = "Excellent! Outstanding performance across all levels."
        elif tools_avg >= 80:
            grade = "B"
            comment = (
                "Very Good! Strong performance with room for improvement."
            )
        elif tools_avg >= 70:
            grade = "C"
            comment = "Good. Solid foundation but needs more work on harder problems."
        elif tools_avg >= 60:
            grade = "D"
            comment = "Fair. Struggles with competition math, needs significant improvement."
        else:
            grade = "F"
            comment = (
                "Needs Work. Major improvements needed across all levels."
            )

        print(f"Overall Accuracy (With Tools): {tools_avg:.1f}%")
        print(f"Grade: {grade}")
        print(f"Comment: {comment}")
        print(f"{'='*70}\n")
