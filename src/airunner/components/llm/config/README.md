# Multi-Tier Model Architecture

## Overview

AI Runner uses a **multi-tier model architecture** where different models specialize in different tasks. This provides better performance, lower resource usage, and more reliable tool calling.

### Architecture Layers

```
┌─────────────────────────────────────────────────────────────┐
│                     USER CONVERSATION                        │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              PRIMARY LLM (7-8B Parameters)                   │
│         - Handles conversation                               │
│         - Makes tool calls                                   │
│         - Orchestrates workflow                              │
│         - Examples: Qwen3-8B, Qwen2.5-7B, Ministral3-8B     │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ Tool Calls
                         ▼
┌─────────────────────────────────────────────────────────────┐
│            SPECIALIZED MODELS (2-3B Parameters)              │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐  │
│  │   Qwen2.5    │  │  Qwen2.5     │  │  Qwen2.5        │  │
│  │     3B       │  │  Coder 7B    │  │     3B          │  │
│  ├──────────────┤  ├──────────────┤  ├─────────────────┤  │
│  │   Prompt     │  │     Code     │  │  Summarize      │  │
│  │  Enhancement │  │  Generation  │  │  Translate      │  │
│  └──────────────┘  └──────────────┘  └─────────────────┘  │
│                                                              │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │   FINAL OUTPUTS     │
              │  - Enhanced images  │
              │  - Generated code   │
              │  - Summaries        │
              └─────────────────────┘
```

## How It Works

### 1. User Interaction
- User talks to **Primary LLM** (Qwen2.5-7B)
- Primary LLM understands intent and decides which tools to use

### 2. Tool Execution
- When a tool is called (e.g., `generate_image`), the tool can:
  - Execute directly (simple operations)
  - Load a **specialized model** for complex tasks

### 3. Specialized Model Usage
- Tool loads appropriate specialized model via `LLMModelManager.use_specialized_model()`
- Model Resource Manager handles VRAM swapping
- Specialized model executes task
- Primary model automatically reloads after task completes

## Example Flow

```python
# User says: "Create a dark fantasy dragon"

# 1. Primary LLM (Qwen2.5-7B) processes request
primary_llm.invoke("Create a dark fantasy dragon")

# 2. Primary LLM calls generate_image tool
tool_call = {
    "name": "generate_image",
    "args": {
        "prompt": "dark fantasy dragon",
        "second_prompt": "mysterious atmosphere"
    }
}

# 3. generate_image tool enhances prompt using Qwen2.5-3B
enhanced_prompt = use_specialized_model(
    ModelCapability.PROMPT_ENHANCEMENT,
    "Enhance this: dark fantasy dragon"
)
# Returns: "masterpiece, dark fantasy style, majestic dragon with 
#           iridescent scales, dramatic volumetric lighting, 
#           mystical fog, highly detailed, 8k uhd"

# 4. Tool sends enhanced prompt to Stable Diffusion
stable_diffusion.generate(enhanced_prompt)

# 5. Primary LLM resumes conversation
# User gets: High-quality image + natural response
```

## Model Assignments

### Primary Conversational Models

| Model | Size | Function Calling | Context | Use Case |
|-------|------|------------------|---------|----------|
| **Qwen3-8B** | 8B | ✅ Excellent | 32K (131K YaRN) | **Default** - Supports thinking & instruct modes |
| **Qwen2.5-7B-Instruct** | 7B | ✅ Excellent | 128K | Alternative - great tool calling |
| **Ministral3-8B-Instruct** | 8B | ✅ Native | 256K | Vision + native function calling |

### Specialized Models

| Model | Size | Capability | Use Case |
|-------|------|------------|----------|
| **Qwen2.5-3B-Instruct** | 3B | Prompt Enhancement | Enhance SD prompts |
| **Qwen2.5-3B-Instruct** | 3B | Summarization | Summarize documents |
| **Qwen2.5-3B-Instruct** | 3B | Translation | Translate text |
| **Qwen2.5-Coder-7B** | 7B | Code Generation | 8GB VRAM code model |
| **Qwen3-Coder-30B-A3B** | 30B MoE | Code Generation | SOTA agentic coding |

## Configuration

### Model Registry

Models are defined in `model_capabilities.py`:

```python
from airunner.components.llm.config.model_capabilities import (
    ModelCapability,
    get_model_for_capability,
)

# Get the prompt enhancement model
spec = get_model_for_capability(ModelCapability.PROMPT_ENHANCEMENT)
print(spec.model_path)  # "Qwen/Qwen2.5-3B-Instruct"
print(spec.gpu_memory_gb)  # 2.0
```

### Adding New Models

Edit `model_capabilities.py`:

```python
MODEL_REGISTRY["my-model/path"] = ModelSpec(
    model_path="my-model/path",
    capabilities=[
        ModelCapability.PROMPT_ENHANCEMENT,
    ],
    max_context=32768,
    supports_function_calling=False,
    quantization="4bit",
    gpu_memory_gb=2.5,
    priority=90,
)

CAPABILITY_TO_MODEL[ModelCapability.PROMPT_ENHANCEMENT] = "my-model/path"
```

