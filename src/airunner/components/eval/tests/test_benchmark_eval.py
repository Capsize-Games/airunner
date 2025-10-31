"""
Benchmark evaluation tests using standard datasets.

Tests AI Runner's LLM capabilities against GSM8K, MATH, and HumanEval benchmarks.
"""

import logging
import pytest
import time
from typing import Dict, Any
from airunner.components.eval.benchmark_datasets import extract_numeric_answer, normalize_answer
from airunner.components.eval.benchmark_datasets.benchmark_example import BenchmarkExample
from airunner.components.eval.benchmark_datasets.gsm8k_dataset import load_gsm8k
from airunner.components.eval.benchmark_datasets.human_eval_dataset import load_humaneval
from airunner.components.eval.benchmark_datasets.math_dataset import load_math
from airunner.components.eval.evaluators import (
    create_correctness_evaluator,
    create_helpfulness_evaluator,
)

logger = logging.getLogger(__name__)

# Disable timeout for benchmark tests - they need time for model loading + generation + evaluation
# Each test: ~40s generation + 2x40s evaluation = ~120s total
pytestmark = [
    pytest.mark.benchmark,
    pytest.mark.timeout(0),  # 0 = disable timeout
]


def run_benchmark_test(
    client,
    example: BenchmarkExample,
    evaluators: list,
    min_score: float = 0.6,
    raise_on_fail: bool = True,
    verbose: bool = True,
) -> Dict[str, Any]:
    """Run a single benchmark test case.

    Args:
        client: AIRunnerClient instance
        example: BenchmarkExample to test
        evaluators: List of evaluators
        min_score: Minimum acceptable score
        raise_on_fail: Whether to call pytest.fail() on failure
        verbose: Whether to print detailed output

    Returns:
        Dict with test results
    """
    prompt = example.prompt
    reference = example.reference_output
    category = example.category
    difficulty = example.difficulty
    expected_answer = example.answer

    if verbose:
        print(f"\n{'='*70}")
        print(f"📝 Category: {category} | Difficulty: {difficulty}")
        print(f"❓ Prompt: {prompt[:200]}...")
        if expected_answer:
            print(f"✓ Expected answer: {expected_answer}")

    # Generate response
    try:
        response = client.generate(
            prompt,
            temperature=0.0,
            max_tokens=1000,
            use_memory=False,  # Disable conversation history for isolated tests
        )
        output = response.get("text", "")

        # Debug: Check if response is empty
        if not output or not output.strip():
            if verbose:
                print(f"⚠️  WARNING: Empty response received!")
                print(f"   Response object: {response}")
                print(f"   Response keys: {list(response.keys())}")
            pytest.fail("Generation returned empty response")
    except Exception as e:
        if verbose:
            print(f"❌ Generation failed: {e}")
        pytest.fail(f"Generation failed: {e}")

    if verbose:
        print(f"🤖 Response: {output[:300]}...")

    # Extract answer from response
    if category.startswith("math"):
        generated_answer = extract_numeric_answer(output)
        if verbose:
            print(f"🔢 Extracted answer: {generated_answer}")

        # Check exact match
        if expected_answer and generated_answer:
            norm_expected = normalize_answer(expected_answer)
            norm_generated = normalize_answer(generated_answer)
            exact_match = norm_expected == norm_generated
            match_status = "✅" if exact_match else "❌"
            if verbose:
                print(
                    f"{match_status} Exact match: "
                    f"{norm_generated} vs {norm_expected}"
                )

    # Run evaluators
    evaluation_results = {}
    all_passed = True

    for evaluator in evaluators:
        result = evaluator(
            inputs=prompt,
            outputs=output,
            reference_outputs=reference,
        )

        feedback_key = result["feedback_key"]
        score = result["score"]
        reasoning = result["reasoning"]

        evaluation_results[feedback_key] = result

        passed = score >= min_score
        status = "✅" if passed else "❌"
        if verbose:
            print(f"{status} {feedback_key}: {score:.2f}/1.0 - {reasoning}")

        if not passed:
            all_passed = False

    # Overall result
    if verbose:
        if all_passed:
            print(f"{'='*70}")
            print("✅ TEST PASSED - All evaluations met minimum score")
        else:
            print(f"{'='*70}")
            print("❌ TEST FAILED - Some evaluations below minimum score")

    if not all_passed and raise_on_fail:
        pytest.fail(
            f"Evaluation failed: Some scores below {min_score}. "
            f"Results: {evaluation_results}"
        )

    return {
        "prompt": prompt,
        "output": output,
        "reference": reference,
        "expected_answer": expected_answer,
        "category": category,
        "difficulty": difficulty,
        "evaluations": evaluation_results,
        "passed": all_passed,
        "metadata": example.metadata,
    }


