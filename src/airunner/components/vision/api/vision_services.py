"""
Vision API Service for image captioning and tagging.

Provides a high-level interface for the Qwen2.5-VL vision model.
"""

import base64
import io
from typing import Dict, List, Any, Optional, Union

from PIL import Image

from airunner.components.application.api.api_service_base import APIServiceBase
from airunner.utils.application.get_logger import get_logger


class VisionAPIService(APIServiceBase):
    """
    API service for vision-related operations.
    
    Provides methods for image captioning, visual Q&A, and tag generation
    using the Qwen2.5-VL model.
    """

    def __init__(self):
        """Initialize the Vision API service."""
        super().__init__()
        self.logger = get_logger(__name__)
        self._model_manager = None

    @property
    def model_manager(self):
        """Lazy-load the Qwen2.5-VL model manager."""
        if self._model_manager is None:
            from airunner.components.vision.managers.qwen_vl_model_manager import (
                QwenVLModelManager,
            )
            self._model_manager = QwenVLModelManager()
        return self._model_manager

    def _decode_image(
        self,
        image_data: Union[str, bytes, Image.Image],
    ) -> Optional[Image.Image]:
        """
        Decode image from various formats.
        
        Args:
            image_data: Base64 string, bytes, or PIL Image.
            
        Returns:
            PIL Image or None if decoding fails.
        """
        try:
            if isinstance(image_data, Image.Image):
                return image_data
            
            if isinstance(image_data, str):
                # Assume base64 encoded
                # Handle data URL format
                if "base64," in image_data:
                    image_data = image_data.split("base64,")[1]
                image_bytes = base64.b64decode(image_data)
            elif isinstance(image_data, bytes):
                image_bytes = image_data
            else:
                self.logger.error(f"Unsupported image format: {type(image_data)}")
                return None

            return Image.open(io.BytesIO(image_bytes))
        except Exception as e:
            self.logger.error(f"Failed to decode image: {e}")
            return None

    def caption(
        self,
        image: Union[str, bytes, Image.Image],
        max_tokens: int = 50,
    ) -> str:
        """
        Generate a caption for an image.
        
        Args:
            image: Image as base64 string, bytes, or PIL Image.
            max_tokens: Maximum tokens to generate.
            
        Returns:
            Caption string.
        """
        pil_image = self._decode_image(image)
        if pil_image is None:
            return ""
        return self.model_manager.generate_caption(pil_image, max_tokens)

    def answer(
        self,
        image: Union[str, bytes, Image.Image],
        question: str,
        max_tokens: int = 50,
    ) -> str:
        """
        Answer a question about an image (VQA).
        
        Args:
            image: Image as base64 string, bytes, or PIL Image.
            question: Question about the image.
            max_tokens: Maximum tokens to generate.
            
        Returns:
            Answer string.
        """
        pil_image = self._decode_image(image)
        if pil_image is None:
            return ""
        return self.model_manager.answer_question(pil_image, question, max_tokens)

    def tags(
        self,
        image: Union[str, bytes, Image.Image],
        max_tags: int = 10,
    ) -> List[str]:
        """
        Generate tags for an image.
        
        Args:
            image: Image as base64 string, bytes, or PIL Image.
            max_tags: Maximum number of tags.
            
        Returns:
            List of tag strings.
        """
        pil_image = self._decode_image(image)
        if pil_image is None:
            return []
        return self.model_manager.generate_tags(pil_image, max_tags)

    def analyze(
        self,
        image: Union[str, bytes, Image.Image],
        max_tags: int = 10,
    ) -> Dict[str, Any]:
        """
        Perform full image analysis.
        
        Args:
            image: Image as base64 string, bytes, or PIL Image.
            max_tags: Maximum number of tags.
            
        Returns:
            Dictionary with 'caption' and 'tags' keys.
        """
        pil_image = self._decode_image(image)
        if pil_image is None:
            return {"caption": "", "tags": []}
        return self.model_manager.analyze_image(pil_image, max_tags)

    def load_model(self) -> bool:
        """
        Load the vision model.
        
        Returns:
            True if model loaded successfully.
        """
        return self.model_manager.load()

    def unload_model(self):
        """Unload the vision model to free resources."""
        self.model_manager.unload()

    def is_loaded(self) -> bool:
        """Check if the vision model is loaded."""
        return self.model_manager.vision_is_loaded
