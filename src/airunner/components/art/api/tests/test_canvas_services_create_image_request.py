"""Tests for canvas image-request construction."""

from types import SimpleNamespace
from unittest.mock import Mock, PropertyMock, patch

from PIL import Image

from airunner.components.art.api import canvas_services as module
from airunner.components.art.api.canvas_services import CanvasAPIService
from airunner_model.models.canvas_layer import CanvasLayer
from airunner_model.models.controlnet_settings import ControlnetSettings
from airunner_model.models.drawingpad_settings import DrawingPadSettings
from airunner_model.models.image_to_image_settings import (
    ImageToImageSettings,
)
from airunner_model.models.outpaint_settings import OutpaintSettings
from airunner_model.models.brush_settings import BrushSettings
from airunner_model.models.metadata_settings import MetadataSettings
from airunner.enums import GeneratorSection, SignalCode


def test_create_image_request_uses_img2img_fallback_image(monkeypatch):
    """Img2img requests should carry a real image for Z-Image backends."""
    service = CanvasAPIService.__new__(CanvasAPIService)
    service.logger = Mock()
    fallback_image = Image.new("RGB", (32, 32), "white")

    monkeypatch.setattr(
        module.AIModels,
        "objects",
        SimpleNamespace(
            get=lambda *_args, **_kwargs: None,
            first=lambda *_args, **_kwargs: None,
        ),
        raising=False,
    )

    with patch.object(
        CanvasAPIService,
        "generator_settings",
        new_callable=PropertyMock,
        return_value=SimpleNamespace(
            pipeline_action=GeneratorSection.TXT2IMG.value,
            strength=50,
            scheduler="flow",
            model=None,
            version="z_image",
            prompt="prompt",
            negative_prompt="",
            second_prompt="",
            second_negative_prompt="",
            crops_coords_top_left=None,
            negative_crops_coords_top_left=None,
            random_seed=False,
            use_compel=False,
            steps=10,
            ddim_eta=0,
            scale=100,
            seed=123,
            n_samples=1,
            images_per_batch=1,
            generate_infinite_images=False,
            clip_skip=0,
            target_size=None,
            original_size=None,
            negative_target_size=None,
            negative_original_size=None,
            lora_scale=100,
            custom_path=None,
        ),
    ), patch.object(
        CanvasAPIService,
        "image_to_image_settings",
        new_callable=PropertyMock,
        return_value=SimpleNamespace(enabled=True, strength=100, image=None),
    ), patch.object(
        CanvasAPIService,
        "controlnet_settings",
        new_callable=PropertyMock,
        return_value=SimpleNamespace(
            enabled=False,
            image=None,
            conditioning_scale=0,
            controlnet=None,
        ),
    ), patch.object(
        CanvasAPIService,
        "outpaint_settings",
        new_callable=PropertyMock,
        return_value=SimpleNamespace(enabled=False, strength=0, mask_blur=0),
    ), patch.object(
        CanvasAPIService,
        "application_settings",
        new_callable=PropertyMock,
        return_value=SimpleNamespace(
            working_width=512,
            working_height=512,
            current_image_generator="z_image",
        ),
    ), patch.object(
        CanvasAPIService,
        "img2img_image",
        new_callable=PropertyMock,
        return_value=fallback_image,
    ), patch.object(
        CanvasAPIService,
        "drawing_pad_settings",
        new_callable=PropertyMock,
        return_value=SimpleNamespace(image=None),
    ):
        request = CanvasAPIService.create_image_request(service)

    assert request.generator_section is GeneratorSection.IMG2IMG
    assert request.image is fallback_image
    assert request.strength == 1.0


