"""
Smoke tests for BaseDiffusersModelManager refactoring.

These tests verify that the mixin extraction was successful and all methods
are accessible via the Method Resolution Order (MRO).
"""

import pytest


def test_all_imports_work():
    """Test that all mixin imports work correctly."""
    from airunner.components.art.managers.stablediffusion.mixins import (
        SDPropertiesMixin,
        SDPipelineManagementMixin,
        SDModelLoadingMixin,
        SDModelUnloadingMixin,
        SDMemoryManagementMixin,
        SDGenerationPreparationMixin,
        SDImageGenerationMixin,
    )

    assert SDPropertiesMixin is not None
    assert SDPipelineManagementMixin is not None
    assert SDModelLoadingMixin is not None
    assert SDModelUnloadingMixin is not None
    assert SDMemoryManagementMixin is not None
    assert SDGenerationPreparationMixin is not None
    assert SDImageGenerationMixin is not None


def test_base_diffusers_model_manager_imports():
    """Test that BaseDiffusersModelManager imports successfully."""
    from airunner.components.art.managers.stablediffusion.base_diffusers_model_manager import (
        BaseDiffusersModelManager,
    )

    assert BaseDiffusersModelManager is not None


def test_mro_correct():
    """Test that Method Resolution Order includes all mixins."""
    from airunner.components.art.managers.stablediffusion.base_diffusers_model_manager import (
        BaseDiffusersModelManager,
    )

    mro = BaseDiffusersModelManager.__mro__
    mro_classes = [cls.__name__ for cls in mro]

    # Verify all mixins are in MRO
    assert "SDPropertiesMixin" in mro_classes
    assert "SDPipelineManagementMixin" in mro_classes
    assert "SDModelLoadingMixin" in mro_classes
    assert "SDModelUnloadingMixin" in mro_classes
    assert "SDMemoryManagementMixin" in mro_classes
    assert "SDGenerationPreparationMixin" in mro_classes
    assert "SDImageGenerationMixin" in mro_classes
    assert "BaseModelManager" in mro_classes


def test_properties_accessible():
    """Test that property methods from SDPropertiesMixin are accessible."""
    from airunner.components.art.managers.stablediffusion.base_diffusers_model_manager import (
        BaseDiffusersModelManager,
    )

    # Check that property methods exist
    assert hasattr(BaseDiffusersModelManager, "hardware_profiler")
    assert hasattr(BaseDiffusersModelManager, "controlnet")
    assert hasattr(BaseDiffusersModelManager, "scheduler")
    assert hasattr(BaseDiffusersModelManager, "pipeline")
    assert hasattr(BaseDiffusersModelManager, "model_path")
    assert hasattr(BaseDiffusersModelManager, "is_txt2img")
    assert hasattr(BaseDiffusersModelManager, "is_img2img")
    assert hasattr(BaseDiffusersModelManager, "is_inpaint")
    assert hasattr(BaseDiffusersModelManager, "is_outpaint")
    assert hasattr(BaseDiffusersModelManager, "use_compel")
    assert hasattr(BaseDiffusersModelManager, "generator")
    assert hasattr(BaseDiffusersModelManager, "lora_scale")
    assert hasattr(BaseDiffusersModelManager, "data_type")


def test_pipeline_methods_accessible():
    """Test that pipeline management methods are accessible."""
    from airunner.components.art.managers.stablediffusion.base_diffusers_model_manager import (
        BaseDiffusersModelManager,
    )

    assert hasattr(BaseDiffusersModelManager, "_swap_pipeline")
    assert hasattr(BaseDiffusersModelManager, "_set_pipe")
    assert hasattr(BaseDiffusersModelManager, "_move_pipe_to_device")
    assert hasattr(BaseDiffusersModelManager, "_send_pipeline_loaded_signal")
    assert hasattr(BaseDiffusersModelManager, "_unload_pipe")


def test_loading_methods_accessible():
    """Test that model loading methods are accessible."""
    from airunner.components.art.managers.stablediffusion.base_diffusers_model_manager import (
        BaseDiffusersModelManager,
    )

    assert hasattr(BaseDiffusersModelManager, "_load_controlnet_model")
    assert hasattr(BaseDiffusersModelManager, "_load_lora")
    assert hasattr(BaseDiffusersModelManager, "_load_embeddings")
    assert hasattr(BaseDiffusersModelManager, "_load_embedding")
    assert hasattr(BaseDiffusersModelManager, "_load_compel")
    assert hasattr(BaseDiffusersModelManager, "_load_deep_cache")
    assert hasattr(BaseDiffusersModelManager, "_load_scheduler")
    assert hasattr(BaseDiffusersModelManager, "_load_lora_weights")
    assert hasattr(
        BaseDiffusersModelManager, "_load_textual_inversion_manager"
    )
    assert hasattr(BaseDiffusersModelManager, "_load_compel_proc")


