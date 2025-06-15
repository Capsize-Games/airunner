# Agents Module (src/airunner/handlers/llm/agent/agents)

## Purpose
This module contains the core agent classes, prompt configuration, and logic for LLM-based agents in AI Runner.

## PromptConfig Usage
- All prompt templates in `PromptConfig` use Python's `.format()` method for string interpolation.
- **Important:** Each template specifies its required placeholders. For example, `MOOD_UPDATE` requires only `username` and `botname`.
- Do **not** attempt to format these templates with additional keys (e.g., `mood`) unless the template explicitly includes them.

### Example: Correct Usage
```python
prompt = PromptConfig.MOOD_UPDATE.format(username="Alice", botname="Robo")
```

## Common Pitfalls
- **KeyError:** If you attempt to format a prompt with a key not present in the template (e.g., `mood`), a `KeyError` will be raised.
- **Double-formatting:** Do not format a prompt string twice or pass it to another `.format()` call with extra arguments.

## Recent Bug (May 2025)
- A `KeyError: '"mood"'` was raised when formatting `PromptConfig.MOOD_UPDATE`.
- **Root Cause:** The code attempted to format the template with a `mood` key, but the template only expects `username` and `botname`.
- **Resolution:** Ensure only the required keys are passed to `.format()` for each prompt template. See the template definition in `prompt_config.py` for details.

## Best Practices
- Always check the template definition before formatting.
- Update this README if you add or change prompt templates or their required arguments.

---
_Last updated: 2025-05-27_
