"""
Level 5 MATH problems test - Agent-based math solving.

Tests the agent's ability to solve hard math problems, optionally using
computational tools (sympy_compute, numpy_compute, python_compute).
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

pytestmark = [
    pytest.mark.benchmark,
    pytest.mark.timeout(0),  # Disable timeout for long tests
]


@pytest.mark.benchmark
class TestMATHLevel5:
    """MATH Level 5 (hardest) problems - Agent-based solving."""

    @pytest.fixture(scope="class")
    def math_samples_level5(self):
        """Load MATH Level 5 samples."""
        return load_math(
            num_samples=10, level="Level 5", split="test", seed=42
        )

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
                max_tokens=4096,  # Increased for long MATH solutions
                use_memory=False,
                tool_categories=[],  # Explicitly disable tools
            )

            print(f"🔧 DEBUG: Response type: {type(response)}", flush=True)
            print(
                f"🔧 DEBUG: Response keys: {list(response.keys())}", flush=True
            )

            output = response.get("text", "")

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

            # Check exact match
            is_correct = False
            if answer and example.answer:
                norm_answer = normalize_answer(answer)
                norm_expected = normalize_answer(example.answer)
                is_correct = norm_answer == norm_expected

            if is_correct or score >= 0.8:
                correct += 1

            status = "✅" if is_correct else "❌"
            print(f"\n{status} Answer: {answer}")
            print(f"   Expected: {example.answer}")
            print(f"   Score: {score:.2f}")
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

        POLYA_SYSTEM_PROMPT = """You are a mathematics expert. Solve problems systematically using Polya's 4-step method.

**POLYA'S METHOD:**
1. UNDERSTAND the problem - identify knowns, unknowns, and constraints
2. PLAN your approach - choose appropriate mathematical methods and tools
3. EXECUTE the plan - perform calculations using available tools
4. VERIFY your solution - check that it makes sense

**TOOL USAGE:**
- polya_reasoning(problem, step, context): Get structured guidance for each Polya step
- sympy_compute(code): Symbolic math, algebra, calculus, exact solutions
- numpy_compute(code): Numerical methods, matrices, approximations
- python_compute(code): General calculations with standard math libraries

**WORKFLOW:**
1. Use polya_reasoning to think through each step
2. When you need to compute, use the math tools (sympy/numpy/python)
3. After getting tool results, provide your final answer as: #### [answer]"""

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
                "Use Polya's method: understand, plan, execute, verify.\n"
                "Use the available tools when helpful.\n"
                "Provide your final answer in the format: #### [your answer]"
            )

            response = airunner_client.generate(
                prompt_with_instruction,
                temperature=0.0,
                max_tokens=4096,  # Higher for multi-step reasoning + tools
                use_memory=False,
                # system_prompt=POLYA_SYSTEM_PROMPT,  # TEMPORARILY DISABLE to test if this is the issue
                tool_categories=[
                    ToolCategory.MATH.value,
                    ToolCategory.ANALYSIS.value,
                ],  # Enable math + reasoning tools
            )

            output = response.get("text", "")

            # Print FULL response for debugging
            print(f"\n{'='*70}")
            print("🤖 FULL LLM Response:")
            print(f"{'='*70}")
            print(output)
            print(f"{'='*70}")

            answer = extract_numeric_answer(output)
            print(f"\n🔍 DEBUG: Extracted answer: '{answer}'")

            # Evaluate
            eval_result = evaluators[0](
                inputs=example.prompt,
                outputs=output,
                reference_outputs=example.reference_output or "",
            )

            score = eval_result["score"]
            elapsed = time.time() - start
            total_time += elapsed

            # Check exact match
            is_correct = False
            if answer and example.answer:
                norm_answer = normalize_answer(answer)
                norm_expected = normalize_answer(example.answer)
                is_correct = norm_answer == norm_expected

            if is_correct or score >= 0.8:
                correct += 1

            status = "✅" if is_correct else "❌"
            print(f"\n{status} Answer: {answer}")
            print(f"   Expected: {example.answer}")
            print(f"   Score: {score:.2f}")
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
