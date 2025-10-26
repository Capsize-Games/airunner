"""
Tiling mixin for X4UpscaleManager.

This mixin handles tile building and pasting for large image upscaling
operations that need to be processed in smaller chunks.
"""

from typing import Dict, List, Tuple, Union

from PIL import Image


class X4TilingMixin:
    """Tile building and pasting for X4UpscaleManager."""

    TILE_OVERLAP = 32
    SCALE_FACTOR = 4

    def _build_tiles(
        self, image: Image.Image, tile_size: int, overlap: int
    ) -> List[Dict[str, Union[Tuple[int, int, int, int], Image.Image]]]:
        """Build list of tiles for processing large images.

        Divides image into overlapping tiles of specified size for
        processing in batches to manage memory usage.

        Args:
            image: Source PIL Image to tile.
            tile_size: Size of each tile (width and height).
            overlap: Number of pixels to overlap between adjacent tiles.

        Returns:
            List of dictionaries, each containing:
                - 'box': Source bounding box (left, top, right, bottom)
                - 'crop': Cropped PIL Image for this tile
        """
        width, height = image.size
        step = max(1, tile_size - overlap)
        tiles: List[
            Dict[str, Union[Tuple[int, int, int, int], Image.Image]]
        ] = []

        for top in range(0, height, step):
            bottom = min(top + tile_size, height)
            top = max(0, bottom - tile_size)

            for left in range(0, width, step):
                right = min(left + tile_size, width)
                left = max(0, right - tile_size)

                crop = image.crop((left, top, right, bottom))
                tiles.append({"box": (left, top, right, bottom), "crop": crop})

        return tiles

    @staticmethod
    def _paste_tile(
        canvas: Image.Image,
        tile: Image.Image,
        source_box: Tuple[int, int, int, int],
        scale_factor: int,
    ):
        """Paste upscaled tile onto canvas at scaled coordinates.

        Handles alpha channel compositing and ensures proper RGB conversion.
        Falls back gracefully on errors.

        Args:
            canvas: Destination PIL Image to paste into.
            tile: Upscaled tile to paste.
            source_box: Original tile coordinates (left, top, right, bottom).
            scale_factor: Upscale multiplier (typically 4).
        """
        left, top, right, bottom = source_box
        dest_box = (
            left * scale_factor,
            top * scale_factor,
            right * scale_factor,
            bottom * scale_factor,
        )

        try:
            # Choose composite or simple paste based on alpha presence
            if "A" in tile.getbands():
                X4TilingMixin._paste_tile_composite(canvas, tile, dest_box)
            else:
                X4TilingMixin._paste_tile_simple(canvas, tile, dest_box)
        except Exception:
            # Best-effort paste on error
            try:
                canvas.paste(tile, dest_box)
            except Exception:
                pass

    @staticmethod
    def _paste_tile_composite(
        canvas: Image.Image,
        tile: Image.Image,
        dest_box: Tuple[int, int, int, int],
    ):
        """Paste an RGBA tile onto the canvas using alpha compositing.

        Falls back to mask-based paste when alpha_composite fails.
        """
        try:
            tile_rgba = tile.convert("RGBA")
            white_bg = Image.new("RGBA", tile_rgba.size, (255, 255, 255, 255))
            composed = Image.alpha_composite(white_bg, tile_rgba).convert(
                "RGB"
            )
            canvas.paste(composed, dest_box)
        except Exception:
            mask = tile.split()[-1]
            canvas.paste(tile.convert("RGBA"), dest_box, mask)

    @staticmethod
    def _paste_tile_simple(
        canvas: Image.Image,
        tile: Image.Image,
        dest_box: Tuple[int, int, int, int],
    ):
        """Paste a non-alpha tile onto the canvas after RGB conversion."""
        canvas.paste(tile.convert("RGB"), dest_box)
