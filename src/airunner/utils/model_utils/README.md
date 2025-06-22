# Model Utils

This module provides utility functions for determining the correct storage path for Stable Diffusion and related model files in AI Runner.

## Functions

- `get_stable_diffusion_model_storage_path(filename: str) -> str`
  - Returns the absolute path where a model file should be stored in the AI Runner folder. Uses `AIRUNNER_ART_MODEL_PATH` from settings if set, otherwise defaults to `~/.ai_runner/models`.

## Usage

```python
from airunner.utils.model_utils.model_utils import get_stable_diffusion_model_storage_path

model_path = get_stable_diffusion_model_storage_path("my_model.safetensors")
```