def test_create_image_request_can_skip_img2img_image_payload(monkeypatch):
    """Metadata-only requests should not compose the live img2img image."""
    service = CanvasAPIService.__new__(CanvasAPIService)
    service.logger = Mock()

    monkeypatch.setattr(
        module.AIModels,
        "objects",
        SimpleNamespace(
            get=lambda *_args, **_kwargs: None,
            first=lambda *_args, **_kwargs: None,
        ),
        raising=False,
    )

    with patch.object(
        CanvasAPIService,
        "generator_settings",
        new_callable=PropertyMock,
        return_value=SimpleNamespace(
            pipeline_action=GeneratorSection.TXT2IMG.value,
            strength=50,
            scheduler="flow",
            model=None,
            version="z_image",
            prompt="prompt",
            negative_prompt="",
            second_prompt="",
            second_negative_prompt="",
            crops_coords_top_left=None,
            negative_crops_coords_top_left=None,
            random_seed=False,
            use_compel=False,
            steps=10,
            ddim_eta=0,
            scale=100,
            seed=123,
            n_samples=1,
            images_per_batch=1,
            generate_infinite_images=False,
            clip_skip=0,
            target_size=None,
            original_size=None,
            negative_target_size=None,
            negative_original_size=None,
            lora_scale=100,
            custom_path=None,
        ),
    ), patch.object(
        CanvasAPIService,
        "image_to_image_settings",
        new_callable=PropertyMock,
        return_value=SimpleNamespace(enabled=True, strength=100, image=None),
    ), patch.object(
        CanvasAPIService,
        "controlnet_settings",
        new_callable=PropertyMock,
        return_value=SimpleNamespace(
            enabled=False,
            image=None,
            conditioning_scale=0,
            controlnet=None,
        ),
    ), patch.object(
        CanvasAPIService,
        "outpaint_settings",
        new_callable=PropertyMock,
        return_value=SimpleNamespace(enabled=False, strength=0, mask_blur=0),
    ), patch.object(
        CanvasAPIService,
        "application_settings",
        new_callable=PropertyMock,
        return_value=SimpleNamespace(
            working_width=512,
            working_height=512,
            current_image_generator="z_image",
        ),
    ), patch.object(
        CanvasAPIService,
        "img2img_image",
        new_callable=PropertyMock,
        side_effect=AssertionError("img2img fallback should not run"),
    ), patch.object(
        CanvasAPIService,
        "drawing_pad_settings",
        new_callable=PropertyMock,
        return_value=SimpleNamespace(image=None),
    ):
        request = CanvasAPIService.create_image_request(
            service,
            include_image_data=False,
        )

    assert request.generator_section is GeneratorSection.IMG2IMG
    assert request.image is None
    assert request.strength == 1.0


def test_create_image_request_uses_controlnet_fallback_image(monkeypatch):
    """ControlNet requests should fall back to the live grid image."""
    service = CanvasAPIService.__new__(CanvasAPIService)
    service.logger = Mock()
    fallback_image = Image.new("RGB", (32, 32), "white")

    monkeypatch.setattr(
        module.AIModels,
        "objects",
        SimpleNamespace(
            get=lambda *_args, **_kwargs: None,
            first=lambda *_args, **_kwargs: None,
        ),
        raising=False,
    )

    with patch.object(
        CanvasAPIService,
        "generator_settings",
        new_callable=PropertyMock,
        return_value=SimpleNamespace(
            pipeline_action=GeneratorSection.TXT2IMG.value,
            strength=50,
            scheduler="flow",
            model=None,
            version="z_image",
            prompt="prompt",
            negative_prompt="",
            second_prompt="",
            second_negative_prompt="",
            crops_coords_top_left=None,
            negative_crops_coords_top_left=None,
            random_seed=False,
            use_compel=False,
            steps=10,
            ddim_eta=0,
            scale=100,
            seed=123,
            n_samples=1,
            images_per_batch=1,
            generate_infinite_images=False,
            clip_skip=0,
            target_size=None,
            original_size=None,
            negative_target_size=None,
            negative_original_size=None,
            lora_scale=100,
            custom_path=None,
        ),
    ), patch.object(
        CanvasAPIService,
        "image_to_image_settings",
        new_callable=PropertyMock,
        return_value=SimpleNamespace(enabled=False, strength=100, image=None),
    ), patch.object(
        CanvasAPIService,
        "controlnet_settings",
        new_callable=PropertyMock,
        return_value=SimpleNamespace(
            enabled=True,
            image=None,
            strength=65,
            conditioning_scale=70,
            controlnet="canny",
        ),
    ), patch.object(
        CanvasAPIService,
        "controlnet_image",
        new_callable=PropertyMock,
        return_value=fallback_image,
    ), patch.object(
        CanvasAPIService,
        "outpaint_settings",
        new_callable=PropertyMock,
        return_value=SimpleNamespace(enabled=False, strength=0, mask_blur=0),
    ), patch.object(
        CanvasAPIService,
        "application_settings",
        new_callable=PropertyMock,
        return_value=SimpleNamespace(
            working_width=512,
            working_height=512,
            current_image_generator="z_image",
        ),
    ), patch.object(
        CanvasAPIService,
        "drawing_pad_settings",
        new_callable=PropertyMock,
        return_value=SimpleNamespace(image=None),
    ):
        request = CanvasAPIService.create_image_request(service)

    assert request.controlnet_enabled is True
    assert request.controlnet_image is fallback_image
    assert request.strength == 0.65


