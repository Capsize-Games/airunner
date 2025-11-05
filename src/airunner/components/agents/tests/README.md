# Expert Agent System Testing Strategy

## Overview
The expert agent system has two complementary test suites:

1. **Unit Tests** (`test_agent_system.py`) - Architecture validation
2. **Eval Tests** (`eval_test_agent_system.py`) - LLM quality validation

## Unit Tests (60 tests)

**Purpose:** Validate the agent system architecture works correctly

**Technology:**
- pytest with anyio for async support
- Direct assertion-based testing
- No LLM required

**Coverage:**
- Agent capability registration
- Registry operations (register, unregister, find)
- Task routing (single and multi-agent)
- Expert agent execution
- Edge cases and error handling
- End-to-end workflows

**Run:**
```bash
pytest src/airunner/components/agents/tests/test_agent_system.py
```

**Threshold:** Uses `min_score=0.05` for keyword-based routing

## Eval Tests (3 test suites)

**Purpose:** Validate LLM-generated outputs are correct and high-quality

**Technology:**
- LangSmith for experiment tracking
- openevals LLM-as-judge evaluators
- ollama with llama3.2 model
- pytest-asyncio for async support

**Test Suites:**

### 1. Agent Routing Correctness
- **Evaluator:** CORRECTNESS_PROMPT (1-5 scoring)
- **Test Cases:** 6 routing scenarios
- **Success Criteria:** ≥80% score 4+/5
- **Validates:** Correct agent selection for tasks

### 2. Agent Response Quality
- **Evaluator:** CONCISENESS_PROMPT (1-5 scoring)
- **Test Cases:** 6 agent executions
- **Success Criteria:** ≥70% score 3+/5
- **Validates:** Responses are concise and actionable

### 3. Multi-Agent Collaboration
- **Evaluators:** Both CORRECTNESS and CONCISENESS
- **Test Cases:** 2 complex multi-agent tasks
- **Success Criteria:** 100% task success
- **Validates:** Effective agent coordination

**Run:**
```bash
# Requires ollama running with llama3.2 model
pytest src/airunner/components/agents/tests/eval_test_agent_system.py
```

**Prerequisites:**
1. Install ollama: https://ollama.ai/
2. Pull model: `ollama pull llama3.2`
3. Set LANGCHAIN_API_KEY environment variable
4. Ensure ollama service is running

## Why Both Test Types?

**Unit Tests:**
- Fast (< 1 second)
- Deterministic
- Validate architecture
- No external dependencies
- Run in CI/CD pipeline

**Eval Tests:**
- Slower (minutes)
- LLM-based evaluation
- Validate output quality
- Require ollama + LangSmith
- Run before releases

## LangSmith Integration

Eval tests log results to LangSmith for:
- Experiment tracking
- Score visualization
- Regression detection
- Quality trends over time

Results available at: https://smith.langchain.com/

## Test Cases

### Routing Test Cases
1. Calendar: "Schedule a team meeting for next Tuesday at 2pm"
2. Code: "Write a Python function to calculate fibonacci numbers"
3. Research: "Research the latest advances in quantum computing"
4. Creative: "Write a creative short story about time travel"
5. Calendar: "Create a reminder to call the dentist tomorrow"
6. Code: "Debug this Python code that's throwing an exception"

### Collaboration Test Cases
1. Research + Code: "Research Python best practices and write example code"
2. Creative + Calendar: "Brainstorm story ideas and schedule writing time"

## Continuous Improvement

**When to Update Tests:**
- Adding new expert agents → Add test cases for new agent types
- Changing routing logic → Update min_score thresholds
- Improving prompts → Re-run eval tests to measure impact
- Modifying capabilities → Update expected agent names

**Monitoring:**
- Unit tests must pass before committing
- Eval tests should pass before releasing
- Track LangSmith scores to detect quality regressions