def test_unloading_methods_accessible():
    """Test that model unloading methods are accessible."""
    from airunner.components.art.managers.stablediffusion.base_diffusers_model_manager import (
        BaseDiffusersModelManager,
    )

    assert hasattr(BaseDiffusersModelManager, "_unload_controlnet")
    assert hasattr(BaseDiffusersModelManager, "_unload_loras")
    assert hasattr(BaseDiffusersModelManager, "_unload_lora")
    assert hasattr(BaseDiffusersModelManager, "_unload_emebeddings")
    assert hasattr(BaseDiffusersModelManager, "_unload_embedding")
    assert hasattr(BaseDiffusersModelManager, "_unload_compel")
    assert hasattr(BaseDiffusersModelManager, "_unload_deep_cache")
    assert hasattr(BaseDiffusersModelManager, "_unload_scheduler")
    assert hasattr(BaseDiffusersModelManager, "_unload_generator")


def test_memory_methods_accessible():
    """Test that memory management methods are accessible."""
    from airunner.components.art.managers.stablediffusion.base_diffusers_model_manager import (
        BaseDiffusersModelManager,
    )

    assert hasattr(BaseDiffusersModelManager, "_make_memory_efficient")
    assert hasattr(BaseDiffusersModelManager, "_apply_memory_setting")
    assert hasattr(BaseDiffusersModelManager, "_apply_last_channels")
    assert hasattr(BaseDiffusersModelManager, "_apply_vae_slicing")
    assert hasattr(BaseDiffusersModelManager, "_apply_attention_slicing")
    assert hasattr(BaseDiffusersModelManager, "_apply_tiled_vae")
    assert hasattr(
        BaseDiffusersModelManager, "_apply_accelerated_transformers"
    )
    assert hasattr(BaseDiffusersModelManager, "_apply_cpu_offload")
    assert hasattr(BaseDiffusersModelManager, "_apply_model_offload")
    assert hasattr(BaseDiffusersModelManager, "_apply_tome")
    assert hasattr(BaseDiffusersModelManager, "_remove_tome_sd")
    assert hasattr(
        BaseDiffusersModelManager, "_clear_memory_efficient_settings"
    )


def test_generation_prep_methods_accessible():
    """Test that generation preparation methods are accessible."""
    from airunner.components.art.managers.stablediffusion.base_diffusers_model_manager import (
        BaseDiffusersModelManager,
    )

    assert hasattr(BaseDiffusersModelManager, "_prepare_data")
    assert hasattr(BaseDiffusersModelManager, "_prepare_compel_data")
    assert hasattr(BaseDiffusersModelManager, "_build_conditioning_tensors")
    assert hasattr(BaseDiffusersModelManager, "_resize_image")
    assert hasattr(BaseDiffusersModelManager, "_set_seed")
    assert hasattr(BaseDiffusersModelManager, "_is_sde_scheduler")
    assert hasattr(BaseDiffusersModelManager, "_prepare_sde_noise_sampler")


def test_generation_methods_accessible():
    """Test that image generation methods are accessible."""
    from airunner.components.art.managers.stablediffusion.base_diffusers_model_manager import (
        BaseDiffusersModelManager,
    )

    assert hasattr(BaseDiffusersModelManager, "handle_generate_signal")
    assert hasattr(BaseDiffusersModelManager, "_generate")
    assert hasattr(BaseDiffusersModelManager, "_get_results")
    assert hasattr(BaseDiffusersModelManager, "interrupt_image_generation")
    assert hasattr(BaseDiffusersModelManager, "_callback")
    # __interrupt_callback was removed - interrupt handled differently now


def test_coordination_methods_accessible():
    """Test that coordination methods remain in main class."""
    from airunner.components.art.managers.stablediffusion.base_diffusers_model_manager import (
        BaseDiffusersModelManager,
    )

    # These should be in the main class, not mixins
    assert hasattr(BaseDiffusersModelManager, "load")
    assert hasattr(BaseDiffusersModelManager, "unload")
    assert hasattr(BaseDiffusersModelManager, "reload")
    assert hasattr(BaseDiffusersModelManager, "reload_lora")
    assert hasattr(BaseDiffusersModelManager, "reload_embeddings")
    assert hasattr(BaseDiffusersModelManager, "load_embeddings")
    assert hasattr(BaseDiffusersModelManager, "_load_pipe")
    assert hasattr(BaseDiffusersModelManager, "_set_lora_adapters")
    assert hasattr(
        BaseDiffusersModelManager, "_finalize_load_stable_diffusion"
    )


def test_helper_class_exists():
    """Test that DeterministicSDENoiseSampler helper class still exists."""
    from airunner.components.art.managers.stablediffusion.noise_sampler import (
        DeterministicSDENoiseSampler,
    )

    assert DeterministicSDENoiseSampler is not None
    assert hasattr(DeterministicSDENoiseSampler, "__call__")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
