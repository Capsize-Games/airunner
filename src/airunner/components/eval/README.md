## AI Runner Evaluation Testing Framework

A comprehensive evaluation testing framework for AI Runner that enables automated quality assessment of LLM outputs using the LLM-as-judge pattern.

### Overview

This framework provides:

- **AIRunnerClient**: Python client library for interacting with headless AI Runner server
- **LLM-as-Judge Evaluators**: Automated quality assessment using LLM evaluators
- **Comprehensive Datasets**: 18+ test cases across 6 categories
- **Pytest Fixtures**: Automated server management for testing
- **CI/CD Integration**: GitHub Actions workflow for continuous evaluation

### Quick Start

#### 1. Start Headless Server

```bash
# Terminal 1: Start the headless server
airunner-headless --port 8188
```

#### 2. Run Evaluation Tests

```bash
# Terminal 2: Run eval tests (requires LLM model loaded)
pytest src/airunner/components/eval/tests/test_real_eval.py -v -m llm_required

# Run specific category
pytest src/airunner/components/eval/tests/test_real_eval.py::TestMathReasoning -v

# Run without LLM requirement (smoke tests only)
pytest src/airunner/components/eval/tests/ -v -m "eval and not llm_required"
```

### Components

#### AIRunnerClient

Python client for headless server:

```python
from airunner.components.eval.client import AIRunnerClient

client = AIRunnerClient(base_url="http://localhost:8188")

# Non-streaming generation
response = client.generate("What is 2+2?")
print(response["text"])

# Streaming generation
for chunk in client.generate_stream("Tell me a story"):
    print(chunk["text"], end="", flush=True)
    if chunk.get("done"):
        break

# Health check
health = client.health_check()  # Returns {"status": "ready", ...}

# List models
models = client.list_models()
```

#### LLM-as-Judge Evaluators

Automated quality assessment:

```python
from airunner.components.eval.evaluators import (
    create_correctness_evaluator,
    create_conciseness_evaluator,
    create_helpfulness_evaluator,
    create_relevance_evaluator,
)

client = AIRunnerClient()

# Create evaluators
correctness = create_correctness_evaluator(client)
conciseness = create_conciseness_evaluator(client)

# Evaluate a response
result = correctness(
    inputs="What is the capital of France?",
    outputs="Paris is the capital and largest city of France.",
    reference_outputs="Paris is the capital of France.",
)

print(f"Score: {result['score']}/1.0")
print(f"Reasoning: {result['reasoning']}")
```

#### Evaluation Datasets

Pre-defined test datasets:

```python
from airunner.components.eval.datasets import (
    MATH_REASONING_DATASET,
    GENERAL_KNOWLEDGE_DATASET,
    SUMMARIZATION_DATASET,
    CODING_DATASET,
    INSTRUCTION_FOLLOWING_DATASET,
    REASONING_DATASET,
    get_all_test_cases,
    get_dataset_by_category,
    get_dataset_by_difficulty,
)

# Get all test cases
all_cases = get_all_test_cases()  # 18 cases

# Get by category
math_cases = get_dataset_by_category("math_reasoning")

# Get by difficulty
easy_cases = get_dataset_by_difficulty("easy")
```

### Dataset Categories

1. **Math & Reasoning** (4 cases)
   - Simple arithmetic
   - Word problems
   - Algebra
   - Geometry

2. **General Knowledge** (4 cases)
   - Geography
   - Science
   - Literature
   - Basic facts

3. **Summarization** (2 cases)
   - Historical text
   - Technical definitions

4. **Coding** (3 cases)
   - Python functions
   - Language features
   - Comparisons

5. **Instruction Following** (3 cases)
   - List generation
   - Formatted output
   - Creative writing

6. **Reasoning** (2 cases)
   - Logic puzzles
   - Problem solving

### Pytest Fixtures

Automated server management:

```python
def test_llm_generation(airunner_client):
    """Test using session-scoped client fixture."""
    response = airunner_client.generate("Hello")
    assert response["text"]

def test_with_fresh_client(airunner_client_function_scope):
    """Test with function-scoped client."""
    health = airunner_client_function_scope.health_check()
    assert health["status"] == "ready"
```

Available fixtures:
- `airunner_server`: Session-scoped server process
- `airunner_client`: Session-scoped client
- `airunner_client_function_scope`: Function-scoped client

