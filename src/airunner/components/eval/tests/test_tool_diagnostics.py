"""
Tool Category Diagnostic Tests.

These tests isolate each tool category to diagnose which tools are causing
performance issues. We discovered that enabling tools (MATH + ANALYSIS) causes
a 46.7% accuracy drop compared to baseline Polya reasoning.

This test suite tests each category individually to identify the problem.
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
from airunner.components.llm.core.tool_registry import ToolCategory
from airunner.settings import AIRUNNER_DEFAULT_LLM_HF_PATH

logger = logging.getLogger(__name__)

# Ensure print flushes immediately
import builtins as _builtins

_original_print = _builtins.print


def _flush_print(*args, **kwargs):
    if "flush" not in kwargs:
        kwargs["flush"] = True
    result = _original_print(*args, **kwargs)
    sys.stdout.flush()
    return result


print = _flush_print

pytestmark = [
    pytest.mark.benchmark,
    pytest.mark.timeout(900),  # 15 minutes
]


@pytest.mark.benchmark
class TestToolCategoryDiagnostics:
    """Diagnostic tests to identify which tool categories cause problems."""

    @pytest.fixture(scope="class")
    def gsm8k_samples(self):
        """Load GSM8K (grade school) samples for testing."""
        return load_gsm8k(num_samples=5, split="test", seed=42)

    @pytest.fixture(scope="class")
    def math_samples_level2(self):
        """Load MATH Level 2 samples for testing."""
        return load_math(num_samples=5, level="Level 2", split="test", seed=42)

    def _run_diagnostic_test(
        self,
        airunner_client,
        test_name: str,
        samples: List,
        tool_categories: List[str],
        system_prompt: str,
    ) -> Dict[str, Any]:
        """
        Run a diagnostic test with specific tool categories.

        Args:
            airunner_client: The AI Runner client
            test_name: Name for this diagnostic test
            samples: List of BenchmarkExample instances
            tool_categories: List of tool category strings to enable
            system_prompt: System prompt to use

        Returns:
            Dictionary with test results
        """
        print(f"\n{'='*70}")
        print(f"🔍 DIAGNOSTIC: {test_name}")
        print(f"{'='*70}")
        print(
            f"Tool Categories: {tool_categories if tool_categories else 'NONE'}"
        )
        print(f"Problems: {len(samples)}")
        print(f"{'='*70}\n")

        results = []
        correct = 0
        total_time = 0

        for i, example in enumerate(samples, 1):
            print(f"\n{'─'*70}")
            print(f"Problem {i}/{len(samples)}")
            print(f"Question: {example.prompt[:100]}...")
            print(f"Expected: {example.answer}")

            start = time.time()

            prompt_with_instruction = (
                f"Solve this math problem:\n\n{example.prompt}\n\n"
                "Work through it step-by-step.\n"
                "Provide your final answer in the format: \\boxed{{your answer}}"
            )

            response = airunner_client.generate(
                prompt_with_instruction,
                temperature=0.0,
                max_tokens=4096,
                use_memory=False,
                system_prompt=system_prompt,
                tool_categories=tool_categories,
                model=AIRUNNER_DEFAULT_LLM_HF_PATH,
            )

            output = response.get("text", "")
            elapsed = time.time() - start
            total_time += elapsed

            # Extract answer
            answer = extract_numeric_answer(output)
            print(f"\n🔍 Extracted answer: '{answer}'")

            # Check mathematical equivalence
            is_correct = False
            if answer and example.answer:
                is_correct = answers_are_equivalent(answer, example.answer)

            if is_correct:
                correct += 1

            status = "✅" if is_correct else "❌"
            print(f"{status} Answer: {answer}, Expected: {example.answer}")
            print(f"   Time: {elapsed:.1f}s")

            results.append(
                {
                    "problem": i,
                    "answer": answer,
                    "expected": example.answer,
                    "correct": is_correct,
                    "time": elapsed,
                }
            )

        accuracy = correct / len(results) * 100 if results else 0
        avg_time = total_time / len(results) if results else 0

        print(f"\n{'='*70}")
        print(f"📊 RESULTS - {test_name}")
        print(f"{'='*70}")
        print(f"Correct: {correct}/{len(results)}")
        print(f"Accuracy: {accuracy:.1f}%")
        print(f"Average time: {avg_time:.1f}s per problem")
        print(f"{'='*70}\n")

        return {
            "test_name": test_name,
            "accuracy": accuracy,
            "correct": correct,
            "total": len(results),
            "avg_time": avg_time,
            "tool_categories": tool_categories,
            "results": results,
        }

    # ===== Baseline Test =====

    def test_baseline_no_tools(self, airunner_client, gsm8k_samples):
        """Baseline: Polya reasoning with NO tools."""
        POLYA_PROMPT = """You are a mathematics expert solving problems step-by-step.

