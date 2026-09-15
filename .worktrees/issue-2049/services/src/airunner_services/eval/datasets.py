"""
Evaluation datasets for AI Runner testing.

Contains datasets with prompts, reference outputs, and metadata
for testing various LLM capabilities.
"""

from typing import List, Dict, Any


# Math and reasoning dataset
MATH_REASONING_DATASET: List[Dict[str, Any]] = [
    {
        "prompt": "What is 15 + 27?",
        "reference_output": "42",
        "category": "math",
        "difficulty": "easy",
    },
    {
        "prompt": "If a train travels 120 km in 2 hours, what is its average speed in km/h?",
        "reference_output": "60 km/h. The average speed is calculated by dividing the distance (120 km) by the time (2 hours), which equals 60 km/h.",
        "category": "math",
        "difficulty": "medium",
    },
    {
        "prompt": "Solve for x: 2x + 5 = 17",
        "reference_output": "x = 6. Subtract 5 from both sides: 2x = 12, then divide both sides by 2: x = 6.",
        "category": "math",
        "difficulty": "medium",
    },
    {
        "prompt": "A rectangle has a length of 8 cm and width of 5 cm. What is its area?",
        "reference_output": "40 cm². The area of a rectangle is length × width = 8 cm × 5 cm = 40 cm².",
        "category": "math",
        "difficulty": "easy",
    },
]

# General knowledge dataset
GENERAL_KNOWLEDGE_DATASET: List[Dict[str, Any]] = [
    {
        "prompt": "What is the capital of France?",
        "reference_output": "Paris is the capital of France.",
        "category": "geography",
        "difficulty": "easy",
    },
    {
        "prompt": "Explain photosynthesis in one sentence.",
        "reference_output": "Photosynthesis is the process by which plants use sunlight, water, and carbon dioxide to produce oxygen and energy in the form of sugar.",
        "category": "science",
        "difficulty": "medium",
    },
    {
        "prompt": "Who wrote 'Romeo and Juliet'?",
        "reference_output": "William Shakespeare wrote 'Romeo and Juliet'.",
        "category": "literature",
        "difficulty": "easy",
    },
    {
        "prompt": "What are the three states of matter?",
        "reference_output": "The three states of matter are solid, liquid, and gas.",
        "category": "science",
        "difficulty": "easy",
    },
]

# Summarization dataset
SUMMARIZATION_DATASET: List[Dict[str, Any]] = [
    {
        "prompt": "Summarize the following in one sentence: The Industrial Revolution was a period of major industrialization and innovation during the late 1700s and early 1800s. It began in Great Britain and spread to other parts of the world. New manufacturing processes transformed economies that had been based on agriculture and handicrafts into economies based on large-scale industry and mechanized manufacturing.",
        "reference_output": "The Industrial Revolution was a transformative period in the late 1700s and early 1800s when economies shifted from agriculture and handicrafts to large-scale mechanized industry, starting in Great Britain and spreading worldwide.",
        "category": "summarization",
        "difficulty": "medium",
    },
    {
        "prompt": "Summarize this paragraph: Artificial intelligence (AI) refers to computer systems designed to perform tasks that typically require human intelligence. These tasks include visual perception, speech recognition, decision-making, and language translation. AI has applications in many fields including healthcare, finance, transportation, and education.",
        "reference_output": "Artificial intelligence (AI) is computer technology that performs human-like tasks such as perception, recognition, decision-making, and translation, with applications across healthcare, finance, transportation, and education.",
        "category": "summarization",
        "difficulty": "medium",
    },
]

# Coding/technical dataset
CODING_DATASET: List[Dict[str, Any]] = [
    {
        "prompt": "What does the Python 'len()' function do?",
        "reference_output": "The len() function returns the number of items in an object, such as the length of a string, list, tuple, or other sequence.",
        "category": "coding",
        "difficulty": "easy",
    },
    {
        "prompt": "Explain what a Python list comprehension is.",
        "reference_output": "A list comprehension is a concise way to create lists in Python. It consists of square brackets containing an expression followed by a for clause, and optionally if clauses. For example: [x**2 for x in range(10)] creates a list of squares.",
        "category": "coding",
        "difficulty": "medium",
    },
    {
        "prompt": "What is the difference between '==' and '===' in JavaScript?",
        "reference_output": "In JavaScript, '==' checks for value equality with type coercion (converts types if needed), while '===' checks for strict equality, meaning both value and type must be the same.",
        "category": "coding",
        "difficulty": "medium",
    },
]

