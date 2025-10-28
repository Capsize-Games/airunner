"""Mixin providing image-related property access with layer composition."""

from typing import Optional

from PIL import Image


class ImagePropertyMixin:
    """Provides @property access to composed and single-layer images."""

    @property
    def drawing_pad_image(self) -> Optional[Image.Image]:
        """Get composed image from all visible layers for drawing pad.

        Returns:
            PIL Image composed from visible layers, or single layer fallback.
        """
        from airunner.components.art.utils.layer_compositor import (
            layer_compositor,
        )
        from airunner.utils.image import convert_binary_to_image

        composed_image = layer_compositor.compose_visible_layers(
            target_size=self._get_target_image_size()
        )
        if composed_image is not None:
            return composed_image.convert("RGB")

        base_64_image = self.drawing_pad_settings.image
        image = convert_binary_to_image(base_64_image)
        if image is not None:
            image = image.convert("RGB")
        return image

    @property
    def drawing_pad_mask(self) -> Optional[Image.Image]:
        """Get drawing pad mask image."""
        from airunner.utils.image import convert_binary_to_image

        base_64_image = self.drawing_pad_settings.mask
        image = convert_binary_to_image(base_64_image)
        if image is not None:
            image = image.convert("RGB")
        return image

    @property
    def img2img_image(self) -> Optional[Image.Image]:
        """Get composed image from all visible layers for img2img.

        Returns:
            PIL Image composed from visible layers, or single layer fallback.
        """
        from airunner.components.art.utils.layer_compositor import (
            layer_compositor,
        )
        from airunner.utils.image import convert_binary_to_image

        composed_image = layer_compositor.compose_visible_layers(
            target_size=self._get_target_image_size()
        )
        if composed_image is not None:
            return composed_image.convert("RGB")

        base_64_image = self.image_to_image_settings.image
        image = convert_binary_to_image(base_64_image)
        if image is not None:
            image = image.convert("RGB")
        return image

    @property
    def controlnet_image(self) -> Optional[Image.Image]:
        """Get composed image from all visible layers for controlnet.

        Returns:
            PIL Image composed from visible layers, or single layer fallback.
        """
        from airunner.components.art.utils.layer_compositor import (
            layer_compositor,
        )
        from airunner.utils.image import convert_binary_to_image

        composed_image = layer_compositor.compose_visible_layers(
            target_size=self._get_target_image_size()
        )
        if composed_image is not None:
            return composed_image.convert("RGB")

        base_64_image = self.controlnet_settings.image
        image = convert_binary_to_image(base_64_image)
        if image is not None:
            image = image.convert("RGB")
        return image

    @property
    def controlnet_generated_image(self) -> Optional[Image.Image]:
        """Get ControlNet-generated imported image."""
        from airunner.utils.image import convert_binary_to_image

        base_64_image = self.controlnet_settings.imported_image_base64
        image = convert_binary_to_image(base_64_image)
        if image is not None:
            image = image.convert("RGB")
        return image

    @property
    def outpaint_mask(self) -> Optional[Image.Image]:
        """Get outpaint mask image."""
        from airunner.utils.image import convert_binary_to_image

        base_64_image = self.drawing_pad_settings.mask
        image = convert_binary_to_image(base_64_image)
        if image is not None:
            image = image.convert("RGB")
        return image

    @property
    def outpaint_image(self) -> Optional[Image.Image]:
        """Get composed image from all visible layers for outpaint.

        Returns:
            PIL Image composed from visible layers, or single layer fallback.
        """
        from airunner.components.art.utils.layer_compositor import (
            layer_compositor,
        )
        from airunner.utils.image import convert_binary_to_image

        composed_image = layer_compositor.compose_visible_layers(
            target_size=self._get_target_image_size()
        )
        if composed_image is not None:
            return composed_image.convert("RGB")

        base_64_image = self.outpaint_settings.image
        image = convert_binary_to_image(base_64_image)
        if image is not None:
            image = image.convert("RGB")
        return image
