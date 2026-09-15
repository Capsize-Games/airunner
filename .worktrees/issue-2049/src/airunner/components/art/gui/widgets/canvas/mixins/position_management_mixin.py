"""Mixin for position management in CustomGraphicsView.

This mixin handles retrieval of original item positions from the database.
"""

from typing import Dict, Optional


class PositionManagementMixin:
    """Provides position management functionality for graphics view.

    This mixin manages:
    - Retrieval of original positions for layer images
    - Database lookup for saved positions
    - Fallback to default positions

    Dependencies:
        - self.session: Database session
        - self.LayerImagePosition: Database model
    """

    def get_layer_position(self, layer_id: int) -> Optional[Dict[str, float]]:
        """Get original saved position for a layer from database.

        Args:
            layer_id: ID of the layer to get position for.

        Returns:
            Dict with x, y coordinates if found, None otherwise.
        """
        if not hasattr(self, "session"):
            return None

        try:
            result = (
                self.session.query(self.LayerImagePosition)
                .filter_by(layer_id=layer_id)
                .first()
            )
            if result:
                return {"x": result.x, "y": result.y}
            return None
        except Exception:
            return None
