from typing import List, Optional, Any, Dict
from PIL.Image import Image
from dataclasses import dataclass
from airunner.handlers.stablediffusion.rect import Rect


@dataclass
class ImageResponse:
    """
    Represents the response for an image generation request.

    Attributes:
        images: A list of generated images.
        data: Additional metadata related to the image generation.
        nsfw_content_detected: Flag indicating if NSFW content was detected.
        active_rect: The active rectangular region in the image.
        is_outpaint: Flag indicating if the image is an outpainting.
    """

    images: Optional[List[Image]]
    data: Dict[str, Any]
    nsfw_content_detected: bool
    active_rect: Rect
    is_outpaint: bool
    node_id: Optional[str] = None

    def to_dict(self) -> Dict:
        """
        Convert the ImageResponse object to a dictionary.

        :return: A dictionary representation of the ImageResponse.
        """
        return {
            "images": self.images,
            "data": self.data,
            "nsfw_content_detected": self.nsfw_content_detected,
            "active_rect": {
                "x": self.active_rect.x,
                "y": self.active_rect.y,
                "width": self.active_rect.width,
                "height": self.active_rect.height,
            },
            "is_outpaint": self.is_outpaint,
        }
