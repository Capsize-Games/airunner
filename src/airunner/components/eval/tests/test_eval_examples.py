"""
Example evaluation tests for AI Runner using the eval testing framework.

These tests demonstrate how to use the airunner_client fixture to:
- Test LLM generation capabilities
- Verify streaming responses
- Evaluate model outputs against reference answers

Pattern based on openevals/langsmith evaluation framework.
"""

import pytest
from typing import Dict, Any


# Eval dataset with prompts and reference outputs
EVAL_DATASET = [
    {
        "prompt": "What is 2+2?",
        "reference_output": "4",
        "category": "math",
    },
    {
        "prompt": "Explain photosynthesis in one sentence.",
        "reference_output": (
            "Photosynthesis is the process by which plants use sunlight, "
            "water, and carbon dioxide to produce oxygen and energy in "
            "the form of sugar."
        ),
        "category": "science",
    },
    {
        "prompt": "Write a haiku about coding.",
        "reference_output": (
            "Lines of code flow fast\n"
            "Debugging through the dark night\n"
            "Solution found, light"
        ),
        "category": "creative",
    },
]


def run_test_case(
    client, test_case: Dict[str, Any], stream: bool = False
) -> Dict[str, Any]:
    """Run a single eval test case.

    Args:
        client: AIRunnerClient instance
        test_case: Dict with 'prompt' and 'reference_output'
        stream: Whether to use streaming mode

    Returns:
        Dict with test results including outputs and metadata
    """
    prompt = test_case["prompt"]
    reference = test_case["reference_output"]

    # Generate response
    if stream:
        # Collect streaming chunks
        chunks = []
        for chunk in client.generate_stream(prompt):
            chunks.append(chunk)
            if chunk.get("done"):
                break

        # Combine text from all chunks
        output = "".join(chunk.get("text", "") for chunk in chunks)
    else:
        response = client.generate(prompt)
        output = response.get("text", "")

    # Log results (in real eval framework, this would go to langsmith)
    result = {
        "prompt": prompt,
        "output": output,
        "reference": reference,
        "category": test_case.get("category", "general"),
        "stream_mode": stream,
    }

    print(f"\n✓ Test completed: {prompt}")
    print(f"Response: {output[:200]}...")
    print(f"Reference: {reference[:200]}...")

    return result


@pytest.mark.eval
@pytest.mark.integration
@pytest.mark.skip(reason="Requires LLM model to be loaded")
def test_math_question(airunner_client):
    """Test basic math question."""
    result = run_test_case(airunner_client, EVAL_DATASET[0])

    # Basic assertion - in real eval, use LLM-as-judge
    assert result["output"] is not None
    assert len(result["output"]) > 0


@pytest.mark.eval
@pytest.mark.integration
@pytest.mark.skip(reason="Requires LLM model to be loaded")
def test_science_explanation(airunner_client):
    """Test science explanation generation."""
    result = run_test_case(airunner_client, EVAL_DATASET[1])

    assert result["output"] is not None
    assert len(result["output"]) > 0


@pytest.mark.eval
@pytest.mark.integration
@pytest.mark.skip(reason="Requires LLM model to be loaded")
def test_creative_writing(airunner_client):
    """Test creative writing capability."""
    result = run_test_case(airunner_client, EVAL_DATASET[2])

    assert result["output"] is not None
    assert len(result["output"]) > 0


@pytest.mark.eval
@pytest.mark.streaming
@pytest.mark.integration
@pytest.mark.skip(reason="Requires LLM model to be loaded")
def test_streaming_response(airunner_client):
    """Test streaming LLM generation."""
    result = run_test_case(airunner_client, EVAL_DATASET[0], stream=True)

    assert result["output"] is not None
    assert result["stream_mode"] is True


@pytest.mark.eval
def test_client_health_check(airunner_client):
    """Test that client can check server health."""
    health = airunner_client.health_check()

    assert health is not None
    assert health.get("status") == "ready"


@pytest.mark.eval
def test_client_list_models(airunner_client):
    """Test that client can list available models."""
    models = airunner_client.list_models()

    assert isinstance(models, list)
    # In headless mode with no models loaded, might be empty
    # But API should still respond


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "eval"])