**YOUR TASK:**
Solve the problem using the Polya method:
1. Understand the problem
2. Plan the solution
3. Execute the plan
4. Verify the answer

Work step-by-step and provide your final answer in \\boxed{} format."""

        self._run_diagnostic_test(
            airunner_client,
            "Baseline (No Tools)",
            gsm8k_samples,
            tool_categories=[],
            system_prompt=POLYA_PROMPT,
        )

    # ===== Individual Tool Category Tests =====

    def test_math_tools_only(self, airunner_client, gsm8k_samples):
        """Test with ONLY MATH category tools (sympy, numpy, python compute)."""
        PROMPT = """You are a mathematics expert solving problems step-by-step.

**AVAILABLE TOOLS:**
- sympy_compute: Symbolic mathematics (equations, algebra, calculus)
- numpy_compute: Numerical computations (matrices, linear algebra)
- python_compute: General calculations

Use tools when helpful. Provide final answer in \\boxed{} format."""

        self._run_diagnostic_test(
            airunner_client,
            "MATH Tools Only",
            gsm8k_samples,
            tool_categories=[ToolCategory.MATH.value],
            system_prompt=PROMPT,
        )

    def test_analysis_tools_only(self, airunner_client, gsm8k_samples):
        """Test with ONLY ANALYSIS category tools (polya_reasoning, etc.)."""
        PROMPT = """You are a mathematics expert solving problems step-by-step.

**AVAILABLE TOOLS:**
- polya_reasoning: Structured problem-solving framework

Use the polya_reasoning tool to guide your thinking. Provide final answer in \\boxed{} format."""

        self._run_diagnostic_test(
            airunner_client,
            "ANALYSIS Tools Only",
            gsm8k_samples,
            tool_categories=[ToolCategory.ANALYSIS.value],
            system_prompt=PROMPT,
        )

    def test_math_and_analysis_tools(self, airunner_client, gsm8k_samples):
        """Test with BOTH MATH and ANALYSIS tools (current 'with tools' config)."""
        PROMPT = """You are a mathematics expert solving problems step-by-step.

**AVAILABLE TOOLS:**
- polya_reasoning: Structured problem-solving framework
- sympy_compute: Symbolic mathematics
- numpy_compute: Numerical computations
- python_compute: General calculations

Use tools when helpful. Provide final answer in \\boxed{} format."""

        self._run_diagnostic_test(
            airunner_client,
            "MATH + ANALYSIS Tools",
            gsm8k_samples,
            tool_categories=[
                ToolCategory.MATH.value,
                ToolCategory.ANALYSIS.value,
            ],
            system_prompt=PROMPT,
        )

    # ===== Comparison Test on Different Dataset =====

    def test_level2_baseline(self, airunner_client, math_samples_level2):
        """Baseline on MATH Level 2 (harder problems)."""
        POLYA_PROMPT = """You are a mathematics expert solving problems step-by-step.

**YOUR TASK:**
Solve the problem using the Polya method:
1. Understand the problem
2. Plan the solution
3. Execute the plan
4. Verify the answer

Work step-by-step and provide your final answer in \\boxed{} format."""

        self._run_diagnostic_test(
            airunner_client,
            "Level 2 Baseline",
            math_samples_level2,
            tool_categories=[],
            system_prompt=POLYA_PROMPT,
        )

    def test_level2_math_tools_only(
        self, airunner_client, math_samples_level2
    ):
        """MATH Level 2 with ONLY math computation tools."""
        PROMPT = """You are a mathematics expert solving problems step-by-step.

