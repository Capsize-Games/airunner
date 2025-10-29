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

#### Prerequisites

**IMPORTANT**: Evaluation tests require an actual LLM model to be configured and loaded.

1. **Install AI Runner**: `pip install -e .`
2. **Download Models**: Run `airunner-setup` to download an LLM model
3. **Configure Settings**: Ensure an LLM model is selected in settings

To check if a model is configured:
```bash
python -c "from airunner.components.llm.data.llm_generator_settings import LLMGeneratorSettings; s = LLMGeneratorSettings.objects.first(); print(f'Model: {s.model_name if s else \"NOT CONFIGURED\"}')"
```

#### 1. Start Headless Server

```bash
# Terminal 1: Start the headless server
airunner-headless --port 8188
```

**Note**: The server will load the configured LLM model on first request. This may take 30-60 seconds.

#### 2. Run Evaluation Tests

```bash
# Terminal 2: Run eval tests (requires LLM model loaded)
pytest src/airunner/components/eval/tests/test_real_eval.py -v

# Run specific category
pytest src/airunner/components/eval/tests/test_real_eval.py::TestMathReasoning -v

# Increase timeout for slow model loading (if needed)
pytest src/airunner/components/eval/tests/test_real_eval.py -v --timeout=300
```

**Common Issues:**

- **Timeout Error**: Model loading takes longer than 30s default timeout. Use `--timeout=300` or pre-load model.
- **No Response**: No LLM model configured. Run `airunner-setup` to download a model.
- **Port Conflict**: Another server running on 8188. Use `pkill -f airunner-headless` to stop it.

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

### Standard Benchmark Datasets

The framework now includes industry-standard benchmark datasets for comprehensive evaluation:

#### GSM8K (Grade School Math)

8,000+ grade school math word problems requiring multi-step reasoning.

```python
from airunner.components.eval.benchmark_datasets import load_gsm8k

# Load 100 random test samples
samples = load_gsm8k(num_samples=100, split="test", seed=42)

for example in samples:
    print(f"Problem: {example.prompt}")
    print(f"Answer: {example.answer}")
```

**Performance Baselines**:
- GPT-3 (175B): ~17% accuracy
- GPT-3.5-turbo: ~57% accuracy
- GPT-4: ~92% accuracy
- Qwen2.5-7B-Instruct: ~60-65% expected

#### MATH (Competition Mathematics)

12,500 competition-level math problems from AMC, AIME, and other contests.

```python
from airunner.components.eval.benchmark_datasets import load_math

# Load Level 1 problems (easiest)
easy_samples = load_math(num_samples=50, level="Level 1", seed=42)

# Load Algebra problems
algebra_samples = load_math(num_samples=50, subject="Algebra", seed=42)
```

**Subjects**: Algebra, Counting & Probability, Geometry, Intermediate Algebra, Number Theory, Prealgebra, Precalculus

**Performance Baselines**:
- GPT-3 (175B): ~5% accuracy
- GPT-4: ~42% accuracy
- Minerva 540B: ~50% accuracy
- Qwen2.5-7B-Instruct: ~15-25% expected (varies by level)

#### HumanEval (Code Generation)

164 hand-written programming problems with function signatures and test cases.

```python
from airunner.components.eval.benchmark_datasets import load_humaneval

# Load 20 random problems
samples = load_humaneval(num_samples=20, seed=42)
```

**Performance Baselines** (pass@1):
- GPT-3 (175B): ~0% accuracy
- GPT-3.5-turbo: ~48% accuracy
- GPT-4: ~67% accuracy
- Qwen2.5-7B-Instruct: ~30-40% expected

#### Running Benchmark Tests

```bash
# Run all benchmark tests
pytest -v -m benchmark

# Run only GSM8K tests
pytest -v src/airunner/components/eval/tests/test_benchmark_eval.py::TestGSM8K

# Run only MATH tests
pytest -v src/airunner/components/eval/tests/test_benchmark_eval.py::TestMATH

# Run only HumanEval tests
pytest -v src/airunner/components/eval/tests/test_benchmark_eval.py::TestHumanEval -m code

# Skip slow batch tests
pytest -v -m "benchmark and not slow"
```

#### Benchmark Test Structure

```python
import pytest
from airunner.components.eval.benchmark_datasets import load_gsm8k
from airunner.components.eval.evaluators import create_correctness_evaluator

@pytest.mark.benchmark
@pytest.mark.llm_required
def test_gsm8k_sample(airunner_client):
    """Test with GSM8K dataset."""
    samples = load_gsm8k(num_samples=5, seed=42)
    evaluator = create_correctness_evaluator(airunner_client)
    
    for example in samples:
        # Generate (use temp=0.0 for deterministic math)
        response = airunner_client.generate(
            example.prompt, 
            temperature=0.0,
            max_tokens=1000
        )
        output = response["text"]
        
        # Evaluate
        result = evaluator(
            inputs=example.prompt,
            outputs=output,
            reference_outputs=example.reference_output,
        )
        
        # Assert
        assert result["score"] >= 0.6, f"Failed: {result['reasoning']}"
```

### Future Enhancements

- [x] Standard benchmark datasets (GSM8K, MATH, HumanEval)
- [ ] Add more evaluation criteria (coherence, factuality, safety)
- [ ] Support for multi-turn conversations
- [ ] Benchmark tracking over time
- [ ] Integration with langsmith/openevals
- [ ] Custom dataset upload
- [ ] Evaluation result visualization
- [ ] More benchmarks (MMLU, BBH, TruthfulQA, HellaSwag)
- [ ] Code execution and testing for HumanEval
- [ ] Automated regression testing in CI/CD

### References

- **Pattern**: Based on openevals LLM-as-judge pattern
- **Architecture**: AI Runner signal-based decoupled design
- **Testing**: Pytest with custom fixtures and marks
- **GSM8K**: [Training Verifiers to Solve Math Word Problems](https://arxiv.org/abs/2110.14168)
- **MATH**: [Measuring Mathematical Problem Solving](https://github.com/hendrycks/math)
- **HumanEval**: [Evaluating Large Language Models Trained on Code](https://arxiv.org/abs/2107.03374)
- **Math Evaluation Harness**: [Comprehensive math benchmark suite](https://github.com/ZubinGou/math-evaluation-harness)