@pytest.mark.benchmark
@pytest.mark.llm_required
class TestGSM8K:
    """Tests using GSM8K dataset (grade school math)."""

    @pytest.fixture(scope="class")
    def gsm8k_samples(self):
        """Load GSM8K samples for testing."""
        return load_gsm8k(num_samples=10, split="test", seed=42)

    def test_gsm8k_sample_1(self, airunner_client, gsm8k_samples):
        """Test GSM8K problem #1."""
        evaluators = [
            create_correctness_evaluator(airunner_client),
            # TODO: Fix mood system prompt issue before re-enabling
            # create_helpfulness_evaluator(airunner_client),
        ]
        run_benchmark_test(
            airunner_client,
            gsm8k_samples[0],
            evaluators,
            min_score=0.6,
        )

    def test_gsm8k_sample_2(self, airunner_client, gsm8k_samples):
        """Test GSM8K problem #2."""
        evaluators = [
            create_correctness_evaluator(airunner_client),
        ]
        run_benchmark_test(
            airunner_client,
            gsm8k_samples[1],
            evaluators,
            min_score=0.6,
        )

    def test_gsm8k_sample_3(self, airunner_client, gsm8k_samples):
        """Test GSM8K problem #3."""
        evaluators = [
            create_correctness_evaluator(airunner_client),
        ]
        run_benchmark_test(
            airunner_client,
            gsm8k_samples[2],
            evaluators,
            min_score=0.6,
        )

    @pytest.mark.slow
    def test_gsm8k_batch(self, airunner_client, gsm8k_samples):
        """Test batch of GSM8K problems.

        This runs all 10 samples and reports statistics.
        """
        evaluators = [create_correctness_evaluator(airunner_client)]

        results = []
        for i, example in enumerate(gsm8k_samples):
            print(f"\n{'#'*70}")
            print(f"Running GSM8K problem {i+1}/{len(gsm8k_samples)}")
            print(f"{'#'*70}")

            try:
                result = run_benchmark_test(
                    airunner_client,
                    example,
                    evaluators,
                    min_score=0.5,  # Lower threshold for batch test
                    raise_on_fail=False,  # Don't stop on failures
                )
                results.append(result)
            except Exception as e:
                print(f"⚠️  Problem {i+1} failed: {e}")

        # Print summary
        print(f"\n{'='*70}")
        print("📊 GSM8K BATCH TEST SUMMARY")
        print(f"{'='*70}")
        print(f"Total problems: {len(results)}")
        print(f"Passed: {sum(1 for r in results if r['passed'])}")
        print(f"Failed: {sum(1 for r in results if not r['passed'])}")

        if results:
            correctness_scores = [
                r["evaluations"]["correctness"]["score"]
                for r in results
                if "correctness" in r["evaluations"]
            ]
            if correctness_scores:
                avg = sum(correctness_scores) / len(correctness_scores)
                print(f"Average correctness: {avg:.2f}/1.0")


