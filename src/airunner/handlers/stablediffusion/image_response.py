from typing import List, Optional, Any, Dict
from PySide6.QtCore import QRect
from PIL.Image import Image
from dataclasses import dataclass, asdict


@dataclass
class ImageResponse:
    images: Optional[List[Image]]
    data: Dict[str, Any]
    nsfw_content_detected: bool
    active_rect: QRect
    is_outpaint: bool

    def to_dict(self) -> Dict:
        return asdict(self)