## Using Specialized Models in Tools

### Method 1: One-Shot Generation

For simple, single-use cases:

```python
from airunner.components.llm.managers.llm_model_manager import LLMModelManager
from airunner.components.llm.config.model_capabilities import ModelCapability

def my_tool(prompt: str, api: Any = None) -> str:
    manager = LLMModelManager()
    
    # Load specialized model, generate, auto-restore primary
    result = manager.use_specialized_model(
        ModelCapability.PROMPT_ENHANCEMENT,
        prompt="Enhance this: " + prompt,
        max_tokens=256,
    )
    
    return result
```

### Method 2: Manual Model Management

For complex multi-step operations:

```python
from airunner.components.llm.managers.llm_model_manager import LLMModelManager
from airunner.components.llm.config.model_capabilities import ModelCapability

def complex_tool(data: dict, api: Any = None) -> str:
    manager = LLMModelManager()
    
    # Load specialized model
    model = manager.load_specialized_model(
        ModelCapability.CODE_GENERATION,
        return_to_primary=True  # Auto-restore after
    )
    
    if not model:
        return "Failed to load code generator"
    
    # Use model multiple times
    result1 = model.invoke("Write a function to...")
    result2 = model.invoke("Now add error handling...")
    
    # Primary model automatically restored when method returns
    return result1 + "\n\n" + result2
```

## Resource Management

### VRAM Usage

All model swapping is handled by `ModelResourceManager`:

- **Automatic VRAM clearing** between model swaps
- **Quantization** (4-bit) keeps models small
- **Smart caching** (future) for frequently-used models

### Example VRAM Requirements

| Scenario | VRAM Usage |
|----------|------------|
| Primary LLM only | ~5 GB |
| Primary + Specialized (swapped) | ~5 GB |
| Primary + Specialized (cached)* | ~7 GB |
| Primary + SD (swapped) | ~6-8 GB |

*Future feature: keep small models in VRAM

## Benefits

### 1. Better Tool Calling
- Primary model (Qwen2.5-7B) has excellent tool calling
- No more "tool schema echo" issues
- Handles 39 tools reliably

### 2. Better Task Performance
- Specialized models excel at their tasks
- Qwen2.5-3B generates better SD prompts than 7B model
- Qwen2.5-Coder generates better code than general LLM

### 3. Lower Resource Usage
- Small specialized models use less VRAM
- Faster inference for simple tasks
- Primary model stays focused on conversation

### 4. Modularity
- Easy to swap specialized models
- Can add new capabilities without touching primary
- Test different models for different tasks

## Migration Guide

### Switching from Single Model

**Before** (single model does everything):
```python
# LLM handles prompt enhancement inline
response = llm.invoke("Enhance this prompt: a cat")
# Model struggles with both tool calling AND enhancement
```

**After** (multi-tier):
```python
# Primary LLM calls tool
tool_call = primary_llm.invoke("Generate image: a cat")

# Tool uses specialized model
enhanced = use_specialized_model(
    ModelCapability.PROMPT_ENHANCEMENT,
    "Enhance: a cat"
)
# Returns: "fluffy white cat, soft fur, detailed whiskers..."
```

### Updating Existing Tools

1. Import capabilities:
   ```python
   from airunner.components.llm.config.model_capabilities import ModelCapability
   ```

2. Use specialized model:
   ```python
   manager = LLMModelManager()
   result = manager.use_specialized_model(
       ModelCapability.PROMPT_ENHANCEMENT,
       prompt,
   )
   ```

3. Add fallback:
   ```python
   if not result:
       result = original_prompt  # Use original on failure
   ```

## Troubleshooting

### "Model not found"
- Ensure model is in `MODEL_REGISTRY`
- Check `CAPABILITY_TO_MODEL` mapping
- Download model from *Tools → Download Models* menu

### "Out of VRAM"
- Models swap automatically
- Check quantization is enabled (4-bit)
- Close other applications

### "Specialized model slow"
- Check model is actually being loaded
- Verify quantization settings
- Consider using smaller model

## Future Enhancements

### Smart Caching
Keep frequently-used small models in VRAM:
```python
# If VRAM > 12GB, cache 3B models
if available_vram > 12:
    keep_in_memory([
        ModelCapability.PROMPT_ENHANCEMENT,
    ])
```

### Multi-GPU Support
Distribute models across GPUs:
```python
# Primary on GPU 0, specialized on GPU 1
assign_device(ModelCapability.PRIMARY_CONVERSATION, "cuda:0")
assign_device(ModelCapability.PROMPT_ENHANCEMENT, "cuda:1")
```

### Capability Auto-Detection
Automatically assign models based on available VRAM:
```python
auto_assign_models(max_vram=8)
# Chooses best models that fit in 8GB
```

## See Also

- `model_capabilities.py` - Model registry
- `llm_model_manager.py` - Model loading implementation
- `image_tools.py` - Example tool using specialized models
- `../api/README.md` - API documentation