# Instruction following dataset
INSTRUCTION_FOLLOWING_DATASET: List[Dict[str, Any]] = [
    {
        "prompt": "List three primary colors.",
        "reference_output": "The three primary colors are:\n1. Red\n2. Yellow\n3. Blue",
        "category": "instruction",
        "difficulty": "easy",
    },
    {
        "prompt": "Write a haiku about coding (3 lines: 5-7-5 syllables).",
        "reference_output": "Code flows line by line (5)\nDebugging through the dark night (7)\nSolution shines bright (5)",
        "category": "instruction",
        "difficulty": "hard",
    },
    {
        "prompt": "Provide a numbered list of steps to make a peanut butter sandwich.",
        "reference_output": "1. Get two slices of bread\n2. Get peanut butter and a knife\n3. Spread peanut butter on one slice\n4. Place the second slice on top\n5. Cut in half (optional)",
        "category": "instruction",
        "difficulty": "easy",
    },
]

# Reasoning and logic dataset
REASONING_DATASET: List[Dict[str, Any]] = [
    {
        "prompt": "If all roses are flowers, and some flowers are red, can we conclude that some roses are red?",
        "reference_output": "No, we cannot conclude that some roses are red. While all roses are flowers, we only know that SOME flowers are red, not which ones. The red flowers might not include any roses.",
        "category": "logic",
        "difficulty": "hard",
    },
    {
        "prompt": "You have a 3-gallon jug and a 5-gallon jug. How can you measure exactly 4 gallons?",
        "reference_output": "Fill the 5-gallon jug completely. Pour from the 5-gallon jug into the 3-gallon jug until it's full (leaving 2 gallons in the 5-gallon jug). Empty the 3-gallon jug. Pour the 2 gallons from the 5-gallon jug into the 3-gallon jug. Fill the 5-gallon jug again. Pour from the 5-gallon jug into the 3-gallon jug until it's full (which takes 1 gallon), leaving exactly 4 gallons in the 5-gallon jug.",
        "category": "logic",
        "difficulty": "hard",
    },
]

# Combined dataset for comprehensive testing
ALL_DATASETS = {
    "math_reasoning": MATH_REASONING_DATASET,
    "general_knowledge": GENERAL_KNOWLEDGE_DATASET,
    "summarization": SUMMARIZATION_DATASET,
    "coding": CODING_DATASET,
    "instruction_following": INSTRUCTION_FOLLOWING_DATASET,
    "reasoning": REASONING_DATASET,
}


def get_dataset_by_category(category: str) -> List[Dict[str, Any]]:
    """Get dataset by category name.

    Args:
        category: Dataset category name

    Returns:
        List of test cases

    Raises:
        ValueError: If category not found
    """
    if category not in ALL_DATASETS:
        raise ValueError(
            f"Unknown category: {category}. "
            f"Available: {list(ALL_DATASETS.keys())}"
        )
    return ALL_DATASETS[category]


def get_dataset_by_difficulty(difficulty: str) -> List[Dict[str, Any]]:
    """Get all test cases with specified difficulty.

    Args:
        difficulty: Difficulty level (easy, medium, hard)

    Returns:
        List of test cases matching difficulty
    """
    results = []
    for dataset in ALL_DATASETS.values():
        results.extend(
            [case for case in dataset if case.get("difficulty") == difficulty]
        )
    return results


def get_all_test_cases() -> List[Dict[str, Any]]:
    """Get all test cases from all datasets.

    Returns:
        Combined list of all test cases
    """
    results = []
    for dataset in ALL_DATASETS.values():
        results.extend(dataset)
    return results
