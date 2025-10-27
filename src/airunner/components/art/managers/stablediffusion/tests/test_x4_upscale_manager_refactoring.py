"""Lightweight tests for X4 upscaler mixins.

These tests avoid importing the full `x4_upscale_manager` to prevent
circular import issues during collection. They verify that each mixin
exists and exposes expected class attributes or method names.
"""

from airunner.components.art.managers.stablediffusion.x4_upscale_mixins import (
    X4PropertiesMixin,
    X4PipelineSetupMixin,
    X4DataPreparationMixin,
    X4UpscalingCoreMixin,
    X4TilingMixin,
    X4ImageProcessingMixin,
    X4ResponseMixin,
    X4UtilityMixin,
)


def test_mixins_are_classes():
    assert isinstance(X4PropertiesMixin, type)
    assert isinstance(X4PipelineSetupMixin, type)
    assert isinstance(X4DataPreparationMixin, type)
    assert isinstance(X4UpscalingCoreMixin, type)
    assert isinstance(X4TilingMixin, type)
    assert isinstance(X4ImageProcessingMixin, type)
    assert isinstance(X4ResponseMixin, type)
    assert isinstance(X4UtilityMixin, type)


def test_properties_mixin_attributes():
    # Check that expected attribute names exist on the mixin
    for attr in ("use_compel", "preview_dir", "preview_path", "is_loaded"):
        assert hasattr(X4PropertiesMixin, attr)


def test_pipeline_setup_mixin_methods():
    for meth in ("load", "_configure_pipeline", "_prepare_pipe_data"):
        assert hasattr(X4PipelineSetupMixin, meth)


def test_data_prep_mixin_methods():
    for meth in (
        "_prepare_data",
        "_build_request_from_payload",
        "_build_pipeline_kwargs",
    ):
        assert hasattr(X4DataPreparationMixin, meth)


def test_upscaling_core_mixin_methods():
    for meth in (
        "handle_upscale_request",
        "_run_upscale",
        "_single_pass_upscale",
        "_tile_upscale",
    ):
        assert hasattr(X4UpscalingCoreMixin, meth)


def test_tiling_mixin_methods():
    for meth in ("_build_tiles", "_paste_tile"):
        assert hasattr(X4TilingMixin, meth)


def test_image_processing_mixin_methods():
    for meth in ("_extract_images", "_ensure_image", "_is_all_black"):
        assert hasattr(X4ImageProcessingMixin, meth)


def test_response_mixin_methods():
    for meth in ("_emit_failure", "_emit_completed", "_save_preview_image"):
        assert hasattr(X4ResponseMixin, meth)


def test_utility_mixin_methods():
    for meth in ("_empty_cache", "_is_out_of_memory"):
        assert hasattr(X4UtilityMixin, meth)