def test_input_image_changed_skips_image_payload_for_enabled_toggle():
    """Enabled toggles should not force synchronous input image composition."""
    service = CanvasAPIService.__new__(CanvasAPIService)
    service.emit_signal = Mock()
    service.create_image_request = Mock(return_value="request")

    CanvasAPIService.input_image_changed(
        service,
        "image_to_image_settings",
        "enabled",
        True,
    )

    service.create_image_request.assert_called_once_with(
        include_image_data=False,
    )
    service.emit_signal.assert_called_once_with(
        SignalCode.INPUT_IMAGE_SETTINGS_CHANGED,
        {
            "section": "image_to_image_settings",
            "setting": "enabled",
            "value": True,
            "image_request": "request",
        },
    )


def test_remove_background_emits_signal():
    """Canvas background-removal requests should emit the worker signal."""
    service = CanvasAPIService.__new__(CanvasAPIService)
    service.emit_signal = Mock()

    CanvasAPIService.remove_background(service)

    service.emit_signal.assert_called_once_with(
        SignalCode.REMOVE_BACKGROUND
    )


def test_create_new_layer_only_creates_layer_scoped_settings():
    """Global brush/metadata settings should not be created per layer."""
    service = CanvasAPIService.__new__(CanvasAPIService)
    service.begin_layer_operation = Mock()
    service.cancel_layer_operation = Mock()
    service.commit_layer_operation = Mock()

    layer = SimpleNamespace(id=1)

    with patch.object(CanvasLayer.objects, "create", return_value=layer):
        with patch.object(DrawingPadSettings.objects, "create") as drawing:
            with patch.object(ControlnetSettings.objects, "create") as controlnet:
                with patch.object(
                    ImageToImageSettings.objects,
                    "create",
                ) as image_to_image:
                    with patch.object(
                        OutpaintSettings.objects,
                        "create",
                    ) as outpaint:
                        with patch.object(
                            BrushSettings.objects,
                            "create",
                        ) as brush_create:
                            with patch.object(
                                MetadataSettings.objects,
                                "create",
                            ) as metadata_create:
                                result = CanvasAPIService.create_new_layer(
                                    service,
                                    order=0,
                                    name="Layer 1",
                                )

    assert result is layer
    drawing.assert_called_once_with(layer_id=1)
    controlnet.assert_called_once_with(layer_id=1)
    image_to_image.assert_called_once_with(layer_id=1)
    outpaint.assert_called_once_with(layer_id=1)
    brush_create.assert_not_called()
    metadata_create.assert_not_called()
    service.commit_layer_operation.assert_called_once_with("create", [1])