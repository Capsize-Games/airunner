"""Tests for canvas image-request construction."""

from types import SimpleNamespace
from unittest.mock import Mock, PropertyMock, patch

from PIL import Image

from airunner.components.art.api import canvas_services as module
from airunner.components.art.api.canvas_services import CanvasAPIService
from airunner.enums import GeneratorSection


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