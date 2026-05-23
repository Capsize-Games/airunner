"""Z-Image model manager package."""

__all__ = ["ZImageModelManager"]


def __getattr__(name):
    if name == "ZImageModelManager":
        from airunner_services.art.managers.zimage.zimage_model_manager import (
            ZImageModelManager,
        )

        return ZImageModelManager
    raise AttributeError(f"module {__name__} has no attribute {name}")
