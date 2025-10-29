"""
Benchmark evaluation tests using standard datasets.

Tests LLM performance on industry-standard benchmarks:
- GSM8K: Grade school math reasoning
- MATH: Competition-level mathematics
- HumanEval: Code generation

Run with: pytest -v -m "benchmark"
Skip slow benchmarks: pytest -v -m "not slow"
"""

import pytest
from typing import Dict, Any, List
from airunner.components.eval.benchmark_datasets import (
    load_gsm8k,
    load_math,
    load_humaneval,
    BenchmarkExample,
    extract_numeric_answer,
    normalize_answer,
)
from airunner.components.eval.evaluators import (
    create_correctness_evaluator,
    create_conciseness_evaluator,
    create_helpfulness_evaluator,
)


def run_benchmark_test(
    client,
    example: BenchmarkExample,
    evaluators: list,
    min_score: float = 0.6,
) -> Dict[str, Any]:
    """Run a single benchmark test case.

    Args:
        client: AIRunnerClient instance
        example: BenchmarkExample to test
        evaluators: List of evaluators
        min_score: Minimum acceptable score

    Returns:
        Dict with test results
    """
    prompt = example.prompt
    reference = example.reference_output
    category = example.category
    difficulty = example.difficulty
    expected_answer = example.answer

    print(f"\n{'='*70}")
    print(f"📝 Category: {category} | Difficulty: {difficulty}")
    print(f"❓ Prompt: {prompt[:200]}...")
    if expected_answer:
        print(f"✓ Expected answer: {expected_answer}")

    # Generate response
    try:
        response = client.generate(
            prompt, temperature=0.0, max_tokens=1000
        )  # temp=0 for deterministic math
        output = response.get("text", "")

        # Debug: Check if response is empty
        if not output or not output.strip():
            print(f"⚠️  WARNING: Empty response received!")
            print(f"   Response object: {response}")
            print(f"   Response keys: {list(response.keys())}")
            pytest.fail("Generation returned empty response")
    except Exception as e:
        print(f"❌ Generation failed: {e}")
        pytest.fail(f"Generation failed: {e}")

    print(f"🤖 Response: {output[:300]}...")

    # Extract answer from response
    if category.startswith("math"):
        generated_answer = extract_numeric_answer(output)
        print(f"🔢 Extracted answer: {generated_answer}")

        # Check exact match
        if expected_answer and generated_answer:
            norm_expected = normalize_answer(expected_answer)
            norm_generated = normalize_answer(generated_answer)
            exact_match = norm_expected == norm_generated
            match_status = "✅" if exact_match else "❌"
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
        print(f"{status} {feedback_key}: {score:.2f}/1.0 - {reasoning}")

        if not passed:
            all_passed = False

    # Overall result
    if all_passed:
        print(f"{'='*70}")
        print("✅ TEST PASSED - All evaluations met minimum score")
    else:
        print(f"{'='*70}")
        print("❌ TEST FAILED - Some evaluations below minimum score")
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
            create_helpfulness_evaluator(airunner_client),
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
    def math_samples_easy(self):
        """Load easy MATH samples (Level 1)."""
        return load_math(num_samples=5, split="test", level="Level 1", seed=42)

    @pytest.fixture(scope="class")
    def math_samples_medium(self):
        """Load medium MATH samples (Level 3)."""
        return load_math(num_samples=5, split="test", level="Level 3", seed=42)

    def test_math_level1_problem_1(self, airunner_client, math_samples_easy):
        """Test MATH Level 1 problem."""
        evaluators = [
            create_correctness_evaluator(airunner_client),
            create_helpfulness_evaluator(airunner_client),
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
            create_helpfulness_evaluator(airunner_client),
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


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "benchmark"])
