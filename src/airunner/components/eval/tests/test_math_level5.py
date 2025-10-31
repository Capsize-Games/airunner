"""
Level 5 MATH problems test - Agent-based math solving.

Tests the agent's ability to solve hard math problems, optionally using
computational tools (sympy_compute, numpy_compute, python_compute).
"""

import logging
import pytest
import sys
import time
from pathlib import Path
from typing import Dict, Any
from airunner.components.eval.benchmark_datasets import (
    extract_numeric_answer,
    normalize_answer,
)
from airunner.components.eval.benchmark_datasets.math_dataset import load_math
from airunner.components.eval.evaluators import create_correctness_evaluator
from airunner.components.llm.core.tool_registry import ToolCategory

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

# Mark ALL tests in this module with longer timeout (300s = 5 minutes)
# MATH Level 5 problems with tools can take 60-120 seconds per problem
pytestmark = [
    pytest.mark.benchmark,
    pytest.mark.timeout(
        600
    ),  # 10 minutes for tool-based generation with continuation
]


@pytest.mark.benchmark
class TestMATHLevel5:
    """Test MATH Level 5 (hardest problems) with baseline and agent approaches."""

    @pytest.fixture(scope="class")
    def math_samples_level5(self):
        """Load MATH Level 5 samples."""
        return load_math(
            num_samples=10, level="Level 5", split="test", seed=42
        )

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
                max_tokens=65536,
                use_memory=False,
                system_prompt=system_prompt,
                tool_categories=tool_categories,
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

    def test_level5_agent_baseline(self, airunner_client, math_samples_level5):
        """Test agent solving Level 5 math problems (baseline - no tools)."""
        print(f"\n{'='*70}")
        print("📊 MATH LEVEL 5 - AGENT BASELINE (No Tools)")
        print(f"{'='*70}")
        print("Method: Simple LLM generation with correctness evaluation")
        print(f"Problems: {len(math_samples_level5)}")
        print(f"{'='*70}\n")

        evaluators = [create_correctness_evaluator(airunner_client)]
        results = []
        correct = 0
        total_time = 0

        for i, example in enumerate(math_samples_level5, 1):
            print(f"\n{'─'*70}")
            print(f"Problem {i}/{len(math_samples_level5)}")
            print(f"Subject: {example.metadata.get('subject', 'Unknown')}")
            print(f"Question: {example.prompt[:150]}...")
            print(f"Expected: {example.answer}")

            start = time.time()

            # Baseline: Simple generation with STRICT answer formatting
            # Enforce \boxed{} format which is standard for MATH dataset
            prompt_with_instruction = (
                f"{example.prompt}\n\n"
                "CRITICAL INSTRUCTIONS:\n"
                "1. Solve this problem step-by-step showing all work\n"
                "2. At the very end, write ONLY: \\boxed{{your_final_answer}}\n"
                "3. Do NOT add any text after the \\boxed{{}} answer\n"
                "4. Do NOT second-guess or change your answer after \\boxed{{}}\n"
                "\n"
                "Begin your solution:"
            )

            print(f"\n🔧 DEBUG: Requesting max_tokens=4096", flush=True)

            response = airunner_client.generate(
                prompt_with_instruction,
                temperature=0.0,
                max_tokens=32768,  # Very high limit to test if truncation is token-related
                use_memory=False,
                tool_categories=[],  # Explicitly disable tools
            )

            print(f"🔧 DEBUG: Response type: {type(response)}", flush=True)
            print(
                f"🔧 DEBUG: Response keys: {list(response.keys())}", flush=True
            )

            output = response.get("text", "")

            # Check if response is complete, if not, continue it
            if not self._is_response_complete(output):
                print("\n🔄 Response incomplete, requesting continuation...")
                output = self._continue_response(
                    airunner_client=airunner_client,
                    original_prompt=example.prompt,
                    previous_response=output,
                    system_prompt="You are a mathematical expert. Solve problems step-by-step.",
                    tool_categories=[],  # No tools for baseline
                    max_continuations=10,
                )

            # Print FULL response for debugging
            print(f"\n{'='*70}")
            print("🤖 FULL LLM Response:")
            print(f"{'='*70}")
            words = len(output.split())
            chars = len(output)
            est_tokens = chars // 4  # Rough estimate: 4 chars per token
            print(
                f"Length: {chars} chars, ~{words} words, ~{est_tokens} tokens (estimate)"
            )
            print(output)
            print(f"{'='*70}")

            answer = extract_numeric_answer(output)
            print(f"\n🔍 DEBUG: Extracted answer: '{answer}'")

            # Evaluate with correctness evaluator
            eval_result = evaluators[0](
                inputs=example.prompt,
                outputs=output,
                reference_outputs=example.reference_output or "",
            )

            score = eval_result["score"]
            elapsed = time.time() - start
            total_time += elapsed

            # Check exact match (PRIMARY METRIC - evaluator is unreliable)
            is_correct = False
            if answer and example.answer:
                norm_answer = normalize_answer(answer)
                norm_expected = normalize_answer(example.answer)
                is_correct = norm_answer == norm_expected

            # Count ONLY exact matches as correct
            # NOTE: LLM evaluator often gives false positives (score 1.00 for wrong answers)
            if is_correct:
                correct += 1

            status = "✅" if is_correct else "❌"
            print(f"\n{status} Answer: {answer}")
            print(f"   Expected: {example.answer}")
            print(f"   Evaluator score: {score:.2f} (unreliable - ignore)")
            print(f"   Exact match: {is_correct}")
            print(f"   Time: {elapsed:.1f}s")

            results.append(
                {
                    "problem": i,
                    "subject": example.metadata.get("subject"),
                    "answer": answer,
                    "expected": example.answer,
                    "correct": is_correct,
                    "score": score,
                    "time": elapsed,
                }
            )

        accuracy = correct / len(results) * 100
        avg_time = total_time / len(results)

        print(f"\n{'='*70}")
        print(f"📊 RESULTS - MATH LEVEL 5 (Baseline)")
        print(f"{'='*70}")
        print(f"Correct: {correct}/{len(results)}")
        print(f"Accuracy: {accuracy:.1f}%")
        print(f"Average time: {avg_time:.1f}s per problem")
        print(f"Total time: {total_time/60:.1f} minutes")
        print(f"{'='*70}\n")

        return {
            "accuracy": accuracy,
            "correct": correct,
            "total": len(results),
            "avg_time": avg_time,
            "results": results,
        }

    def test_level5_agent_with_tools(
        self, airunner_client, math_samples_level5
    ):
        """Test agent solving Level 5 math problems WITH reasoning + math tools."""
        print(f"\n{'='*70}")
        print("🔧 MATH LEVEL 5 - AGENT WITH POLYA + MATH TOOLS")
        print(f"{'='*70}")
        print("Method: Agent with Polya reasoning + computation tools")
        print(
            "Tools: polya_reasoning, sympy_compute, numpy_compute, python_compute"
        )
        print(f"Problems: {len(math_samples_level5)}")
        print(f"{'='*70}\n")

        POLYA_SYSTEM_PROMPT = """You are a competition mathematics expert solving MATH Level 5 problems.

**YOUR TASK:**
Solve the problem step-by-step using the Polya method:
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
6. Focus ONLY on the math problem - no discussion of dates, times, or other topics

**NOTE:** Tool usage instructions will be provided automatically by the system."""

        evaluators = [create_correctness_evaluator(airunner_client)]
        results = []
        correct = 0
        total_time = 0

        for i, example in enumerate(math_samples_level5, 1):
            print(f"\n{'─'*70}")
            print(f"Problem {i}/{len(math_samples_level5)}")
            print(f"Subject: {example.metadata.get('subject', 'Unknown')}")
            print(f"Question: {example.prompt[:150]}...")
            print(f"Expected: {example.answer}")

            start = time.time()

            prompt_with_instruction = (
                f"Solve this math problem:\n\n{example.prompt}\n\n"
                "Work through it step-by-step.\n"
                "Provide your final answer in the format: #### [your answer]"
            )

            response = airunner_client.generate(
                prompt_with_instruction,
                temperature=0.0,
                max_tokens=65536,  # Very high limit - Qwen supports 131k
                use_memory=False,
                system_prompt=POLYA_SYSTEM_PROMPT,  # Math-focused system prompt
                tool_categories=[
                    ToolCategory.MATH.value,
                    ToolCategory.ANALYSIS.value,
                ],  # Enable math + reasoning tools
            )

            output = response.get("text", "")

            # Check if response is complete, if not, continue it
            if not self._is_response_complete(output):
                print("\n🔄 Response incomplete, requesting continuation...")
                output = self._continue_response(
                    airunner_client=airunner_client,
                    original_prompt=example.prompt,
                    previous_response=output,
                    system_prompt=POLYA_SYSTEM_PROMPT,
                    tool_categories=[
                        ToolCategory.MATH.value,
                        ToolCategory.ANALYSIS.value,
                    ],
                    max_continuations=10,
                )

            # Print FULL response for debugging
            print(f"\n{'='*70}")
            print("🤖 FULL LLM Response:")
            print(f"{'='*70}")
            print(output)
            print(f"{'='*70}")

            answer = extract_numeric_answer(output)
            print(f"\n🔍 DEBUG: Extracted answer: '{answer}'")

            # Evaluate with full output (evaluator needs reasoning context)
            eval_result = evaluators[0](
                inputs=example.prompt,
                outputs=output,
                reference_outputs=example.reference_output or "",
            )

            score = eval_result["score"]
            elapsed = time.time() - start
            total_time += elapsed

            # Check exact match (PRIMARY METRIC - evaluator is unreliable)
            is_correct = False
            if answer and example.answer:
                norm_answer = normalize_answer(answer)
                norm_expected = normalize_answer(example.answer)
                is_correct = norm_answer == norm_expected

            # Count ONLY exact matches as correct
            # NOTE: LLM evaluator often gives false positives (score 1.00 for wrong answers)
            if is_correct:
                correct += 1

            status = "✅" if is_correct else "❌"
            print(f"\n{status} Answer: {answer}")
            print(f"   Expected: {example.answer}")
            print(f"   Evaluator score: {score:.2f} (unreliable - ignore)")
            print(f"   Exact match: {is_correct}")
            print(f"   Time: {elapsed:.1f}s")

            results.append(
                {
                    "problem": i,
                    "subject": example.metadata.get("subject"),
                    "answer": answer,
                    "expected": example.answer,
                    "correct": is_correct,
                    "score": score,
                    "time": elapsed,
                }
            )

        accuracy = correct / len(results) * 100
        avg_time = total_time / len(results)

        print(f"\n{'='*70}")
        print(f"📊 RESULTS - MATH LEVEL 5 (With Tools)")
        print(f"{'='*70}")
        print(f"Correct: {correct}/{len(results)}")
        print(f"Accuracy: {accuracy:.1f}%")
        print(f"Average time: {avg_time:.1f}s per problem")
        print(f"Total time: {total_time/60:.1f} minutes")
        print(f"{'='*70}\n")

        return {
            "accuracy": accuracy,
            "correct": correct,
            "total": len(results),
            "avg_time": avg_time,
            "results": results,
        }