@pytest.mark.benchmark
@pytest.mark.llm_required
class TestMATH:
    """Tests using MATH dataset (competition mathematics)."""

    @pytest.fixture(scope="class")
    def gsm8k_samples(self):
        """Load GSM8K samples (shared with comprehensive test)."""
        return load_gsm8k(num_samples=10, split="test", seed=42)

    @pytest.fixture(scope="class")
    def math_samples_easy(self):
        """Load easy MATH samples (Level 1)."""
        return load_math(
            num_samples=10, split="test", level="Level 1", seed=42
        )

    @pytest.fixture(scope="class")
    def math_samples_medium(self):
        """Load medium MATH samples (Level 3)."""
        return load_math(
            num_samples=10, split="test", level="Level 3", seed=42
        )

    def test_math_level1_problem_1(self, airunner_client, math_samples_easy):
        """Test MATH Level 1 problem."""
        evaluators = [
            create_correctness_evaluator(airunner_client),
            # FIXME: helpfulness evaluator calls tools despite tool_categories=[]
            # create_helpfulness_evaluator(airunner_client),
        ]
        run_benchmark_test(
            airunner_client,
            math_samples_easy[0],
            evaluators,
            min_score=0.6,
        )

    def test_math_level1_problem_2(self, airunner_client, math_samples_easy):
        """Test MATH Level 1 problem #2."""
        evaluators = [create_correctness_evaluator(airunner_client)]
        run_benchmark_test(
            airunner_client,
            math_samples_easy[1],
            evaluators,
            min_score=0.6,
        )

    @pytest.mark.slow
    def test_math_level3_problem_1(self, airunner_client, math_samples_medium):
        """Test MATH Level 3 problem (harder)."""
        evaluators = [
            create_correctness_evaluator(airunner_client),
            # FIXME: helpfulness evaluator calls tools despite tool_categories=[]
            # create_helpfulness_evaluator(airunner_client),
        ]
        run_benchmark_test(
            airunner_client,
            math_samples_medium[0],
            evaluators,
            min_score=0.5,  # Lower threshold for harder problems
        )

    @pytest.mark.slow
    def test_math_batch_level1(self, airunner_client, math_samples_easy):
        """Test batch of Level 1 MATH problems."""
        evaluators = [create_correctness_evaluator(airunner_client)]

        results = []
        for i, example in enumerate(math_samples_easy):
            print(f"\n{'#'*70}")
            print(
                f"Running MATH Level 1 problem {i+1}/{len(math_samples_easy)}"
            )
            print(f"{'#'*70}")

            try:
                result = run_benchmark_test(
                    airunner_client,
                    example,
                    evaluators,
                    min_score=0.5,
                )
                results.append(result)
            except Exception as e:
                print(f"⚠️  Problem {i+1} failed: {e}")

        # Print summary
        print(f"\n{'='*70}")
        print("📊 MATH LEVEL 1 BATCH TEST SUMMARY")
        print(f"{'='*70}")
        print(f"Total problems: {len(results)}")
        print(f"Passed: {sum(1 for r in results if r['passed'])}")

        if results:
            correctness_scores = [
                r["evaluations"]["correctness"]["score"]
                for r in results
                if "correctness" in r["evaluations"]
            ]
            if correctness_scores:
                avg = sum(correctness_scores) / len(correctness_scores)
                print(f"Average correctness: {avg:.2f}/1.0")

    @pytest.fixture(scope="class")
    def math_samples_level2(self):
        """Load MATH Level 2 samples."""
        return load_math(
            num_samples=10, split="test", level="Level 2", seed=42
        )

    @pytest.fixture(scope="class")
    def math_samples_level4(self):
        """Load MATH Level 4 samples (challenging)."""
        return load_math(
            num_samples=10, split="test", level="Level 4", seed=42
        )

    @pytest.fixture(scope="class")
    def math_samples_level5(self):
        """Load MATH Level 5 samples (very hard)."""
        return load_math(
            num_samples=10, split="test", level="Level 5", seed=42
        )

    @pytest.mark.slow
    def test_math_comprehensive_summary(
        self,
        airunner_client,
        math_samples_easy,
        math_samples_level2,
        math_samples_medium,
        math_samples_level4,
        math_samples_level5,
        gsm8k_samples,
    ):
        """Comprehensive math test across all difficulty levels.

        This test:
        - Runs problems from GSM8K (grade school)
        - Runs MATH problems from Level 1-5
        - Generates a comprehensive summary report
        """
        evaluators = [create_correctness_evaluator(airunner_client)]

        all_results = {
            "GSM8K (Grade School)": [],
            "MATH Level 1": [],
            "MATH Level 2": [],
            "MATH Level 3": [],
            "MATH Level 4": [],
            "MATH Level 5": [],
        }

        tests_per_category = 10

        test_sets = [
            ("GSM8K (Grade School)", gsm8k_samples[:tests_per_category]),
            ("MATH Level 1", math_samples_easy[:tests_per_category]),
            ("MATH Level 2", math_samples_level2[:tests_per_category]),
            ("MATH Level 3", math_samples_medium[:tests_per_category]),
            ("MATH Level 4", math_samples_level4[:tests_per_category]),
            ("MATH Level 5", math_samples_level5[:tests_per_category]),
        ]

        # Calculate total problems
        total_problems = sum(len(samples) for _, samples in test_sets)
        problems_completed = 0
        test_start_time = time.time()

        print(f"\n{'='*70}", flush=True)
        print("🚀 STARTING COMPREHENSIVE MATH EVALUATION", flush=True)
        print(f"{'='*70}", flush=True)
        print(f"📊 Total problems to test: {total_problems}", flush=True)
        print(f"📂 Categories: {len(test_sets)}", flush=True)
        print(
            f"⏱️  Estimated time: {total_problems * 1.5:.0f}-{total_problems * 2:.0f} minutes",
            flush=True,
        )
        print(f"{'='*70}\n", flush=True)

        for category_idx, (category, samples) in enumerate(test_sets, 1):
            print(f"\n{'#'*70}", flush=True)
            print(
                f"📂 Category {category_idx}/{len(test_sets)}: {category}",
                flush=True,
            )
            print(f"{'#'*70}", flush=True)

            for i, example in enumerate(samples):
                problems_completed += 1
                problem_start = time.time()

                print(
                    f"\n🔄 Progress: {problems_completed}/{total_problems} total problems",
                    flush=True,
                )
                print(
                    f"📝 Current: Problem {i+1}/{len(samples)} in {category}",
                    flush=True,
                )

                try:
                    result = run_benchmark_test(
                        airunner_client,
                        example,
                        evaluators,
                        min_score=0.3,  # Low threshold to collect data
                        raise_on_fail=False,
                        verbose=False,  # Suppress detailed output for comprehensive test
                    )
                    all_results[category].append(result)

                    # Show quick result indicator
                    passed = result.get("passed", False)
                    score = (
                        result.get("evaluations", {})
                        .get("correctness", {})
                        .get("score", 0)
                    )
                    status = "✅ PASS" if passed else "❌ FAIL"
                    elapsed = time.time() - problem_start
                    print(
                        f"   {status} - Score: {score:.2f} - Time: {elapsed:.1f}s",
                        flush=True,
                    )

                except Exception as e:
                    print(
                        f"⚠️  Problem {i+1} failed with exception: {e}",
                        flush=True,
                    )

        # Generate comprehensive summary
        total_elapsed = time.time() - test_start_time
        print(f"\n{'='*70}")
        print("📊 COMPREHENSIVE MATH EVALUATION SUMMARY")
        print(f"{'='*70}")
        print(
            f"⏱️  Total Time: {total_elapsed/60:.1f} minutes ({total_elapsed:.0f}s)"
        )
        print(f"{'='*70}\n")

        total_problems = 0
        total_passed = 0
        all_scores = []

        for category, results in all_results.items():
            if not results:
                continue

            passed = sum(1 for r in results if r.get("passed", False))
            total = len(results)
            total_problems += total
            total_passed += passed

            scores = [
                r["evaluations"]["correctness"]["score"]
                for r in results
                if "correctness" in r.get("evaluations", {})
            ]
            all_scores.extend(scores)

            avg_score = sum(scores) / len(scores) if scores else 0.0

            print(f"{category}:")
            print(f"  Problems tested: {total}")
            print(f"  Passed (≥0.3): {passed}/{total}")
            print(f"  Average score: {avg_score:.2f} ({avg_score*100:.0f}%)")
            print()

        overall_avg = sum(all_scores) / len(all_scores) if all_scores else 0.0
        print(f"{'='*70}")
        print(f"OVERALL RESULTS:")
        print(f"  Total problems: {total_problems}")
        print(f"  Total passed: {total_passed}/{total_problems}")
        print(
            f"  Overall average score: {overall_avg:.2f} ({overall_avg*100:.0f}%)"
        )
        print(f"{'='*70}\n")

        # Grade the performance
        if overall_avg >= 0.9:
            grade = "A (Excellent)"
        elif overall_avg >= 0.8:
            grade = "B (Good)"
        elif overall_avg >= 0.7:
            grade = "C (Fair)"
        elif overall_avg >= 0.6:
            grade = "D (Needs Improvement)"
        else:
            grade = "F (Poor - Consider adding math tools)"

        print(f"📈 Performance Grade: {grade}")
        print()

        if overall_avg < 0.7:
            print("💡 Recommendations:")
            print("  - Add calculator tool for arithmetic operations")
            print("  - Add python_eval tool for computational problems")
            print("  - Add symbolic_math tool for algebraic manipulation")
            print()


