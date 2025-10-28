"""
Real evaluation tests with LLM-as-judge pattern.

These tests generate responses using AI Runner and evaluate them
using LLM-as-judge evaluators for quality assessment.

Run with: pytest -v -m "eval and not skip_llm"
Skip LLM tests: pytest -v -m "eval and skip_llm"
"""

import pytest
from typing import Dict, Any
from airunner.components.eval.datasets import (
    MATH_REASONING_DATASET,
    GENERAL_KNOWLEDGE_DATASET,
    SUMMARIZATION_DATASET,
    CODING_DATASET,
    INSTRUCTION_FOLLOWING_DATASET,
    get_all_test_cases,
)
from airunner.components.eval.evaluators import (
    create_correctness_evaluator,
    create_conciseness_evaluator,
    create_helpfulness_evaluator,
)


def run_eval_test_case(
    client,
    test_case: Dict[str, Any],
    evaluators: list,
    min_score: float = 0.6,
) -> Dict[str, Any]:
    """Run a single eval test case with LLM-as-judge evaluation.

    Args:
        client: AIRunnerClient instance
        test_case: Dict with 'prompt', 'reference_output', etc.
        evaluators: List of LLMAsJudge evaluators to run
        min_score: Minimum acceptable score (0.0-1.0)

    Returns:
        Dict with test results and evaluation scores
    """
    prompt = test_case["prompt"]
    reference = test_case["reference_output"]
    category = test_case.get("category", "general")
    difficulty = test_case.get("difficulty", "medium")

    print(f"\n{'='*70}")
    print(f"📝 Category: {category} | Difficulty: {difficulty}")
    print(f"❓ Prompt: {prompt}")
    print(f"📚 Reference: {reference[:100]}...")

    # Generate response from AI Runner
    try:
        response = client.generate(prompt, temperature=0.7, max_tokens=500)
        output = response.get("text", "")
    except Exception as e:
        print(f"❌ Generation failed: {e}")
        pytest.fail(f"Generation failed: {e}")

    print(f"🤖 Response: {output[:200]}...")

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
        "category": category,
        "difficulty": difficulty,
        "evaluations": evaluation_results,
        "passed": all_passed,
    }


# Math and Reasoning Tests
@pytest.mark.eval
@pytest.mark.llm_required
class TestMathReasoning:
    """Tests for math and reasoning capabilities."""

    def test_simple_addition(self, airunner_client):
        """Test simple addition problem."""
        evaluators = [
            create_correctness_evaluator(airunner_client),
            create_conciseness_evaluator(airunner_client),
        ]
        run_eval_test_case(
            airunner_client,
            MATH_REASONING_DATASET[0],
            evaluators,
            min_score=0.7,
        )

    def test_speed_calculation(self, airunner_client):
        """Test speed calculation problem."""
        evaluators = [
            create_correctness_evaluator(airunner_client),
            create_helpfulness_evaluator(airunner_client),
        ]
        run_eval_test_case(
            airunner_client,
            MATH_REASONING_DATASET[1],
            evaluators,
            min_score=0.6,
        )

    def test_algebra_equation(self, airunner_client):
        """Test solving linear equation."""
        evaluators = [
            create_correctness_evaluator(airunner_client),
            create_helpfulness_evaluator(airunner_client),
        ]
        run_eval_test_case(
            airunner_client,
            MATH_REASONING_DATASET[2],
            evaluators,
            min_score=0.6,
        )


# General Knowledge Tests
@pytest.mark.eval
@pytest.mark.llm_required
class TestGeneralKnowledge:
    """Tests for general knowledge questions."""

    def test_capital_question(self, airunner_client):
        """Test basic geography question."""
        evaluators = [
            create_correctness_evaluator(airunner_client),
            create_conciseness_evaluator(airunner_client),
        ]
        run_eval_test_case(
            airunner_client,
            GENERAL_KNOWLEDGE_DATASET[0],
            evaluators,
            min_score=0.8,
        )

    def test_photosynthesis_explanation(self, airunner_client):
        """Test science explanation."""
        evaluators = [
            create_correctness_evaluator(airunner_client),
            create_conciseness_evaluator(airunner_client),
        ]
        run_eval_test_case(
            airunner_client,
            GENERAL_KNOWLEDGE_DATASET[1],
            evaluators,
            min_score=0.6,
        )


