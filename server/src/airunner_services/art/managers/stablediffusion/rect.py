"""Service-owned rectangle helper for image generation responses."""

from dataclasses import dataclass


@dataclass
class Rect:
    """Simple rectangle container used by art request and response types."""

    x: int
    y: int
    width: int
    height: int

    def left(self) -> int:
        """Return the x-coordinate of the left edge."""
        return self.x

    def top(self) -> int:
        """Return the y-coordinate of the top edge."""
        return self.y

    def translate(self, x: int, y: int):
        """Translate the rectangle by the given x and y offsets."""
        self.x += x
        self.y += y