### Writing Custom Eval Tests

```python
import pytest
from airunner.components.eval.evaluators import create_correctness_evaluator

@pytest.mark.eval
@pytest.mark.llm_required
def test_custom_evaluation(airunner_client):
    """Custom evaluation test."""
    
    # Generate response
    response = airunner_client.generate("Explain gravity")
    output = response["text"]
    
    # Create evaluator
    evaluator = create_correctness_evaluator(airunner_client)
    
    # Evaluate
    result = evaluator(
        inputs="Explain gravity",
        outputs=output,
        reference_outputs="Gravity is a force that attracts objects with mass.",
    )
    
    # Assert minimum quality
    assert result["score"] >= 0.6, f"Low score: {result['reasoning']}"
```

### Environment Variables

Configure server connection:

```bash
export AIRUNNER_HTTP_HOST=127.0.0.1
export AIRUNNER_HTTP_PORT=8188
export AIRUNNER_HEADLESS=1
```

### CI/CD Integration

GitHub Actions workflow (`.github/workflows/eval-tests.yml`):

```yaml
- name: Run eval tests
  run: |
    pytest src/airunner/components/eval/tests/ \
      -v \
      -m eval \
      --timeout=300
```

### Pytest Marks

- `@pytest.mark.eval`: All evaluation tests
- `@pytest.mark.llm_required`: Requires LLM model loaded
- `@pytest.mark.streaming`: Tests streaming functionality
- `@pytest.mark.integration`: Integration tests
- `@pytest.mark.slow`: Long-running tests

### Running Different Test Suites

```bash
# All eval tests (including those requiring LLM)
pytest -v -m eval

# Only tests that don't need LLM
pytest -v -m "eval and not llm_required"

# Only LLM-required tests
pytest -v -m llm_required

# Specific test class
pytest -v -m eval -k TestMathReasoning

# Comprehensive test with summary
pytest -v -m slow src/airunner/components/eval/tests/test_real_eval.py::test_comprehensive_evaluation
```

### Score Interpretation

Evaluation scores range from 0.0 to 1.0:

- **0.8-1.0**: Excellent quality
- **0.6-0.8**: Good quality, minor issues
- **0.4-0.6**: Acceptable, needs improvement
- **0.0-0.4**: Poor quality, significant issues

### Customizing Evaluators

Create custom evaluation criteria:

```python
from airunner.components.eval.evaluators import LLMAsJudge

CUSTOM_PROMPT = """Evaluate the creativity of this response...
Score: [0-10]
Reasoning: [explanation]
"""

creativity_evaluator = LLMAsJudge(
    client=client,
    prompt_template=CUSTOM_PROMPT,
    feedback_key="creativity",
)

result = creativity_evaluator(inputs="...", outputs="...", reference_outputs="...")
```

### Troubleshooting

**Server won't start:**
```bash
# Check if port is in use
lsof -i :8188

# Use different port
airunner-headless --port 9999
export AIRUNNER_HTTP_PORT=9999
```

**Tests timeout:**
- Ensure LLM model is loaded in AI Runner
- Increase timeout: `pytest --timeout=600`
- Check server logs for errors

**Evaluation scores unexpected:**
- Verify reference outputs are accurate
- Adjust `min_score` thresholds
- Check evaluation reasoning in output

### Architecture

```
src/airunner/components/eval/
├── __init__.py              # Public API exports
├── client.py                # AIRunnerClient library
├── evaluators.py            # LLM-as-judge evaluators
├── datasets.py              # Test case datasets
├── fixtures.py              # Pytest fixtures
└── tests/
    ├── conftest.py          # Fixture configuration
    ├── test_client.py       # Client unit tests
    ├── test_fixtures.py     # Fixture tests
    ├── test_eval_examples.py # Simple eval examples
    └── test_real_eval.py    # Real LLM-as-judge tests
```

### Future Enhancements

- [ ] Add more evaluation criteria (coherence, factuality, safety)
- [ ] Support for multi-turn conversations
- [ ] Benchmark tracking over time
- [ ] Integration with langsmith/openevals
- [ ] Custom dataset upload
- [ ] Evaluation result visualization

### References

- **Pattern**: Based on openevals LLM-as-judge pattern
- **Architecture**: AI Runner signal-based decoupled design
- **Testing**: Pytest with custom fixtures and marks