@pytest.mark.benchmark
@pytest.mark.llm_required
@pytest.mark.code
class TestHumanEval:
    """Tests using HumanEval dataset (code generation)."""

    @pytest.fixture(scope="class")
    def humaneval_samples(self):
        """Load HumanEval samples."""
        return load_humaneval(num_samples=5, seed=42)

    def test_humaneval_problem_1(self, airunner_client, humaneval_samples):
        """Test HumanEval code generation problem #1."""
        evaluators = [
            create_correctness_evaluator(airunner_client),
            create_helpfulness_evaluator(airunner_client),
        ]

        # Add instruction to generate code
        example = humaneval_samples[0]
        enhanced_prompt = (
            f"{example.prompt}\n\n"
            "Please provide a complete implementation of this function."
        )
        example.prompt = enhanced_prompt

        run_benchmark_test(
            airunner_client,
            example,
            evaluators,
            min_score=0.5,  # Code generation is harder
        )

    @pytest.mark.slow
    def test_humaneval_batch(self, airunner_client, humaneval_samples):
        """Test batch of HumanEval problems."""
        evaluators = [
            create_correctness_evaluator(airunner_client),
        ]

        results = []
        for i, example in enumerate(humaneval_samples):
            print(f"\n{'#'*70}")
            print(f"Running HumanEval problem {i+1}/{len(humaneval_samples)}")
            print(f"{'#'*70}")

            # Enhance prompt
            enhanced_prompt = (
                f"{example.prompt}\n\n"
                "Please provide a complete implementation."
            )
            example.prompt = enhanced_prompt

            try:
                result = run_benchmark_test(
                    airunner_client,
                    example,
                    evaluators,
                    min_score=0.4,  # Lower threshold for code
                )
                results.append(result)
            except Exception as e:
                print(f"⚠️  Problem {i+1} failed: {e}")

        # Print summary
        print(f"\n{'='*70}")
        print("📊 HUMANEVAL BATCH TEST SUMMARY")
        print(f"{'='*70}")
        print(f"Total problems: {len(results)}")
        print(f"Passed: {sum(1 for r in results if r['passed'])}")

        if results:
            correctness_scores = [
                r["evaluations"]["correctness"]["score"]
                for r in results
                if "correctness" in r["evaluations"]
            ]
            if correctness_scores:
                avg = sum(correctness_scores) / len(correctness_scores)
                print(f"Average correctness: {avg:.2f}/1.0")

    @pytest.mark.slow
    def test_humaneval_comprehensive_with_execution(
        self, airunner_client, humaneval_samples
    ):
        """Comprehensive HumanEval test with actual code execution.

        Tests code generation and execution with real test cases.
        Similar to math comprehensive test but for code.
        """
        from airunner.components.eval.code_evaluators import (
            create_code_correctness_evaluator,
        )

        evaluators = [create_code_correctness_evaluator()]

        # Calculate total problems
        num_problems = min(len(humaneval_samples), 10)  # Test first 10
        test_start_time = time.time()

        print(f"\n{'='*70}", flush=True)
        print("🚀 STARTING COMPREHENSIVE CODE EVALUATION", flush=True)
        print(f"{'='*70}", flush=True)
        print(f"📊 Total problems to test: {num_problems}", flush=True)
        print(
            f"⏱️  Estimated time: {num_problems * 1:.0f}-{num_problems * 2:.0f} minutes",
            flush=True,
        )
        print(f"{'='*70}\n", flush=True)

        all_results = []

        for i, example in enumerate(humaneval_samples[:num_problems]):
            problem_start = time.time()

            print(f"\n🔄 Progress: {i+1}/{num_problems} problems", flush=True)
            print(
                f"📝 Problem: {example.metadata.get('entry_point', 'unknown')}",
                flush=True,
            )

            # Enhance prompt for code generation
            enhanced_prompt = (
                f"{example.prompt}\n\n"
                "Please provide a complete, working implementation. "
                "Include only the function code in a ```python code block."
            )

            try:
                # Use verbose=False for cleaner output
                result = {
                    "prompt": enhanced_prompt,
                    "category": example.category,
                    "entry_point": example.metadata.get("entry_point"),
                }

                # Generate code
                response = airunner_client.generate(
                    enhanced_prompt,
                    temperature=0.0,
                    max_tokens=1000,
                    use_memory=False,
                )
                output = response.get("text", "")
                result["output"] = output

                # Evaluate with code executor
                eval_results = {}
                for evaluator in evaluators:
                    eval_result = evaluator(
                        inputs=enhanced_prompt,
                        outputs=output,
                        reference_outputs=example.reference_output,
                    )
                    eval_results[eval_result["feedback_key"]] = eval_result

                result["evaluations"] = eval_results

                # Determine pass/fail
                code_score = eval_results["code_correctness"]["score"]
                result["passed"] = code_score >= 0.8  # High bar for code
                result["score"] = code_score

                all_results.append(result)

                # Show result
                status = "✅ PASS" if result["passed"] else "❌ FAIL"
                elapsed = time.time() - problem_start
                tests_passed = (
                    eval_results["code_correctness"]
                    .get("execution", {})
                    .get("tests_passed", False)
                )
                test_status = "Tests ✅" if tests_passed else "Tests ❌"
                print(
                    f"   {status} - Score: {code_score:.2f} - {test_status} - Time: {elapsed:.1f}s",
                    flush=True,
                )

            except Exception as e:
                print(
                    f"⚠️  Problem {i+1} failed with exception: {e}", flush=True
                )
                logger.exception("Code evaluation failed")

        # Generate summary
        total_elapsed = time.time() - test_start_time
        print(f"\n{'='*70}")
        print("📊 COMPREHENSIVE CODE EVALUATION SUMMARY")
        print(f"{'='*70}")
        print(
            f"⏱️  Total Time: {total_elapsed/60:.1f} minutes ({total_elapsed:.0f}s)"
        )
        print(f"{'='*70}\n")

        total_problems = len(all_results)
        total_passed = sum(1 for r in all_results if r.get("passed", False))
        all_scores = [r.get("score", 0) for r in all_results]
        avg_score = sum(all_scores) / len(all_scores) if all_scores else 0

        # Print table
        print("| Problem | Tests Passed | Score |")
        print("|---------|--------------|-------|")
        for r in all_results:
            entry = r.get("entry_point", "unknown")[:30]
            tests = (
                r.get("evaluations", {})
                .get("code_correctness", {})
                .get("execution", {})
                .get("tests_passed", False)
            )
            score = r.get("score", 0)
            tests_str = "✅" if tests else "❌"
            print(f"| {entry:<30} | {tests_str:^12} | {score:.2f} |")

        print()
        print(
            f"Overall: {total_problems} problems, {total_passed} passed ({total_passed/total_problems*100:.0f}%), average score: {avg_score:.2f}"
        )

        # Grade
        if avg_score >= 0.90:
            grade = "A"
            comment = "Excellent - Production ready code generation"
        elif avg_score >= 0.80:
            grade = "B"
            comment = "Good - Minor improvements needed"
        elif avg_score >= 0.70:
            grade = "C"
            comment = "Acceptable - Moderate improvements needed"
        elif avg_score >= 0.60:
            grade = "D"
            comment = "Poor - Significant improvements needed"
        else:
            grade = "F"
            comment = "Failing - Major rework required"

        print(f"\nGrade: {grade} - {comment}")
        print(f"{'='*70}\n")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "benchmark"])
