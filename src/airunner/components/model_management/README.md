# Model Management System

Universal model resource management for AI Runner. Provides centralized hardware detection, quantization selection, model registry, and memory allocation across all model types (LLM, SD, TTS, STT, etc.).

## Architecture

### Components

- **HardwareProfiler**: Detects and monitors system resources (VRAM, RAM, compute capability)
- **QuantizationStrategy**: Selects optimal quantization based on model size and available memory
- **ModelRegistry**: Database of supported models with hardware requirements
- **MemoryAllocator**: Manages VRAM/RAM allocation across all loaded models
- **ModelResourceManager**: Central coordinator for all model operations

### Design Goals

1. **Universal**: Works for all model types (LLM, Stable Diffusion, TTS, STT, Video)
2. **Automatic**: Intelligent model and quantization selection based on hardware
3. **Memory-Safe**: Prevents OOM by tracking allocations
4. **Provider-Agnostic**: Supports multiple providers (Mistral, Llama, etc.)
5. **Extensible**: Easy to add new models and providers

## Usage

### Basic Usage

```python
from airunner.components.model_management import ModelResourceManager
from airunner.components.model_management.model_registry import ModelProvider, ModelType
from airunner.components.model_management.quantization_strategy import QuantizationLevel

# Get singleton instance
manager = ModelResourceManager()

# Auto-select best model for hardware
model = manager.select_best_model(
    provider=ModelProvider.MISTRAL,
    model_type=ModelType.LLM
)

# Prepare for loading with auto quantization
metadata, quantization, allocation = manager.prepare_model_loading(
    model_id="mistralai/Ministral-8B-v0.1"
)

# Or with manual quantization preference
metadata, quantization, allocation = manager.prepare_model_loading(
    model_id="mistralai/Magistral-23B-v0.1",
    preferred_quantization=QuantizationLevel.INT4
)

# After unloading model
manager.cleanup_model(model_id)

# Check memory pressure
if manager.check_memory_pressure():
    # Unload some models
    pass
```

### Adding New Models

```python
from airunner.components.model_management.model_registry import ModelMetadata, ModelProvider, ModelType

metadata = ModelMetadata(
    name="Llama 3.3 70B",
    provider=ModelProvider.LLAMA,
    model_type=ModelType.LLM,
    size_gb=70.0,
    min_vram_gb=24.0,
    min_ram_gb=32.0,
    recommended_vram_gb=40.0,
    recommended_ram_gb=64.0,
    supports_quantization=True,
    huggingface_id="meta-llama/Llama-3.3-70B",
)

manager.model_registry.register_model(metadata)
```

## Integration with Existing Managers

The system is designed to integrate with existing model managers (LLMModelManager, BaseDiffusersModelManager, etc.) by:

1. Replacing direct hardware detection with `HardwareProfiler`
2. Replacing manual quantization logic with `QuantizationStrategy`
3. Using `MemoryAllocator` to track and prevent OOM
4. Using `ModelRegistry` for model metadata and selection

## Future Enhancements

- [ ] Model warmup/preload strategies
- [ ] Timeout-based model cleanup (Ollama-style)
- [ ] Multi-model orchestration
- [ ] Dynamic quantization adjustment based on workload
- [ ] Cross-provider model swapping
