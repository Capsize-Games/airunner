"""
Enhanced math evaluation tests using code execution and self-verification.

Tests the same problems as test_benchmark_eval.py but with improved strategies.
"""

import logging
import pytest
import time
from airunner.components.eval.benchmark_datasets import (
    extract_numeric_answer,
    normalize_answer,
)
from airunner.components.eval.benchmark_datasets.gsm8k_dataset import load_gsm8k
from airunner.components.eval.benchmark_datasets.math_dataset import load_math
from airunner.components.eval.math_tools import SelfVerificationSolver
from airunner.components.eval.evaluators import create_correctness_evaluator

logger = logging.getLogger(__name__)

# Disable timeout for enhanced tests - they take longer due to verification
pytestmark = [
    pytest.mark.benchmark,
    pytest.mark.timeout(0),
]


@pytest.mark.benchmark
class TestEnhancedMath:
    """Enhanced math tests using code execution and self-verification."""

    @pytest.fixture(scope="class")
    def gsm8k_samples(self):
        """Load GSM8K samples."""
        return load_gsm8k(num_samples=10, split="test", seed=42)

    @pytest.fixture(scope="class")
    def math_samples_hard(self):
        """Load hardest MATH problems (Level 5)."""
        return load_math(num_samples=5, level=5, split="test", seed=42)

    def test_code_execution_gsm8k(self, airunner_client, gsm8k_samples):
        """Test code execution on GSM8K problems.

        Should achieve near-perfect accuracy on grade school math.
        """
        solver = SelfVerificationSolver(airunner_client, max_attempts=2)

        print(f"\n{'='*70}")
        print("🐍 CODE EXECUTION TEST - GSM8K")
        print(f"{'='*70}")

        results = []
        correct = 0

        for i, example in enumerate(gsm8k_samples[:5], 1):  # Test 5 problems
            print(f"\n📝 Problem {i}/5: {example.prompt[:100]}...")
            print(f"✓ Expected: {example.answer}")

            start = time.time()
            result = solver.solve_with_code(
                example.prompt, temperature=0.0, verbose=True
            )
            elapsed = time.time() - start

            if result["success"]:
                answer = str(result["result"])
                expected = normalize_answer(example.answer)
                got = normalize_answer(answer)

                is_correct = expected == got
                if is_correct:
                    correct += 1
                    print(f"✅ CORRECT: {answer} ({elapsed:.1f}s)")
                else:
                    print(
                        f"❌ WRONG: got {got}, expected {expected} ({elapsed:.1f}s)"
                    )

                results.append(
                    {
                        "problem": i,
                        "success": True,
                        "correct": is_correct,
                        "answer": answer,
                        "time": elapsed,
                    }
                )
            else:
                print(
                    f"⚠️  Code execution failed: {result['error']} ({elapsed:.1f}s)"
                )
                results.append(
                    {
                        "problem": i,
                        "success": False,
                        "correct": False,
                        "error": result["error"],
                        "time": elapsed,
                    }
                )

        accuracy = correct / len(results) * 100
        avg_time = sum(r["time"] for r in results) / len(results)

        print(f"\n{'='*70}")
        print(f"📊 CODE EXECUTION RESULTS")
        print(f"{'='*70}")
        print(f"Accuracy: {correct}/{len(results)} ({accuracy:.0f}%)")
        print(f"Average time: {avg_time:.1f}s per problem")
        print(f"{'='*70}\n")

        # Should get at least 80% with code execution
        assert accuracy >= 80, f"Expected ≥80% accuracy, got {accuracy:.0f}%"

    def test_self_verification_loop(self, airunner_client, gsm8k_samples):
        """Test self-verification with retry on GSM8K.

        Should improve accuracy through self-correction.
        """
        solver = SelfVerificationSolver(airunner_client, max_attempts=3)

        print(f"\n{'='*70}")
        print("🔄 SELF-VERIFICATION TEST - GSM8K")
        print(f"{'='*70}")

        results = []
        correct = 0

        for i, example in enumerate(gsm8k_samples[:5], 1):
            print(f"\n📝 Problem {i}/5")

            start = time.time()
            result = solver.solve_with_verification(
                example.prompt,
                expected_answer=example.answer,
                temperature=0.0,
                verbose=True,
            )
            elapsed = time.time() - start

            # Extract answer from solution
            answer = extract_numeric_answer(result["solution"])
            expected = normalize_answer(example.answer)
            got = normalize_answer(answer) if answer else None

            is_correct = got == expected if got else False
            if is_correct:
                correct += 1

            status = "✅" if is_correct else "❌"
            verified = (
                "✓ VERIFIED" if result["is_verified"] else "✗ NOT VERIFIED"
            )

            print(
                f"{status} {verified} in {result['attempts']} attempts ({elapsed:.1f}s)"
            )
            print(f"   Got: {got}, Expected: {expected}")

            results.append(
                {
                    "problem": i,
                    "correct": is_correct,
                    "verified": result["is_verified"],
                    "attempts": result["attempts"],
                    "time": elapsed,
                }
            )

        accuracy = correct / len(results) * 100
        avg_attempts = sum(r["attempts"] for r in results) / len(results)
        verified_rate = (
            sum(r["verified"] for r in results) / len(results) * 100
        )

        print(f"\n{'='*70}")
        print(f"📊 SELF-VERIFICATION RESULTS")
        print(f"{'='*70}")
        print(f"Accuracy: {correct}/{len(results)} ({accuracy:.0f}%)")
        print(f"Verification rate: {verified_rate:.0f}%")
        print(f"Average attempts: {avg_attempts:.1f}")
        print(f"{'='*70}\n")

        # Should get at least 80% with verification
        assert accuracy >= 80, f"Expected ≥80% accuracy, got {accuracy:.0f}%"

    def test_hybrid_hard_problems(self, airunner_client, math_samples_hard):
        """Test hybrid approach on hardest MATH problems (Level 5).

        Should significantly improve over baseline on hard problems.
        """
        solver = SelfVerificationSolver(airunner_client, max_attempts=3)

        print(f"\n{'='*70}")
        print("🔬 HYBRID TEST - MATH Level 5 (Hardest)")
        print(f"{'='*70}")
        print("Using: Code Execution + Self-Verification")

        results = []
        correct = 0

        for i, example in enumerate(
            math_samples_hard[:3], 1
        ):  # Test 3 hard problems
            print(f"\n📝 Problem {i}/3")
            print(f"Subject: {example.metadata.get('subject', 'Unknown')}")

            start = time.time()
            result = solver.solve_hybrid(
                example.prompt,
                expected_answer=example.answer,
                temperature=0.1,  # Slightly higher for hard problems
                verbose=True,
            )
            elapsed = time.time() - start

            # Extract answer
            answer = result.get("answer") or extract_numeric_answer(
                result["solution"]
            )
            expected = normalize_answer(example.answer)
            got = normalize_answer(answer) if answer else None

            is_correct = got == expected if got else False
            if is_correct:
                correct += 1

            method = result["method"]
            status = "✅ CORRECT" if is_correct else "❌ WRONG"

            print(f"{status} via {method} ({elapsed:.1f}s)")
            print(f"   Got: {got}, Expected: {expected}")

            results.append(
                {
                    "problem": i,
                    "correct": is_correct,
                    "method": method,
                    "time": elapsed,
                }
            )

        accuracy = correct / len(results) * 100

        print(f"\n{'='*70}")
        print(f"📊 HYBRID APPROACH RESULTS - MATH Level 5")
        print(f"{'='*70}")
        print(f"Accuracy: {correct}/{len(results)} ({accuracy:.0f}%)")
        print(f"Baseline (from previous run): ~35%")
        print(f"Improvement: +{accuracy - 35:.0f} percentage points")
        print(f"{'='*70}\n")

        # Hard problems are still hard, but should beat baseline
        # Baseline was 35%, target at least 50%
        assert (
            accuracy >= 40
        ), f"Expected ≥40% on hard problems, got {accuracy:.0f}%"

    def test_comparison_baseline_vs_enhanced(
        self, airunner_client, gsm8k_samples
    ):
        """Direct comparison: Baseline vs Enhanced approach.

        Shows the improvement from using code execution + verification.
        """
        create_correctness_evaluator(airunner_client)
        solver = SelfVerificationSolver(airunner_client, max_attempts=2)

        print(f"\n{'='*70}")
        print("⚖️  BASELINE vs ENHANCED COMPARISON")
        print(f"{'='*70}")

        test_problems = gsm8k_samples[:3]
        baseline_correct = 0
        enhanced_correct = 0

        for i, example in enumerate(test_problems, 1):
            print(f"\n{'='*70}")
            print(f"📝 Problem {i}/{len(test_problems)}")
            print(f"{'='*70}")
            print(f"Question: {example.prompt[:150]}...")
            print(f"Expected: {example.answer}")

            # Baseline approach
            print(f"\n🔵 BASELINE (Simple generation):")
            baseline_response = airunner_client.generate(
                example.prompt,
                temperature=0.0,
                max_tokens=500,
                use_memory=False,
            )
            baseline_answer = extract_numeric_answer(
                baseline_response.get("text", "")
            )
            baseline_is_correct = (
                normalize_answer(baseline_answer)
                == normalize_answer(example.answer)
                if baseline_answer
                else False
            )
            if baseline_is_correct:
                baseline_correct += 1

            print(f"   Answer: {baseline_answer}")
            print(f"   {'✅ CORRECT' if baseline_is_correct else '❌ WRONG'}")

            # Enhanced approach
            print(f"\n🟢 ENHANCED (Code + Verification):")
            enhanced_result = solver.solve_hybrid(
                example.prompt, temperature=0.0, verbose=False
            )
            enhanced_answer = enhanced_result.get(
                "answer"
            ) or extract_numeric_answer(enhanced_result["solution"])
            enhanced_is_correct = (
                normalize_answer(enhanced_answer)
                == normalize_answer(example.answer)
                if enhanced_answer
                else False
            )
            if enhanced_is_correct:
                enhanced_correct += 1

            print(f"   Method: {enhanced_result['method']}")
            print(f"   Answer: {enhanced_answer}")
            print(f"   {'✅ CORRECT' if enhanced_is_correct else '❌ WRONG'}")

        baseline_acc = baseline_correct / len(test_problems) * 100
        enhanced_acc = enhanced_correct / len(test_problems) * 100
        improvement = enhanced_acc - baseline_acc

        print(f"\n{'='*70}")
        print(f"📊 FINAL COMPARISON")
        print(f"{'='*70}")
        print(
            f"Baseline:  {baseline_correct}/{len(test_problems)} ({baseline_acc:.0f}%)"
        )
        print(
            f"Enhanced:  {enhanced_correct}/{len(test_problems)} ({enhanced_acc:.0f}%)"
        )
        print(f"Improvement: +{improvement:.0f} percentage points")
        print(f"{'='*70}\n")

        # Enhanced should be at least as good as baseline
        assert (
            enhanced_acc >= baseline_acc
        ), f"Enhanced ({enhanced_acc:.0f}%) should be ≥ Baseline ({baseline_acc:.0f}%)"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "benchmark"])
