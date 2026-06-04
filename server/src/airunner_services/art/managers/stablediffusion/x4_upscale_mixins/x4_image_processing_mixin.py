"""
Image processing mixin for X4UpscaleManager.

This mixin handles image format conversions, validation, and fallback
operations for the upscaling pipeline.
"""

from typing import Dict, List, Sequence, Union

import numpy as np
import torch
from PIL import Image


class X4ImageProcessingMixin:
    """Image format conversion and processing for X4UpscaleManager."""

    SCALE_FACTOR = 4

    def _is_all_black(self, images: List[Image.Image]) -> bool:
        """Check if all images in list are completely black.

        Used to detect pipeline failures that produce black output,
        triggering bicubic fallback.

        Args:
            images: List of PIL Images to check.

        Returns:
            True if all images are entirely black (all pixels = 0).
        """
        try:
            for img in images:
                arr = np.asarray(img)
                if arr.size and int(arr.max()) > 0:
                    return False
            return True
        except Exception:
            return False

    def _bicubic_fallback(
        self, images: List[Image.Image]
    ) -> List[Image.Image]:
        """Fallback to bicubic upscaling when pipeline fails.

        When pipeline produces black output, use PIL's bicubic
        resampling as a fallback.

        Args:
            images: List of source PIL Images to upscale.

        Returns:
            List of upscaled PIL Images using bicubic interpolation.
        """
        fallback_tiles = []
        for crop in images:
            try:
                w, h = crop.size
                fw, fh = w * self.SCALE_FACTOR, h * self.SCALE_FACTOR
                up = crop.convert("RGB").resize(
                    (fw, fh), resample=Image.BICUBIC
                )
                fallback_tiles.append(up)
            except Exception:
                # White tile on error
                fallback_tiles.append(
                    Image.new("RGB", (fw, fh), (255, 255, 255))
                )
        return fallback_tiles

    def _extract_images(
        self, result: Union[Dict, Sequence[Image.Image], Image.Image]
    ) -> List[Image.Image]:
        """Extract PIL Images from pipeline result.

        Handles different pipeline output formats (dict with 'images',
        object with .images attribute, or direct image(s)).

        Args:
            result: Pipeline output in various possible formats.

        Returns:
            List of PIL Images.
        """
        if isinstance(result, dict) and "images" in result:
            images = result["images"]
        elif hasattr(result, "images"):
            images = result.images
        else:
            images = result

        if isinstance(images, (Image.Image, np.ndarray, torch.Tensor)):
            images = [images]

        return [self._ensure_image(img) for img in images]

    def _ensure_image(
        self, value: Union[Image.Image, np.ndarray, torch.Tensor]
    ) -> Image.Image:
        """Convert various image formats to PIL Image.

        Handles torch tensors, numpy arrays, and PIL Images with proper
        normalization and color space conversion.

        Args:
            value: Image in PIL, numpy, or torch format.

        Returns:
            PIL Image in RGB format.
        """
        # Pass-through for PIL images
        if isinstance(value, Image.Image):
            return value

        # Handle torch tensors
        if torch.is_tensor(value):
            return self._tensor_to_image(value)

        # Handle numpy arrays
        return self._array_to_image(np.asarray(value))

    def _tensor_to_image(self, tensor: torch.Tensor) -> Image.Image:
        """Convert torch tensor to PIL Image.

        Args:
            tensor: Torch tensor (CHW or HWC format).

        Returns:
            PIL Image.
        """
        tensor = tensor.detach().cpu()

        # Convert CHW to HWC if needed
        if tensor.ndim == 3 and tensor.shape[0] in (1, 3, 4):
            tensor = tensor.permute(1, 2, 0)

        # Normalize to 0-255 uint8
        if tensor.dtype.is_floating_point:
            array = self._normalize_float_tensor(tensor)
        else:
            array = tensor.to(torch.uint8).numpy()

        # Promote grayscale to RGB
        if array.ndim == 2:
            array = np.stack([array] * 3, axis=-1)

        return Image.fromarray(array)

    def _normalize_float_tensor(self, tensor: torch.Tensor) -> np.ndarray:
        """Normalize floating-point tensor to uint8 array.

        Args:
            tensor: Float tensor (values in [-1,1] or [0,1] or [0,255]).

        Returns:
            Uint8 numpy array.
        """
        try:
            tmin = float(tensor.min())
            tmax = float(tensor.max())
        except Exception:
            tmin, tmax = 0.0, 1.0

        # Handle [-1,1] range
        if tmin < 0.0 or tmax <= 1.0:
            if tmin < 0.0:
                tensor = (tensor + 1.0) / 2.0
            tensor = tensor.clamp(0.0, 1.0)
            array = (tensor * 255.0).round().to(torch.uint8).numpy()
        else:
            # Assume [0,255] range
            array = tensor.clamp(0.0, 255.0).round().to(torch.uint8).numpy()

        return array

    def _array_to_image(self, array: np.ndarray) -> Image.Image:
        """Convert numpy array to PIL Image.

        Args:
            array: Numpy array (HWC or CHW format).

        Returns:
            PIL Image.
        """
        # Convert CHW to HWC if needed
        if array.ndim == 3 and array.shape[0] in (1, 3, 4):
            array = np.moveaxis(array, 0, -1)

        # Normalize floating-point arrays
        if np.issubdtype(array.dtype, np.floating):
            array = self._normalize_float_array(array)

        # Convert integer types to uint8
        if np.issubdtype(array.dtype, np.integer) and array.dtype != np.uint8:
            array = np.clip(array, 0, 255).astype(np.uint8)

        # Promote grayscale to RGB
        if array.ndim == 2:
            array = np.stack([array] * 3, axis=-1)

        return Image.fromarray(array)

    def _normalize_float_array(self, array: np.ndarray) -> np.ndarray:
        """Normalize floating-point array to uint8.

        Args:
            array: Float numpy array.

        Returns:
            Uint8 numpy array.
        """
        a_min = float(np.nanmin(array)) if array.size else 0.0
        a_max = float(np.nanmax(array)) if array.size else 1.0

        # Handle [-1,1] range
        if a_min < 0.0:
            array = (array + 1.0) / 2.0

        # Scale to 0-255
        if a_max <= 1.5:
            array = np.clip(array, 0.0, 1.0) * 255.0
        else:
            array = np.clip(array, 0.0, 255.0)

        return np.rint(array).astype(np.uint8)

    def _is_image_sequence(
        self, value: Union[Image.Image, Sequence[Image.Image]]
    ) -> bool:
        """Check if value is a sequence of images.

        Args:
            value: Single image or sequence of images.

        Returns:
            True if value is a sequence (but not str/bytes).
        """
        return isinstance(value, Sequence) and not isinstance(
            value, (str, bytes, bytearray)
        )