# Summarization Tests
@pytest.mark.eval
@pytest.mark.llm_required
class TestSummarization:
    """Tests for summarization capabilities."""

    def test_industrial_revolution_summary(self, airunner_client):
        """Test summarizing historical text."""
        evaluators = [
            create_correctness_evaluator(airunner_client),
            create_conciseness_evaluator(airunner_client),
        ]
        run_eval_test_case(
            airunner_client,
            SUMMARIZATION_DATASET[0],
            evaluators,
            min_score=0.6,
        )

    def test_ai_definition_summary(self, airunner_client):
        """Test summarizing technical definition."""
        evaluators = [
            create_correctness_evaluator(airunner_client),
            create_conciseness_evaluator(airunner_client),
        ]
        run_eval_test_case(
            airunner_client,
            SUMMARIZATION_DATASET[1],
            evaluators,
            min_score=0.6,
        )


# Coding Tests
@pytest.mark.eval
@pytest.mark.llm_required
class TestCoding:
    """Tests for coding and technical questions."""

    def test_python_len_function(self, airunner_client):
        """Test explaining Python len() function."""
        evaluators = [
            create_correctness_evaluator(airunner_client),
            create_helpfulness_evaluator(airunner_client),
        ]
        run_eval_test_case(
            airunner_client,
            CODING_DATASET[0],
            evaluators,
            min_score=0.7,
        )

    def test_list_comprehension(self, airunner_client):
        """Test explaining list comprehensions."""
        evaluators = [
            create_correctness_evaluator(airunner_client),
            create_helpfulness_evaluator(airunner_client),
        ]
        run_eval_test_case(
            airunner_client,
            CODING_DATASET[1],
            evaluators,
            min_score=0.6,
        )


# Instruction Following Tests
@pytest.mark.eval
@pytest.mark.llm_required
class TestInstructionFollowing:
    """Tests for instruction following capabilities."""

    def test_list_primary_colors(self, airunner_client):
        """Test following list instruction."""
        evaluators = [
            create_correctness_evaluator(airunner_client),
            create_helpfulness_evaluator(airunner_client),
        ]
        run_eval_test_case(
            airunner_client,
            INSTRUCTION_FOLLOWING_DATASET[0],
            evaluators,
            min_score=0.7,
        )

    def test_numbered_list_instruction(self, airunner_client):
        """Test following numbered list instruction."""
        evaluators = [
            create_correctness_evaluator(airunner_client),
            create_helpfulness_evaluator(airunner_client),
        ]
        run_eval_test_case(
            airunner_client,
            INSTRUCTION_FOLLOWING_DATASET[2],
            evaluators,
            min_score=0.6,
        )


# Comprehensive test running all datasets
@pytest.mark.eval
@pytest.mark.llm_required
@pytest.mark.slow
def test_comprehensive_evaluation(airunner_client):
    """Run comprehensive evaluation across all datasets.

    This test runs a subset of test cases from each category
    and reports overall statistics.
    """
    all_cases = get_all_test_cases()

    # Run a sample (first 10 test cases)
    sample_cases = all_cases[:10]

    evaluators = [
        create_correctness_evaluator(airunner_client),
        create_conciseness_evaluator(airunner_client),
    ]

    results = []
    for test_case in sample_cases:
        try:
            result = run_eval_test_case(
                airunner_client,
                test_case,
                evaluators,
                min_score=0.5,  # Lower threshold for comprehensive test
            )
            results.append(result)
        except Exception as e:
            print(f"⚠️  Test case failed: {e}")
            # Continue with other tests

    # Print summary statistics
    print(f"\n{'='*70}")
    print("📊 COMPREHENSIVE TEST SUMMARY")
    print(f"{'='*70}")
    print(f"Total test cases run: {len(results)}")
    print(f"Passed: {sum(1 for r in results if r['passed'])}")
    print(f"Failed: {sum(1 for r in results if not r['passed'])}")

    # Calculate average scores
    for eval_name in ["correctness", "conciseness"]:
        scores = [
            r["evaluations"][eval_name]["score"]
            for r in results
            if eval_name in r["evaluations"]
        ]
        if scores:
            avg = sum(scores) / len(scores)
            print(f"Average {eval_name}: {avg:.2f}/1.0")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "eval and llm_required"])
