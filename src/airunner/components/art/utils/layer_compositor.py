"""
Layer composition utilities for combining visible layers into composite images.

This module handles compositing layers within a specified bounding box (typically
the active grid area) for AI generation operations like img2img, inpaint, and outpaint.
"""

from typing import List, Optional, Tuple, Any
from PIL import Image

from airunner.components.art.data.canvas_layer import CanvasLayer
from airunner.components.art.data.drawingpad_settings import DrawingPadSettings
from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger
from airunner.utils.image import convert_binary_to_image


logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


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

    def get_layer_bounds(self, layer_id: int) -> Optional[Tuple[int, int, int, int]]:
        """Get the bounding box (x, y, width, height) of a layer.

        Args:
            layer_id: The layer's database ID.

        Returns:
            Tuple of (x, y, width, height) or None if layer has no image.
        """
        try:
            results = DrawingPadSettings.objects.filter_by(layer_id=layer_id)
            if not results:
                return None
            
            drawing_pad = results[0]
            if not drawing_pad.image:
                return None
            
            layer_image = convert_binary_to_image(drawing_pad.image)
            if layer_image is None:
                return None
            
            x = drawing_pad.x_pos or 0
            y = drawing_pad.y_pos or 0
            width, height = layer_image.size
            
            return (x, y, width, height)
        except Exception as e:
            self.logger.error(f"Error getting layer bounds for layer {layer_id}: {e}")
            return None

    def compose_layers_in_region(
        self,
        region_x: int,
        region_y: int,
        region_width: int,
        region_height: int,
        background_color: str = "white",
    ) -> Optional[Image.Image]:
        """Compose all visible layers within a specified region.

        This method creates a composite image of all visible layers that
        intersect with the specified region (typically the active grid area).
        Each layer is positioned correctly based on its stored coordinates.

        Args:
            region_x: X coordinate of the region's top-left corner.
            region_y: Y coordinate of the region's top-left corner.
            region_width: Width of the region.
            region_height: Height of the region.
            background_color: Background color for the composite image.

        Returns:
            PIL Image of the composed layers within the region, or None if no layers found.
        """
        visible_layers = self.get_visible_layers()

        if not visible_layers:
            self.logger.warning("No visible layers found for composition")
            return None

        # Create base composite image for the region
        composite = Image.new("RGBA", (region_width, region_height), background_color)
        layers_composed = 0

        # Composite each visible layer
        for layer in visible_layers:
            try:
                # Get layer's drawing pad settings for position and image
                results = DrawingPadSettings.objects.filter_by(layer_id=layer.id)
                if not results:
                    continue
                
                drawing_pad = results[0]
                if not drawing_pad.image:
                    continue
                
                layer_image = convert_binary_to_image(drawing_pad.image)
                if layer_image is None:
                    continue

                # Get layer position in canvas coordinates
                layer_x = drawing_pad.x_pos or 0
                layer_y = drawing_pad.y_pos or 0
                layer_width, layer_height = layer_image.size

                # Check if layer intersects with the region
                if (layer_x + layer_width <= region_x or 
                    layer_x >= region_x + region_width or
                    layer_y + layer_height <= region_y or 
                    layer_y >= region_y + region_height):
                    # Layer doesn't intersect with region, skip it
                    continue

                # Convert layer image to RGBA for proper compositing
                if layer_image.mode != "RGBA":
                    layer_image = layer_image.convert("RGBA")

                # Calculate the portion of the layer that's within the region
                # and where it should be placed in the composite
                
                # Source rectangle (in layer coordinates)
                src_left = max(0, region_x - layer_x)
                src_top = max(0, region_y - layer_y)
                src_right = min(layer_width, region_x + region_width - layer_x)
                src_bottom = min(layer_height, region_y + region_height - layer_y)
                
                # Destination position (in composite/region coordinates)
                dst_x = max(0, layer_x - region_x)
                dst_y = max(0, layer_y - region_y)

                # Crop the layer to the intersection area
                cropped_layer = layer_image.crop((src_left, src_top, src_right, src_bottom))

                # Apply layer opacity (convert from 0-100 to 0-255)
                opacity = layer.opacity if layer.opacity is not None else 100
                if opacity < 100:
                    # Reduce alpha channel by opacity factor
                    r, g, b, a = cropped_layer.split()
                    a = a.point(lambda x: int(x * opacity / 100))
                    cropped_layer = Image.merge("RGBA", (r, g, b, a))

                # Paste the cropped layer onto the composite
                composite.alpha_composite(cropped_layer, (dst_x, dst_y))
                layers_composed += 1

                self.logger.debug(
                    f"Composed layer '{layer.name}' at ({dst_x}, {dst_y}) "
                    f"(layer pos: {layer_x}, {layer_y}, opacity: {opacity})"
                )

            except Exception as e:
                self.logger.error(f"Error composing layer '{layer.name}': {e}")
                continue

        if layers_composed > 0:
            self.logger.info(
                f"Successfully composed {layers_composed} layers in region "
                f"({region_x}, {region_y}, {region_width}x{region_height})"
            )
            return composite.convert("RGB")
        else:
            self.logger.warning("No layers were successfully composed in region")
            return None

    def compose_visible_layers(
        self,
        target_size: Tuple[int, int] = None,
        background_color: str = "white",
        use_active_grid_region: bool = True,
    ) -> Optional[Image.Image]:
        """Compose all visible layers into a single image.

        This method supports two modes:
        1. Region-based (default): Uses the active grid area as the composition
           region, properly handling layer positions on the infinite canvas.
        2. Legacy: Resizes all layers to target_size and stacks them at (0,0).

        Args:
            target_size: Target size for the composite image (width, height).
                        If None, uses active grid area size or first layer size.
            background_color: Background color for the composite image.
            use_active_grid_region: If True (default), compose layers within
                        the active grid area bounds with proper positioning.

        Returns:
            PIL Image of the composed layers, or None if no layers found.
        """
        # Try to use region-based composition with active grid area
        if use_active_grid_region:
            try:
                from airunner.components.art.data.active_grid_settings import (
                    ActiveGridSettings,
                )
                from airunner.components.application.data.application_settings import (
                    ApplicationSettings,
                )

                # Get active grid position
                grid_settings = ActiveGridSettings.objects.first()
                app_settings = ApplicationSettings.objects.first()
                
                if grid_settings and app_settings:
                    region_x = grid_settings.pos_x or 0
                    region_y = grid_settings.pos_y or 0
                    region_width = target_size[0] if target_size else (app_settings.working_width or 1024)
                    region_height = target_size[1] if target_size else (app_settings.working_height or 1024)

                    result = self.compose_layers_in_region(
                        region_x=region_x,
                        region_y=region_y,
                        region_width=region_width,
                        region_height=region_height,
                        background_color=background_color,
                    )
                    if result is not None:
                        return result
                    # Fall through to legacy method if no layers in region
            except Exception as e:
                self.logger.warning(
                    f"Could not use active grid region for composition: {e}, "
                    f"falling back to legacy method"
                )

        # Legacy composition method (fallback)
        visible_layers = self.get_visible_layers()

        if not visible_layers:
            self.logger.warning("No visible layers found for composition")
            return None

        # Determine composite image size
        composite_size = target_size
        if composite_size is None:
            # Find the first layer with an image to determine size
            for layer in visible_layers:
                results = DrawingPadSettings.objects.filter_by(layer_id=layer.id)
                if results and results[0].image:
                    layer_image = convert_binary_to_image(results[0].image)
                    if layer_image:
                        composite_size = layer_image.size
                        break

            # Fallback to default size if no layer images found
            if composite_size is None:
                composite_size = (1024, 1024)  # Default size
                self.logger.warning(
                    f"No layer images found, using default size: {composite_size}"
                )

        # Create base composite image
        composite = Image.new("RGB", composite_size, background_color)

        layers_composed = 0

        # Composite each visible layer (legacy mode - no positioning)
        for layer in visible_layers:
            try:
                # Get layer image from DrawingPadSettings
                results = DrawingPadSettings.objects.filter_by(layer_id=layer.id)
                if not results or not results[0].image:
                    continue
                
                layer_image = convert_binary_to_image(results[0].image)
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
                    # Legacy mode: paste at (0,0)
                    composite.paste(layer_image, (0, 0))
                    layers_composed += 1

                    self.logger.debug(
                        f"Composed layer '{layer.name}' (opacity: {opacity}) [legacy mode]"
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
