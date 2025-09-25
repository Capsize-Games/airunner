"""
Layer composition utilities for combining visible layers into composite images.
"""

from typing import List, Optional, Tuple, Any
import logging
from PIL import Image, ImageDraw

from airunner.components.art.data.canvas_layer import CanvasLayer
from airunner.utils.image import convert_binary_to_image


logger = logging.getLogger(__name__)


class LayerCompositor:
    """Handles composition of canvas layers into single images for AI generation."""

    def __init__(self):
        self.logger = logger

    def get_visible_layers(self) -> List:
        """Get all visible canvas layers ordered by their display order.

        Returns:
            List of visible CanvasLayer objects, ordered from bottom to top.
        """
        try:
            layers = CanvasLayer.objects.order_by("order").all()
            return [layer for layer in layers if layer.visible]
        except Exception as e:
            self.logger.error(f"Error getting visible layers: {e}")
            return []

    def compose_visible_layers(
        self,
        target_size: Tuple[int, int] = None,
        background_color: str = "white",
    ) -> Optional[Image.Image]:
        """Compose all visible layers into a single image.

        Args:
            target_size: Target size for the composite image (width, height).
                        If None, uses the size of the first layer with an image.
            background_color: Background color for the composite image.

        Returns:
            PIL Image of the composed layers, or None if no layers found.
        """
        visible_layers = self.get_visible_layers()

        if not visible_layers:
            self.logger.warning("No visible layers found for composition")
            return None

        # Determine composite image size
        composite_size = target_size
        if composite_size is None:
            # Find the first layer with an image to determine size
            for layer in visible_layers:
                if layer.image:
                    layer_image = convert_binary_to_image(layer.image)
                    if layer_image:
                        composite_size = layer_image.size
                        break

            # Fallback to default size if no layer images found
            if composite_size is None:
                composite_size = (512, 512)  # Default size
                self.logger.warning(
                    f"No layer images found, using default size: {composite_size}"
                )

        # Create base composite image
        composite = Image.new("RGB", composite_size, background_color)

        layers_composed = 0

        # Composite each visible layer
        for layer in visible_layers:
            try:
                if layer.image:
                    layer_image = convert_binary_to_image(layer.image)
                    if layer_image:
                        # Convert to RGB if necessary
                        if layer_image.mode != "RGB":
                            layer_image = layer_image.convert("RGB")

                        # Resize layer image to match composite size if needed
                        if layer_image.size != composite_size:
                            layer_image = layer_image.resize(
                                composite_size, Image.LANCZOS
                            )

                        # Apply layer opacity (convert from 0-100 to 0-1)
                        opacity = (
                            layer.opacity / 100.0
                            if layer.opacity is not None
                            else 1.0
                        )

                        if opacity < 1.0:
                            # Create a transparent version of the layer
                            layer_rgba = layer_image.convert("RGBA")
                            alpha = int(255 * opacity)
                            alpha_layer = Image.new(
                                "RGBA", composite_size, (255, 255, 255, alpha)
                            )
                            layer_image = Image.alpha_composite(
                                Image.new(
                                    "RGBA", composite_size, (0, 0, 0, 0)
                                ),
                                Image.alpha_composite(alpha_layer, layer_rgba),
                            ).convert("RGB")

                        # Composite the layer onto the base image
                        # For now, using simple paste - could be extended with blend modes
                        composite.paste(layer_image, (0, 0))
                        layers_composed += 1

                        self.logger.debug(
                            f"Composed layer '{layer.name}' (opacity: {opacity})"
                        )

            except Exception as e:
                self.logger.error(f"Error composing layer '{layer.name}': {e}")
                continue

        if layers_composed > 0:
            self.logger.info(f"Successfully composed {layers_composed} layers")
            return composite
        else:
            self.logger.warning("No layers were successfully composed")
            return None

    def create_layer_from_image(
        self, image: Image.Image, name: str = None, visible: bool = True
    ) -> Optional[Any]:
        """Create a new canvas layer from a PIL image.

        Args:
            image: PIL Image to create layer from.
            name: Name for the new layer. If None, auto-generates name.
            visible: Whether the layer should be visible by default.

        Returns:
            Layer ID if successful, None otherwise.
        """
        try:
            from airunner.utils.image import convert_image_to_binary

            # Generate layer name if not provided
            if name is None:
                existing_layers = CanvasLayer.objects.all()
                layer_count = len(existing_layers) if existing_layers else 0
                name = f"Generated Layer {layer_count + 1}"

            # Convert image to binary for storage
            image_binary = convert_image_to_binary(image)

            # Determine layer order (place on top)
            existing_layers = CanvasLayer.objects.order_by("order").all()
            max_order = max(
                [layer.order for layer in existing_layers], default=-1
            )

            # Create the new layer
            layer_id = CanvasLayer.objects.create(
                order=max_order + 1,
                name=name,
                visible=visible,
                image=image_binary,
            )

            if layer_id:
                self.logger.info(
                    f"Created new layer '{name}' with ID {layer_id}"
                )
                return layer_id
            else:
                return None

        except Exception as e:
            self.logger.error(f"Error creating layer from image: {e}")
            return None


# Global compositor instance
layer_compositor = LayerCompositor()
