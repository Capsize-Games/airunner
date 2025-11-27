from airunner.components.vision.managers.qwen_vl_model_manager import (
    QwenVLModelManager,
)

# Legacy alias for backwards compatibility
BlipModelManager = QwenVLModelManager

__all__ = ["QwenVLModelManager", "BlipModelManager"]
