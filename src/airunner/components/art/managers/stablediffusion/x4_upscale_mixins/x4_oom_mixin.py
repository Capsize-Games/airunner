"""
OOM handling helpers extracted from core mixin.
"""



class X4OOMMixin:
    def _reduce_batch_size_if_possible(
        self,
        current_batch_size,
        image,
        current_tile_size,
        reductions_remaining,
    ):
        """Reduce batch size on OOM if possible and return updated state."""
        if current_batch_size > 1:
            current_batch_size = max(1, current_batch_size // 2)
            self.logger.warning(
                "OOM during tiled upscale; reducing batch size to %d",
                current_batch_size,
            )
            return (
                current_batch_size,
                current_tile_size,
                reductions_remaining,
                self._build_tiles(
                    image, current_tile_size, overlap=self.TILE_OVERLAP
                ),
                None,
                0,
                None,
            )
        return None

    def _reduce_tile_size_if_possible(
        self,
        current_batch_size,
        current_tile_size,
        reductions_remaining,
        image,
        overlap,
    ):
        """Reduce tile size on OOM if possible and return updated state."""
        if current_tile_size > self.MIN_TILE_SIZE and reductions_remaining > 0:
            reductions_remaining -= 1
            current_tile_size = max(self.MIN_TILE_SIZE, current_tile_size // 2)
            self.logger.warning(
                "OOM persists; reducing tile size to %d", current_tile_size
            )

            tiles, total_tiles, output = self._create_smaller_tiles_and_output(
                image, current_tile_size, overlap
            )

            return (
                self.DEFAULT_TILE_BATCH_SIZE,
                current_tile_size,
                reductions_remaining,
                tiles,
                total_tiles,
                0,
                output,
            )

        return None
