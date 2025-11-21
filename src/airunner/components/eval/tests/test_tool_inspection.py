"""
Inspect tool usage to diagnose why tools hurt performance.

This test runs a single problem with tools and prints the FULL output
to see exactly how the LLM is using (or misusing) the tools.
"""

import logging
import pytest
from airunner.components.llm.core.tool_registry import ToolCategory
from airunner.settings import AIRUNNER_DEFAULT_LLM_HF_PATH

logger = logging.getLogger(__name__)

pytestmark = [
    pytest.mark.benchmark,
    pytest.mark.timeout(120),
]


@pytest.mark.benchmark
def test_inspect_tool_usage(airunner_client):
    """Run a single GSM8K problem with tools and inspect the full output."""

    # ACTUAL Problem 3 from GSM8K dataset:
    problem = """It costs $194 per meter to repave a street. Monica's street is 150 meters long. How much more does it cost to repave Lewis' street, which is 490 meters long?"""

    expected_answer = "65,960"

    print("\n" + "=" * 80)
    print("PROBLEM:")
    print("=" * 80)
    print(problem)
    print(f"\nExpected answer: {expected_answer}")
    print("=" * 80)

    # Test WITHOUT tools (baseline)
    print("\n" + "=" * 80)
    print("TEST 1: NO TOOLS (BASELINE)")
    print("=" * 80)

    prompt_no_tools = f"""Solve this math problem step-by-step:

{problem}

Work through it carefully and provide your final answer in \\boxed{{}} format."""

    response_no_tools = airunner_client.generate(
        prompt_no_tools,
        model=AIRUNNER_DEFAULT_LLM_HF_PATH,
        temperature=0.0,
        max_tokens=4096,
        use_memory=False,
        system_prompt="You are a mathematics expert.",
        tool_categories=[],
    )

    output_no_tools = response_no_tools.get("text", "")
    print("\n--- FULL OUTPUT (NO TOOLS) ---")
    print(output_no_tools)
    print("\n" + "-" * 80)

    # Test WITH MATH tools
    print("\n" + "=" * 80)
    print("TEST 2: WITH MATH TOOLS")
    print("=" * 80)

    prompt_with_tools = f"""Solve this math problem:

{problem}

You have access to computation tools. Use them if helpful.
Provide your final answer in \\boxed{{}} format."""

    response_with_tools = airunner_client.generate(
        prompt_with_tools,
        model=AIRUNNER_DEFAULT_LLM_HF_PATH,
        temperature=0.0,
        max_tokens=4096,
        use_memory=False,
        system_prompt="""You are a mathematics expert.

**AVAILABLE TOOLS:**
- sympy_compute: Symbolic mathematics (equations, algebra, calculus)
- numpy_compute: Numerical computations (matrices, linear algebra)
- python_compute: General calculations

Use tools when they would help verify your work.""",
        tool_categories=[ToolCategory.MATH.value],
    )

    output_with_tools = response_with_tools.get("text", "")
    print("\n--- FULL OUTPUT (WITH TOOLS) ---")
    print(output_with_tools)
    print("\n" + "-" * 80)

    # Check if there are tool_calls in the response
    if "tool_calls" in response_with_tools:
        print("\n--- TOOL CALLS ---")
        print(response_with_tools["tool_calls"])
        print("-" * 80)

    # Compare
    print("\n" + "=" * 80)
    print("COMPARISON")
    print("=" * 80)
    print(f"Expected: {expected_answer}")
    print(f"\nNo tools output length: {len(output_no_tools)} chars")
    print(f"With tools output length: {len(output_with_tools)} chars")

    # Check for tool-related artifacts
    if (
        "sp." in output_with_tools
        or "numpy" in output_with_tools
        or "python_compute" in output_with_tools
    ):
        print("\n⚠️  WARNING: Tool code/artifacts found in output!")

    print("=" * 80)


@pytest.mark.benchmark
def test_inspect_analysis_tool(airunner_client):
    """Test the polya_reasoning tool specifically."""

    problem = """A team of 4 painters worked on a mansion for 3/8ths of a day every day for 3 weeks. How many hours of work did the painters do total?"""

    expected_answer = "189"

    print("\n" + "=" * 80)
    print("PROBLEM:")
    print("=" * 80)
    print(problem)
    print(f"\nExpected answer: {expected_answer}")
    print("=" * 80)

    # Test WITH ANALYSIS tools (polya_reasoning)
    print("\n" + "=" * 80)
    print("TEST: WITH ANALYSIS TOOLS (polya_reasoning)")
    print("=" * 80)

    prompt = f"""Solve this math problem:

{problem}

Use the polya_reasoning tool to guide your thinking.
Provide your final answer in \\boxed{{}} format."""

    response = airunner_client.generate(
        prompt,
        model=AIRUNNER_DEFAULT_LLM_HF_PATH,
        temperature=0.0,
        max_tokens=4096,
        use_memory=False,
        system_prompt="""You are a mathematics expert.

**AVAILABLE TOOLS:**
- polya_reasoning: Structured problem-solving framework

Use the polya_reasoning tool to guide your thinking.""",
        tool_categories=[ToolCategory.ANALYSIS.value],
    )

    output = response.get("text", "")
    print("\n--- FULL OUTPUT ---")
    print(output)
    print("\n" + "-" * 80)

    if "tool_calls" in response:
        print("\n--- TOOL CALLS ---")
        print(response["tool_calls"])
        print("-" * 80)

    print("=" * 80)