**AVAILABLE TOOLS:**
- sympy_compute: Symbolic mathematics
- numpy_compute: Numerical computations
- python_compute: General calculations

Use tools when helpful. Provide final answer in \\boxed{} format."""

        self._run_diagnostic_test(
            airunner_client,
            "Level 2 MATH Tools",
            math_samples_level2,
            tool_categories=[ToolCategory.MATH.value],
            system_prompt=PROMPT,
        )

    # ===== Summary Test =====

    def test_diagnostic_summary(
        self,
        airunner_client,
        gsm8k_samples,
        math_samples_level2,
    ):
        """Run all diagnostics and print comprehensive summary."""
        print(f"\n{'#'*70}")
        print("🔬 TOOL CATEGORY DIAGNOSTIC SUITE")
        print("Isolating tool categories to identify performance issues")
        print(f"{'#'*70}\n")

        all_results = []

        # GSM8K tests
        print(f"\n{'='*70}")
        print("🎯 GSM8K (Grade School Math) DIAGNOSTICS")
        print(f"{'='*70}\n")

        # Baseline
        POLYA_PROMPT = """You are a mathematics expert solving problems step-by-step.

**YOUR TASK:**
Solve the problem using the Polya method:
1. Understand the problem
2. Plan the solution
3. Execute the plan
4. Verify the answer

Work step-by-step and provide your final answer in \\boxed{} format."""

        baseline_gsm8k = self._run_diagnostic_test(
            airunner_client,
            "Baseline (No Tools)",
            gsm8k_samples,
            tool_categories=[],
            system_prompt=POLYA_PROMPT,
        )
        all_results.append(baseline_gsm8k)

        # MATH tools only
        MATH_PROMPT = """You are a mathematics expert solving problems step-by-step.

**AVAILABLE TOOLS:**
- sympy_compute: Symbolic mathematics (equations, algebra, calculus)
- numpy_compute: Numerical computations (matrices, linear algebra)
- python_compute: General calculations

Use tools when helpful. Provide final answer in \\boxed{} format."""

        math_only_gsm8k = self._run_diagnostic_test(
            airunner_client,
            "MATH Tools Only",
            gsm8k_samples,
            tool_categories=[ToolCategory.MATH.value],
            system_prompt=MATH_PROMPT,
        )
        all_results.append(math_only_gsm8k)

        # ANALYSIS tools only
        ANALYSIS_PROMPT = """You are a mathematics expert solving problems step-by-step.

**AVAILABLE TOOLS:**
- polya_reasoning: Structured problem-solving framework

Use the polya_reasoning tool to guide your thinking. Provide final answer in \\boxed{} format."""

        analysis_only_gsm8k = self._run_diagnostic_test(
            airunner_client,
            "ANALYSIS Tools Only",
            gsm8k_samples,
            tool_categories=[ToolCategory.ANALYSIS.value],
            system_prompt=ANALYSIS_PROMPT,
        )
        all_results.append(analysis_only_gsm8k)

        # Both tools
        BOTH_PROMPT = """You are a mathematics expert solving problems step-by-step.

**AVAILABLE TOOLS:**
- polya_reasoning: Structured problem-solving framework
- sympy_compute: Symbolic mathematics
- numpy_compute: Numerical computations
- python_compute: General calculations

