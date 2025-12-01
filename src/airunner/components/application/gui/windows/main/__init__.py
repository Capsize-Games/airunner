# NOTE: Imports moved to lazy loading to avoid circular import issues.
# Import directly from the specific modules instead of from this package.
# e.g., from airunner.components.application.gui.windows.main.model_load_balancer import ModelLoadBalancer

__all__ = ["ModelLoadBalancer", "LLMGeneratorSettings", "WorkerManager"]


def __getattr__(name):
    """Lazy loading to avoid circular imports."""
    if name == "ModelLoadBalancer":
        from airunner.components.application.gui.windows.main.model_load_balancer import (
            ModelLoadBalancer,
        )
        return ModelLoadBalancer
    elif name == "LLMGeneratorSettings":
        from airunner.components.llm.data.llm_generator_settings import (
            LLMGeneratorSettings,
        )
        return LLMGeneratorSettings
    elif name == "WorkerManager":
        from airunner.components.application.gui.windows.main.worker_manager import (
            WorkerManager,
        )
        return WorkerManager
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
