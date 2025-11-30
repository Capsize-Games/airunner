"""
Reasoning and problem-solving strategy tools for LLM agents.

Provides structured reasoning frameworks like Polya's method for systematic
problem-solving across domains.
"""

from typing import Annotated
from airunner.components.llm.core.tool_registry import tool, ToolCategory


@tool(
    name="polya_reasoning",
    category=ToolCategory.ANALYSIS,
    description="Apply Polya's 4-step problem-solving method for systematic reasoning through complex problems",
    return_direct=False,
    requires_api=False,
)
def polya_reasoning(
    problem: Annotated[str, "The problem statement to analyze"],
    step: Annotated[
        str,
        "Which Polya step: 'understand', 'plan', 'execute', or 'verify'",
    ],
    context: Annotated[
        str,
        "Current work/context from previous steps (empty for first step)",
    ] = "",
) -> str:
    """Guide reasoning through Polya's problem-solving method.

    Polya's 4 steps:
    1. UNDERSTAND: Restate problem, identify knowns/unknowns, constraints
    2. PLAN: Choose strategy, identify needed tools/formulas
    3. EXECUTE: Carry out the plan step-by-step
    4. VERIFY: Check solution, verify it makes sense

    Args:
        problem: The problem to solve
        step: Which step to execute
        context: Work from previous steps

    """
    step = step.lower().strip()

    prompts = {
        "understand": f"""STEP 1 - UNDERSTAND THE PROBLEM:

Problem: {problem}

Please analyze:
1. What is being asked? Restate in your own words.
2. What information is given? (knowns)
3. What do we need to find? (unknowns)
4. What are the constraints or conditions?
5. Can you visualize or diagram the problem?

Provide a clear understanding of the problem before proceeding.""",
        "plan": f"""STEP 2 - DEVISE A PLAN:

Problem: {problem}
Understanding: {context}

Based on your understanding, create a solution strategy:
1. What mathematical concepts/formulas apply?
2. Have you seen a similar problem before?
3. What tools would help? (sympy for algebra, calculus; numpy for numerical methods; python for calculations)
4. What is your step-by-step approach?
5. Can you break it into smaller sub-problems?

Outline your complete plan before executing.""",
        "execute": f"""STEP 3 - CARRY OUT THE PLAN:

Problem: {problem}
Plan: {context}

Now execute your plan:
1. Work through each step systematically
2. Use computation tools where helpful:
   - sympy_compute for symbolic math, equations, exact answers
   - numpy_compute for numerical methods, matrices
   - python_compute for general calculations
3. Show your work clearly
4. If a step fails, revise your plan

Execute the plan and show all work.""",
        "verify": f"""STEP 4 - LOOK BACK AND VERIFY:

Problem: {problem}
Solution: {context}

Check your solution:
1. Does it answer the original question?
2. Is the answer reasonable? (check units, magnitude, sign)
3. Can you verify using a different method?
4. Does it satisfy all constraints?
5. Can you simplify or improve it?

Verify your solution and provide the final answer.""",
    }

    if step not in prompts:
        return f"Error: Unknown step '{step}'. Use: understand, plan, execute, or verify"

    return prompts[step]


@tool(
    name="chain_of_thought",
    category=ToolCategory.ANALYSIS,
    description="Structure reasoning with clear logical steps, showing intermediate thinking",
    return_direct=False,
    requires_api=False,
)
def chain_of_thought(
    problem: Annotated[str, "The problem to reason through"],
    previous_thoughts: Annotated[
        str, "Previous reasoning steps (empty to start)"
    ] = "",
) -> str:
    """Guide step-by-step reasoning with chain of thought.

    Args:
        problem: Problem to solve
        previous_thoughts: Previous reasoning to build on

    """
    if not previous_thoughts:
        return f"""Problem: {problem}

Let's think through this step-by-step:
1. First, what do we know?
2. What is the key insight or approach?
3. What's the next logical step?

Show your reasoning clearly."""
    else:
        return f"""Problem: {problem}

Previous reasoning:
{previous_thoughts}

Continue reasoning:
1. What have we established so far?
2. What's the next logical step?
3. What conclusion can we draw?

Continue your step-by-step reasoning."""