Use tools when helpful. Provide final answer in \\boxed{} format."""

        both_gsm8k = self._run_diagnostic_test(
            airunner_client,
            "MATH + ANALYSIS Tools",
            gsm8k_samples,
            tool_categories=[
                ToolCategory.MATH.value,
                ToolCategory.ANALYSIS.value,
            ],
            system_prompt=BOTH_PROMPT,
        )
        all_results.append(both_gsm8k)

        # Level 2 tests
        print(f"\n{'='*70}")
        print("🎯 MATH LEVEL 2 DIAGNOSTICS")
        print(f"{'='*70}\n")

        baseline_l2 = self._run_diagnostic_test(
            airunner_client,
            "Level 2 Baseline",
            math_samples_level2,
            tool_categories=[],
            system_prompt=POLYA_PROMPT,
        )
        all_results.append(baseline_l2)

        math_l2 = self._run_diagnostic_test(
            airunner_client,
            "Level 2 MATH Tools",
            math_samples_level2,
            tool_categories=[ToolCategory.MATH.value],
            system_prompt=MATH_PROMPT,
        )
        all_results.append(math_l2)

        # Print summary
        self._print_diagnostic_summary(all_results)

    def _print_diagnostic_summary(self, all_results: List[Dict[str, Any]]):
        """Print comprehensive diagnostic summary."""
        print(f"\n{'#'*70}")
        print("📋 DIAGNOSTIC SUMMARY - TOOL CATEGORY ANALYSIS")
        print(f"{'#'*70}\n")

        # GSM8K results
        gsm8k_results = [
            r for r in all_results if "Level 2" not in r["test_name"]
        ]
        level2_results = [
            r for r in all_results if "Level 2" in r["test_name"]
        ]

        print(f"{'='*70}")
        print("GSM8K (Grade School Math) Results")
        print(f"{'='*70}")
        print(
            f"{'Configuration':<30} {'Accuracy':<15} {'Avg Time':<15} {'Change'}"
        )
        print(f"{'-'*70}")

        baseline_acc = next(
            (
                r["accuracy"]
                for r in gsm8k_results
                if "Baseline" in r["test_name"]
            ),
            0,
        )

        for result in gsm8k_results:
            config = result["test_name"]
            accuracy = f"{result['accuracy']:.1f}%"
            avg_time = f"{result['avg_time']:.1f}s"
            change = result["accuracy"] - baseline_acc
            change_str = f"{change:+.1f}%" if "Baseline" not in config else "-"
            print(f"{config:<30} {accuracy:<15} {avg_time:<15} {change_str}")

        print()

        # Level 2 results
        if level2_results:
            print(f"{'='*70}")
            print("MATH Level 2 Results")
            print(f"{'='*70}")
            print(
                f"{'Configuration':<30} {'Accuracy':<15} {'Avg Time':<15} {'Change'}"
            )
            print(f"{'-'*70}")

            baseline_l2_acc = next(
                (
                    r["accuracy"]
                    for r in level2_results
                    if "Baseline" in r["test_name"]
                ),
                0,
            )

            for result in level2_results:
                config = result["test_name"]
                accuracy = f"{result['accuracy']:.1f}%"
                avg_time = f"{result['avg_time']:.1f}s"
                change = result["accuracy"] - baseline_l2_acc
                change_str = (
                    f"{change:+.1f}%" if "Baseline" not in config else "-"
                )
                print(
                    f"{config:<30} {accuracy:<15} {avg_time:<15} {change_str}"
                )

        # Conclusions
        print(f"\n{'='*70}")
        print("🔍 DIAGNOSTIC CONCLUSIONS")
        print(f"{'='*70}")

        # Find worst performer
        tool_results = [
            r for r in gsm8k_results if "Baseline" not in r["test_name"]
        ]
        if tool_results:
            worst = min(tool_results, key=lambda x: x["accuracy"])
            best_tool = max(tool_results, key=lambda x: x["accuracy"])

            print(f"\n📉 Worst Tool Configuration:")
            print(f"   {worst['test_name']}: {worst['accuracy']:.1f}%")
            print(f"   Impact: {worst['accuracy'] - baseline_acc:+.1f}%")

            print(f"\n📈 Best Tool Configuration:")
            print(f"   {best_tool['test_name']}: {best_tool['accuracy']:.1f}%")
            print(f"   Impact: {best_tool['accuracy'] - baseline_acc:+.1f}%")

            if worst["accuracy"] < baseline_acc:
                print(
                    f"\n⚠️  WARNING: ALL tool configurations perform worse than baseline!"
                )
                print(
                    "   This suggests tools are being misused or causing errors."
                )

        print(f"{'='*70}\n")
