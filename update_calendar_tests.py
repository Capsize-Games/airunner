#!/usr/bin/env python
"""
Script to update test_calendar_tool_eval.py with trajectory tracking.
"""

import re

file_path = "src/airunner/components/eval/tests/test_calendar_tool_eval.py"

# Read the file
with open(file_path, "r") as f:
    content = f.read()

# Pattern 1: Simple response assignment
pattern1 = r"(\s+)response = airunner_client_function_scope\.generate\(\n(\s+)prompt=prompt,\n(\s+)max_tokens=(\d+),\n(\s+)tool_categories=\[([^\]]+)\],\n(\s+)\)"

replacement1 = r"""\1result = track_trajectory_sync(
\1    airunner_client_function_scope,
\1    prompt=prompt,
\1    max_tokens=\4,
\1    tool_categories=[\6],
\1)
\1
\1response = result["response"]
\1trajectory = result["trajectory"]
\1tools = result["tools"]"""

# Pattern 2: Loop response assignment
pattern2 = r"(\s+)response = airunner_client_function_scope\.generate\(\n(\s+)prompt=prompt,\n(\s+)max_tokens=(\d+),\n(\s+)tool_categories=\[([^\]]+)\],\n(\s+)\)"

replacement2 = r"""\1result = track_trajectory_sync(
\1    airunner_client_function_scope,
\1    prompt=prompt,
\1    max_tokens=\4,
\1    tool_categories=[\6],
\1)
\1
\1response = result["response"]
\1tools = result["tools"]"""

# Apply replacements
content = re.sub(pattern1, replacement1, content)

# Update response.get("text", "").lower() to handle both str and dict
content = re.sub(
    r'response\.get\("text", ""\)\.lower\(\)',
    'response.lower() if isinstance(response, str) else response.get("text", "").lower()',
    content,
)

# Write back
with open(file_path, "w") as f:
    f.write(content)

print(f"Updated {file_path}")
