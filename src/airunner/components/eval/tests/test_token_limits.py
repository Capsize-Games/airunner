"""
Test to diagnose token limit issues with Problem 1.

This test isolates Problem 1 to understand why it's being truncated
when other problems complete successfully.
"""

import logging
import pytest
import sys
import time
from airunner.components.eval.benchmark_datasets import (
    extract_numeric_answer,
    normalize_answer,
)
from airunner.components.eval.benchmark_datasets.math_dataset import load_math
from airunner.components.llm.core.tool_registry import ToolCategory

logger = logging.getLogger(__name__)

# Force print to flush
import builtins as _builtins

_original_print = _builtins.print


def _flush_print(*args, **kwargs):
    if "flush" not in kwargs:
        kwargs["flush"] = True
    result = _original_print(*args, **kwargs)
    sys.stdout.flush()
    return result


print = _flush_print

pytestmark = [pytest.mark.benchmark, pytest.mark.timeout(600)]  # 10 minutes


@pytest.mark.benchmark
class TestTokenLimits:
    """Test token limit behavior with Problem 1."""

    @pytest.fixture(scope="class")
    def problem_1(self):
        """Load Problem 1 specifically."""
        samples = load_math(
            num_samples=10, level="Level 5", split="test", seed=42
        )
        return samples[0]  # First problem (the one that truncates)

    def test_problem_1_baseline_no_tools(self, airunner_client, problem_1):
        """Test Problem 1 with baseline (no tools) to see if it completes."""
        print(f"\n{'='*70}")
        print("🔍 PROBLEM 1 - BASELINE (No Tools)")
        print(f"{'='*70}")
        print(f"Subject: {problem_1.metadata.get('subject', 'Unknown')}")
        print(f"Question: {problem_1.prompt[:300]}...")
        print(f"Expected: {problem_1.answer}")
        print(f"{'='*70}\n")

        start = time.time()

        prompt = f"{problem_1.prompt}\n\nProvide your final answer in the format: #### [answer]"

        # Test with INCREASING token limits
        for max_tokens in [4096, 8192, 16384, 32768, 65536]:
            print(f"\n{'─'*70}")
            print(f"Testing with max_tokens={max_tokens}")
            print(f"{'─'*70}\n")

            response = airunner_client.generate(
                prompt,
                temperature=0.0,
                max_tokens=max_tokens,
                use_memory=False,
                tool_categories=[],  # No tools
            )

            output = response.get("text", "")

            # Analyze output
            chars = len(output)
            words = len(output.split())
            est_tokens = chars // 4
            has_answer = "\\boxed" in output or "####" in output

            print(
                f"Output length: {chars} chars, ~{words} words, ~{est_tokens} tokens (est)"
            )
            print(f"Has answer marker: {has_answer}")
            print(f"Last 200 chars: ...{output[-200:]}")

            if has_answer:
                print(f"✅ Found answer marker with max_tokens={max_tokens}")
                break
            else:
                print(f"❌ No answer marker - response truncated")

        elapsed = time.time() - start
        print(f"\nTotal time: {elapsed:.1f}s")

        return {"output": output, "time": elapsed}

    def test_problem_1_with_tools_incremental(
        self, airunner_client, problem_1
    ):
        """Test Problem 1 with tools at different token limits."""
        print(f"\n{'='*70}")
        print("🔧 PROBLEM 1 - WITH TOOLS (Incremental)")
        print(f"{'='*70}")
        print(f"Subject: {problem_1.metadata.get('subject', 'Unknown')}")
        print(f"Question: {problem_1.prompt[:300]}...")
        print(f"Expected: {problem_1.answer}")
        print(f"{'='*70}\n")

        SYSTEM_PROMPT = """You are a mathematics expert solving problems systematically.

Use available tools for complex calculations.
Provide your final answer clearly at the end."""

        start = time.time()

        prompt = f"{problem_1.prompt}\n\nProvide your final answer in the format: #### [answer]"

        # Test with INCREASING token limits
        for max_tokens in [8192, 16384, 32768, 65536, 98304, 131072]:
            print(f"\n{'─'*70}")
            print(f"Testing with max_tokens={max_tokens}")
            print(f"{'─'*70}\n")

            response = airunner_client.generate(
                prompt,
                temperature=0.0,
                max_tokens=max_tokens,
                use_memory=False,
                system_prompt=SYSTEM_PROMPT,
                tool_categories=[
                    ToolCategory.MATH.value,
                    ToolCategory.ANALYSIS.value,
                ],
            )

            output = response.get("text", "")

            # Analyze output
            chars = len(output)
            words = len(output.split())
            est_tokens = chars // 4
            has_answer = "\\boxed" in output or "####" in output
            has_tool_calls = "Action:" in output or '{"tool":' in output

            print(
                f"Output length: {chars} chars, ~{words} words, ~{est_tokens} tokens (est)"
            )
            print(f"Has answer marker: {has_answer}")
            print(f"Has tool calls: {has_tool_calls}")
            print(f"Last 300 chars: ...{output[-300:]}")

            if has_answer:
                print(f"✅ Found answer marker with max_tokens={max_tokens}")
                answer = extract_numeric_answer(output)
                print(f"Extracted answer: {answer}")
                print(f"Expected answer: {problem_1.answer}")
                break
            else:
                print(
                    f"❌ No answer marker - response truncated or incomplete"
                )

        elapsed = time.time() - start
        print(f"\nTotal time: {elapsed:.1f}s")

        return {"output": output, "time": elapsed}

    def test_problem_1_character_analysis(self, problem_1):
        """Analyze Problem 1's characteristics."""
        print(f"\n{'='*70}")
        print("📊 PROBLEM 1 - CHARACTER ANALYSIS")
        print(f"{'='*70}\n")

        prompt_chars = len(problem_1.prompt)
        prompt_words = len(problem_1.prompt.split())
        est_prompt_tokens = prompt_chars // 4

        print(f"Prompt length: {prompt_chars} chars")
        print(f"Prompt words: {prompt_words} words")
        print(f"Estimated prompt tokens: ~{est_prompt_tokens}")
        print(f"\nSubject: {problem_1.metadata.get('subject', 'Unknown')}")
        print(f"Expected answer: {problem_1.answer}")
        print(f"\nFull question:")
        print(f"{'─'*70}")
        print(problem_1.prompt)
        print(f"{'─'*70}\n")

    def test_compare_problem_1_vs_problem_2(self, airunner_client):
        """Compare Problem 1 (fails) vs Problem 2 (succeeds)."""
        print(f"\n{'='*70}")
        print("⚖️ COMPARISON: Problem 1 vs Problem 2")
        print(f"{'='*70}\n")

        samples = load_math(
            num_samples=10, level="Level 5", split="test", seed=42
        )
        problem_1 = samples[0]
        problem_2 = samples[1]

        SYSTEM_PROMPT = """You are a mathematics expert solving problems systematically.

Use available tools for complex calculations.
Provide your final answer clearly at the end."""

        for i, problem in enumerate([problem_1, problem_2], 1):
            print(f"\n{'─'*70}")
            print(f"Problem {i}")
            print(f"{'─'*70}")
            print(f"Subject: {problem.metadata.get('subject', 'Unknown')}")
            print(f"Prompt length: {len(problem.prompt)} chars")
            print(f"Expected: {problem.answer}")

            prompt = f"{problem.prompt}\n\nProvide your final answer in the format: #### [answer]"

            start = time.time()
            response = airunner_client.generate(
                prompt,
                temperature=0.0,
                max_tokens=65536,
                use_memory=False,
                system_prompt=SYSTEM_PROMPT,
                tool_categories=[
                    ToolCategory.MATH.value,
                    ToolCategory.ANALYSIS.value,
                ],
            )
            elapsed = time.time() - start

            output = response.get("text", "")
            has_answer = "\\boxed" in output or "####" in output

            print(f"Output length: {len(output)} chars")
            print(f"Generation time: {elapsed:.1f}s")
            print(f"Has answer: {'✅' if has_answer else '❌'}")

            if has_answer:
                answer = extract_numeric_answer(output)
                print(f"Extracted: {answer}")
                is_correct = normalize_answer(answer) == normalize_answer(
                    problem.answer
                )
                print(f"Correct: {'✅' if is_correct else '❌'}")
            else:
                print(f"TRUNCATED - Last 200 chars: ...{output[-200:]}")

        print(f"\n{'='*70}\n")
